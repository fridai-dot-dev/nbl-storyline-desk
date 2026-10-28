"""Regression checks for Sol's round-1 review (2026-10-28): the gaps the first suite didn't reach."""
import asyncio
import json
import sqlite3
import time
from types import SimpleNamespace

import pytest

from conftest import CORPUS, EV_STATS, OPENER, POST, PRE, Q3_ADL, REPO, SUPP, make_ctx


# ---------- critical: write_finding must be callable through the real MCP server ----------

def _desk_env(monkeypatch, stats_db, store, run_id, as_of):
    monkeypatch.setenv("STORYDESK_RUN_ID", str(run_id))
    monkeypatch.setenv("STORYDESK_AS_OF", as_of)
    monkeypatch.setenv("STORYDESK_STATS_DB", str(stats_db))
    monkeypatch.setenv("STORYDESK_STORE", str(store.path))
    monkeypatch.setenv("STORYDESK_CORPUS", str(CORPUS))


async def test_mcp_write_finding_schema_and_call(monkeypatch, stats_db, store):
    from storydesk.mcp_server import server

    run_id = store.start_run("post_game", OPENER, POST, route="test")
    _desk_env(monkeypatch, stats_db, store, run_id, POST)

    tools = {t.name: t for t in await server.list_tools()}
    props = set(tools["write_finding"].input_schema.get("properties", {}))
    assert {"agent", "source_type", "claim", "kind", "evidence", "number", "query", "chart", "parent_id"} <= props
    assert "kwargs" not in props

    result = await server.call_tool("write_finding", {
        "agent": "stats", "source_type": "stats", "kind": "checked",
        "claim": "Adelaide scored 26 points in the third quarter", "number": 26, "query": Q3_ADL,
        "evidence": [EV_STATS],
    })
    assert not result.is_error, result.content
    assert [f["claim"] for f in store.findings(run_id)] == ["Adelaide scored 26 points in the third quarter"]

    sql = await server.call_tool("stats_sql", {"sql": f"SELECT score FROM box_team WHERE match_id = '{OPENER}'"})
    assert not sql.is_error, sql.content


# ---------- critical: only the four cutoff-safe relations are reachable ----------

@pytest.mark.parametrize("sql", [
    "SELECT * FROM raw_results",
    "SELECT count(*) FROM raw_pbp",
    "SELECT * FROM match_ends",
    "SELECT * FROM (SELECT * FROM raw_box_team) t",
    "WITH x AS (SELECT * FROM raw_results) SELECT * FROM x",
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM duckdb_tables()",
])
def test_stats_sql_only_reaches_safe_relations(post_ctx, sql):
    from storydesk.tools import ToolError, stats_sql

    with pytest.raises(ToolError):
        stats_sql(post_ctx, sql)


def test_recheck_cannot_use_raw_tables(post_ctx, store, stats_db):
    from storydesk.gates import apply_gates
    from storydesk.tools import ToolError, write_finding

    sneaky = ("SELECT count(*) FROM raw_results WHERE match_time_utc >= '2026-10-01' "
              "AND (home_team_name = 'Adelaide 36ers' OR away_team_name = 'Adelaide 36ers')")
    try:
        fid = write_finding(post_ctx, agent="stats", source_type="stats", kind="checked",
                            claim="Adelaide played games in October", number=30, query=sneaky, evidence=[EV_STATS])
    except ToolError:
        return  # rejected at write time: fine
    apply_gates(store, post_ctx.run_id, stats_db=stats_db, as_of=POST)
    assert store.get_finding(fid)["status"] == "dropped"


# ---------- high: tool-call attribution comes from PostToolUse, not lifecycle events ----------

async def test_post_tool_use_hook_records_agent_identity(tmp_path, store):
    from storydesk.agents import build_options

    run_id = store.start_run("smoke", OPENER, POST, route="test")
    opts = build_options("smoke", run_id=run_id, as_of=POST, stats_db=tmp_path / "stats.duckdb",
                         store_path=store.path, corpus_dir=CORPUS, digest_dir=tmp_path / "digest")
    base = {"session_id": "s", "cwd": str(REPO), "transcript_path": ""}
    for matcher in opts.hooks["PostToolUse"]:
        for hook in matcher.hooks:
            await hook({**base, "hook_event_name": "PostToolUse", "tool_name": "mcp__desk__stats_sql",
                        "tool_input": {"sql": "SELECT 1"}, "tool_response": {}, "tool_use_id": "t1",
                        "agent_id": "agent-1", "agent_type": "stats"}, "t1", None)
    for matcher in opts.hooks["SubagentStop"]:
        for hook in matcher.hooks:
            await hook({**base, "hook_event_name": "SubagentStop", "stop_hook_active": False,
                        "agent_id": "agent-2", "agent_type": "fans", "agent_transcript_path": ""}, None, None)
    from storydesk.runner import ingest_tool_log

    ingest_tool_log(store, run_id)
    con = sqlite3.connect(store.path)
    rows = con.execute("SELECT agent_id, agent_type, tool FROM tool_calls WHERE run_id = ?", (run_id,)).fetchall()
    assert ("agent-1", "stats", "mcp__desk__stats_sql") in rows
    assert not any(agent_type == "fans" and tool.startswith("mcp__desk__") for _, agent_type, tool in rows)


