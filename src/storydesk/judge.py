"""Scoring signals for the improvement loop."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from .store import Store


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


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
        output.append(store.get_finding(finding["id"]))
    return output
