"""D12: the Agent SDK configuration, tested without a model call. Same definitions feed the `claude -p` fallback."""
import pytest

from conftest import CORPUS, POST, REPO

SPECIALISTS = {"stats", "commentary", "media", "fans"}
RUN_TYPES = ["pre_game", "post_game", "supplemental", "follow_up"]
OPUS = {"opus", "claude-opus-5-5"}
SONNET = {"sonnet", "claude-sonnet-5-5"}


def _prompt(name):
    p = REPO / "prompts" / f"{name}.md"
    assert p.exists(), f"missing prompt file {p}"
    text = p.read_text(encoding="utf-8").strip()
    assert len(text) > 200, f"{p} is a stub"
    return text


def _options(run_type, tmp_path):
    from storydesk.agents import build_options

    return build_options(run_type, run_id=7, as_of=POST, stats_db=tmp_path / "stats.duckdb",
                         store_path=tmp_path / "store.db", corpus_dir=CORPUS, digest_dir=tmp_path / "digest")


@pytest.mark.parametrize("run_type", RUN_TYPES)
def test_options_shape(run_type, tmp_path):
    from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions

    opts = _options(run_type, tmp_path)
    assert isinstance(opts, ClaudeAgentOptions)
    assert opts.model in OPUS
    assert _prompt("lead") in str(opts.system_prompt)

    assert set(opts.agents) == SPECIALISTS
    for name, agent in opts.agents.items():
        assert isinstance(agent, AgentDefinition)
        assert agent.model in SONNET
        assert _prompt(name) in agent.prompt
        assert agent.mcpServers and "desk" in [s if isinstance(s, str) else next(iter(s)) for s in agent.mcpServers]
        assert any(t.startswith("mcp__desk__") for t in (agent.tools or []))
        assert isinstance(agent.maxTurns, int) and agent.maxTurns > 0
        assert agent.description

    desk = opts.mcp_servers["desk"]
    assert "storydesk.mcp_server" in " ".join([desk["command"], *desk.get("args", [])])
    assert desk["env"]["STORYDESK_AS_OF"] == POST
    assert desk["env"]["STORYDESK_RUN_ID"] == "7"

    assert opts.env["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] == "1"
    assert opts.env["CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS"] == "5"
    assert opts.env.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY") == "1"
    assert 0 < opts.max_budget_usd <= 5
    assert {"WebSearch", "WebFetch"} <= set(opts.disallowed_tools)
    assert "Agent" in opts.allowed_tools
    assert opts.setting_sources == []
    assert opts.strict_mcp_config is True
    assert opts.hooks and opts.hooks.get("PostToolUse") and opts.hooks.get("SubagentStop")


def test_run_types_and_time_limits():
    from storydesk.agents import RUN_TYPES as CONFIG

    assert set(CONFIG) >= set(RUN_TYPES)
    assert CONFIG["post_game"]["time_limit_s"] == 1500
    assert {"stats", "commentary", "fans"} <= set(CONFIG["post_game"]["required_sources"])
    for rt in RUN_TYPES:
        assert CONFIG[rt]["time_limit_s"] > 0
        _prompt(f"runs/{rt}")


def test_follow_up_prompt_carries_question_and_anchor(tmp_path):
    from storydesk.agents import build_prompt

    q = "Where does this rank among other fourth-quarter collapses league-wide?"
    text = build_prompt("follow_up", digest_dir=tmp_path, question=q, anchor_finding_id=42)
    assert q in text and "42" in text


def test_cli_fallback_uses_the_same_definitions(tmp_path):
    from storydesk.agents import build_cli_config

    opts = _options("post_game", tmp_path)
    agents_json, mcp_json = build_cli_config("post_game", run_id=7, as_of=POST, stats_db=tmp_path / "stats.duckdb",
                                             store_path=tmp_path / "store.db", corpus_dir=CORPUS,
                                             digest_dir=tmp_path / "digest")
    assert set(agents_json) == SPECIALISTS
    for name in SPECIALISTS:
        assert agents_json[name]["prompt"] == opts.agents[name].prompt
        assert agents_json[name]["model"] == opts.agents[name].model
    assert mcp_json["mcpServers"]["desk"]["env"]["STORYDESK_AS_OF"] == POST


def test_judge_prompt_exists():
    _prompt("judge")
