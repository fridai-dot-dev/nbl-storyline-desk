"""Checks from the first live smoke run (2026-10-28).

Under parallel specialists, the PostToolUse hook lost rows to SQLite lock contention with the MCP server, and a
specialist wrote source_type "transcript", which can never satisfy the "commentary" coverage requirement.
"""
import asyncio
import sqlite3
import time

import pytest

from conftest import CORPUS, EV_STATS, OPENER, POST, REPO


async def test_hook_never_blocks_on_the_store_and_rows_arrive_after_ingest(tmp_path, store):
    from storydesk.agents import build_options
    from storydesk.runner import ingest_tool_log

    run_id = store.start_run("smoke", OPENER, POST, route="test")
    opts = build_options("smoke", run_id=run_id, as_of=POST, stats_db=tmp_path / "stats.duckdb",
                         store_path=store.path, corpus_dir=CORPUS, digest_dir=tmp_path / "digest")
    hook = opts.hooks["PostToolUse"][0].hooks[0]
    event = {"session_id": "s", "cwd": str(REPO), "transcript_path": "", "hook_event_name": "PostToolUse",
             "tool_name": "mcp__desk__search_fans", "tool_input": {"query": "bench"}, "tool_response": [],
             "tool_use_id": "t9", "agent_id": "agent-fans", "agent_type": "fans"}

    locker = sqlite3.connect(store.path, timeout=0)
    locker.execute("BEGIN EXCLUSIVE")  # another writer (the MCP server) holds the store
    try:
        started = time.monotonic()
        await asyncio.wait_for(hook(event, "t9", None), timeout=2)
        assert time.monotonic() - started < 1.0
    finally:
        locker.rollback()
        locker.close()

    ingest_tool_log(store, run_id)
    ingest_tool_log(store, run_id)  # idempotent: no duplicate rows
    con = sqlite3.connect(store.path)
    rows = con.execute("SELECT agent_id, agent_type, tool FROM tool_calls WHERE run_id = ? AND tool LIKE 'mcp__desk__%'",
                       (run_id,)).fetchall()
    assert rows == [("agent-fans", "fans", "mcp__desk__search_fans")]


def test_source_type_must_be_a_known_source(post_ctx):
    from storydesk.tools import SOURCE_TYPES, ToolError, write_finding

    assert {"stats", "commentary", "media", "fans", "press"} <= set(SOURCE_TYPES)
    with pytest.raises(ToolError):
        write_finding(post_ctx, agent="commentary", source_type="transcript", kind="nothing_found",
                      claim="No commentary before the cutoff", evidence=[])
    with pytest.raises(ToolError):
        write_finding(post_ctx, agent="stats", source_type="stats", kind="checked", number=1,
                      query="SELECT 1", claim="One", evidence=[{**EV_STATS, "source_type": "spreadsheet"}])


def test_contract_names_the_source_types():
    from storydesk.tools import SOURCE_TYPES

    contract = (REPO / "prompts" / "contract.md").read_text(encoding="utf-8")
    for source in SOURCE_TYPES:
        assert f"`{source}`" in contract, source
