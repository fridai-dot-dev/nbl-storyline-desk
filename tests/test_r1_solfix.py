"""Sol's R1 fix-round regressions. All model seams are stubbed; no network calls."""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from pathlib import Path

import pytest

from conftest import OPENER, POST, REPO
from test_r1_support import one, parse_html, seed_r1_store


COPY_FIELDS = ("plain_headline", "premise", "metric", "threshold", "test_direction", "actual", "outcome")


def _build_r1(tmp_path: Path, stats_db, mutate=None):
    from storydesk.site import build_site

    ns = seed_r1_store(tmp_path, stats_db)
    if mutate:
        mutate(ns)
    out = tmp_path / "site"
    build_site(ns.store, ns.stats_db, out, game_id=ns.game_id)
    return ns, out


def _mail(out: Path, kind: str):
    return one(parse_html((out / "index.html").read_text(encoding="utf-8")), cls="mail", data_email_type=kind)


def _strip(out: Path):
    root = parse_html((out / "index.html").read_text(encoding="utf-8"))
    return one(root, cls="inbox", data_region="inbox-strip")


def _plain_finding(store) -> int:
    run_id = store.start_run("post_game", OPENER, POST, route="fixture")
    finding_id = store.add_finding(
        run_id=run_id, agent="media", source_type="media", kind="qualitative",
        claim="Melbourne changed its defensive coverage.", audience=["leadership"],
    )
    store.update_finding(finding_id, status="shipped")
    return finding_id


# Item 1: every live steer-away blocks, regardless of sensitivity.
def test_item_1_non_sensitive_steer_away_blocks_until_an_override_clears_it(store):
    from storydesk.gates import is_promotable

    finding_id = _plain_finding(store)
    store.set_stance(finding_id, "Marketing", "steer_away", "Wait for review.", at="2026-09-19T12:00:00+00:00")
    store.set_stance(finding_id, "Broadcast", "push", "Use it.", at="2026-09-19T12:01:00+00:00")
    assert is_promotable(store, finding_id) is False
    store.set_stance(finding_id, "League GM", "push", "Cleared.", at="2026-09-19T12:02:00+00:00")
    assert is_promotable(store, finding_id) is True


# Item 2: stale writes are rejected and override clearance resolves directives atomically.
def test_item_2_stale_stance_update_is_rejected_without_side_effects(store):
    finding_id = _plain_finding(store)
    store.set_stance(finding_id, "Marketing", "push", "Current view.", at="2026-09-19T12:00:00+00:00")
    before = store.directives()
    with pytest.raises(ValueError, match="stale"):
        store.set_stance(finding_id, "Marketing", "steer_away", "Old view.", at="2026-09-19T11:59:00+00:00")
    [stance] = [row for row in store.stances(finding_id) if row["role"] == "Marketing"]
    assert (stance["stance"], stance["comment"], stance["time"]) == (
        "push", "Current view.", "2026-09-19T12:00:00+00:00")
    assert store.directives() == before


def test_item_2_override_clears_the_overridden_steer_away_directive(store):
    finding_id = _plain_finding(store)
    store.set_stance(finding_id, "Marketing", "steer_away", "Wait for footage.", at="2026-09-19T12:00:00+00:00")
    active = [row for row in store.directives() if row.get("finding_id") == finding_id and row["status"] == "active"]
    assert len(active) == 1 and active[0]["stance_role"] == "Marketing"
    store.set_stance(finding_id, "League GM", "push", "Cleared after review.", at="2026-09-19T12:01:00+00:00")
    related = [row for row in store.directives() if row.get("finding_id") == finding_id]
    assert related and all(row["status"] == "cleared" for row in related)


def _copy_run(store):
    run_id = store.start_run("pre_game", OPENER, POST, route="fixture")
    first = store.add_finding(
        run_id=run_id, agent="stats", source_type="stats", kind="checked", number=21,
        claim="Melbourne held Bryce Cotton to 21 points.", audience=["leadership"],
    )
    second = store.add_finding(
        run_id=run_id, agent="stats", source_type="stats", kind="checked", number=25,
        claim="Adelaide scored 25 points in the third quarter.", audience=["leadership"],
    )
    store.add_evidence(first, [{"source_type": "stats", "url": "", "ref": "Bryce Cotton: 21 points"}])
    store.update_finding(first, plain_headline="Did Melbourne hold Bryce Cotton to 21?", premise="Melbourne held Bryce Cotton to 21 points.")
    store.update_finding(second, plain_headline="Did Adelaide score 25 points?", premise="Adelaide scored 25 points in the third quarter.")
    result_run = store.start_run("post_game", OPENER, POST, route="fixture")
    child = store.add_finding(
        run_id=result_run, parent_id=first, agent="stats", source_type="stats", kind="checked", number=29,
        claim="Bryce Cotton scored 29 points against Melbourne.", audience=["leadership"],
    )
    return run_id, first, second, child


