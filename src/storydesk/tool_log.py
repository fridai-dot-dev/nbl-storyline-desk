"""Small, lock-free spool files for SDK hook tool-call events."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


MAX_ARGS_JSON_CHARS = 1_000


def tool_log_path(store_path: str | Path, run_id: int) -> Path:
    """Return this run's hook-event spool alongside its SQLite store."""
    store = Path(store_path)
    return store.with_name(f"{store.name}.{run_id}.tool-calls.jsonl")


def compact_args_json(args: Any) -> str:
    """Serialise hook input without allowing one event to make the spool large."""
    value = json.dumps(args, default=str, separators=(",", ":"))
    if len(value) <= MAX_ARGS_JSON_CHARS:
        return value
    return json.dumps(
        {"truncated": True, "preview": value[: MAX_ARGS_JSON_CHARS - 80]},
        separators=(",", ":"),
    )


def append_tool_log(
    store_path: str | Path, run_id: int, *, agent_id: Any, agent_type: Any,
    tool: Any, args: Any, event_id: str | None = None,
) -> None:
    """Append one hook event without opening or waiting on the SQLite store.

    A single append-only write keeps concurrent hook events independent.  Failure to
    write a diagnostic event must never make an SDK hook delay a tool call.
    """
    event = {
        "event_id": event_id or uuid.uuid4().hex,
        "agent_id": None if agent_id is None else str(agent_id),
        "agent_type": None if agent_type is None else str(agent_type),
        "tool": str(tool),
        "args_json": compact_args_json(args),
    }
    line = (json.dumps(event, default=str, separators=(",", ":")) + "\n").encode("utf-8")
    try:
        descriptor = os.open(tool_log_path(store_path, run_id), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, line)
        finally:
            os.close(descriptor)
    except OSError:
        # Hooks are observability only: never let a full or unavailable spool block a run.
        return
