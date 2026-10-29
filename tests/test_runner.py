"""D7 usage ledger, the wall-clock deadline (D10's mechanism), the --live guard, and the MCP server's tool list."""
import asyncio
import json

import pytest

from conftest import OPENER, POST, fake_result, run_py

TOOL_NAMES = {
    "stats_sql", "get_game", "search_transcripts", "search_fans", "search_media",
    "write_finding", "read_findings", "create_tracking_table", "update_tracking_table",
}


def test_record_result_writes_the_ledger(store):
    from storydesk.runner import record_result

    run_id = store.start_run("post_game", OPENER, POST, route="sdk")
    record_result(store, run_id, fake_result(1.234, 1180), route="sdk", num_agents=5)
    run = store.get_run(run_id)
    assert run["status"] == "complete"
    assert run["cost_usd"] == pytest.approx(1.234)
    assert run["duration_s"] == pytest.approx(1180)
    assert run["model_usage"]["claude-opus-5-5"]["outputTokens"] == 200
    assert run["route"] == "sdk"
    assert run["num_agents"] == 5


async def test_deadline_interrupts_a_slow_run():
    from storydesk.runner import enforce_deadline

    interrupted = []

    async def slow():
        await asyncio.sleep(5)
        return "late"

    async def interrupt():
        interrupted.append(True)

    status, result = await enforce_deadline(slow(), 0.2, interrupt)
    assert status == "timeout" and interrupted and result is None

    async def quick():
        return "ok"

    status, result = await enforce_deadline(quick(), 2, interrupt)
    assert (status, result) == ("complete", "ok")


def test_run_refuses_without_live_flag():
    out = run_py("-m", "storydesk", "run", "post_game", "--game", OPENER)
    assert out.returncode != 0
    assert "--live" in (out.stdout + out.stderr)


def test_mcp_server_lists_its_tools():
    out = run_py("-m", "storydesk.mcp_server", "--list-tools")
    assert out.returncode == 0, out.stderr
    assert set(json.loads(out.stdout)) == TOOL_NAMES


def test_mcp_tools_take_no_as_of_argument():
    """The cutoff comes from the server's environment, so an agent can't widen it."""
    import inspect

    from storydesk import tools

    for name in TOOL_NAMES:
        params = inspect.signature(getattr(tools, name)).parameters
        assert "as_of" not in params, f"{name} must not accept as_of from the agent"
