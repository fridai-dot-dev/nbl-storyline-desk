"""The stdio MCP process that keeps tools identical on both execution routes."""

from __future__ import annotations

import json
import os
import sys
from functools import wraps
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer

from .store import Store
from .tools import (
    ToolContext, create_tracking_table, get_game, read_findings, search_fans, search_media,
    search_transcripts, stats_sql, update_tracking_table, write_finding,
)


TOOL_NAMES = [
    "stats_sql", "get_game", "search_transcripts", "search_fans", "search_media",
    "write_finding", "read_findings", "create_tracking_table", "update_tracking_table",
]
server = MCPServer(name="desk", title="NBL Storyline Desk")


def _context() -> ToolContext:
    required = ("STORYDESK_RUN_ID", "STORYDESK_AS_OF", "STORYDESK_STATS_DB", "STORYDESK_STORE", "STORYDESK_CORPUS")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError("missing Storyline Desk environment: " + ", ".join(missing))
    store = Store(os.environ["STORYDESK_STORE"])
    store.init()
    return ToolContext(
        stats_db=os.environ["STORYDESK_STATS_DB"], store=store, corpus_dir=os.environ["STORYDESK_CORPUS"],
        run_id=int(os.environ["STORYDESK_RUN_ID"]), as_of=os.environ["STORYDESK_AS_OF"],
    )


def _logged(name: str, function: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        ctx = _context()
        ctx.store.log_tool_call(ctx.run_id, None, None, name, json.dumps(kwargs, default=str))
        return function(ctx, *args, **kwargs)
    return wrapped


@server.tool(name="stats_sql", description="Run cutoff-safe SQL over results, box_team, box_player or pbp.")
async def mcp_stats_sql(sql: str, limit: int = 200) -> dict[str, Any]:
    return _logged("stats_sql", stats_sql)(sql=sql, limit=limit)


@server.tool(name="get_game", description="Get cutoff-safe fixture, result and quarter-score metadata for one game.")
async def mcp_get_game(match_id: str) -> dict[str, Any]:
    return _logged("get_game", get_game)(match_id=match_id)


@server.tool(name="search_transcripts", description="Search timestamped commentary and transcript excerpts before the cutoff.")
async def mcp_search_transcripts(query: str, limit: int = 20) -> list[dict[str, Any]]:
    return _logged("search_transcripts", search_transcripts)(query=query, limit=limit)


@server.tool(name="search_fans", description="Search anonymised fan reactions posted before the cutoff.")
async def mcp_search_fans(query: str, limit: int = 20) -> list[dict[str, Any]]:
    return _logged("search_fans", search_fans)(query=query, limit=limit)


@server.tool(name="search_media", description="Search media published before the cutoff date.")
async def mcp_search_media(query: str, limit: int = 20) -> list[dict[str, Any]]:
    return _logged("search_media", search_media)(query=query, limit=limit)


@server.tool(name="write_finding", description="Persist one sourced finding for deterministic review and release gates.")
async def mcp_write_finding(
    agent: str,
    source_type: str,
    claim: str,
    kind: str,
    evidence: list[dict[str, Any]],
    number: float | int | None = None,
    query: str | None = None,
    chart: dict[str, Any] | None = None,
    parent_id: int | None = None,
    audience: list[str] | None = None,
    sensitivity: str | None = None,
    prompted_by: str | None = None,
) -> int:
    return _logged("write_finding", write_finding)(
        agent=agent, source_type=source_type, claim=claim, kind=kind, evidence=evidence,
        number=number, query=query, chart=chart, parent_id=parent_id,
        audience=audience or [], sensitivity=sensitivity, prompted_by=prompted_by,
    )


@server.tool(name="read_findings", description="Read findings already written during the current run.")
async def mcp_read_findings(agent: str | None = None) -> list[dict[str, Any]]:
    return _logged("read_findings", read_findings)(agent=agent)


@server.tool(name="create_tracking_table", description="Create a small run-local tracking table with typed columns.")
async def mcp_create_tracking_table(name: str, columns: dict[str, str]) -> str:
    return _logged("create_tracking_table", create_tracking_table)(name=name, columns=columns)


@server.tool(name="update_tracking_table", description="Append rows to a run-local tracking table.")
async def mcp_update_tracking_table(name: str, rows: list[dict[str, Any]]) -> int:
    return _logged("update_tracking_table", update_tracking_table)(name=name, rows=rows)


def main() -> None:
    if "--list-tools" in sys.argv:
        print(json.dumps(TOOL_NAMES))
        return
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
