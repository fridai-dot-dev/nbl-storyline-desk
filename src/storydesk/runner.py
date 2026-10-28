"""Execution and ledger handling for deliberately invoked live runs."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from claude_agent_sdk import (
    TERMINAL_TASK_STATUSES,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TaskNotificationMessage,
    TaskStartedMessage,
    TaskUpdatedMessage,
)

from .agents import RUN_TYPES, build_options, build_prompt
from .gates import apply_gates, coverage
from .judge import score_findings
from .prepare import prepare_run
from .store import Store
from .tool_log import tool_log_path
from .tools import ToolContext, get_game, search_media, search_transcripts


def ingest_tool_log(store: Store, run_id: int) -> int:
    """Copy this run's SDK-hook spool into SQLite exactly once per event."""
    path = tool_log_path(store.path, run_id)
    if not path.exists():
        return 0
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line in source:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or not all(
                isinstance(event.get(key), str) for key in ("event_id", "tool", "args_json")
            ):
                continue
            events.append(event)
    return store.ingest_tool_calls(run_id, events)


def record_result(store: Store, run_id: int, result: Any, *, route: str, num_agents: int) -> None:
    if result is None:
        store.finish_run(run_id, status="timeout", cost_usd=None, duration_s=None, model_usage={}, num_agents=num_agents, route=route)
        return
    if isinstance(summary := getattr(result, "result", None), str) and summary.strip():
        store.set_run_summary(run_id, summary.strip())
    success = not bool(getattr(result, "is_error", False)) and getattr(result, "subtype", "") == "success"
    status = "complete" if success else ("timeout" if getattr(result, "terminal_reason", None) == "timeout" else "error")
    duration_ms = getattr(result, "duration_ms", None)
    store.finish_run(
        run_id, status=status, cost_usd=getattr(result, "total_cost_usd", None),
        duration_s=(duration_ms / 1000) if duration_ms is not None else None,
        model_usage=getattr(result, "model_usage", None) or {}, num_agents=num_agents, route=route,
    )


async def enforce_deadline(awaitable: Awaitable[Any], seconds: float, interrupt: Callable[[], Awaitable[Any]]) -> tuple[str, Any | None]:
    task = asyncio.create_task(awaitable)
    try:
        return "complete", await asyncio.wait_for(task, timeout=seconds)
    except asyncio.TimeoutError:
        await interrupt()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        return "timeout", None


def _is_result(message: Any) -> bool:
    return isinstance(message, ResultMessage) or (
        hasattr(message, "total_cost_usd") and hasattr(message, "subtype")
    )


async def _receive_result(client: Any) -> Any | None:
    """Wait for a lead result that is not ahead of its background specialists."""
    receive = getattr(client, "receive_messages", None) or client.receive_response
    pending_tasks: set[str] = set()
    result = None
    async for message in receive():
        if isinstance(message, TaskStartedMessage) and message.task_type == "local_agent":
            pending_tasks.add(message.task_id)
        elif isinstance(message, TaskNotificationMessage):
            if message.status in TERMINAL_TASK_STATUSES:
                pending_tasks.discard(message.task_id)
        elif isinstance(message, TaskUpdatedMessage):
            task_status = message.patch.get("status", message.status)
            if task_status in TERMINAL_TASK_STATUSES:
                pending_tasks.discard(message.task_id)
        elif _is_result(message):
            result = message
            if not pending_tasks:
                return result
    return result


async def _query_with_deadline(client: Any, prompt: str, seconds: float) -> tuple[str, Any | None]:
    async def query_and_receive() -> Any | None:
        await client.query(prompt)
        return await _receive_result(client)

    try:
        return "complete", await asyncio.wait_for(query_and_receive(), timeout=max(0.001, seconds))
    except asyncio.TimeoutError:
        await client.interrupt()
        drained = None
        with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError, Exception):
            # Interrupt normally places the terminal result straight onto the stream.
            # Do not let a stalled drain turn a wall-clock timeout into another wait.
            drained = await asyncio.wait_for(_receive_result(client), timeout=0.25)
        return "timeout", drained


