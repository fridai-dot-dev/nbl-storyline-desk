"""Checks from the first live post-game run (2026-10-28).

1. The lead launched specialists as background agents and ended its turn. In streaming mode that turn's result
   arrives while specialists are still working; their completions come later as task notifications, and the lead
   resumes on its own. The runner stopped reading at the first result, then topped up and closed, killing them.
2. Corpus search returned the first matches in time order, so agents never saw late-game commentary or chat.
"""
import asyncio
from types import SimpleNamespace

from claude_agent_sdk import TaskNotificationMessage, TaskStartedMessage

from conftest import CORPUS, EV_STATS, OPENER, POST, Q3_ADL, SUPP, make_ctx


def _result(cost, subtype="success", terminal_reason=None):
    return SimpleNamespace(subtype=subtype, is_error=subtype != "success", total_cost_usd=cost, duration_ms=1000,
                           num_turns=3, model_usage={"claude-opus-5-5": {"costUSD": cost}},
                           terminal_reason=terminal_reason, result="done")


def _started(task_id):
    return TaskStartedMessage(subtype="task_started", data={}, task_id=task_id, description="specialist",
                              uuid=f"u-{task_id}", session_id="s", tool_use_id=f"tu-{task_id}", task_type="local_agent")


def _done(task_id):
    return TaskNotificationMessage(subtype="task_notification", data={}, task_id=task_id, status="completed",
                                   output_file="", summary="done", uuid=f"n-{task_id}", session_id="s",
                                   tool_use_id=f"tu-{task_id}", usage=None)


class BackgroundClient:
    """Fake ClaudeSDKClient where the lead's first turn ends while a background specialist is still working."""

    def __init__(self, options, finish=True):
        self.options, self.finish = options, finish
        self.queries, self.interrupted = [], asyncio.Event()
        self.queue: asyncio.Queue = asyncio.Queue()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def query(self, prompt):
        self.queries.append(prompt)
        if len(self.queries) == 1:
            for item in (_started("t1"), _result(0.30)):
                await self.queue.put(item)
            if self.finish:
                for item in ("WRITE", _done("t1"), _result(0.90)):  # specialist writes, completes; lead resumes
                    await self.queue.put(item)
        else:
            await self.queue.put(_result(0.95))

    async def interrupt(self):
        self.interrupted.set()
        await self.queue.put(_result(0.40, subtype="error_during_execution", terminal_reason="aborted_streaming"))

    async def _next(self):
        item = await self.queue.get()
        if item == "WRITE":
            await asyncio.sleep(0.05)
            self._write()
            return await self._next()
        return item

    async def receive_messages(self):
        while True:
            yield await self._next()

    async def receive_response(self):
        while True:
            message = await self._next()
            yield message
            if hasattr(message, "total_cost_usd") and hasattr(message, "subtype"):
                return

    def _write(self):
        from storydesk.agents import RUN_TYPES
        from storydesk.store import Store
        from storydesk.tools import ToolContext, write_finding

        env = self.options.mcp_servers["desk"]["env"]
        ctx = ToolContext(stats_db=env["STORYDESK_STATS_DB"], store=Store(env["STORYDESK_STORE"]),
                          corpus_dir=env["STORYDESK_CORPUS"], run_id=int(env["STORYDESK_RUN_ID"]),
                          as_of=env["STORYDESK_AS_OF"])
        for source in RUN_TYPES["post_game"]["required_sources"]:
            if source == "stats":
                write_finding(ctx, agent="stats", source_type="stats", kind="checked", number=26, query=Q3_ADL,
                              claim="Adelaide scored 26 points in the third quarter", evidence=[EV_STATS])
            else:
                write_finding(ctx, agent=source, source_type=source, kind="nothing_found",
                              claim=f"No {source} items mentioned the third quarter", evidence=[])


