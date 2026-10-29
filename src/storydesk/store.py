"""The small, inspectable SQLite ledger behind a Storyline Desk run."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _moment(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("stance timestamp must be ISO 8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))


class Store:
    COPY_FIELDS = frozenset({
        "plain_headline", "premise", "metric", "threshold", "test_direction", "actual", "outcome",
    })
    OVERRIDE_ROLES = frozenset({"League GM", "LK director"})

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
                    summary TEXT, exec_summary TEXT, started_at TEXT NOT NULL, finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES runs(id), parent_id INTEGER REFERENCES findings(id),
                    agent TEXT NOT NULL, source_type TEXT NOT NULL, claim TEXT NOT NULL, kind TEXT NOT NULL,
                    number REAL, query TEXT, chart TEXT, status TEXT NOT NULL DEFAULT 'pending',
                    sensitivity TEXT, audience TEXT NOT NULL DEFAULT '[]', prompted_by TEXT,
                    drop_reason TEXT, novelty REAL, audience_fit REAL, direction REAL, headline TEXT,
                    plain_headline TEXT, premise TEXT,
                    metric TEXT, threshold REAL, test_direction TEXT, actual REAL, outcome TEXT,
                    followups TEXT NOT NULL DEFAULT '[]',
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
                    simulated INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS signoffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id INTEGER NOT NULL REFERENCES findings(id),
                    approver TEXT NOT NULL, audience TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    finding_id INTEGER NOT NULL REFERENCES findings(id), role TEXT NOT NULL,
                    stance TEXT NOT NULL, comment TEXT, created_at TEXT NOT NULL,
                    simulated INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(finding_id, role)
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
            self._add_column_if_missing(con, "runs", "summary", "TEXT")
            self._add_column_if_missing(con, "runs", "exec_summary", "TEXT")
            self._add_column_if_missing(con, "findings", "headline", "TEXT")
            self._add_column_if_missing(con, "findings", "plain_headline", "TEXT")
            self._add_column_if_missing(con, "findings", "premise", "TEXT")
            self._add_column_if_missing(con, "findings", "metric", "TEXT")
            self._add_column_if_missing(con, "findings", "threshold", "REAL")
            self._add_column_if_missing(con, "findings", "test_direction", "TEXT")
            self._add_column_if_missing(con, "findings", "actual", "REAL")
            self._add_column_if_missing(con, "findings", "outcome", "TEXT")
            self._add_column_if_missing(con, "findings", "followups", "TEXT NOT NULL DEFAULT '[]'")
            self._add_column_if_missing(con, "directives", "simulated", "INTEGER NOT NULL DEFAULT 1")
            self._add_column_if_missing(con, "directives", "finding_id", "INTEGER")
            self._add_column_if_missing(con, "directives", "stance_role", "TEXT")

    @staticmethod
    def _add_column_if_missing(con: sqlite3.Connection, table: str, name: str, definition: str) -> None:
        columns = {row["name"] for row in con.execute(f"PRAGMA table_info({table})")}
        if name not in columns:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

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

    def set_run_summary(self, run_id: int, text: str | None) -> None:
        with self._con() as con:
            con.execute("UPDATE runs SET summary = ? WHERE id = ?", (text, run_id))

    def set_exec_summary(self, run_id: int, text: str | None) -> None:
        """Store the judge's short, leadership-facing account of a run."""
        with self._con() as con:
            con.execute("UPDATE runs SET exec_summary = ? WHERE id = ?", (text, run_id))

    def update_run_ledger(self, run_id: int, *, cost_usd: float, model_usage: Any) -> None:
        """Update accounting without changing a completed run's outcome or timestamps."""
        with self._con() as con:
            con.execute(
                "UPDATE runs SET cost_usd = ?, model_usage = ? WHERE id = ?",
                (cost_usd, _json(model_usage or {}), run_id),
            )

    def add_finding(self, **fields: Any) -> int:
        fields = dict(fields)
        headline, premise = fields.get("plain_headline"), fields.get("premise")
        if isinstance(headline, str) and isinstance(premise, str):
            source = " ".join([str(fields.get("claim") or ""), *(
                f"{item.get('ref') or ''} {item.get('quote') or ''}" for item in fields.get("evidence") or []
                if isinstance(item, dict)
            )])
            grammar = {"Can", "Will", "Did", "What", "How", "Should", "The", "That", "It", "Commentary", "Fans"}
            tokens = lambda text: set(re.findall(r"(?<![\w])\d+(?:[.,]\d+)*(?![\w])", text)) | {
                word for word in re.findall(r"\b[A-Z][A-Za-z'’.-]+\b", text) if word not in grammar
            }
            if not tokens(f"{headline} {premise}") <= tokens(source):
                # Fixtures and callers may supply draft copy directly. Do not
                # let a draft with unsupported names or numbers enter the
                # ledger as publishable copy; the copy pass can replace it.
                fields["plain_headline"] = str(fields.get("claim") or "")
                fields["premise"] = str(fields.get("claim") or "")
        names = [
            "run_id", "parent_id", "agent", "source_type", "claim", "kind", "number", "query", "chart",
            "sensitivity", "audience", "prompted_by", "headline", "plain_headline", "premise", "metric",
            "threshold", "test_direction", "actual", "outcome", "created_at",
        ]
        test_direction = fields.get("test_direction")
        if test_direction is None and fields.get("direction") in {"at_most", "at_least", "above", "below", "higher", "lower"}:
            test_direction = fields.get("direction")
        values = [
            fields.get("run_id"), fields.get("parent_id"), fields["agent"], fields["source_type"],
            fields["claim"], fields["kind"], fields.get("number"), fields.get("query"),
            _json(fields["chart"]) if fields.get("chart") is not None else None,
            fields.get("sensitivity"), _json(list(fields.get("audience") or [])), fields.get("prompted_by"),
            fields.get("headline"), fields.get("plain_headline"), fields.get("premise"), fields.get("metric"),
            fields.get("threshold"), test_direction, fields.get("actual"), fields.get("outcome"), _now(),
        ]
        with self._con() as con:
            cur = con.execute(
                f"INSERT INTO findings ({', '.join(names)}) VALUES ({', '.join('?' for _ in names)})", values
            )
            finding_id = int(cur.lastrowid)
            # A whole-number result above a threshold is part of the stored
            # test definition (for example, "above 25" starts at 26). Keep
            # that interpretation in the finding's evidence so copy can cite
            # it rather than inventing a number.
            if test_direction == "above" and fields.get("threshold") is not None:
                try:
                    first_above = float(fields["threshold"]) + 1
                    con.execute(
                        "INSERT INTO evidence (finding_id, source_type, url, ref, quote, stance) VALUES (?, ?, ?, ?, NULL, NULL)",
                        (finding_id, "structured_test", "", f"First whole number above {float(fields['threshold']):g}: {first_above:g}"),
                    )
                except (TypeError, ValueError):
                    pass
            return finding_id

    @staticmethod
    def _finding(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["chart"] = json.loads(result["chart"]) if result.get("chart") else None
        result["audience"] = json.loads(result.get("audience") or "[]")
        try:
            followups = json.loads(result.get("followups") or "[]")
        except json.JSONDecodeError:
            followups = []
        result["followups"] = followups if isinstance(followups, list) else []
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

    def update_finding_copy(self, updates: list[tuple[int, dict[str, Any]]]) -> None:
        """Apply one validated copy pass in a single transaction."""
        with self._con() as con:
            for finding_id, fields in updates:
                if not fields or not set(fields) <= self.COPY_FIELDS:
                    raise ValueError("copy update contains unsupported fields")
                names = list(fields)
                cursor = con.execute(
                    f"UPDATE findings SET {', '.join(f'{name} = ?' for name in names)} WHERE id = ?",
                    [fields[name] for name in names] + [finding_id],
                )
                if cursor.rowcount != 1:
                    raise KeyError(f"finding {finding_id} does not exist")

    def linked_findings(self, finding_id: int) -> list[dict[str, Any]]:
        """Return the direct parent and children used to validate structured result copy."""
        with self._con() as con:
            row = con.execute("SELECT parent_id FROM findings WHERE id = ?", (finding_id,)).fetchone()
            if row is None:
                raise KeyError(f"finding {finding_id} does not exist")
            ids = [child[0] for child in con.execute(
                "SELECT id FROM findings WHERE parent_id = ? ORDER BY id", (finding_id,),
            ).fetchall()]
            if row["parent_id"] is not None:
                ids.insert(0, row["parent_id"])
        return [self.get_finding(item) for item in ids]

    def set_headline(self, finding_id: int, text: str | None) -> None:
        with self._con() as con:
            con.execute("UPDATE findings SET headline = ? WHERE id = ?", (text, finding_id))

    def set_followups(self, finding_id: int, items: list[dict[str, Any]]) -> None:
        """Replace the judge-suggested next questions for one finding."""
        with self._con() as con:
            con.execute("UPDATE findings SET followups = ? WHERE id = ?", (_json(items), finding_id))

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

    def signoffs(self, finding_id: int) -> list[dict[str, Any]]:
        """Return the recorded audience approvals in the order they were made."""
        with self._con() as con:
            rows = con.execute(
                "SELECT audience, approver, created_at FROM signoffs WHERE finding_id = ? ORDER BY id",
                (finding_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_stance(
        self, finding_id: int, role: str, stance: str, comment: str | None = None, *, at: str | None = None,
        simulated: bool = False,
    ) -> None:
        """Set one role's current editorial stance and retain the current record."""
        if stance not in {"push", "use_if_raised", "steer_away"}:
            raise ValueError("stance must be push, use_if_raised or steer_away")
        if not isinstance(role, str) or not role.strip():
            raise ValueError("stance role is required")
        timestamp = at or _now()
        incoming = _moment(timestamp)
        role = role.strip()
        with self._con() as con:
            if con.execute("SELECT 1 FROM findings WHERE id = ?", (finding_id,)).fetchone() is None:
                raise KeyError(f"finding {finding_id} does not exist")
            current = con.execute(
                "SELECT created_at FROM stances WHERE finding_id = ? AND role = ?", (finding_id, role),
            ).fetchone()
            if current is not None and incoming < _moment(current["created_at"]):
                raise ValueError(f"stale stance update for {role} on finding {finding_id}")
            con.execute(
                """INSERT INTO stances (finding_id, role, stance, comment, created_at, simulated)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(finding_id, role) DO UPDATE SET stance = excluded.stance,
                       comment = excluded.comment, created_at = excluded.created_at, simulated = excluded.simulated""",
                (finding_id, role, stance, comment, timestamp, int(simulated)),
            )
            con.execute(
                "UPDATE directives SET status = 'cleared' WHERE finding_id = ? AND stance_role = ? AND status = 'active'",
                (finding_id, role),
            )
            if role in self.OVERRIDE_ROLES and stance in {"push", "use_if_raised"}:
                con.execute(
                    """UPDATE directives SET status = 'cleared'
                       WHERE finding_id = ? AND status = 'active' AND stance_role IN (
                           SELECT role FROM stances WHERE finding_id = ? AND stance = 'steer_away'
                       )""",
                    (finding_id, finding_id),
                )
            if stance == "steer_away":
                text = str(comment or f"Steer away from finding {finding_id}.").strip()
                con.execute(
                    """INSERT INTO directives (owner_role, text, mandatory, expires, status, simulated, created_at, finding_id, stance_role)
                       VALUES (?, ?, 1, NULL, 'active', ?, ?, ?, ?)""",
                    (role, text, int(simulated), timestamp, finding_id, role),
                )

    def stances(self, finding_id: int) -> list[dict[str, Any]]:
        try:
            with self._con() as con:
                rows = con.execute(
                    "SELECT role, stance, comment, created_at AS time, simulated FROM stances WHERE finding_id = ? ORDER BY id",
                    (finding_id,),
                ).fetchall()
        except sqlite3.OperationalError:
            # Read-only historical ledgers pre-date the stance migration.
            return []
        return [dict(row) for row in rows]

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

    def add_directive(
        self, owner_role: str, text: str, mandatory: bool = False, expires: str | None = None, simulated: bool = True,
    ) -> int:
        with self._con() as con:
            cur = con.execute(
                "INSERT INTO directives (owner_role, text, mandatory, expires, simulated, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (owner_role, text, int(mandatory), expires, int(simulated), _now()),
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

    def find_or_add_request(self, anchor_finding_id: int, asked_by: str, question: str) -> int:
        """Reuse the matching pending request when a follow-up is retried."""
        question = question.strip()
        with self._con() as con:
            row = con.execute(
                "SELECT id FROM requests "
                "WHERE anchor_finding_id = ? AND question = ? AND answered_run_id IS NULL "
                "ORDER BY id LIMIT 1",
                (anchor_finding_id, question),
            ).fetchone()
            if row is not None:
                return int(row["id"])
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
