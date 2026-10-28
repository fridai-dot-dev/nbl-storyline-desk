"""Scoring signals for the improvement loop."""

from __future__ import annotations

import asyncio
import inspect
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .store import Store


FOLLOWUP_TYPES = frozenset({"rarity", "on_pace", "comparison", "context"})


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _judge_headline(value: Any) -> str | None:
    """Accept only the compact headline shape we ask the independent judge for."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or "<" in value or ">" in value or len(value) > 120 or len(value.split()) > 14:
        return None
    return value


def _judge_followups(value: Any) -> list[dict[str, str]]:
    """Keep only the small, typed follow-up contract the site can safely present."""
    if not isinstance(value, list):
        return []
    output: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        kind, question, why = item.get("type"), item.get("question"), item.get("why")
        if kind not in FOLLOWUP_TYPES or not isinstance(question, str) or not isinstance(why, str):
            continue
        question, why = question.strip(), why.strip()
        if not question or not why:
            continue
        output.append({"type": kind, "question": question, "why": why})
        if len(output) == 3:
            break
    return output


def novelty_similarity(claim: str, coverage_texts: list[str]) -> float:
    claim_words = _words(claim)
    if not claim_words or not coverage_texts:
        return 0.0
    scores = []
    for coverage in coverage_texts:
        words = _words(coverage)
        scores.append(len(claim_words & words) / len(claim_words | words) if words else 0.0)
    return max(scores, default=0.0)


def score_findings(
    store: Store, run_id: int, coverage_texts: list[str],
    scorer: Callable[[list[dict[str, Any]], list[str]], Any] | None = None,
) -> list[dict[str, Any]]:
    """Store deterministic novelty and optional independent judge scores.

    ``scorer`` is intentionally injectable: the live runner owns the single model call,
    while fixture and regression evaluation stay deterministic and free.
    """
    findings = store.findings(run_id)
    judged: Any = scorer(findings, coverage_texts) if scorer else {}
    if isinstance(judged, list):
        judged = {str(item.get("id")): item for item in judged if isinstance(item, dict)}
    if not isinstance(judged, dict):
        judged = {}
    output = []
    for finding in findings:
        raw = judged.get(str(finding["id"]), judged.get(finding["id"], {}))
        raw = raw if isinstance(raw, dict) else {}
        novelty = 1.0 - novelty_similarity(finding["claim"], coverage_texts)
        audience_fit = raw.get("audience_fit")
        direction = raw.get("direction")
        store.update_finding(finding["id"], novelty=novelty, audience_fit=audience_fit, direction=direction)
        if not finding.get("headline") and (headline := _judge_headline(raw.get("headline"))):
            store.set_headline(finding["id"], headline)
        store.set_followups(finding["id"], _judge_followups(raw.get("followups")))
        output.append(store.get_finding(finding["id"]))
    return output


def _rejudge_result(value: Any) -> tuple[dict[Any, Any], float, dict[str, Any]]:
    """Accept the live scorer contract while keeping fixture scorers lightweight."""
    if isinstance(value, tuple) and len(value) in {2, 3}:
        scores, cost = value[:2]
        usage = value[2] if len(value) == 3 else {"calls": 1}
    else:
        scores, cost, usage = value, 0.0, {"calls": 1}
    try:
        cost = float(cost or 0.0)
    except (TypeError, ValueError):
        cost = 0.0
    return (
        scores if isinstance(scores, dict) else {},
        cost,
        usage if isinstance(usage, dict) else {"calls": 1},
    )


def _live_rejudge_scorer(findings: list[dict[str, Any]], coverage_texts: list[str]) -> Any:
    """Lazy import keeps the ordinary runner-to-judge dependency one-way."""
    from .runner import _default_judge_scorer

    return asyncio.run(_default_judge_scorer(findings, coverage_texts))


def rejudge(
    store: Store, run_id: int, *, stats_db: str | Path, corpus_dir: str | Path,
    scorer: Callable[[list[dict[str, Any]], list[str]], Any] | None = None,
) -> list[dict[str, Any]]:
    """Run one fresh judge pass for a finished run without re-running its agents."""
    run = store.get_run(run_id)
    if not run.get("finished_at"):
        raise ValueError(f"run {run_id} has not finished")

    # Reuse the cutoff-safe coverage collection used by the original run.  It is
    # imported here to avoid a module cycle with runner's score_findings import.
    from .runner import _coverage_texts
    from .tools import ToolContext

    ctx = ToolContext(
        stats_db=stats_db, store=store, corpus_dir=corpus_dir, run_id=run_id, as_of=run["as_of"],
    )
    coverage_texts = _coverage_texts(ctx, run["game_id"])
    findings = [finding for finding in store.findings(run_id) if finding["kind"] != "nothing_found"]
    if not findings:
        return []

    response = (scorer or _live_rejudge_scorer)(findings, coverage_texts)
    if inspect.isawaitable(response):
        response = asyncio.run(response)
    scores, cost, usage = _rejudge_result(response)
    output = score_findings(store, run_id, coverage_texts, lambda _findings, _coverage: scores)

    model_usage = dict(run.get("model_usage") or {})
    previous = model_usage.get("rejudge")
    if previous is None:
        model_usage["rejudge"] = usage
    elif isinstance(previous, list):
        model_usage["rejudge"] = [*previous, usage]
    else:
        model_usage["rejudge"] = [previous, usage]
    store.update_run_ledger(
        run_id, cost_usd=float(run.get("cost_usd") or 0.0) + cost,
        model_usage=model_usage,
    )
    return output