# Item 3: validate every candidate first, then write the run in one transaction.
def test_item_3_invalid_copy_rejects_the_run_without_partial_writes(store):
    from storydesk.judge import copy_pass

    run_id, first, second, _child = _copy_run(store)
    before = {fid: {name: store.get_finding(fid).get(name) for name in COPY_FIELDS} for fid in (first, second)}

    def copier(_findings):
        return {
            first: {"plain_headline": "Did Melbourne hold Bryce Cotton to 21?",
                    "premise": "Bryce Cotton scored 29 points against Melbourne.",
                    "metric": "points", "threshold": 21, "direction": "at_most", "actual": 29,
                    "outcome": "contradicted"},
            second: {"plain_headline": "Did Sydney score 88 points?",
                     "premise": "Sydney scored 88 points against Adelaide."},
        }

    with pytest.raises(ValueError, match=r"unsupported|copy"):
        copy_pass(store, run_id, copier)
    assert {fid: {name: store.get_finding(fid).get(name) for name in COPY_FIELDS} for fid in (first, second)} == before


def test_item_3_unstored_structured_number_is_rejected(store):
    from storydesk.judge import copy_pass

    run_id, first, _second, _child = _copy_run(store)
    before = {name: store.get_finding(first).get(name) for name in COPY_FIELDS}
    with pytest.raises(ValueError, match=r"actual|99|number"):
        copy_pass(store, run_id, lambda _findings: {
            first: {"plain_headline": "Did Melbourne hold Bryce Cotton to 21?",
                    "premise": "Melbourne held Bryce Cotton to 21 points.",
                    "metric": "points", "threshold": 21, "direction": "at_most", "actual": 99,
                    "outcome": "contradicted"},
        })
    assert {name: store.get_finding(first).get(name) for name in COPY_FIELDS} == before


def test_item_3_published_copy_passes_the_validator_over_a_read_only_store():
    from storydesk.judge import validate_copy_candidate
    from storydesk.store import Store

    class ReadOnlyStore(Store):
        def _con(self):
            con = sqlite3.connect(f"{self.path.resolve().as_uri()}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA query_only = ON")
            return con

    store = ReadOnlyStore(REPO / "published" / "store.db")
    checked = 0
    for run in store.game_runs(OPENER):
        if run["status"] != "complete":
            continue
        for finding in store.findings(run["id"], include_dropped=True):
            if not finding.get("plain_headline") or not finding.get("premise"):
                continue
            candidate = {name: finding.get(name) for name in COPY_FIELDS if finding.get(name) is not None}
            validate_copy_candidate(store, finding, candidate)
            checked += 1
    assert checked >= 25


def _protected_published_rows(path: Path):
    con = sqlite3.connect(path)
    try:
        return con.execute(
            "SELECT id, claim, novelty, audience_fit, direction, headline, followups, "
            "plain_headline, premise, metric, threshold, test_direction, actual, outcome FROM findings ORDER BY id"
        ).fetchall()
    finally:
        con.close()


# Item 4: the committed published ledger carries only the stance-format simulated round.
def test_item_4_simulate_preserves_published_copy_and_judge_output(tmp_path):
    from storydesk.cli import main

    copied = tmp_path / "published.db"
    shutil.copy2(REPO / "published" / "store.db", copied)
    before = _protected_published_rows(copied)
    assert main(["simulate", "--store", str(copied), "--file", str(REPO / "published" / "simulated-round.json")]) == 0
    assert _protected_published_rows(copied) == before


