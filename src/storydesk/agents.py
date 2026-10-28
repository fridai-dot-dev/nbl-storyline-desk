"""One shared set of agent definitions for SDK and ``claude -p`` routes."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, HookMatcher

from .store import Store


ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "prompts"
TOOL_NAMES = (
    "stats_sql", "get_game", "search_transcripts", "search_fans", "search_media",
    "write_finding", "read_findings", "create_tracking_table", "update_tracking_table",
)
TOOL_IDS = [f"mcp__desk__{name}" for name in TOOL_NAMES]
RUN_TYPES: dict[str, dict[str, Any]] = {
    "pre_game": {"time_limit_s": 1800, "required_sources": ["stats", "commentary", "media", "fans"]},
    "post_game": {"time_limit_s": 1500, "required_sources": ["stats", "commentary", "fans"]},
    "supplemental": {"time_limit_s": 900, "required_sources": ["commentary", "media", "fans"]},
    "follow_up": {"time_limit_s": 600, "required_sources": ["stats", "commentary", "media", "fans"]},
    "smoke": {"time_limit_s": 180, "required_sources": []},  # proves tool access; writes no findings
}


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8").strip()


def _server_config(*, run_id: int, as_of: str, stats_db: str | Path, store_path: str | Path, corpus_dir: str | Path) -> dict[str, Any]:
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": ["-m", "storydesk.mcp_server"],
        "env": {
            "STORYDESK_RUN_ID": str(run_id), "STORYDESK_AS_OF": str(as_of),
            "STORYDESK_STATS_DB": str(stats_db), "STORYDESK_STORE": str(store_path),
            "STORYDESK_CORPUS": str(corpus_dir),
        },
    }


def _specialist_definitions() -> dict[str, AgentDefinition]:
    source_tools = {
        "stats": ["stats_sql", "get_game", "write_finding", "read_findings", "create_tracking_table", "update_tracking_table"],
        "commentary": ["search_transcripts", "get_game", "write_finding", "read_findings"],
        "media": ["search_media", "search_transcripts", "write_finding", "read_findings"],
        "fans": ["search_fans", "write_finding", "read_findings"],
    }
    descriptions = {
        "stats": "Checks NBL history, box scores and play-by-play with reproducible SQL.",
        "commentary": "Finds concrete moments and tension in the timestamped commentary corpus.",
        "media": "Connects previews, press conferences and dated media coverage to a usable angle.",
        "fans": "Samples fan reaction while keeping handles private and treating quotes as sensitive.",
    }
    return {
        name: AgentDefinition(
            description=descriptions[name], prompt=_prompt(name) + "\n\n" + _prompt("contract"),
            tools=[f"mcp__desk__{tool}" for tool in tools], mcpServers=["desk"],
            model="claude-sonnet-5-5", maxTurns=8, effort="medium", permissionMode="dontAsk",
        )
        for name, tools in source_tools.items()
    }


def _value(input_data: Any, key: str, default: Any = None) -> Any:
    if isinstance(input_data, dict):
        return input_data.get(key, default)
    return getattr(input_data, key, default)


def _tool_logging_hook(store_path: str | Path, run_id: int):
    async def callback(input_data: Any, tool_use_id: str | None = None, context: Any = None) -> dict[str, Any]:
        tool = _value(input_data, "tool_name") or _value(input_data, "tool") or "unknown_tool"
        args = _value(input_data, "tool_input") or _value(input_data, "input") or {}
        Store(store_path).log_tool_call(
            run_id, _value(input_data, "agent_id"), _value(input_data, "agent_type"),
            str(tool), json.dumps(args, default=str),
        )
        return {}
    return callback


def _lifecycle_logging_hook(store_path: str | Path, run_id: int):
    async def callback(input_data: Any, tool_use_id: str | None = None, context: Any = None) -> dict[str, Any]:
        event = _value(input_data, "hook_event_name", "SubagentLifecycle")
        Store(store_path).log_tool_call(
            run_id, _value(input_data, "agent_id"), _value(input_data, "agent_type"),
            f"lifecycle__{event}", "{}",
        )
        return {}
    return callback


def build_options(
    run_type: str, *, run_id: int, as_of: str, stats_db: str | Path, store_path: str | Path,
    corpus_dir: str | Path, digest_dir: str | Path, question: str | None = None,
    anchor_finding_id: int | None = None,
) -> ClaudeAgentOptions:
    if run_type not in RUN_TYPES:
        raise ValueError(f"unknown run type: {run_type}")
    config = RUN_TYPES[run_type]
    system_prompt = "\n\n".join([
        _prompt("lead"), _prompt("contract"), _prompt(f"runs/{run_type}"),
        f"This run has a US$5.00 budget and a {config['time_limit_s']} second wall-clock limit.",
    ])
    tool_hook = _tool_logging_hook(store_path, run_id)
    lifecycle_hook = _lifecycle_logging_hook(store_path, run_id)
    return ClaudeAgentOptions(
        model="claude-opus-5-5", system_prompt=system_prompt, agents=_specialist_definitions(),
        mcp_servers={"desk": _server_config(run_id=run_id, as_of=as_of, stats_db=stats_db,
                                             store_path=store_path, corpus_dir=corpus_dir)},
        allowed_tools=["Agent", *TOOL_IDS],
        disallowed_tools=["WebSearch", "WebFetch", "Bash", "Write", "Edit"],
        permission_mode="dontAsk", env={
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
            "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "5",
            "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
        },
        max_budget_usd=5.0, setting_sources=[], strict_mcp_config=True,
        hooks={
            "PostToolUse": [HookMatcher(matcher=None, hooks=[tool_hook], timeout=5)],
            "SubagentStart": [HookMatcher(matcher=None, hooks=[lifecycle_hook], timeout=5)],
            "SubagentStop": [HookMatcher(matcher=None, hooks=[lifecycle_hook], timeout=5)],
        },
    )


def build_prompt(
    run_type: str, *, digest_dir: str | Path, question: str | None = None,
    anchor_finding_id: int | None = None,
) -> str:
    if run_type not in RUN_TYPES:
        raise ValueError(f"unknown run type: {run_type}")
    directory = Path(digest_dir)
    digest_parts = []
    if directory.exists():
        for source in sorted(directory.glob("*.md")):
            digest_parts.append(f"## {source.name}\n{source.read_text(encoding='utf-8').strip()}")
    text = "\n\n".join([
        "Run brief:\n" + _prompt(f"runs/{run_type}"),
        "Starting-set digest:\n" + ("\n\n".join(digest_parts) or "No digest files were prepared."),
    ])
    if run_type == "follow_up":
        text += f"\n\nAnchor finding ID: {anchor_finding_id}\nQuestion: {question or ''}"
    return text


def build_cli_config(run_type: str, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    options = build_options(run_type, **kwargs)
    agents_json: dict[str, Any] = {}
    for name, agent in (options.agents or {}).items():
        agents_json[name] = {
            "description": agent.description, "prompt": agent.prompt, "tools": agent.tools,
            "mcpServers": agent.mcpServers, "model": agent.model, "maxTurns": agent.maxTurns,
            "effort": agent.effort, "permissionMode": agent.permissionMode,
        }
    return agents_json, {"mcpServers": options.mcp_servers}