def _coverage_texts(ctx: ToolContext, game_id: str) -> list[str]:
    """Collect pre-cutoff comparison coverage by team/title terms, never UUID."""
    game = get_game(ctx, game_id)
    query = f"{game['home_team']} {game['away_team']}"
    texts = [
        " ".join(part for part in (item.get("title", ""), item.get("excerpt", "")) if part)
        for item in search_media(ctx, query, limit=100)
    ]
    texts.extend(
        " ".join(part for part in (item.get("source_title", ""), item.get("quote", "")) if part)
        for item in search_transcripts(ctx, query, limit=100)
    )
    return [text for text in texts if text]


def _parse_judge_result(text: str | None) -> dict[Any, Any]:
    candidate = (text or "").strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1])
    try:
        value = json.loads(candidate)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


async def _default_judge_scorer(
    findings: list[dict[str, Any]], coverage_texts: list[str],
) -> tuple[dict[Any, Any], float, dict[str, Any]]:
    """Make the one independent, no-tool judge call used by a real live run."""
    judge_prompt = (Path(__file__).resolve().parents[2] / "prompts" / "judge.md").read_text(encoding="utf-8")
    options = ClaudeAgentOptions(
        model="claude-opus-5-5", system_prompt=judge_prompt, tools=[], allowed_tools=[],
        disallowed_tools=["WebSearch", "WebFetch", "Bash", "Write", "Edit", "Agent"],
        permission_mode="dontAsk", setting_sources=[], max_turns=1, max_budget_usd=1.0,
    )
    payload = json.dumps({"findings": findings, "coverage_texts": coverage_texts}, default=str)
    result = None
    async with ClaudeSDKClient(options=options) as client:
        try:
            await client.query(payload)
            result = await _receive_result(client)
        except asyncio.CancelledError:
            await client.interrupt()
            raise
    return (
        _parse_judge_result(getattr(result, "result", None)),
        float(getattr(result, "total_cost_usd", 0.0) or 0.0),
        getattr(result, "model_usage", None) or {},
    )


async def rejudge_live(store: Store, run_id: int, *, stats_db: str | Path, corpus_dir: str | Path) -> list[dict[str, Any]]:
    """Run the independent judge again for one finished run after an explicit live opt-in."""
    run = store.get_run(run_id)
    if not run.get("finished_at"):
        raise ValueError(f"run {run_id} has not finished")
    ctx = ToolContext(
        stats_db=stats_db, store=store, corpus_dir=corpus_dir, run_id=run_id, as_of=run["as_of"],
    )
    findings = [finding for finding in store.findings(run_id) if finding["kind"] != "nothing_found"]
    if not findings:
        return []
    coverage_texts = _coverage_texts(ctx, run["game_id"])
    scores, _cost, _usage = await _default_judge_scorer(findings, coverage_texts)
    return score_findings(store, run_id, coverage_texts, lambda _findings, _coverage: scores)


async def _call_judge(
    scorer: Callable[[list[dict[str, Any]], list[str]], Any] | None,
    findings: list[dict[str, Any]], coverage_texts: list[str], seconds: float,
) -> tuple[dict[Any, Any], float, dict[str, Any]]:
    if scorer is None:
        return await asyncio.wait_for(_default_judge_scorer(findings, coverage_texts), timeout=max(0.001, seconds))
    response = scorer(findings, coverage_texts)
    if inspect.isawaitable(response):
        response = await asyncio.wait_for(response, timeout=max(0.001, seconds))
    if not isinstance(response, tuple) or len(response) not in {2, 3}:
        raise ValueError("judge_scorer must return (scores_by_finding_id, cost_usd)")
    scores, cost = response[:2]
    usage = response[2] if len(response) == 3 else {"calls": 1}
    return (scores if isinstance(scores, dict) else {}, float(cost or 0.0), usage or {"calls": 1})