def test_item_4_published_store_has_expected_simulated_stances_and_renders_them(tmp_path):
    from storydesk.site import build_site
    from storydesk.store import Store

    expected = json.loads((REPO / "published" / "simulated-round.json").read_text(encoding="utf-8"))["stances"]
    con = sqlite3.connect(f"{(REPO / 'published/store.db').resolve().as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        assert con.execute("SELECT COUNT(*) FROM feedback WHERE simulated = 1").fetchone()[0] == 0
        actual = [dict(row) for row in con.execute(
            "SELECT finding_id, role, stance, comment, simulated FROM stances WHERE simulated = 1 ORDER BY finding_id, role"
        )]
    finally:
        con.close()
    normalised = sorted(
        ({"finding_id": item["finding_id"], "role": item["role"], "stance": item["stance"],
          "comment": item.get("comment"), "simulated": int(item["simulated"])} for item in expected),
        key=lambda item: (item["finding_id"], item["role"]),
    )
    assert actual == normalised

    out = tmp_path / "published-site"
    build_site(Store(REPO / "published" / "store.db"), REPO / "data" / "stats.duckdb", out, game_id=OPENER)
    for stance in expected:
        page = parse_html((out / "findings" / f'{stance["finding_id"]}.html').read_text(encoding="utf-8"))
        rows = [row for row in page.descendants(cls="stance-record") if stance["role"] in row.text()]
        assert len(rows) == 1 and "simulated" in rows[0].text().lower(), stance


# Item 5: what-moved is a compact test-result list, not a second set of full story cards.
def test_item_5_what_moved_contains_only_compact_structured_tests(tmp_path, stats_db):
    ns, out = _build_r1(tmp_path, stats_db)
    moved = one(_mail(out, "post_game"), data_section="what-moved")
    boxes = [node for node in moved.descendants(cls="item") if node.attrs.get("data-test-finding")]
    assert {box.attrs["data-test-finding"] for box in boxes} == {
        str(ns.finding_ids["test_valid"]), str(ns.finding_ids["test_mismatch"]),
        str(ns.finding_ids["test_indeterminate"]),
    }
    for box in boxes:
        assert not [node for node in box.descendants(cls="premise") if "legacy-check" not in node.classes]
        assert not [node for node in box.descendants(cls="stance") if "legacy-check" not in node.classes]
        assert box.descendants(cls="full-story")
    valid = next(box for box in boxes if box.attrs["data-test-finding"] == str(ns.finding_ids["test_valid"]))
    assert valid.descendants("img", "chart")
    assert one(valid, cls="result-line").text() == (
        "Result: 26 Bryce Cotton points against a test line of 21. Contradicted.")
    indeterminate = next(
        box for box in boxes
        if box.attrs["data-test-finding"] == str(ns.finding_ids["test_indeterminate"])
    )
    assert not indeterminate.descendants("img", "chart")
    assert one(indeterminate, cls="result-line").text() == "Couldn't tell from the data."


@pytest.mark.parametrize("raw,plain", [
    ("confirms", "Confirmed"), ("contradicts", "Contradicted"),
    ("not_supported", "Not supported"), ("indeterminate", "Couldn't tell from the data"),
])
def test_item_5_outcome_enums_map_to_plain_reader_words(raw, plain):
    from storydesk.site import _outcome_label

    assert _outcome_label(raw) == plain


# Item 6: a missing executive summary produces a data lead, never repeated premise copy.
def test_item_6_pre_game_fallback_lead_is_built_from_counts(tmp_path, stats_db):
    def drop_summary(ns):
        ns.store.set_exec_summary(ns.run_ids["pre"], None)

    ns, out = _build_r1(tmp_path, stats_db, drop_summary)
    lead = one(_mail(out, "pre_game"), cls="lead").text()
    premises = {ns.store.get_finding(fid)["premise"] for key, fid in ns.finding_ids.items() if key.startswith("test_")}
    assert lead == "3 storylines to test tonight: 2 checked against the stats, 0 sensitive and waiting for a stance."
    assert lead not in premises


def test_item_6_fallback_lead_does_not_count_a_sensitive_story_with_a_promoting_stance(tmp_path, stats_db):
    def approve_sensitive_story(ns):
        ns.store.set_exec_summary(ns.run_ids["pre"], None)
        finding_id = ns.finding_ids["test_indeterminate"]
        ns.store.update_finding(finding_id, sensitivity="injury")
        ns.store.set_stance(
            finding_id, "Broadcast", "push", "Cleared for the pre-game note.",
            at="2026-09-19T06:31:00+00:00",
        )

    _ns, out = _build_r1(tmp_path, stats_db, approve_sensitive_story)
    assert one(_mail(out, "pre_game"), cls="lead").text() == (
        "3 storylines to test tonight: 2 checked against the stats, 0 sensitive and waiting for a stance."
    )


# Item 7: fixed row order, top-pick post preview, and honest follow-up timing.
def test_item_7_inbox_preview_order_and_follow_up_later_label(tmp_path, stats_db):
    ns, out = _build_r1(tmp_path, stats_db)
    rows = _strip(out).descendants(cls="row")
    assert [row.attrs["data-run-type"] for row in rows] == ["pre_game", "post_game", "supplemental", "follow_up"]
    by_kind = {row.attrs["data-run-type"]: row for row in rows}
    post_preview = one(by_kind["post_game"], cls="preview").text().lstrip("· ")
    from storydesk.site import _copy_headline  # statements outside the pre-game email (Bart, 2026-10-30)
    assert post_preview == _copy_headline(ns.store.get_finding(ns.finding_ids["top_pick"]))
    assert one(by_kind["follow_up"], cls="t").text().strip().lower() == "later"
    follow = one(parse_html((out / "emails" / "follow-up.html").read_text(encoding="utf-8")), cls="mail")
    header = one(follow, cls="head").text()
    assert "later" in header.lower()
    assert not re.search(r"\b\d{1,2}:\d{2}\s+(?:am|pm)\b", header, re.I)


# Item 8: run cutoffs use the same Melbourne-local presentation as mail headers.
def test_item_8_runs_table_uses_melbourne_local_times_without_iso(tmp_path, stats_db):
    _ns, out = _build_r1(tmp_path, stats_db)
    table = one(parse_html((out / "index.html").read_text(encoding="utf-8")), cls="runs-table")
    text = table.text()
    assert not re.search(r"\d{4}-\d\d-\d\dT", text)
    for local in ("Sat 4:30 pm", "Sat 9:26 pm", "Sat 10:20 pm"):
        assert local in text
