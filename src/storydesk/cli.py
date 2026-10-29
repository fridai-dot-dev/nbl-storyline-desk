"""Command-line entry points, with an explicit guard around subscription-spending runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .data import build_stats_db, raw_connection
from .judge import rejudge
from .runner import copy_pass_live, run_live
from .scorecard import scorecard
from .site import build_site
from .store import Store


OPENER = "36dbeb55-58ad-11f1-a69b-43a6b5595d3e"
_SIMULATED_STANCES = {"push", "use_if_raised", "steer_away"}


def _fetch(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    downloads = {
        "results.csv": "https://github.com/JaseZiv/nblr_data/releases/download/match_results/results_wide.csv",
        "box_team.csv": "https://github.com/JaseZiv/nblr_data/releases/download/box_team/box_team.csv",
        "box_player.csv": "https://github.com/JaseZiv/nblr_data/releases/download/pbp/pbp.csv",
        "match_opener.json": f"https://prod.rosetta.nbl.com.au/get/match/{args.game}/live/all",
    }
    for filename, url in downloads.items():
        headers = {"accept": "*/*", "user-agent": "Mozilla/5.0"}
        if "rosetta" in url:
            headers.update({"origin": "https://nbl.com.au", "referer": "https://nbl.com.au/"})
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response, (out / filename).open("wb") as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
    return 0


def _build_db(args: argparse.Namespace) -> int:
    raw = Path(args.raw_dir)
    matches = list(raw.glob("match*.json"))
    build_stats_db(args.db, results_csv=raw / "results.csv", box_team_csv=raw / "box_team.csv",
                   box_player_csv=raw / "box_player.csv", match_json_paths=matches)
    return 0


def default_as_of(run_type: str, *, stats_db: str | Path, game_id: str) -> str:
    """Return the approved default UTC cutoff for a game and run type."""
    if run_type not in {"pre_game", "post_game", "supplemental", "follow_up", "smoke"}:
        raise ValueError(f"unknown run type: {run_type}")
    con = raw_connection(stats_db)
    try:
        if run_type == "pre_game":
            row = con.execute(
                "SELECT match_time_utc FROM raw_results WHERE CAST(match_id AS VARCHAR) = ? LIMIT 1",
                [str(game_id)],
            ).fetchone()
        else:
            row = con.execute(
                "SELECT end_time FROM match_ends WHERE CAST(match_id AS VARCHAR) = ? LIMIT 1",
                [str(game_id)],
            ).fetchone()
    finally:
        con.close()
    if row is None:
        raise ValueError("no match cutoff is available; pass --as-of")
    cutoff = row[0]
    if isinstance(cutoff, str):
        cutoff = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if run_type == "pre_game":
        cutoff = cutoff - timedelta(hours=3)
    elif run_type == "supplemental":
        cutoff = cutoff + timedelta(minutes=45)
    cutoff = cutoff.replace(microsecond=0)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    else:
        cutoff = cutoff.astimezone(timezone.utc)
    return cutoff.isoformat()


def _run(args: argparse.Namespace) -> int:
    if not args.live:
        raise SystemExit("Refusing to start a model run without --live")
    store = Store(args.store)
    store.init()
    as_of = args.as_of or default_as_of(args.run_type, stats_db=args.stats_db, game_id=args.game)
    run_id = asyncio.run(run_live(
        args.run_type, game_id=args.game, as_of=as_of, stats_db=args.stats_db, store=store,
        corpus_dir=args.corpus, digest_dir=args.digest_dir, question=args.question, anchor_finding_id=args.anchor,
        asked_by=args.asked_by,
    ))
    print(run_id)
    return 0


def _scorecard(args: argparse.Namespace) -> int:
    card = scorecard(Store(args.store), args.stats_db, args.run_id)
    print(json.dumps(card) if args.json else card)
    return 0


def _rejudge(args: argparse.Namespace) -> int:
    if not args.live:
        raise SystemExit("Refusing to re-run the judge without --live")
    store = Store(args.store)
    store.init()
    rejudge(store, args.run_id, stats_db=args.stats_db, corpus_dir=args.corpus)
    print(args.run_id)
    return 0


def _copy_pass(args: argparse.Namespace) -> int:
    if not args.live:
        raise SystemExit("Refusing to run the copy pass without --live")
    store = Store(args.store)
    store.init()
    asyncio.run(copy_pass_live(store, args.run_id))
    print(args.run_id)
    return 0


def _site(args: argparse.Namespace) -> int:
    paths = build_site(Store(args.store), args.stats_db, args.out_dir, game_id=args.game)
    for path in paths:
        print(path)
    return 0


def _simulate(args: argparse.Namespace) -> int:
    """Replace only the labelled simulated collaboration round in one transaction."""
    try:
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read simulated round: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("simulated round must be a JSON object")
    stances, directives = payload.get("stances"), payload.get("directives")
    if not isinstance(stances, list) or not isinstance(directives, list):
        raise ValueError("simulated round needs stances and directives lists")

    checked_stances: list[tuple[int, str, str, str | None]] = []
    checked_directives: list[tuple[str, str, bool, str | None]] = []
    seen_stances: set[tuple[int, str]] = set()
    for item in stances:
        if not isinstance(item, dict):
            raise ValueError("each stance item must be an object")
        finding_id, role, stance, comment = item.get("finding_id"), item.get("role"), item.get("stance"), item.get("comment")
        if not isinstance(finding_id, int) or isinstance(finding_id, bool):
            raise ValueError("stance finding_id must be an integer")
        if not isinstance(role, str) or not role.strip() or stance not in _SIMULATED_STANCES:
            raise ValueError("stance needs a role and an allowed stance")
        if comment is not None and not isinstance(comment, str):
            raise ValueError("stance comment must be a string or null")
        if item.get("simulated") is not True:
            raise ValueError("simulated stances must be labelled simulated")
        key = (finding_id, role.strip())
        if key in seen_stances:
            raise ValueError("simulated round has more than one stance for a role and finding")
        seen_stances.add(key)
        checked_stances.append((finding_id, role.strip(), stance, comment))
    for item in directives:
        if not isinstance(item, dict):
            raise ValueError("each directive item must be an object")
        owner_role, text, mandatory, expires = item.get("owner_role"), item.get("text"), item.get("mandatory", False), item.get("expires")
        if not isinstance(owner_role, str) or not owner_role.strip() or not isinstance(text, str) or not text.strip():
            raise ValueError("directive needs owner_role and text")
        if not isinstance(mandatory, bool) or expires is not None and not isinstance(expires, str):
            raise ValueError("directive mandatory must be boolean and expires must be a string or null")
        checked_directives.append((owner_role, text, mandatory, expires))

    # Resolve every target through a genuinely read-only handle before Store.init
    # is allowed to create, migrate, or otherwise touch the ledger.
    store_path = Path(args.store)
    if not store_path.is_file():
        raise ValueError(f"store does not exist: {store_path}")
    target_ids = {finding_id for finding_id, _role, _stance, _comment in checked_stances}
    try:
        read_only = sqlite3.connect(f"{store_path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            read_only.execute("PRAGMA query_only = ON")
            if target_ids:
                placeholders = ",".join("?" for _ in target_ids)
                found_ids = {
                    int(row[0]) for row in read_only.execute(
                        f"SELECT id FROM findings WHERE id IN ({placeholders})", sorted(target_ids),
                    ).fetchall()
                }
            else:
                read_only.execute("SELECT id FROM findings WHERE 0").fetchall()
                found_ids = set()
        finally:
            read_only.close()
    except sqlite3.Error as exc:
        raise ValueError(f"could not validate store: {exc}") from exc
    missing_ids = target_ids - found_ids
    if missing_ids:
        raise KeyError(f"unknown finding id: {min(missing_ids)}")

    store = Store(store_path)
    store.init()
    with store._con() as con:
        # Remove the retired simulated feedback at the same time so the old
        # reaction model cannot appear beside the new, labelled stances.
        con.execute("DELETE FROM feedback WHERE simulated = 1")
        con.execute("DELETE FROM stances WHERE simulated = 1")
        con.execute("DELETE FROM directives WHERE simulated = 1")
        con.executemany(
            "INSERT INTO stances (finding_id, role, stance, comment, simulated, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            [(finding_id, role, stance, comment, datetime.now(timezone.utc).replace(microsecond=0).isoformat())
             for finding_id, role, stance, comment in checked_stances],
        )
        con.executemany(
            "INSERT INTO directives (owner_role, text, mandatory, expires, simulated, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            [(owner_role, text, int(mandatory), expires, datetime.now(timezone.utc).replace(microsecond=0).isoformat())
             for owner_role, text, mandatory, expires in checked_directives],
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="storydesk")
    subs = parser.add_subparsers(dest="command", required=True)
    fetch = subs.add_parser("fetch")
    fetch.add_argument("--out-dir", default="data/raw")
    fetch.add_argument("--game", default=OPENER)
    fetch.set_defaults(func=_fetch)
    build = subs.add_parser("build-db")
    build.add_argument("--raw-dir", default="data/raw")
    build.add_argument("--db", default="data/stats.duckdb")
    build.set_defaults(func=_build_db)
    run = subs.add_parser("run")
    run.add_argument("run_type", choices=["pre_game", "post_game", "supplemental", "follow_up", "smoke"])
    run.add_argument("--game", required=True)
    run.add_argument("--as-of")
    run.add_argument("--question")
    run.add_argument("--anchor", type=int)
    run.add_argument("--asked-by", default="producer")
    run.add_argument("--live", action="store_true")
    run.add_argument("--stats-db", default="data/stats.duckdb")
    run.add_argument("--store", default="store/demo.db")
    run.add_argument("--corpus", default="data/corpus")
    run.add_argument("--digest-dir", default="data/digests")
    run.set_defaults(func=_run)
    card = subs.add_parser("scorecard")
    card.add_argument("--store", required=True)
    card.add_argument("--stats-db", required=True)
    card.add_argument("--run-id", required=True, type=int)
    card.add_argument("--json", action="store_true")
    card.set_defaults(func=_scorecard)
    rejudge = subs.add_parser("rejudge")
    rejudge.add_argument("--run-id", required=True, type=int)
    rejudge.add_argument("--live", action="store_true")
    rejudge.add_argument("--stats-db", default="data/stats.duckdb")
    rejudge.add_argument("--store", default="store/demo.db")
    rejudge.add_argument("--corpus", default="data/corpus")
    rejudge.set_defaults(func=_rejudge)
    copy = subs.add_parser("copy-pass")
    copy.add_argument("--run-id", required=True, type=int)
    copy.add_argument("--live", action="store_true")
    copy.add_argument("--store", default="store/demo.db")
    copy.set_defaults(func=_copy_pass)
    site = subs.add_parser("site")
    site.add_argument("--store", default="store/demo.db")
    site.add_argument("--stats-db", default="data/stats.duckdb")
    site.add_argument("--out-dir", default="site")
    site.add_argument("--game", default=OPENER)
    site.set_defaults(func=_site)
    simulate = subs.add_parser("simulate")
    simulate.add_argument("--store", required=True)
    simulate.add_argument("--file", required=True)
    simulate.set_defaults(func=_simulate)
    args = parser.parse_args(argv)
    return int(args.func(args))
