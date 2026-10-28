"""Command-line entry points, with an explicit guard around subscription-spending runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .data import build_stats_db, raw_connection
from .runner import run_live
from .scorecard import scorecard
from .site import build_site
from .store import Store


OPENER = "36dbeb55-58ad-11f1-a69b-43a6b5595d3e"


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
    ))
    print(run_id)
    return 0


def _scorecard(args: argparse.Namespace) -> int:
    card = scorecard(Store(args.store), args.stats_db, args.run_id)
    print(json.dumps(card) if args.json else card)
    return 0


def _site(args: argparse.Namespace) -> int:
    paths = build_site(Store(args.store), args.stats_db, args.out_dir, game_id=args.game)
    for path in paths:
        print(path)
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
    site = subs.add_parser("site")
    site.add_argument("--store", default="store/demo.db")
    site.add_argument("--stats-db", default="data/stats.duckdb")
    site.add_argument("--out-dir", default="site")
    site.add_argument("--game", default=OPENER)
    site.set_defaults(func=_site)
    args = parser.parse_args(argv)
    return int(args.func(args))