# ---------- high: each run type starts with the findings it extends ----------

def _digest_text(run_type, as_of, ns, tmp_path, **kw):
    from storydesk.prepare import prepare_run

    out = prepare_run(run_type, game_id=OPENER, as_of=as_of, stats_db=ns.stats_db, store=ns.store,
                      corpus_dir=CORPUS, out_dir=tmp_path / run_type, **kw)
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(out.glob("*.md")))


def test_post_game_digest_carries_pre_game_findings(demo_store, tmp_path):
    text = _digest_text("post_game", POST, demo_store, tmp_path)
    assert demo_store.store.get_finding(demo_store.pre_finding)["claim"] in text


def test_supplemental_digest_carries_shipped_post_game_findings(demo_store, tmp_path):
    text = _digest_text("supplemental", SUPP, demo_store, tmp_path)
    assert demo_store.store.get_finding(demo_store.f_checked)["claim"] in text
    assert "Adelaide scored 30 points" not in text  # dropped findings stay out


def test_follow_up_digest_carries_the_anchor_and_its_evidence(demo_store, tmp_path):
    text = _digest_text("follow_up", POST, demo_store, tmp_path, anchor_finding_id=demo_store.f_checked)
    assert "Adelaide scored 26 points in the third quarter" in text
    assert EV_STATS["url"] in text
    assert str(demo_store.f_checked) in text


def test_follow_up_rejects_unknown_anchor(demo_store, tmp_path):
    with pytest.raises(ValueError):
        _digest_text("follow_up", POST, demo_store, tmp_path, anchor_finding_id=999_999)


# ---------- high: the live pipeline is timed end to end and always finalised ----------

class FakeClient:
    """Stands in for ClaudeSDKClient: async context manager with query / receive_response / interrupt."""

    def __init__(self, options, behaviour, result_cost=0.5):
        self.options, self.behaviour, self.result_cost = options, behaviour, result_cost
        self.queries, self.interrupted = [], asyncio.Event()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def query(self, prompt):
        self.queries.append(prompt)
        if self.behaviour == "raise":
            raise RuntimeError("connection dropped")
        if self.behaviour == "write" and len(self.queries) == 1:
            self._write_findings()

    async def interrupt(self):
        self.interrupted.set()

    async def receive_response(self):
        if self.behaviour == "hang":
            await self.interrupted.wait()
            yield _result(self.result_cost, subtype="error_during_execution", terminal_reason="aborted_streaming")
            return
        yield _result(self.result_cost)

    def _write_findings(self):
        from storydesk.store import Store
        from storydesk.tools import ToolContext, write_finding

        env = self.options.mcp_servers["desk"]["env"]
        ctx = ToolContext(stats_db=env["STORYDESK_STATS_DB"], store=Store(env["STORYDESK_STORE"]),
                          corpus_dir=env["STORYDESK_CORPUS"], run_id=int(env["STORYDESK_RUN_ID"]),
                          as_of=env["STORYDESK_AS_OF"])
        from storydesk.agents import RUN_TYPES
        for source in RUN_TYPES["post_game"]["required_sources"]:
            if source == "stats":
                write_finding(ctx, agent="stats", source_type="stats", kind="checked", number=26, query=Q3_ADL,
                              claim="Adelaide scored 26 points in the third quarter", evidence=[EV_STATS])
            else:
                write_finding(ctx, agent=source, source_type=source, kind="nothing_found",
                              claim=f"No {source} items mentioned the third quarter", evidence=[])


def _result(cost, subtype="success", terminal_reason=None):
    return SimpleNamespace(subtype=subtype, is_error=subtype != "success", total_cost_usd=cost, duration_ms=1000,
                           num_turns=3, model_usage={"claude-opus-5-5": {"outputTokens": 10}},
                           terminal_reason=terminal_reason, result="done")


