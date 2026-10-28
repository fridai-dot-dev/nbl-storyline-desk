"""DuckDB-backed statistics storage with per-run ``as_of`` views."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


def _utc_naive(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def _timestamp_literal(value: str | datetime) -> str:
    return _utc_naive(value).isoformat(sep=" ")


def _display_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if value.get("name"):
            return str(value["name"])
        first = value.get("first_name") or value.get("firstName")
        last = value.get("last_name") or value.get("lastName")
        if first or last:
            return " ".join(str(part) for part in (first, last) if part)
        nested = value.get("player") or value.get("team")
        if nested is not None:
            return _display_name(nested)
    return None


def _payload_rows(path: Path) -> tuple[str, datetime | None, list[tuple[Any, ...]]]:
    """Read one small match payload; large historical data always stays in DuckDB."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    match = payload["data"][0]
    match_id = str(match.get("id") or match.get("external_id"))
    team_names = {
        str(item.get("id")): item.get("name")
        for item in (match.get("home_team") or {}, match.get("away_team") or {})
        if item.get("id")
    }
    team_names.update({
        str(item.get("external_id")): item.get("name")
        for item in (match.get("home_team") or {}, match.get("away_team") or {})
        if item.get("external_id")
    })
    end_time: datetime | None = None
    rows: list[tuple[Any, ...]] = []
    for event in match.get("play_by_play") or []:
        timestamp = event.get("timestamp")
        if event.get("system_action_type") == "game_game_completed" and timestamp:
            end_time = _utc_naive(timestamp)
        team = _display_name(event.get("team"))
        if team is None and event.get("team") is not None:
            team = team_names.get(str(event["team"]))
        rows.append((
            match_id,
            event.get("action_id"),
            event.get("period"),
            event.get("period_type"),
            event.get("clock"),
            event.get("score_1"),
            event.get("score_2"),
            event.get("action_type"),
            event.get("sub_type"),
            team,
            _display_name(event.get("player")),
            _utc_naive(timestamp) if timestamp else None,
        ))
    return match_id, end_time, rows


def _sql_literal(value: Any) -> str:
    """Serialize the small, trusted API payload into one DuckDB statement."""
    if value is None:
        return "NULL"
    if isinstance(value, datetime):
        return "TIMESTAMP '" + value.isoformat(sep=" ").replace("'", "''") + "'"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def build_stats_db(
    db_path: str | Path,
    *,
    results_csv: str | Path,
    box_team_csv: str | Path,
    box_player_csv: str | Path,
    match_json_paths: list[str | Path],
) -> None:
    """Build the durable database without loading the source CSVs into Python."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    try:
        for table in ("raw_results", "raw_box_team", "raw_box_player", "raw_pbp", "match_ends"):
            con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute("CREATE TABLE raw_results AS SELECT * FROM read_csv_auto(?, nullstr='NA', types={'match_id': 'VARCHAR'}, sample_size=-1)", [str(results_csv)])
        # nblR's box_team carries a few near-identical rescrapes of the same match and team (one with
        # fouls zeroed); keep one row per team per match, preferring the one with real foul counts.
        con.execute(
            "CREATE TABLE raw_box_team AS SELECT DISTINCT ON (match_id, name) * "
            "FROM read_csv_auto(?, nullstr='NA', types={'match_id': 'VARCHAR'}, sample_size=-1) "
            "ORDER BY match_id, name, fouls DESC NULLS LAST",
            [str(box_team_csv)],
        )
        con.execute("CREATE TABLE raw_box_player AS SELECT * FROM read_csv_auto(?, nullstr='NA', types={'match_id': 'VARCHAR'}, sample_size=-1)", [str(box_player_csv)])
        con.execute(
            """CREATE TABLE raw_pbp (
                match_id VARCHAR, action_id BIGINT, period INTEGER, period_type VARCHAR,
                clock VARCHAR, score_home INTEGER, score_away INTEGER, action_type VARCHAR,
                sub_type VARCHAR, team VARCHAR, player VARCHAR, timestamp TIMESTAMP
            )"""
        )
        con.execute(
            """CREATE TABLE match_ends AS
               SELECT CAST(match_id AS VARCHAR) AS match_id,
                      date_trunc('second', try_cast(match_time_utc AS TIMESTAMP) + INTERVAL 3 HOUR) AS end_time
               FROM raw_results
               WHERE try_cast(match_time_utc AS TIMESTAMP) IS NOT NULL"""
        )
        for source in match_json_paths:
            match_id, end_time, rows = _payload_rows(Path(source))
            if rows:
                values = ",".join("(" + ",".join(_sql_literal(value) for value in row) + ")" for row in rows)
                con.execute("INSERT INTO raw_pbp VALUES " + values)
            if end_time is not None:
                con.execute("DELETE FROM match_ends WHERE match_id = ?", [match_id])
                con.execute("INSERT INTO match_ends VALUES (?, ?)", [match_id, end_time])
    finally:
        con.close()


def as_of_connection(db_path: str | Path, as_of: str | datetime, *, read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Open a connection exposing only matches complete by a run's cutoff."""
    con = duckdb.connect(str(db_path), read_only=read_only, config={"enable_external_access": "false"})
    cutoff = _timestamp_literal(as_of).replace("'", "''")
    visible = (
        "CAST(r.match_id AS VARCHAR) IN "
        f"(SELECT match_id FROM match_ends WHERE end_time <= TIMESTAMP '{cutoff}')"
    )
    con.execute(f"CREATE OR REPLACE TEMP VIEW results AS SELECT r.* FROM raw_results r WHERE {visible}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW box_team AS SELECT r.* FROM raw_box_team r WHERE {visible}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW box_player AS SELECT r.* FROM raw_box_player r WHERE {visible}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW pbp AS SELECT r.* FROM raw_pbp r WHERE {visible}")
    return con


def raw_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path), read_only=True, config={"enable_external_access": "false"})


def iso_utc(value: str | datetime) -> str:
    parsed = _utc_naive(value)
    return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "+00:00")
