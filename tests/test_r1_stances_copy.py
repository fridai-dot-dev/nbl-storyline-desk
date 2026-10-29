"""R1 unit checks for copy preservation and the stance promotion gate (rows 13, 16, 17, 55, 57, 57b)."""

from __future__ import annotations

import json
import sqlite3

import pytest

from conftest import OPENER, POST, REPO


# Assumed public signatures kept deliberately small:
# copy_pass(store, run_id, copier), Store.set_stance(...)/stances(...),
# and is_promotable(store, finding_id, override_roles=DEFAULT_OVERRIDE_ROLES) -> bool.


def _stance_api(store):
    setter = getattr(store, "set_stance", None)
    getter = getattr(store, "stances", None)
    assert callable(setter), "Store.set_stance is the public write seam for one role's live stance"
    assert callable(getter), "Store.stances is the public read seam for the current stance record"
    return setter, getter


def _promotion_api():
    import storydesk.gates as gates

    function = getattr(gates, "is_promotable", None)
    assert callable(function), "the sensitive-story gate needs one public promotion predicate"
    return gates, function


def _sensitive_finding(store, claim="A sensitive injury story"):
    run_id = store.start_run("post_game", OPENER, POST, route="fixture")
    finding_id = store.add_finding(
        run_id=run_id, agent="media", source_type="media", claim=claim, kind="qualitative",
        sensitivity="injury", audience=["leadership"],
    )
    store.update_finding(finding_id, status="held")
    return run_id, finding_id


def test_r1_row_13_copy_pass_only_changes_copy_and_structured_test_fields(store):
    import storydesk.judge as judge

    run_id = store.start_run("pre_game", OPENER, POST, route="fixture")
    first = store.add_finding(
        run_id=run_id, agent="stats", source_type="stats", claim="Can Melbourne keep Cotton to 21?",
        kind="checked", number=21, audience=["leadership"],
    )
    store.update_finding(first, status="shipped", novelty=0.91, audience_fit=0.82, direction=0.73)
    store.set_followups(first, [{"type": "rarity", "question": "How rare is 21?", "why": "The history can answer."}])
    store.set_run_summary(run_id, "Existing agent summary")
    store.set_exec_summary(run_id, "Existing judge summary")
    store.finish_run(run_id, status="complete", cost_usd=1.23, duration_s=45, model_usage={"judge": 1}, num_agents=5, route="fixture")

    def protected_bytes():
        run = store.get_run(run_id)
        findings = store.findings(run_id, include_dropped=True)
        protected = {
            "run": {key: run.get(key) for key in ("summary", "exec_summary", "status", "cost_usd", "model_usage")},
            "findings": {
                item["id"]: {key: item.get(key) for key in (
                    "claim", "status", "novelty", "audience_fit", "direction", "headline", "followups",
                )}
                for item in findings
            },
            "top_pick": max(findings, key=lambda item: sum(float(item.get(key) or 0) for key in ("novelty", "audience_fit", "direction")))["id"],
        }
        return json.dumps(protected, sort_keys=True, separators=(",", ":"))

    before = protected_bytes()

    def copier(findings):
        return {
            item["id"]: {
                "plain_headline": f"Plain question for {item['id']}?",
                "premise": f"Plain premise for finding {item['id']}.",
                "metric": "points", "threshold": 21, "direction": "at_most",
                "actual": 26, "outcome": "contradicted",
            }
            for item in findings
        }

    copy_pass = getattr(judge, "copy_pass", None)
    assert callable(copy_pass), "storydesk.judge.copy_pass(store, run_id, copier) is missing"
    copy_pass(store, run_id, copier)
    assert protected_bytes() == before
    copied = store.get_finding(first)
    assert copied["plain_headline"] == f"Plain question for {first}?"
    assert copied["premise"] == f"Plain premise for finding {first}."