def _run(store, stats_db, tmp_path, client_holder, finish=True, **kw):
    from storydesk.runner import run_live

    def factory(options):
        client_holder["c"] = BackgroundClient(options, finish=finish)
        return client_holder["c"]

    return asyncio.run(run_live("post_game", game_id=OPENER, as_of=POST, stats_db=stats_db, store=store,
                                corpus_dir=CORPUS, digest_dir=tmp_path / "digest", client_factory=factory,
                                judge_scorer=lambda f, c: ({}, 0.0), **kw))


def test_runner_waits_for_background_specialists(store, stats_db, tmp_path):
    holder = {}
    run_id = _run(store, stats_db, tmp_path, holder, time_limit_s=10)
    run = store.get_run(run_id)
    assert run["status"] == "complete", run
    assert len(holder["c"].queries) == 1           # coverage was met once the specialist finished: no top-up
    assert not holder["c"].interrupted.is_set()
    shipped = [f for f in store.findings(run_id) if f["kind"] == "checked"]
    assert shipped and shipped[0]["status"] == "shipped"
    assert run["cost_usd"] == 0.90                 # cumulative cost from the latest result, not a sum


def test_runner_deadline_still_applies_while_waiting(store, stats_db, tmp_path):
    holder = {}
    run_id = _run(store, stats_db, tmp_path, holder, finish=False, time_limit_s=0.5)
    assert holder["c"].interrupted.is_set()
    assert store.get_run(run_id)["status"] == "timeout"


# ---------- search ranks by relevance then recency, and takes a time window ----------

def test_transcript_search_ranks_latest_first_and_takes_a_window(stats_db, store):
    from storydesk.tools import search_transcripts

    supp = make_ctx(stats_db, store, "supplemental", SUPP)
    hits = search_transcripts(supp, "third quarter")
    assert [h["timestamp"][:16] for h in hits][:2] == ["2026-09-19T11:55", "2026-09-19T10:55"]
    window = search_transcripts(supp, "third quarter", since="2026-09-19T11:00:00+00:00")
    assert [h["quote"][:20] for h in window] == ["We lost the third qu"]
    clamped = search_transcripts(make_ctx(stats_db, store, "post_game", POST), "third quarter",
                                 until="2026-09-19T23:00:00+00:00")
    assert all(h["timestamp"] <= POST for h in clamped)  # a window never widens the cutoff


def test_fan_search_ranks_and_windows(stats_db, store):
    from storydesk.tools import search_fans

    supp = make_ctx(stats_db, store, "supplemental", SUPP)
    hits = search_fans(supp, "third quarter")
    assert hits[0]["text"].startswith("Coach said the third quarter")      # 12:10Z, latest match first
    late = search_fans(supp, "third quarter", since="2026-09-19T11:30:00+00:00")
    assert [h["text"][:5] for h in late] == ["Coach"]


async def test_mcp_search_tools_expose_the_window(monkeypatch, stats_db, store):
    from storydesk.mcp_server import server

    monkeypatch.setenv("STORYDESK_RUN_ID", str(store.start_run("post_game", OPENER, POST, route="test")))
    monkeypatch.setenv("STORYDESK_AS_OF", POST)
    monkeypatch.setenv("STORYDESK_STATS_DB", str(stats_db))
    monkeypatch.setenv("STORYDESK_STORE", str(store.path))
    monkeypatch.setenv("STORYDESK_CORPUS", str(CORPUS))
    tools = {t.name: t for t in await server.list_tools()}
    for name in ("search_transcripts", "search_fans"):
        assert {"query", "limit", "since", "until"} <= set(tools[name].input_schema.get("properties", {})), name


def test_post_game_digest_covers_the_finish(demo_store, tmp_path):
    from storydesk.prepare import prepare_run

    out = prepare_run("post_game", game_id=OPENER, as_of=POST, stats_db=demo_store.stats_db, store=demo_store.store,
                      corpus_dir=CORPUS, out_dir=tmp_path / "digest")
    commentary = (out / "commentary.md").read_text(encoding="utf-8")
    fans = (out / "fans.md").read_text(encoding="utf-8")
    assert "Four threes in a row" in commentary       # 11:24Z, the last commentary before the whistle
    assert "What a finish" in fans                     # 11:25:30Z, the last fan item before the whistle