def _live(store, stats_db, tmp_path, behaviour, **kw):
    from storydesk.runner import run_live

    holder = {}

    def factory(options):
        holder["client"] = FakeClient(options, behaviour)
        return holder["client"]

    run_id = asyncio.run(run_live("post_game", game_id=OPENER, as_of=POST, stats_db=stats_db, store=store,
                                  corpus_dir=CORPUS, digest_dir=tmp_path / "digest", client_factory=factory, **kw))
    return run_id, holder["client"]


def test_live_timeout_drains_result_and_records_wall_time(store, stats_db, tmp_path):
    start = time.monotonic()
    run_id, client = _live(store, stats_db, tmp_path, "hang", time_limit_s=0.5, judge_scorer=lambda f, c: ({}, 0.0))
    run = store.get_run(run_id)
    assert client.interrupted.is_set()
    assert run["status"] == "timeout"
    assert run["cost_usd"] == pytest.approx(0.5)          # drained from the interrupted result
    assert 0.5 <= run["duration_s"] <= time.monotonic() - start + 0.5


def test_live_error_is_finalised(store, stats_db, tmp_path):
    from storydesk.runner import run_live

    with pytest.raises(RuntimeError):
        asyncio.run(run_live("post_game", game_id=OPENER, as_of=POST, stats_db=stats_db, store=store,
                             corpus_dir=CORPUS, digest_dir=tmp_path / "digest",
                             client_factory=lambda o: FakeClient(o, "raise"), judge_scorer=lambda f, c: ({}, 0.0)))
    con = sqlite3.connect(store.path)
    status, finished = con.execute("SELECT status, finished_at FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    assert status == "error" and finished


def test_live_without_coverage_is_incomplete_after_one_top_up(store, stats_db, tmp_path):
    run_id, client = _live(store, stats_db, tmp_path, "empty", judge_scorer=lambda f, c: ({}, 0.0))
    assert store.get_run(run_id)["status"] == "incomplete"
    assert len(client.queries) == 2  # the original query plus one top-up


def test_live_success_runs_gates_and_one_judge_call(store, stats_db, tmp_path):
    calls = []

    def scorer(findings, coverage_texts):
        calls.append(coverage_texts)
        scores = {f["id"]: {"novelty": 0.7, "audience_fit": 0.8, "direction": 0.6} for f in findings}
        return scores, 0.05

    run_id, client = _live(store, stats_db, tmp_path, "write", judge_scorer=scorer)
    run = store.get_run(run_id)
    assert run["status"] == "complete"
    assert len(calls) == 1
    coverage = " ".join(calls[0]).lower()
    assert "preview" in coverage or "matchups to watch" in coverage   # pre-cutoff media reached the judge
    assert "held on" not in coverage                                 # the post-cutoff recap did not
    assert run["cost_usd"] == pytest.approx(0.5 + 0.05)              # judge cost is in the ledger
    shipped = [f for f in store.findings(run_id) if f["kind"] == "checked"]
    assert shipped and shipped[0]["status"] == "shipped"


# ---------- medium: prompts carry the operational contract ----------

def test_shared_contract_is_in_every_prompt(tmp_path):
    from storydesk.agents import build_options

    contract = (REPO / "prompts" / "contract.md").read_text(encoding="utf-8")
    assert len(contract) > 800
    for word in ("results", "box_team", "box_player", "pbp", "p1_score", "score_home", "label", "value",
                 "highlight", "write_finding", "nothing_found", "since at least", "url", "ref"):
        assert word in contract, word
    opts = build_options("post_game", run_id=1, as_of=POST, stats_db=tmp_path / "s.duckdb",
                         store_path=tmp_path / "st.db", corpus_dir=CORPUS, digest_dir=tmp_path / "d")
    assert contract.strip() in str(opts.system_prompt)
    for agent in opts.agents.values():
        assert contract.strip() in agent.prompt


# ---------- medium: default cutoffs follow the approved rule ----------

def test_default_cutoffs(stats_db):
    from storydesk.cli import default_as_of

    assert default_as_of("pre_game", stats_db=stats_db, game_id=OPENER) == "2026-09-19T06:30:00+00:00"
    assert default_as_of("post_game", stats_db=stats_db, game_id=OPENER) == "2026-09-19T11:35:07+00:00"
    assert PRE == "2026-09-19T06:30:00+00:00"