def test_r1_row_16_sensitive_story_needs_push_or_use_stance_to_promote(store):
    gates, is_promotable = _promotion_api()
    setter, _getter = _stance_api(store)
    _run_id, finding_id = _sensitive_finding(store)
    stance_values = getattr(gates, "STANCE_VALUES", None)
    assert stance_values is not None and set(stance_values) == {"push", "use_if_raised", "steer_away"}
    assert is_promotable(store, finding_id) is False
    setter(finding_id, "Broadcast producer", "push", "Use it on air.", at="2026-09-19T12:00:00+00:00")
    assert is_promotable(store, finding_id) is True
    setter(finding_id, "Broadcast producer", "use_if_raised", "Only if asked.", at="2026-09-19T12:01:00+00:00")
    assert is_promotable(store, finding_id) is True


def test_r1_row_17_steer_away_creates_a_later_run_directive(store):
    setter, _getter = _stance_api(store)
    before = store.directives()
    _run_id, finding_id = _sensitive_finding(store)
    setter(finding_id, "League GM", "steer_away", "Do not use the player-blame angle.", at="2026-09-19T12:00:00+00:00")
    created = store.directives()[len(before):]
    assert len(created) == 1
    assert created[0]["owner_role"] == "League GM" and created[0]["status"] == "active"
    assert "Do not use the player-blame angle" in created[0]["text"]


def test_r1_row_57_newer_stance_replaces_same_roles_live_stance_and_conflict_blocks(store):
    setter, getter = _stance_api(store)
    _gates, is_promotable = _promotion_api()
    _run_id, finding_id = _sensitive_finding(store)
    setter(finding_id, "Marketing", "push", "Lead with it.", at="2026-09-19T12:00:00+00:00")
    setter(finding_id, "Marketing", "use_if_raised", "Changed view.", at="2026-09-19T12:01:00+00:00")
    marketing = [item for item in getter(finding_id) if item["role"] == "Marketing"]
    assert marketing == [{
        **marketing[0], "role": "Marketing", "stance": "use_if_raised", "comment": "Changed view.",
        "time": "2026-09-19T12:01:00+00:00",
    }]
    setter(finding_id, "League GM", "steer_away", "Wait.", at="2026-09-19T12:02:00+00:00")
    assert is_promotable(store, finding_id) is False


def test_r1_row_57b_override_roles_clear_blocks_but_only_overrides_lift_override_blocks(store):
    setter, _getter = _stance_api(store)
    gates, is_promotable = _promotion_api()
    override_roles = getattr(gates, "DEFAULT_OVERRIDE_ROLES", None)
    assert override_roles is not None and tuple(override_roles) == ("League GM", "LK director")

    _run_id, ordinary_block = _sensitive_finding(store, "An ordinary sensitive story")
    setter(ordinary_block, "Marketing", "steer_away", "Wait.", at="2026-09-19T12:00:00+00:00")
    assert is_promotable(store, ordinary_block) is False
    setter(ordinary_block, "League GM", "push", "Cleared.", at="2026-09-19T12:01:00+00:00")
    assert is_promotable(store, ordinary_block) is True

    _run_id, override_block = _sensitive_finding(store, "A second sensitive story")
    setter(override_block, "League GM", "steer_away", "League block.", at="2026-09-19T12:02:00+00:00")
    setter(override_block, "Marketing", "push", "Marketing wants it.", at="2026-09-19T12:03:00+00:00")
    assert is_promotable(store, override_block) is False
    setter(override_block, "LK director", "use_if_raised", "Override cleared.", at="2026-09-19T12:04:00+00:00")
    assert is_promotable(store, override_block) is True


@pytest.mark.live_data
def test_r1_row_55_every_published_finding_has_copy_fields():
    path = REPO / "published" / "store.db"
    con = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        columns = {row[1] for row in con.execute("PRAGMA table_info(findings)")}
        assert {"plain_headline", "premise"} <= columns
        rows = con.execute(
            "SELECT f.id, f.plain_headline, f.premise FROM findings f "
            "JOIN runs r ON r.id = f.run_id "
            "WHERE r.status = 'complete' AND r.run_type IN ('pre_game','post_game','supplemental','follow_up') "
            "AND f.status IN ('shipped','held') ORDER BY f.id"
        ).fetchall()
    finally:
        con.close()
    assert rows
    assert [finding_id for finding_id, headline, premise in rows if not str(headline or "").strip() or not str(premise or "").strip()] == []