async def run_live(
    run_type: str, *, game_id: str, as_of: str, stats_db: str | Path, store: Store,
    corpus_dir: str | Path, digest_dir: str | Path, question: str | None = None,
    anchor_finding_id: int | None = None, route: str = "sdk", client_factory: Any = None,
    judge_scorer: Callable[[list[dict[str, Any]], list[str]], Any] | None = None,
    time_limit_s: float | None = None, asked_by: str | None = None,
) -> int:
    """Run a model only when a caller has already opted into the live CLI path."""
    if run_type not in RUN_TYPES:
        raise ValueError(f"unknown run type: {run_type}")
    if run_type == "follow_up" and (anchor_finding_id is None or not question or not question.strip()):
        raise ValueError("follow-up runs require an anchor finding and question")
    store.init()
    run_id = store.start_run(run_type, game_id, as_of, route)
    request_id = (
        store.add_request(anchor_finding_id, asked_by or "producer", question.strip())
        if run_type == "follow_up" and anchor_finding_id is not None and question is not None
        else None
    )
    started = time.monotonic()
    limit = float(RUN_TYPES[run_type]["time_limit_s"] if time_limit_s is None else time_limit_s)
    deadline = started + limit

    def remaining() -> float:
        left = deadline - time.monotonic()
        if left <= 0:
            raise asyncio.TimeoutError
        return left

    status = "error"
    agent_cost = 0.0
    judge_cost = 0.0
    model_usage: dict[str, Any] = {}

    def capture_result(result: Any | None, *, record_summary: bool = False) -> bool:
        nonlocal agent_cost, model_usage
        if result is None:
            return False
        agent_cost = float(getattr(result, "total_cost_usd", 0.0) or 0.0)
        usage = getattr(result, "model_usage", None)
        model_usage = dict(usage) if isinstance(usage, dict) else {}
        if record_summary and isinstance(summary := getattr(result, "result", None), str) and summary.strip():
            store.set_run_summary(run_id, summary.strip())
        return not bool(getattr(result, "is_error", False)) and getattr(result, "subtype", "") == "success"

    try:
        digest = prepare_run(
            run_type, game_id=game_id, as_of=as_of, stats_db=stats_db, store=store,
            corpus_dir=corpus_dir, out_dir=digest_dir, anchor_finding_id=anchor_finding_id,
        )
        remaining()
        options = build_options(
            run_type, run_id=run_id, as_of=as_of, stats_db=stats_db, store_path=store.path,
            corpus_dir=corpus_dir, digest_dir=digest, question=question,
            anchor_finding_id=anchor_finding_id,
        )
        prompt = build_prompt(
            run_type, digest_dir=digest, question=question, anchor_finding_id=anchor_finding_id,
            run_id=run_id, game_id=game_id, as_of=as_of,
        )
        factory = client_factory or ClaudeSDKClient
        agent_success = False
        missing: list[str] = []
        async with factory(options) as client:
            phase_status, result = await _query_with_deadline(client, prompt, remaining())
            agent_success = capture_result(result, record_summary=True)
            if phase_status == "timeout":
                status = "timeout"
            else:
                required = RUN_TYPES[run_type]["required_sources"]
                source_coverage = coverage(store, run_id, required)
                missing = [source for source, value in source_coverage.items() if value == 0]
                if missing:
                    top_up = (
                        "One coverage top-up only. Search these missing required sources and write either a sourced "
                        f"finding or a nothing_found finding for each: {', '.join(missing)}. Do not revisit covered sources."
                    )
                    phase_status, result = await _query_with_deadline(client, top_up, remaining())
                    agent_success = capture_result(result)
                    if phase_status == "timeout":
                        status = "timeout"
                    source_coverage = coverage(store, run_id, required)
                    missing = [source for source, value in source_coverage.items() if value == 0]

        if status != "timeout":
            remaining()
            apply_gates(store, run_id, stats_db=stats_db, as_of=as_of)
            remaining()
            ctx = ToolContext(
                stats_db=stats_db, store=store, corpus_dir=corpus_dir, run_id=run_id, as_of=as_of,
            )
            coverage_texts = _coverage_texts(ctx, game_id)
            remaining()
            findings = [f for f in store.findings(run_id) if f["kind"] != "nothing_found"]
            if findings:  # no judge call (and no usage) when there is nothing to score
                scores, judge_cost, judge_usage = await _call_judge(
                    judge_scorer, findings, coverage_texts, remaining(),
                )
                model_usage["judge"] = judge_usage
                score_findings(
                    store, run_id, coverage_texts,
                    lambda _findings, _coverage: scores,
                )
            remaining()
            status = "complete" if agent_success and not missing else "incomplete"
    except asyncio.TimeoutError:
        status = "timeout"
    except Exception:
        status = "error"
        raise
    finally:
        ingest_tool_log(store, run_id)
        store.finish_run(
            run_id, status=status, cost_usd=agent_cost + judge_cost,
            duration_s=time.monotonic() - started, model_usage=model_usage,
            num_agents=5, route=route,
        )
        if request_id is not None:
            store.answer_request(request_id, run_id)
    return run_id
