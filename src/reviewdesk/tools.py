"""The desk's in-process MCP tools: read the week's data, keep findings, and record drafts."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

SERVER = "reviewdesk"
READ_TOOLS = ("read_data", "read_findings", "write_finding")
WRITE_TOOLS = ("post_review_reply", "draft_promo")
FINDING_REQUIRED = ("id", "thread", "headline", "premise")


def tool_id(name: str) -> str:
    return f"mcp__{SERVER}__{name}"


@dataclass
class DeskData:
    tables: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    outbox: list[dict[str, Any]] = field(default_factory=list)


def _text(value: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}


def _error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "is_error": True}


def _object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required}


def desk_tools(desk: DeskData) -> list[Any]:
    @tool(
        "read_data",
        "Read the rows of one of this week's data tables, optionally narrowed to one store or region.",
        _object({"table": {"type": "string"}, "store": {"type": "integer"}, "region": {"type": "string"}}, ["table"]),
    )
    async def read_data(args: dict[str, Any]) -> dict[str, Any]:
        table = args["table"]
        if table not in desk.tables:
            return _error(f"Unknown table {table!r}. Tables: {', '.join(sorted(desk.tables)) or 'none'}.")
        rows = desk.tables[table]
        if args.get("store") is not None:
            rows = [row for row in rows if row.get("store") == args["store"]]
        if args.get("region") is not None:
            rows = [row for row in rows if row.get("region") == args["region"]]
        return _text(rows)

    @tool("read_findings", "Read the findings written so far this week.", _object({}, []))
    async def read_findings(args: dict[str, Any]) -> dict[str, Any]:
        return _text(desk.findings)

    @tool(
        "write_finding",
        "Record one finding. It needs an id, a thread, a headline, a premise and at least one piece of evidence.",
        _object({"finding": {"type": "object"}}, ["finding"]),
    )
    async def write_finding(args: dict[str, Any]) -> dict[str, Any]:
        finding = args["finding"]
        missing = [name for name in FINDING_REQUIRED if not finding.get(name)]
        if not finding.get("evidence"):
            missing.append("evidence")
        if missing:
            return _error(f"The finding is missing: {', '.join(missing)}.")
        desk.findings.append(copy.deepcopy(finding))
        return _text({"saved": finding["id"]})

    @tool(
        "post_review_reply",
        "Draft a public reply to a customer review. It is recorded as a draft and never posted from here.",
        _object(
            {
                "review_id": {"type": "string"}, "story_id": {"type": "string"},
                "text": {"type": "string"}, "approval_id": {"type": "string"},
            },
            ["review_id", "story_id", "text", "approval_id"],
        ),
    )
    async def post_review_reply(args: dict[str, Any]) -> dict[str, Any]:
        return _draft("post_review_reply", args)

    @tool(
        "draft_promo",
        "Draft a promotion for some stores. It is recorded as a draft and never sent from here.",
        _object(
            {
                "story_id": {"type": "string"}, "stores": {"type": "array", "items": {"type": "integer"}},
                "offer": {"type": "string"}, "rationale": {"type": "string"}, "approval_id": {"type": "string"},
            },
            ["story_id", "stores", "offer", "rationale", "approval_id"],
        ),
    )
    async def draft_promo(args: dict[str, Any]) -> dict[str, Any]:
        return _draft("draft_promo", args)

    def _draft(name: str, args: dict[str, Any]) -> dict[str, Any]:
        desk.outbox.append({**copy.deepcopy(args), "tool": name, "status": "draft"})
        return _text({"status": "draft", "tool": name})

    return [read_data, read_findings, write_finding, post_review_reply, draft_promo]


def build_server(desk: DeskData) -> Any:
    return create_sdk_mcp_server(SERVER, tools=desk_tools(desk))
