"""R3 checks for the reviewdesk SDK module (decision rows 42-47). Construction only: no model calls, no network.

Each role runs as its own code-orchestrated session (not a subagent of the lead), because sandbox,
output_format, can_use_tool, setting_sources and cwd are session options, not AgentDefinition fields.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext
from jsonschema import Draft202012Validator

from conftest import REPO
from test_r3_support import REVIEWDESK, fixture

R = "mcp__reviewdesk__"
WRITE = {f"{R}post_review_reply", f"{R}draft_promo"}
SKILLS = {"theme-coding", "promo-effect"}
UNSAFE_MODES = {"dontAsk", "bypassPermissions", "acceptEdits", "auto", "plan"}

ROLE_MATRIX = {
    #  role:            (model,               effort,   built-in tools,    skills,                           pre-approved tools,                                       gated write tools)
    "lead":           ("claude-opus-5-5",   "high",   ["Skill"],         ["theme-coding", "promo-effect"], [f"{R}read_data", f"{R}read_findings", f"{R}write_finding"], WRITE),
    "customer_voice": ("claude-sonnet-5-5", "medium", ["Skill"],         ["theme-coding"],                 [f"{R}read_data", "StructuredOutput"],                      set()),
    "operations":     ("claude-sonnet-5-5", "medium", ["Bash", "Skill"], ["promo-effect"],                 ["Bash", f"{R}read_data", f"{R}write_finding"],              set()),
    "product":        ("claude-sonnet-5-5", "medium", ["Skill"],         ["theme-coding"],                 [f"{R}read_data", f"{R}read_findings", f"{R}write_finding"], set()),
    "marketing":      ("claude-sonnet-5-5", "medium", ["Skill"],         ["promo-effect"],                 [f"{R}read_data", f"{R}read_findings", f"{R}write_finding"], {f"{R}draft_promo"}),
    "context":        ("claude-sonnet-5-5", "low",    [],                [],                               [f"{R}read_data", f"{R}write_finding"],                      set()),
    "judge":          ("claude-opus-5-5",   "high",   [],                [],                               [f"{R}read_findings"],                                      set()),
}


def _options(role: str, **kw) -> ClaudeAgentOptions:
    from reviewdesk.agents import build_options

    approvals = fixture("approvals.json")["approvals"]
    staff = fixture("roster.json")["staff_names"]
    return build_options(role, approvals=approvals, staff_names=staff, **kw)


def _allowed_bases(options: ClaudeAgentOptions) -> set[str]:
    return {name.split("(", 1)[0] for name in options.allowed_tools}


def _ctx() -> ToolPermissionContext:
    return ToolPermissionContext(tool_use_id="toolu_test")


# ---------- 42: every role constructs offline ----------

def test_r3_row_42_roles_are_the_lead_five_specialists_and_the_judge():
    from reviewdesk.agents import ROLES

    assert ROLES == ("lead", "customer_voice", "operations", "product", "marketing", "context", "judge")


@pytest.mark.parametrize("role", list(ROLE_MATRIX))
def test_r3_row_42_each_role_builds_its_own_session_options(role):
    model, effort, tools, skills, allowed, _gated = ROLE_MATRIX[role]
    options = _options(role)
    assert isinstance(options, ClaudeAgentOptions)
    assert options.model == model and options.effort == effort
    assert options.agents is None, "roles run as code-orchestrated sessions, not subagents"
    assert options.tools == tools and options.skills == skills
    assert set(allowed) <= _allowed_bases(options)
    prompt = options.system_prompt
    assert isinstance(prompt, str)
    contract = (REVIEWDESK / "prompts" / "contract.md").read_text(encoding="utf-8").strip()
    role_prompt = (REVIEWDESK / "prompts" / f"{role}.md").read_text(encoding="utf-8").strip()
    assert role_prompt in prompt and contract in prompt
    assert options.max_budget_usd and options.max_budget_usd > 0
    assert options.strict_mcp_config is True and set(options.mcp_servers) == {"reviewdesk"}
    assert {"WebSearch", "WebFetch", "Write", "Edit"} <= set(options.disallowed_tools)
    if "Bash" not in tools:
        assert "Bash" in options.disallowed_tools
    assert options.env.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY") == "1"


def test_r3_row_42_unknown_role_is_refused():
    from reviewdesk.agents import build_options

    with pytest.raises(ValueError):
        build_options("finance")


def test_r3_row_42_desk_tools_record_drafts_and_never_send():
    from reviewdesk.tools import DeskData, build_server, desk_tools

    desk = DeskData(tables={"pos_by_hour": [{"store": 12, "hour": 20, "transactions": 41},
                                             {"store": 14, "hour": 20, "transactions": 37}]})
    tools = {tool.name: tool for tool in desk_tools(desk)}
    assert set(tools) == {"read_data", "read_findings", "write_finding", "post_review_reply", "draft_promo"}
    server = build_server(desk)
    assert server["type"] == "sdk" and server["name"] == "reviewdesk"

    rows = asyncio.run(tools["read_data"].handler({"table": "pos_by_hour", "store": 12}))
    assert json.loads(rows["content"][0]["text"]) == [{"store": 12, "hour": 20, "transactions": 41}]
    missing = asyncio.run(tools["read_data"].handler({"table": "payroll"}))
    assert missing.get("is_error") is True

    finding = {"id": "dd-09", "thread": "spike", "headline": "Why?", "premise": "p", "evidence": [{"source": "POS by hour", "detail": "d"}]}
    asyncio.run(tools["write_finding"].handler({"finding": finding}))
    assert desk.findings == [finding]
    bad = asyncio.run(tools["write_finding"].handler({"finding": {"id": "dd-10"}}))
    assert bad.get("is_error") is True and len(desk.findings) == 1

    asyncio.run(tools["post_review_reply"].handler({"review_id": "gbp-31-0207", "finding_id": "dd-03",
                                                     "text": "Thanks!", "approval_id": "appr-0001"}))
    asyncio.run(tools["draft_promo"].handler({"finding_id": "dd-04", "stores": [14], "offer": "o",
                                               "rationale": "r", "approval_id": "appr-0002"}))
    for name in ("post_review_reply", "draft_promo"):
        assert {"finding_id", "approval_id"} <= set(tools[name].input_schema["required"]), name
    assert [item["tool"] for item in desk.outbox] == ["post_review_reply", "draft_promo"]
    assert all(item["status"] == "draft" for item in desk.outbox)


# ---------- 43: structured output for theme coding, and the batch builder ----------

def test_r3_row_43_customer_voice_returns_structured_theme_coding():
    from reviewdesk.schema import THEME_CODING_SCHEMA

    options = _options("customer_voice")
    assert options.output_format == {"type": "json_schema", "schema": THEME_CODING_SCHEMA}
    assert "StructuredOutput" in options.allowed_tools, "dontAsk would refuse the tool output_format adds"
    Draft202012Validator.check_schema(THEME_CODING_SCHEMA)
    Draft202012Validator(THEME_CODING_SCHEMA).validate(fixture("theme_coding_sample.json"))
    for role in set(ROLE_MATRIX) - {"customer_voice"}:
        assert _options(role).output_format is None, role


def _walk(schema):
    yield schema
    for value in schema.values():
        if isinstance(value, dict):
            yield from _walk(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield from _walk(item)


@pytest.mark.parametrize("name", ["THEME_CODING_SCHEMA", "REVIEW_CODING_SCHEMA"])
def test_r3_row_43_coding_schemas_use_only_structured_output_keywords(name):
    from reviewdesk import schema

    unsupported = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
                   "minLength", "maxLength", "pattern", "maxItems", "uniqueItems", "if", "then", "not"}
    for node in _walk(getattr(schema, name)):
        assert not unsupported & set(node), unsupported & set(node)
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False
            assert set(node.get("required", [])) == set(node.get("properties", {}))
        assert node.get("minItems", 0) in (0, 1)


def test_r3_row_43_bulk_coding_builds_a_message_batch_request_list():
    from reviewdesk.batches import BATCH_MODEL, build_theme_coding_batch
    from reviewdesk.schema import REVIEW_CODING_SCHEMA

    reviews = fixture("reviews.json")["reviews"]
    requests = build_theme_coding_batch(reviews)
    assert len(requests) == len(reviews)
    ids = [request["custom_id"] for request in requests]
    assert len(set(ids)) == len(ids) and all(re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", cid) for cid in ids)
    for request, review in zip(requests, reviews):
        assert set(request) == {"custom_id", "params"}
        params = request["params"]
        assert params["model"] == BATCH_MODEL == "claude-haiku-5-5" and params["max_tokens"] > 0
        assert params["output_config"] == {"format": {"type": "json_schema", "schema": REVIEW_CODING_SCHEMA}}
        assert "output_format" not in params, "the Messages API takes output_config.format"
        assert params["messages"][0]["role"] == "user" and review["text"] in json.dumps(params["messages"])
        assert review["author"] not in json.dumps(request), "reviewer names never leave the desk"
        assert "theme" in params["system"].lower()
    with pytest.raises(ValueError):
        build_theme_coding_batch([reviews[0], reviews[0]])


def test_r3_row_43_batch_builder_makes_no_call():
    text = (REVIEWDESK / "batches.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(?:import|from)\s+(?:anthropic|httpx|requests|urllib|socket)\b", text, re.M)


# ---------- 44: the approval callback ----------

def _callback():
    from reviewdesk.approvals import make_approval_callback

    return make_approval_callback(fixture("approvals.json")["approvals"], fixture("roster.json")["staff_names"])


@pytest.mark.parametrize("tool,payload", [
    (f"{R}post_review_reply", {"review_id": "gbp-31-0207", "finding_id": "dd-03", "text": "Thanks!"}),
    (f"{R}post_review_reply", {"review_id": "gbp-31-0207", "finding_id": "dd-03", "text": "Thanks!", "approval_id": "appr-9999"}),
    (f"{R}post_review_reply", {"review_id": "gbp-31-0207", "finding_id": "dd-03", "text": "Thanks!", "approval_id": "appr-0002"}),
    (f"{R}draft_promo", {"finding_id": "dd-02", "stores": [12], "offer": "o", "rationale": "r", "approval_id": "appr-0003"}),
    (f"{R}draft_promo", {"finding_id": "dd-02", "stores": [12], "offer": "o", "rationale": "r", "approval_id": "appr-0002"}),
    (f"{R}draft_promo", {"finding_id": "dd-04", "stores": [14], "offer": "o", "rationale": "r", "approval_id": "appr-0001"}),
    (f"{R}draft_promo", {"finding_id": "dd-04", "stores": [14], "offer": "o", "rationale": "r"}),
])
def test_r3_row_44_write_tools_are_denied_without_a_matching_sign_off(tool, payload):
    """A sign-off, recorded outside the email, names the tool, the insight and who signed off (appr-0003 names nobody)."""
    result = asyncio.run(_callback()(tool, payload, _ctx()))
    assert isinstance(result, PermissionResultDeny) and "sign-off" in result.message.lower()


@pytest.mark.parametrize("tool", ["Bash", "WebFetch", f"{R}delete_reviews", "post_review_reply"])
def test_r3_row_44_anything_else_reaching_the_callback_is_denied(tool):
    result = asyncio.run(_callback()(tool, {"approval_id": "appr-0001", "finding_id": "dd-03"}, _ctx()))
    assert isinstance(result, PermissionResultDeny)


def test_r3_row_44_approved_reply_is_allowed_with_staff_names_stripped():
    payload = {"review_id": "gbp-31-0207", "finding_id": "dd-03", "approval_id": "appr-0001",
               "text": "Thanks for the kind words about Priya! PRIYA's team and Mele Tupou say hi. Priyanka too.",
               "notes": ["Tomasz rostered", {"cc": "jordan"}]}
    original = json.loads(json.dumps(payload))
    result = asyncio.run(_callback()(f"{R}post_review_reply", payload, _ctx()))
    assert isinstance(result, PermissionResultAllow)
    out = result.updated_input
    assert out["text"] == ("Thanks for the kind words about [staff member]! [staff member]'s team and "
                           "[staff member] say hi. Priyanka too.")
    assert out["notes"] == ["[staff member] rostered", {"cc": "[staff member]"}]
    assert out["approval_id"] == "appr-0001" and out["review_id"] == "gbp-31-0207"
    assert payload == original, "the callback must not mutate the tool input"


def test_r3_row_44_approved_promo_is_allowed():
    payload = {"finding_id": "dd-04", "stores": [14, 22], "offer": "Add a lunch staff hour", "rationale": "waits", "approval_id": "appr-0002"}
    result = asyncio.run(_callback()(f"{R}draft_promo", payload, _ctx()))
    assert isinstance(result, PermissionResultAllow) and result.updated_input == payload


@pytest.mark.parametrize("role", ["lead", "marketing"])
def test_r3_row_44_callback_is_reachable_on_the_approval_roles(role):
    from reviewdesk.agents import APPROVAL_ROLES
    from reviewdesk.approvals import keep_stream_open

    assert APPROVAL_ROLES == ("lead", "marketing")
    gated = ROLE_MATRIX[role][5]
    options = _options(role)
    assert callable(options.can_use_tool)
    assert options.permission_mode not in UNSAFE_MODES, "dontAsk/bypass/accept modes never consult can_use_tool"
    assert not gated & _allowed_bases(options), "pre-approved tools skip the callback"
    assert not gated & set(options.disallowed_tools)
    assert WRITE - gated <= set(options.disallowed_tools)
    matchers = options.hooks["PreToolUse"]
    assert any(m.matcher is None and keep_stream_open in m.hooks for m in matchers)
    assert asyncio.run(keep_stream_open({}, None, None)) == {"continue_": True}, "an allow here would skip the callback"


@pytest.mark.parametrize("role", sorted(set(ROLE_MATRIX) - {"lead", "marketing"}))
def test_r3_row_44_other_roles_cannot_reach_write_tools(role):
    options = _options(role)
    assert options.can_use_tool is None and options.permission_mode == "dontAsk"
    assert WRITE <= set(options.disallowed_tools)


# ---------- 45: operations runs Python in a sandbox with no network ----------

def test_r3_row_45_operations_is_sandboxed_with_network_off():
    from reviewdesk.agents import AGENT_DIR

    options = _options("operations")
    sandbox = options.sandbox
    assert sandbox["enabled"] is True and sandbox["failIfUnavailable"] is True
    assert sandbox["allowUnsandboxedCommands"] is False and sandbox["autoAllowBashIfSandboxed"] is True
    assert sandbox["network"] == {"allowedDomains": [], "strictAllowlist": True}, \
        "no host is allow-listed, and strictAllowlist refuses every other host in every permission mode"
    assert options.permission_mode == "dontAsk"
    assert str(AGENT_DIR) in sandbox["filesystem"]["denyWrite"], "scratch goes to $TMPDIR, never the skills folder"
    assert "Bash" in options.tools and "Bash" in options.allowed_tools
    assert {"WebFetch", "WebSearch"} <= set(options.disallowed_tools)
    for role in set(ROLE_MATRIX) - {"operations"}:
        assert _options(role).sandbox is None, role


def test_r3_row_45_operations_is_told_where_the_data_is(tmp_path):
    options = _options("operations", data_dir=tmp_path)
    assert str(tmp_path) in options.system_prompt
    assert options.add_dirs == [], "an added dir would also add its .claude/skills to the project source"


# ---------- 46: meeting mode resumes, competing explanations fork ----------

def test_r3_row_46_meeting_mode_resumes_the_week_session():
    from reviewdesk.agents import meeting_options

    options = meeting_options("sess-week-43", approvals=fixture("approvals.json")["approvals"])
    assert options.resume == "sess-week-43" and options.fork_session is False
    assert options.model == ROLE_MATRIX["lead"][0] and callable(options.can_use_tool)


def test_r3_row_46_competing_explanations_fork_the_session():
    from reviewdesk.agents import fork_options

    first, second = fork_options("sess-week-43"), fork_options("sess-week-43")
    for options in (first, second):
        assert options.resume == "sess-week-43" and options.fork_session is True
    assert _options("lead").resume is None and _options("lead").fork_session is False


# ---------- 47: skills exist, load from project settings only, and are contained ----------

def _frontmatter(path: Path) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert match, f"{path} has no frontmatter"
    fields = dict(re.findall(r"^([a-z-]+): (.+)$", match.group(1), re.M))
    return fields


def test_r3_row_47_skill_packages_have_valid_frontmatter():
    from reviewdesk.agents import AGENT_DIR

    skill_dirs = sorted(path.parent for path in (AGENT_DIR / ".claude" / "skills").glob("*/SKILL.md"))
    assert {path.name for path in skill_dirs} == SKILLS
    for directory in skill_dirs:
        fields = _frontmatter(directory / "SKILL.md")
        assert fields.get("name") == directory.name
        assert len(fields.get("description", "")) > 40


@pytest.mark.parametrize("role", list(ROLE_MATRIX))
def test_r3_row_47_options_load_project_settings_only_from_a_pinned_cwd(role):
    from reviewdesk.agents import AGENT_DIR

    options = _options(role)
    assert options.setting_sources == ["project"], "skills set → SDK would default to user+project"
    assert Path(options.cwd) == AGENT_DIR and AGENT_DIR.is_absolute()
    assert isinstance(options.skills, list) and set(options.skills) <= SKILLS
    assert ("Skill" in options.tools) == bool(options.skills)


def test_r3_row_47_nothing_else_loads_on_the_walk_from_cwd_to_the_repo_root():
    from reviewdesk.agents import AGENT_DIR

    # Project settings and .mcp.json are read from cwd only; CLAUDE.md, skills, agents and commands are
    # discovered from cwd up to the repository root. "local" settings are a separate source and never load.
    for name in (".claude/settings.json", ".mcp.json"):
        assert not (AGENT_DIR / name).exists(), name
    directory = AGENT_DIR
    while True:
        for name in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", ".claude/agents", ".claude/commands"):
            assert not (directory / name).exists(), directory / name
        skills = directory / ".claude" / "skills"
        if directory == AGENT_DIR:
            assert {path.name for path in skills.iterdir()} == SKILLS
        else:
            assert not skills.exists(), skills
        if directory == REPO:
            break
        directory = directory.parent
    assert {path.name for path in AGENT_DIR.iterdir()} == {".claude"}, "the pinned cwd holds only .claude/skills"
    assert {path.name for path in (AGENT_DIR / ".claude").iterdir()} == {"skills"}
