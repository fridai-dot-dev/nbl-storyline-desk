"""Claude Agent SDK options for each Review Desk role. Code runs each role as its own session."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

from .approvals import keep_stream_open, make_approval_callback
from .schema import THEME_CODING_SCHEMA
from .tools import READ_TOOLS, WRITE_TOOLS, DeskData, build_server, tool_id

AGENT_DIR = Path(__file__).resolve().parent / "agent"
PROMPTS = Path(__file__).resolve().parent / "prompts"
ROLES = ("lead", "customer_voice", "operations", "product", "marketing", "context", "judge")
APPROVAL_ROLES = ("lead", "marketing")

_OPUS, _SONNET = "claude-opus-5-5", "claude-sonnet-5-5"
# role: (model, effort, built-in tools, skills, pre-approved tools, gated write tools, budget in USD)
_ROLE_SPECS: dict[str, tuple[str, str, list[str], list[str], list[str], tuple[str, ...], float]] = {
    "lead": (_OPUS, "high", ["Skill"], ["theme-coding", "promo-effect"], ["read_data", "read_findings", "write_finding"], WRITE_TOOLS, 2.0),
    "customer_voice": (_SONNET, "medium", ["Skill"], ["theme-coding"], ["read_data", "StructuredOutput"], (), 0.75),
    "operations": (_SONNET, "medium", ["Bash", "Skill"], ["promo-effect"], ["Bash", "read_data", "write_finding"], (), 0.75),
    "product": (_SONNET, "medium", ["Skill"], ["theme-coding"], ["read_data", "read_findings", "write_finding"], (), 0.75),
    "marketing": (_SONNET, "medium", ["Skill"], ["promo-effect"], ["read_data", "read_findings", "write_finding"], ("draft_promo",), 0.75),
    "context": (_SONNET, "low", [], [], ["read_data", "write_finding"], (), 0.75),
    "judge": (_OPUS, "high", [], [], ["read_findings"], (), 1.0),
}
_DESK_TOOLS = (*READ_TOOLS, *WRITE_TOOLS)


def _prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8").strip()


def _pre_approved(name: str) -> str:
    # StructuredOutput is the tool Claude Code adds for output_format; pre-approved so dontAsk can't refuse it.
    return name if name in ("Bash", "Skill", "StructuredOutput") else tool_id(name)


def _sandbox() -> dict[str, Any]:
    # The SDK's SandboxSettings type does not list failIfUnavailable, strictAllowlist or filesystem; Claude Code's
    # sandbox settings do, and the SDK passes this dict through --settings, which can set any user-scope key.
    return {
        "enabled": True, "autoAllowBashIfSandboxed": True, "allowUnsandboxedCommands": False,
        "failIfUnavailable": True, "network": {"allowedDomains": [], "strictAllowlist": True},
        "filesystem": {"denyWrite": [str(AGENT_DIR)]},
    }


def build_options(
    role: str, *, data_dir: str | Path | None = None, approvals: Iterable[Mapping[str, Any]] = (),
    staff_names: Iterable[str] = (), desk: DeskData | None = None, resume: str | None = None,
    fork_session: bool = False,
) -> ClaudeAgentOptions:
    if role not in _ROLE_SPECS:
        raise ValueError(f"Unknown role {role!r}; roles are {', '.join(ROLES)}")
    model, effort, tools, skills, allowed, gated, budget = _ROLE_SPECS[role]
    prompt = _prompt(role) + "\n\n" + _prompt("contract")
    if role == "operations" and data_dir is not None:
        prompt += f"\n\nThis run's data folder is {data_dir}."
    disallowed = ["WebSearch", "WebFetch", "Write", "Edit"]
    if "Bash" not in tools:
        disallowed.append("Bash")
    disallowed += [tool_id(name) for name in WRITE_TOOLS if name not in gated]
    options: dict[str, Any] = {
        "model": model, "effort": effort, "system_prompt": prompt,
        "setting_sources": ["project"], "cwd": str(AGENT_DIR), "skills": list(skills), "tools": list(tools),
        "allowed_tools": [_pre_approved(name) for name in allowed], "disallowed_tools": disallowed,
        "mcp_servers": {"reviewdesk": build_server(desk if desk is not None else DeskData())},
        "strict_mcp_config": True, "env": {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"},
        "max_budget_usd": budget, "resume": resume, "fork_session": fork_session,
    }
    if role in APPROVAL_ROLES:
        options.update(
            permission_mode="default", can_use_tool=make_approval_callback(approvals, staff_names),
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[keep_stream_open])]},
        )
    else:
        options["permission_mode"] = "dontAsk"
    if role == "customer_voice":
        options["output_format"] = {"type": "json_schema", "schema": THEME_CODING_SCHEMA}
    if role == "operations":
        options["sandbox"] = _sandbox()
    return ClaudeAgentOptions(**options)


def meeting_options(session_id: str, **kw: Any) -> ClaudeAgentOptions:
    return build_options("lead", resume=session_id, **kw)


def fork_options(session_id: str, **kw: Any) -> ClaudeAgentOptions:
    return build_options("lead", resume=session_id, fork_session=True, **kw)
