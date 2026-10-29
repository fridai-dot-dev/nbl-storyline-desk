"""A stable view of one run for the prompt/model improvement loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .gates import coverage, recheck_finding
from .store import Store


def scorecard(store: Store, stats_db: str | Path, run_id: int) -> dict[str, Any]:
    run = store.get_run(run_id)
    findings = store.findings(run_id, include_dropped=True)
    shipped_checked = [item for item in findings if item["status"] == "shipped" and item["kind"] == "checked"]
    rate = sum(recheck_finding(stats_db, run["as_of"], item) for item in shipped_checked) / len(shipped_checked) if shipped_checked else 1.0
    def average(field: str) -> float | None:
        values = [float(item[field]) for item in findings if item.get(field) is not None]
        return sum(values) / len(values) if values else None
    required = {"post_game": ["stats", "commentary", "fans"]}.get(run["run_type"], [])
    return {
        "recheck_pass_rate": rate, "coverage": coverage(store, run_id, required),
        "novelty": average("novelty"), "audience_fit": average("audience_fit"), "direction": average("direction"),
        "held": sum(item["status"] == "held" for item in findings),
        "duration_s": run["duration_s"], "cost_usd": run["cost_usd"],
    }
