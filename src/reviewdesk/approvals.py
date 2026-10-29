"""The approval callback: outward-facing tools need an approval record, and staff names are stripped."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

from .tools import WRITE_TOOLS, tool_id

STAFF_PLACEHOLDER = "[staff member]"
APPROVED_STANCES = ("push", "use_if_raised")


def strip_staff_names(value: Any, staff_names: Iterable[str]) -> Any:
    """Return a copy of ``value`` with each staff name replaced by a placeholder, in every string."""
    names = sorted({name.strip() for name in staff_names if name and name.strip()}, key=len, reverse=True)
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(name) for name in names) + r")(?!\w)", re.IGNORECASE) if names else None

    def walk(item: Any) -> Any:
        if isinstance(item, dict):
            return {key: walk(inner) for key, inner in item.items()}
        if isinstance(item, list):
            return [walk(inner) for inner in item]
        if isinstance(item, str) and pattern:
            return pattern.sub(STAFF_PLACEHOLDER, item)
        return item

    return walk(value)


def make_approval_callback(approvals: Iterable[Mapping[str, Any]], staff_names: Iterable[str]):
    records = [dict(record) for record in approvals]
    names = list(staff_names)
    write_tools = {tool_id(name): name for name in WRITE_TOOLS}

    async def can_use_tool(tool_name: str, input_data: dict[str, Any], context: Any) -> PermissionResultAllow | PermissionResultDeny:
        short = write_tools.get(tool_name)
        if short is None:
            return PermissionResultDeny(message=f"{tool_name} is not a tool this desk allows.")
        story_id = input_data.get("story_id")
        approved = story_id is not None and any(
            record.get("id") == input_data.get("approval_id") and record.get("tool") == short
            and record.get("story_id") == story_id and record.get("stance") in APPROVED_STANCES
            for record in records
        )
        if not approved:
            return PermissionResultDeny(message=f"{short} needs an approval record for this story: none matches this tool, story and stance.")
        return PermissionResultAllow(updated_input=strip_staff_names(input_data, names))

    return can_use_tool


async def keep_stream_open(input_data: Any, tool_use_id: str | None, context: Any) -> dict[str, Any]:
    # A PreToolUse hook is needed so the SDK keeps the stream open for can_use_tool. It must not decide anything.
    return {"continue_": True}
