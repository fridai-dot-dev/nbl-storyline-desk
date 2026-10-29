"""Deterministic release gates: numbers, data boundaries and sensitive material."""

from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .data import as_of_connection
from .sqlsafe import validate_safe_sql
from .store import Store


SENSITIVE_CATEGORIES = {"conflict", "injury", "officiating", "legal", "fan_quote"}
STANCE_VALUES = frozenset({"push", "use_if_raised", "steer_away"})
DEFAULT_OVERRIDE_ROLES = ("League GM", "LK director")
_RECORD_WORD = re.compile(r"\b(?:most|fewest|first|last|record|highest|lowest|best|worst|longest)\b", re.IGNORECASE)
_BOUNDARY = re.compile(r"\bsince\s+(?:at\s+least\s+)?(?:2015-16|2015/16|2015–16|2015)\b", re.IGNORECASE)


def _first_value(stats_db: str | Path, as_of: str | datetime, sql: str) -> Any:
    try:
        sql = validate_safe_sql(sql)
    except ValueError:
        return None
    con = as_of_connection(stats_db, as_of)
    try:
        row = con.execute(sql).fetchone()
    except Exception:
        return None
    finally:
        con.close()
    return None if row is None else row[0]


def recheck_finding(stats_db: str | Path, as_of: str | datetime, finding: dict[str, Any]) -> bool:
    if finding.get("kind") != "checked" or not finding.get("query") or finding.get("number") is None:
        return False
    value = _first_value(stats_db, as_of, finding["query"])
    if value is None:
        return False
    if isinstance(value, bool):
        value = int(value)
    try:
        return math.isclose(float(value), float(finding["number"]), rel_tol=0.0, abs_tol=1e-6)
    except (TypeError, ValueError):
        return False


def _chart_is_valid(stats_db: str | Path, as_of: str | datetime, chart: dict[str, Any], number: Any) -> bool:
    try:
        sql = validate_safe_sql(chart["query"])
    except (KeyError, TypeError, ValueError):
        return False
    con = as_of_connection(stats_db, as_of)
    try:
        cursor = con.execute(sql)
        columns = [column[0].lower() for column in cursor.description]
        if not {"label", "value", "highlight"} <= set(columns):
            return False
        index = {name: columns.index(name) for name in ("value", "highlight")}
        highlighted = []
        for row in cursor.fetchall():
            highlight = row[index["highlight"]]
            if bool(highlight):
                highlighted.append(row[index["value"]])
        if len(highlighted) != 1:
            return False
        try:
            return math.isclose(float(highlighted[0]), float(number), abs_tol=1e-6)
        except (TypeError, ValueError):
            return False
    except Exception:
        return False
    finally:
        con.close()


def needs_boundary(claim: str) -> bool:
    return bool(_RECORD_WORD.search(claim) and _BOUNDARY.search(claim))


def boundary_ok(claim: str) -> bool:
    return not needs_boundary(claim) or "since at least" in claim.lower()


def is_promotable(
    store: Store, finding_id: int, *, override_roles: tuple[str, ...] | list[str] = DEFAULT_OVERRIDE_ROLES,
) -> bool:
    """Whether a finding can be put forward as an editorial suggestion.

    A normal positive stance permits a sensitive finding only while nobody has
    steered away.  A positive stance from an override role clears ordinary
    blocks; it is also the only way to clear an override role's block.
    """
    finding = store.get_finding(finding_id)
    if finding.get("sensitivity") not in SENSITIVE_CATEGORIES:
        return True
    stances = store.stances(finding_id)
    positive = [item for item in stances if item.get("stance") in {"push", "use_if_raised"}]
    if not positive:
        return False
    blocked = [item for item in stances if item.get("stance") == "steer_away"]
    if not blocked:
        return True
    overrides = set(override_roles)
    override_positive = [item for item in positive if item.get("role") in overrides]
    if not override_positive:
        return False
    # An override positive stance explicitly clears all ordinary blocks and is
    # the required authority for an override block.
    return True


def apply_gates(store: Store, run_id: int, *, stats_db: str | Path, as_of: str | datetime) -> dict[str, Any]:
    """Apply the fixed gate order, keeping held material visible internally only."""
    for finding in store.findings(run_id, include_dropped=True):
        if finding["status"] == "dropped":
            continue
        if finding["kind"] == "checked" and not recheck_finding(stats_db, as_of, finding):
            store.update_finding(finding["id"], status="dropped", drop_reason="number did not recheck at this run's cutoff")
            continue
        if not boundary_ok(finding["claim"]):
            store.update_finding(finding["id"], status="dropped", drop_reason="record claim omits the data boundary")
            continue
        if finding.get("chart") and not _chart_is_valid(stats_db, as_of, finding["chart"], finding.get("number")):
            store.update_finding(finding["id"], chart=None)
        if finding.get("sensitivity") in SENSITIVE_CATEGORIES:
            store.update_finding(finding["id"], status="held", drop_reason=None)
        else:
            store.update_finding(finding["id"], status="shipped", drop_reason=None)
    all_findings = store.findings(run_id, include_dropped=True)
    shipped = [item for item in all_findings if item["status"] == "shipped"]
    checked = [item for item in shipped if item["kind"] == "checked"]
    return {
        "recheck_pass_rate": (sum(recheck_finding(stats_db, as_of, item) for item in checked) / len(checked)) if checked else 1.0,
        "shipped": len(shipped),
        "dropped": sum(item["status"] == "dropped" for item in all_findings),
        "held": sum(item["status"] == "held" for item in all_findings),
    }


def coverage(store: Store, run_id: int, required: list[str] | tuple[str, ...]) -> dict[str, int | str]:
    findings = store.findings(run_id, include_dropped=True)
    output: dict[str, int | str] = {}
    for source in required:
        matching = [item for item in findings if item["source_type"] == source]
        substantive = [item for item in matching if item["kind"] != "nothing_found"]
        output[source] = len(substantive) if substantive else ("nothing found" if matching else 0)
    return output


def visible_findings(store: Store, run_id: int, audience: str) -> list[dict[str, Any]]:
    if audience not in {"internal", "producers", "partners"}:
        raise ValueError("audience must be internal, producers or partners")
    findings = store.findings(run_id, include_dropped=True)
    if audience == "internal":
        return [item for item in findings if item["status"] in {"shipped", "held"}]
    return [
        item for item in findings
        if item["status"] == "shipped" or (item["status"] == "held" and store.signed_off(item["id"], audience))
    ]
