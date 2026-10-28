"""The small, inspectable SQLite ledger behind a Storyline Desk run."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA busy_timeout = 5000")
        return con

    def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._con() as con:
            con.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_type TEXT NOT NULL, game_id TEXT NOT NULL, as_of TEXT NOT NULL, route TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending', cost_usd REAL, duration_s REAL,
                    model_usage TEXT NOT NULL DEFAULT '{}', num_agents INTEGER,
                    started_at TEXT NOT NULL, finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES runs(id), parent_id INTEGER REFERENCES findings(id),
                    agent TEXT NOT NULL, source_type TEXT NOT NULL, claim TEXT NOT NULL, kind TEXT NOT NULL,
                    number REAL, query TEXT, chart TEXT, status TEXT NOT NULL DEFAULT 'pending',
                    sensitivity TEXT, audience TEXT NOT NULL DEFAULT '[]', prompted_by TEXT,
                    drop_reason TEXT, novelty REAL, audience_fit REAL, direction REAL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL REFERENCES findings(id),
                    source_type TEXT NOT NULL, url TEXT NOT NULL, ref TEXT NOT NULL,
                    quote TEXT, stance TEXT
                );
                CREATE TABLE IF NOT EXISTS directives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, owner_role TEXT NOT NULL, text TEXT NOT NULL,
                    mandatory INTEGER NOT NULL DEFAULT 0, expires TEXT, status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS signoffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL REFERENCES findings(id),
                    approver TEXT NOT NULL, audience TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, anchor_finding_id INTEGER NOT NULL REFERENCES findings(id),
                    asked_by TEXT NOT NULL, question TEXT NOT NULL, answered_run_id INTEGER REFERENCES runs(id),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL REFERENCES findings(id),
                    role TEXT NOT NULL, action TEXT NOT NULL, text TEXT, simulated INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL REFERENCES runs(id),
                    agent_id TEXT, agent_type TEXT, tool TEXT NOT NULL, args_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ingested_tool_events (
                    run_id INTEGER NOT NULL REFERENCES runs(id), event_id TEXT NOT NULL,
                    PRIMARY KEY (run_id, event_id)
                );
                """
            )

    def start_run(self, run_type: str, game_id: str, as_of: str, route: str) -> int:
        with self._con() as con:
            cur = con.execute(
                "INSERT INTO runs (run_type, game_id, as_of, route, started_at) VALUES (?, ?, ?, ?, ?)",
                (run_type, str(game_id), str(as_of), route, _now()),
            )
            return int(cur.lastrowid)

    def get_run(self, run_id: int) -> dict[str, Any]:
        with self._con() as con:
            row = con.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"run {run_id} does not exist")
        result = dict(row)
        result["model_usage"] = json.loads(result.get("model_usage") or "{}")
        return result

    def finish_run(
        self, run_id: int, *, status: str, cost_usd: float | None, duration_s: float | None,
        model_usage: Any, num_agents: int, route: str,
    ) -> None:
        with self._con() as con:
            con.execute(
                """UPDATE runs SET status = ?, cost_usd = ?, duration_s = ?, model_usage = ?,
                   num_agents = ?, route = ?, finished_at = ? WHERE id = ?""",
                (status, cost_usd, duration_s, _json(model_usage or {}), num_agents, route, _now(), run_id),
            )

    def add_finding(self, **fields: Any) -> int:
        names = [
            "run_id", "parent_id", "agent", "source_type", "claim", "kind", "number", "query", "chart",
            "sensitivity", "audience", "prompted_by", "created_at",
        ]
        values = [
            fields.get("run_id"), fields.get("parent_id"), fields["agent"], fields["source_type"],
            fields["claim"], fields["kind"], fields.get("number"), fields.get("query"),
            _json(fields["chart"]) if fields.get("chart") is not None else None,
            fields.get("sensitivity"), _json(list(fields.get("audience") or [])), fields.get("prompted_by"), _now(),
        ]
        with self._con() as con:
            cur = con.execute(
                f"INSERT INTO findings ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})", values
            )
            return int(cur.lastrowid)

    @staticmethod
    def _finding(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["chart"] = json.loads(result["chart"]) if result.get("chart") else None
        result["audience"] = json.loads(result.get("audience") or "[]")
        return result

    def findings(self, run_id: int, include_dropped: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT * FROM findings WHERE run_id = ?"
        if not include_dropped:
            sql += " AND status != 'dropped'"
        sql += " ORDER BY id"
        with self._con() as con:
            return [self._finding(row) for row in con.execute(sql, (run_id,)).fetchall()]

    def get_finding(self, finding_id: int) -> dict[str, Any]:
        with self._con() as con:
            row = con.execute("SELECT * FROM findings WHERE id = ?", (finding_id,)).fetchone()
        if row is None:
            raise KeyError(f"finding {finding_id} does not exist")
        return self._finding(row)

    def update_finding(self, finding_id: int, **fields: Any) -> None:
        if not fields:
            return
        normalised = dict(fields)
        if "chart" in normalised:
            normalised["chart"] = _json(normalised["chart"]) if normalised["chart"] is not None else None
        if "audience" in normalised:
            normalised["audience"] = _json(normalised["audience"])
        names = list(normalised)
        with self._con() as con:
            con.execute(
                f"UPDATE findings SET {', '.join(f'{name} = ?' for name in names)} WHERE id = ?",
                [normalised[name] for name in names] + [finding_id],
            )

    def add_evidence(self, finding_id: int, evidence: Iterable[dict[str, Any]]) -> None:
        rows = [
            (finding_id, item["source_type"], item["url"], str(item["ref"]), item.get("quote"), item.get("stance"))
            for item in evidence
        ]
        if not rows:
            return
        with self._con() as con:
            con.executemany(
                "INSERT INTO evidence (finding_id, source_type, url, ref, quote, stance) VALUES (?, ?, ?, ?, ?, ?)", rows
            )

    def evidence(self, finding_id: int) -> list[dict[str, Any]]:
        with self._con() as con:
            rows = con.execute("SELECT source_type, url, ref, quote, stance FROM evidence WHERE finding_id = ? ORDER BY id", (finding_id,)).fetchall()
        return [dict(row) for row in rows]

    def add_signoff(self, finding_id: int, approver: str, audience: str) -> None:
        with self._con() as con:
            con.execute("INSERT INTO signoffs (finding_id, approver, audience, created_at) VALUES (?, ?, ?, ?)",
                        (finding_id, approver, audience, _now()))

    def signed_off(self, finding_id: int, audience: str) -> bool:
        with self._con() as con:
            return con.execute("SELECT 1 FROM signoffs WHERE finding_id = ? AND audience = ?", (finding_id, audience)).fetchone() is not None

    def add_feedback(self, finding_id: int, role: str, action: str, text: str | None = None, simulated: bool = True) -> None:
        with self._con() as con:
            con.execute("INSERT INTO feedback (finding_id, role, action, text, simulated, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (finding_id, role, action, text, int(simulated), _now()))

    def feedback(self, finding_id: int | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM feedback", ()
        if finding_id is not None:
            sql += " WHERE finding_id = ?"
            args = (finding_id,)
        with self._con() as con:
            return [dict(row) for row in con.execute(sql + " ORDER BY id", args).fetchall()]

    def add_directive(self, owner_role: str, text: str, mandatory: bool = False, expires: str | None = None) -> int:
        with self._con() as con:
            cur = con.execute(
                "INSERT INTO directives (owner_role, text, mandatory, expires, created_at) VALUES (?, ?, ?, ?, ?)",
                (owner_role, text, int(mandatory), expires, _now()),
            )
            return int(cur.lastrowid)

    def directives(self) -> list[dict[str, Any]]:
        with self._con() as con:
            return [dict(row) for row in con.execute("SELECT * FROM directives ORDER BY id").fetchall()]

    def add_request(self, anchor_finding_id: int, asked_by: str, question: str) -> int:
        with self._con() as con:
            cur = con.execute(
                "INSERT INTO requests (anchor_finding_id, asked_by, question, created_at) VALUES (?, ?, ?, ?)",
                (anchor_finding_id, asked_by, question, _now()),
            )
            return int(cur.lastrowid)

    def answer_request(self, request_id: int, run_id: int) -> None:
        with self._con() as con:
            con.execute("UPDATE requests SET answered_run_id = ? WHERE id = ?", (run_id, request_id))

    def requests(self) -> list[dict[str, Any]]:
        with self._con() as con:
            return [dict(row) for row in con.execute("SELECT * FROM requests ORDER BY id").fetchall()]

    def requests_for_anchor(self, finding_id: int) -> list[dict[str, Any]]:
        return [request for request in self.requests() if request["anchor_finding_id"] == finding_id]

    def log_tool_call(self, run_id: int, agent_id: str | None, agent_type: str | None, tool: str, args_json: str) -> None:
        with self._con() as con:
            con.execute(
                "INSERT INTO tool_calls (run_id, agent_id, agent_type, tool, args_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, agent_id, agent_type, tool, args_json, _now()),
            )

    def ingest_tool_calls(self, run_id: int, events: Iterable[dict[str, Any]]) -> int:
        """Add each spooled event once, even if its log is read again."""
        inserted = 0
        with self._con() as con:
            for event in events:
                event_id = str(event["event_id"])
                cursor = con.execute(
                    "INSERT OR IGNORE INTO ingested_tool_events (run_id, event_id) VALUES (?, ?)",
                    (run_id, event_id),
                )
                if cursor.rowcount == 0:
                    continue
                con.execute(
                    "INSERT INTO tool_calls (run_id, agent_id, agent_type, tool, args_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        run_id, event.get("agent_id"), event.get("agent_type"), event["tool"],
                        event["args_json"], _now(),
                    ),
                )
                inserted += 1
        return inserted

    def create_tracking_table(self, name: str, columns: dict[str, str]) -> str:
        table = f"track_{name}"
        with self._con() as con:
            con.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(f'{key} {value}' for key, value in columns.items())})")
        return table

    def update_tracking_table(self, name: str, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        table = f"track_{name}"
        keys = list(rows[0])
        if any(set(row) != set(keys) for row in rows):
            raise ValueError("tracking rows must have the same columns")
        with self._con() as con:
            con.executemany(
                f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})",
                [[row[key] for key in keys] for row in rows],
            )
        return len(rows)

    def game_runs(self, game_id: str) -> list[dict[str, Any]]:
        with self._con() as con:
            rows = con.execute("SELECT * FROM runs WHERE game_id = ? ORDER BY id", (str(game_id),)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["model_usage"] = json.loads(item.get("model_usage") or "{}")
            result.append(item)
        return result

    def game_findings(self, game_id: str, include_dropped: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT f.* FROM findings f JOIN runs r ON r.id = f.run_id WHERE r.game_id = ?"
        if not include_dropped:
            sql += " AND f.status != 'dropped'"
        sql += " ORDER BY f.id"
        with self._con() as con:
            return [self._finding(row) for row in con.execute(sql, (str(game_id),)).fetchall()]
