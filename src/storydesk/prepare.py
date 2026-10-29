"""Build compact, cutoff-safe starting sets once per run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .data import as_of_connection
from .store import Store
from .tools import (
    ToolContext,
    get_game,
    recent_fans,
    recent_transcripts,
    search_fans,
    search_media,
    search_transcripts,
)


def _write(path: Path, name: str, title: str, body: str) -> Path:
    output = path / name
    output.write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")
    return output


def _rows_markdown(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    if not rows:
        return "No data available at this cutoff."
    header = " | ".join(columns)
    divider = " | ".join("---" for _ in columns)
    lines = [f"| {header} |", f"| {divider} |"]
    for row in rows:
        lines.append("| " + " | ".join("" if value is None else str(value) for value in row) + " |")
    return "\n".join(lines)


def _finding_markdown(store: Store, finding: dict[str, Any]) -> str:
    lines = [
        f"## Finding {finding['id']}",
        f"- Claim: {finding['claim']}",
        f"- Kind: {finding['kind']}",
        f"- Status: {finding['status']}",
    ]
    if finding.get("parent_id") is not None:
        lines.append(f"- Parent finding: {finding['parent_id']}")
    evidence = store.evidence(finding["id"])
    if evidence:
        lines.append("- Evidence:")
        for item in evidence:
            detail = f"  - {item['source_type']} · {item['url']} · ref {item['ref']}"
            if item.get("quote"):
                detail += f" · quote: {item['quote']}"
            lines.append(detail)
    return "\n".join(lines)


def _lineage(store: Store, finding: dict[str, Any]) -> list[dict[str, Any]]:
    output = [finding]
    seen = {finding["id"]}
    parent_id = finding.get("parent_id")
    while parent_id is not None and parent_id not in seen:
        parent = store.get_finding(parent_id)
        output.append(parent)
        seen.add(parent["id"])
        parent_id = parent.get("parent_id")
    return output


def _digest_source_tail(
    matches: list[dict[str, Any]], latest: list[dict[str, Any]], render: Any, text_key: str,
) -> str:
    """Keep a focused set of matches while retaining the game-ending context."""
    def item_key(item: dict[str, Any]) -> tuple[Any, Any, Any]:
        return item.get("timestamp"), item.get("source_url"), item.get(text_key)

    latest_keys = {item_key(item) for item in latest}
    relevant = [item for item in matches if item_key(item) not in latest_keys]
    sections = []
    if relevant:
        sections.append("## Relevant matches\n\n" + "\n\n".join(render(item) for item in relevant))
    if latest:
        sections.append("## Latest before cutoff\n\n" + "\n\n".join(render(item) for item in latest))
    return "\n\n".join(sections)


def _prior_context(
    run_type: str, game_id: str, store: Store, anchor_finding_id: int | None,
) -> str:
    runs = store.game_runs(game_id)
    directives = [item for item in store.directives() if item["status"] == "active"]
    sections: list[str] = []
    prior_findings: list[dict[str, Any]] = []

    if run_type == "follow_up":
        if anchor_finding_id is None:
            return "No anchor finding was supplied."
        try:
            anchor = store.get_finding(anchor_finding_id)
            anchor_run = store.get_run(anchor["run_id"])
        except KeyError as exc:
            raise ValueError(f"unknown anchor finding: {anchor_finding_id}") from exc
        if str(anchor_run["game_id"]) != str(game_id):
            raise ValueError("the anchor finding belongs to a different game")
        prior_findings = _lineage(store, anchor)
        sections.append("# Anchor and lineage")
    elif run_type in {"post_game", "supplemental"}:
        source_type = "pre_game" if run_type == "post_game" else "post_game"
        source_runs = [run for run in runs if run["run_type"] == source_type]
        if source_runs:
            prior_findings = [
                item for item in store.findings(source_runs[-1]["id"], include_dropped=True)
                if item["status"] == "shipped"
            ]
        sections.append(f"# Shipped findings from the latest {source_type.replace('_', '-')} run")

    sections.extend(_finding_markdown(store, item) for item in prior_findings)
    relevant_ids = {item["id"] for item in prior_findings}
    feedback = [item for item in store.feedback() if item["finding_id"] in relevant_ids]
    sections.append("# Feedback")
    sections.extend(
        f"- Finding {item['finding_id']} · {item['role']} · {item['action']}: {item.get('text') or ''}"
        for item in feedback
    )
    if not feedback:
        sections.append("No relevant feedback.")
    sections.append("# Active directives")
    sections.extend(
        f"- {'Mandatory' if item['mandatory'] else 'Suggested'} · {item['owner_role']}: {item['text']}"
        for item in directives
    )
    if not directives:
        sections.append("No active directives.")
    return "\n\n".join(sections)


def prepare_run(
    run_type: str, *, game_id: str, as_of: str, stats_db: str | Path, store: Store,
    corpus_dir: str | Path, out_dir: str | Path, anchor_finding_id: int | None = None,
) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    context = ToolContext(stats_db=stats_db, store=store, corpus_dir=corpus_dir, run_id=0, as_of=as_of)
    game = get_game(context, game_id)
    game_lines = [
        f"{game['home_team']} vs {game['away_team']}",
        f"Tip-off: {game['start_time']}",
    ]
    if game["status"] == "complete":
        game_lines.extend([
            f"Final score: {game['home_team']} {game['home_score']} – {game['away_score']} {game['away_team']}",
            f"Quarter scores: {json.dumps(game['quarters'])}",
        ])
    _write(out, "game.md", "Game", "\n\n".join(game_lines))

    con = as_of_connection(stats_db, as_of)
    try:
        form_rows = con.execute(
            """SELECT b.match_id, CAST(try_cast(r.match_time_utc AS TIMESTAMP) AS DATE), r.season,
                      b.name, b.opp_name, b.score, b.opp_score
               FROM box_team AS b JOIN results AS r ON b.match_id = r.match_id
               WHERE b.name IN (?, ?)
               ORDER BY try_cast(r.match_time_utc AS TIMESTAMP) DESC LIMIT 12""",
            [game["home_team"], game["away_team"]],
        ).fetchall()
        history_rows = con.execute(
            """SELECT b.match_id, CAST(try_cast(r.match_time_utc AS TIMESTAMP) AS DATE), r.season,
                      b.name, b.p1_score, b.p2_score, b.p3_score, b.p4_score, b.score
               FROM box_team AS b JOIN results AS r ON b.match_id = r.match_id
               WHERE b.name IN (?, ?) AND b.opp_name IN (?, ?)
               ORDER BY try_cast(r.match_time_utc AS TIMESTAMP) DESC LIMIT 20""",
            [game["home_team"], game["away_team"], game["home_team"], game["away_team"]],
        ).fetchall()
    finally:
        con.close()
    _write(out, "form.md", "Recent form", _rows_markdown(["match", "date", "season", "team", "opponent", "points", "opponent points"], form_rows))
    _write(out, "history.md", "Head-to-head and quarter history", _rows_markdown(["match", "date", "season", "team", "Q1", "Q2", "Q3", "Q4", "points"], history_rows))

    query = f"{game['home_team']} {game['away_team']}"
    transcripts = search_transcripts(context, query, limit=12)
    transcript_body = _digest_source_tail(
        transcripts,
        recent_transcripts(context, limit=3),
        lambda item: f"- {item['timestamp']} — {item.get('source_title') or item.get('source_type')}: {item['quote']} ({item['source_url']})",
        "quote",
    ) or "No transcript material before the cutoff."
    _write(out, "commentary.md", "Commentary and transcripts", transcript_body)

    fans = search_fans(context, "third quarter bench finish defence", limit=12)
    fan_body = _digest_source_tail(
        fans,
        recent_fans(context, limit=3),
        lambda item: f"- {item['timestamp']} · score {item.get('score')}: {item['text']} ({item['source_url']})",
        "text",
    ) or "No fan reaction before the cutoff."
    _write(out, "fans.md", "Fan reaction", fan_body)

    media = search_media(context, query, limit=30)
    media_body = "\n\n".join(
        f"- {item['date']} — {item['title']}: {item['excerpt']} ({item['url']})" for item in media
    ) or "No matching media material before the cutoff."
    _write(out, "media.md", "Media coverage", media_body)

    directives = [item for item in store.directives() if item["status"] == "active"]
    directive_body = "\n".join(
        f"- {'Mandatory' if item['mandatory'] else 'Suggested'} · {item['owner_role']}: {item['text']}"
        for item in directives
    ) or "No active directives."
    _write(out, "directives.md", "Active directives", directive_body)
    if run_type in {"post_game", "supplemental", "follow_up"}:
        _write(
            out, "prior-findings.md", "Prior-finding context",
            _prior_context(run_type, game_id, store, anchor_finding_id),
        )
    return out
