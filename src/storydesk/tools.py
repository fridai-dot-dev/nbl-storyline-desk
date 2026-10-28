"""The bounded tool surface shared by the SDK and Claude Code routes."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .data import as_of_connection, iso_utc, raw_connection
from .sqlsafe import validate_safe_sql
from .store import Store


SENSITIVE_CATEGORIES = {"conflict", "injury", "officiating", "legal", "fan_quote"}
FINDING_KINDS = {"checked", "attributed", "qualitative", "nothing_found"}
SOURCE_TYPES = ("stats", "commentary", "media", "fans", "press", "directives")
_HANDLE = re.compile(r"(?:\bu/[A-Za-z0-9_-]+|@[A-Za-z0-9_-]+)")


class ToolError(ValueError):
    """A validation failure safe to show to an agent."""


@dataclass(frozen=True)
class ToolContext:
    stats_db: str | Path
    store: Store
    corpus_dir: str | Path
    run_id: int
    as_of: str | datetime

    @property
    def corpus_path(self) -> Path:
        return Path(self.corpus_dir)


def _cutoff(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        output = value
    else:
        output = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if output.tzinfo is not None:
        output = output.astimezone(timezone.utc).replace(tzinfo=None)
    return output.replace(microsecond=0)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _validate_select(sql: str) -> str:
    try:
        return validate_safe_sql(sql)
    except ValueError as exc:
        raise ToolError(f"unsafe stats query: {exc}") from exc


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def stats_sql(ctx: ToolContext, sql: str, limit: int = 200) -> dict[str, Any]:
    """Run a bounded read-only query against views frozen to this run's cutoff."""
    statement = _validate_select(sql)
    if not isinstance(limit, int) or limit < 1 or limit > 10_000:
        raise ToolError("limit must be an integer between 1 and 10000")
    con = as_of_connection(ctx.stats_db, ctx.as_of)
    try:
        cursor = con.execute(f"SELECT * FROM ({statement}) AS storydesk_query LIMIT {limit + 1}")
        columns = [item[0] for item in cursor.description]
        values = [_json_value(row) for row in cursor.fetchall()]
    except Exception as exc:
        raise ToolError(f"invalid stats query: {exc}") from exc
    finally:
        con.close()
    return {"columns": columns, "rows": values[:limit], "truncated": len(values) > limit}


def get_game(ctx: ToolContext, match_id: str) -> dict[str, Any]:
    """Return fixture metadata before tip-off and the score only after completion."""
    con = raw_connection(ctx.stats_db)
    try:
        row = con.execute(
            """SELECT match_id, home_team_name, away_team_name, match_time_utc
               FROM raw_results WHERE CAST(match_id AS VARCHAR) = ? LIMIT 1""",
            [str(match_id)],
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise ToolError(f"unknown match: {match_id}")
    game_id, home, away, start = row
    start_time = iso_utc(start) if start is not None else None
    result: dict[str, Any] = {
        "match_id": str(game_id), "home_team": home, "away_team": away,
        "start_time": start_time, "status": "scheduled",
    }
    match_literal = _sql_string(str(match_id))
    visible = stats_sql(ctx, "SELECT count(*) AS count FROM results WHERE CAST(match_id AS VARCHAR) = " + match_literal)
    if not visible["rows"][0][0]:
        return result
    box = stats_sql(
        ctx,
        """SELECT home_away, score, p1_score, p2_score, p3_score, p4_score
           FROM box_team WHERE CAST(match_id AS VARCHAR) = """ + match_literal,
    )
    by_side = {row[0]: row[1:] for row in box["rows"]}
    if not by_side:
        return result
    result.update({
        "status": "complete",
        "home_score": by_side.get("home", (None,))[0],
        "away_score": by_side.get("away", (None,))[0],
        "quarters": {
            "home": list(by_side.get("home", (None, None, None, None, None))[1:]),
            "away": list(by_side.get("away", (None, None, None, None, None))[1:]),
        },
    })
    return result


def _tokens(query: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9]+", query) if len(token) >= 3]


def _matches(item: dict[str, Any], query: str) -> bool:
    return _match_score(item, query) > 0


def _match_score(item: dict[str, Any], query: str) -> int:
    tokens = set(_tokens(query))
    if not tokens:
        return 0
    haystack = " ".join(str(value) for value in item.values() if value is not None).lower()
    return sum(token in haystack for token in tokens)


def _jsonl(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _check_limit(limit: int) -> int:
    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ToolError("limit must be an integer between 1 and 200")
    return limit


def _time_window(
    ctx: ToolContext, since: str | None = None, until: str | None = None,
) -> tuple[datetime | None, datetime]:
    cutoff = _cutoff(ctx.as_of)
    lower = _cutoff(since) if since is not None else None
    upper = min(cutoff, _cutoff(until)) if until is not None else cutoff
    return lower, upper


def _ranked_timestamped_items(
    ctx: ToolContext, filename: str, query: str, *, since: str | None = None, until: str | None = None,
) -> list[tuple[int, datetime, dict[str, Any]]]:
    lower, upper = _time_window(ctx, since, until)
    matches: list[tuple[int, datetime, dict[str, Any]]] = []
    for item in _jsonl(ctx.corpus_path / filename) or ():
        timestamp = _cutoff(item["timestamp"])
        score = _match_score(item, query)
        if (lower is None or lower <= timestamp) and timestamp <= upper and score:
            matches.append((score, timestamp, item))
    return sorted(matches, key=lambda item: (item[0], item[1]), reverse=True)


def _recent_timestamped_items(ctx: ToolContext, filename: str, limit: int) -> list[tuple[datetime, dict[str, Any]]]:
    _, cutoff = _time_window(ctx)
    items = [
        (timestamp, item)
        for item in _jsonl(ctx.corpus_path / filename) or ()
        if (timestamp := _cutoff(item["timestamp"])) <= cutoff
    ]
    return sorted(items, key=lambda item: item[0], reverse=True)[:limit]


def _transcript_result(item: dict[str, Any], timestamp: datetime) -> dict[str, Any]:
    return {
        "quote": item.get("quote", ""), "timestamp": iso_utc(timestamp),
        "source_url": item.get("source_url"), "source_type": item.get("source_type"),
        "source_title": item.get("source_title"),
    }


def _fan_result(item: dict[str, Any], timestamp: datetime) -> dict[str, Any]:
    return {
        "text": _HANDLE.sub("", item.get("text", "")).strip(), "score": item.get("score"),
        "timestamp": iso_utc(timestamp), "source_url": item.get("source_url"),
    }


def search_transcripts(
    ctx: ToolContext, query: str, limit: int = 20, since: str | None = None, until: str | None = None,
) -> list[dict[str, Any]]:
    limit = _check_limit(limit)
    matches = _ranked_timestamped_items(ctx, "transcripts.jsonl", query, since=since, until=until)
    return [_transcript_result(item, timestamp) for _, timestamp, item in matches[:limit]]


def search_fans(
    ctx: ToolContext, query: str, limit: int = 20, since: str | None = None, until: str | None = None,
) -> list[dict[str, Any]]:
    limit = _check_limit(limit)
    matches = _ranked_timestamped_items(ctx, "fans.jsonl", query, since=since, until=until)
    return [_fan_result(item, timestamp) for _, timestamp, item in matches[:limit]]


def search_media(ctx: ToolContext, query: str, limit: int = 20) -> list[dict[str, Any]]:
    limit = _check_limit(limit)
    cutoff_day = _cutoff(ctx.as_of).date()
    matches: list[tuple[int, date, dict[str, Any]]] = []
    for item in _jsonl(ctx.corpus_path / "media.jsonl") or ():
        try:
            item_day = date.fromisoformat(item["date"])
        except (KeyError, ValueError):
            continue
        score = _match_score(item, query)
        if item_day < cutoff_day and score:
            matches.append((score, item_day, item))
    return [
        {
            "title": item.get("title", ""), "date": item["date"], "url": item.get("url"),
            "excerpt": item.get("excerpt", ""),
        }
        for _, _, item in sorted(matches, key=lambda item: (item[0], item[1]), reverse=True)[:limit]
    ]


def recent_transcripts(ctx: ToolContext, limit: int = 3) -> list[dict[str, Any]]:
    """Return a compact, newest-first tail of cutoff-safe commentary."""
    limit = _check_limit(limit)
    return [
        _transcript_result(item, timestamp)
        for timestamp, item in _recent_timestamped_items(ctx, "transcripts.jsonl", limit)
    ]


def recent_fans(ctx: ToolContext, limit: int = 3) -> list[dict[str, Any]]:
    """Return a compact, newest-first tail of cutoff-safe fan reaction."""
    limit = _check_limit(limit)
    return [
        _fan_result(item, timestamp)
        for timestamp, item in _recent_timestamped_items(ctx, "fans.jsonl", limit)
    ]


def write_finding(
    ctx: ToolContext, *, agent: str, source_type: str, claim: str, kind: str,
    evidence: list[dict[str, Any]], number: float | int | None = None, query: str | None = None,
    chart: dict[str, Any] | None = None, parent_id: int | None = None,
    audience: tuple[str, ...] | list[str] = (), sensitivity: str | None = None,
    prompted_by: str | None = None,
) -> int:
    if kind not in FINDING_KINDS:
        raise ToolError(f"unknown finding kind: {kind}")
    if source_type not in SOURCE_TYPES:
        raise ToolError(f"unknown source type: {source_type}")
    if not claim or not str(claim).strip():
        raise ToolError("a finding needs a claim")
    if kind == "checked" and (number is None or not query):
        raise ToolError("checked findings require a number and query")
    if query is not None:
        _validate_select(query)
    if sensitivity is not None and sensitivity not in SENSITIVE_CATEGORIES:
        raise ToolError("unknown sensitivity category")
    if parent_id is not None:
        try:
            ctx.store.get_finding(parent_id)
        except KeyError as exc:
            raise ToolError("parent finding does not exist") from exc
    if kind != "nothing_found" and not evidence:
        raise ToolError("a finding needs at least one evidence item")
    for item in evidence:
        if not item.get("source_type") or not item.get("url") or not item.get("ref"):
            raise ToolError("evidence needs source_type, url and ref")
        if item["source_type"] not in SOURCE_TYPES:
            raise ToolError(f"unknown evidence source type: {item['source_type']}")
    if kind == "attributed" and not any(item.get("quote") for item in evidence):
        raise ToolError("attributed findings need a quoted source")
    if chart is not None:
        if set(chart) != {"type", "query", "y_label"} or chart["type"] not in {"bar", "line"}:
            raise ToolError("chart must specify type, query and y_label")
        if not isinstance(chart["query"], str) or not isinstance(chart["y_label"], str):
            raise ToolError("chart query and y_label must be strings")
        _validate_select(chart["query"])
    finding_id = ctx.store.add_finding(
        run_id=ctx.run_id, parent_id=parent_id, agent=agent, source_type=source_type,
        claim=claim, kind=kind, number=number, query=query, chart=chart,
        audience=audience, sensitivity=sensitivity, prompted_by=prompted_by,
    )
    ctx.store.add_evidence(finding_id, evidence)
    return finding_id


def read_findings(ctx: ToolContext, *, agent: str | None = None) -> list[dict[str, Any]]:
    findings = ctx.store.findings(ctx.run_id, include_dropped=True)
    return [finding for finding in findings if agent is None or finding["agent"] == agent]


_TRACKING_NAME = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_TRACKING_TYPE = {"TEXT", "INTEGER", "REAL"}


def create_tracking_table(ctx: ToolContext, name: str, columns: dict[str, str]) -> str:
    if not _TRACKING_NAME.fullmatch(name):
        raise ToolError("tracking table name is invalid")
    if not columns or any(not _TRACKING_NAME.fullmatch(column) for column in columns):
        raise ToolError("tracking column name is invalid")
    types = {column: str(type_name).upper() for column, type_name in columns.items()}
    if any(type_name not in _TRACKING_TYPE for type_name in types.values()):
        raise ToolError("tracking columns may be TEXT, INTEGER or REAL")
    return ctx.store.create_tracking_table(name, types)


def update_tracking_table(ctx: ToolContext, name: str, rows: list[dict[str, Any]]) -> int:
    if not _TRACKING_NAME.fullmatch(name):
        raise ToolError("tracking table name is invalid")
    try:
        return ctx.store.update_tracking_table(name, rows)
    except (sqlite3.Error, ValueError) as exc:  # pragma: no cover - depends on SQLite's exact error wording
        raise ToolError(str(exc)) from exc
