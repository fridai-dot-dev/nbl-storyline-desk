"""Round 3: suggested follow-ups (Bart, 2026-10-28).

The existing single judge call per run also proposes up to three follow-up questions per finding, typed as rarity,
on_pace, comparison or context. They are stored on the finding and shown on its page (with a copyable command) and,
top three, in the leadership email. Rejudging a finished run adds them without re-running any agent.
"""
import re

from conftest import OPENER, REPO

TYPES = {"rarity", "on_pace", "comparison", "context"}


def _scorer_with_followups(cost=0.07):
    def scorer(findings, coverage):
        scores = {}
        for f in findings:
            scores[f["id"]] = {
                "novelty": 0.6, "audience_fit": 0.7, "direction": 0.5, "headline": f"Headline {f['id']}",
                "followups": [
                    {"type": "rarity", "question": f"How rare is finding {f['id']} league-wide since 2015-16?",
                     "why": "Rankable across all box scores."},
                    {"type": "on_pace", "question": "If Adelaide keep this three-point rate, would it be a season record?",
                     "why": "Projects the current pace."},
                    {"type": "comparison", "question": "How did coverage react the last time a bench lost by 30 and won?",
                     "why": "Past coverage comparison."},
                    {"type": "speculation", "question": "Who will win the title?", "why": "Not a valid type."},
                ],
            }
        return scores, cost
    return scorer


def test_judge_stores_typed_followups_capped_at_three(demo_store):
    from storydesk.judge import score_findings

    def scorer(findings, coverage):
        scores, _ = _scorer_with_followups()(findings, coverage)
        return scores

    score_findings(demo_store.store, demo_store.post_run, [], scorer)
    ups = demo_store.store.get_finding(demo_store.f_checked)["followups"]
    assert 1 <= len(ups) <= 3
    assert {u["type"] for u in ups} <= TYPES                      # invalid types are dropped
    assert all(u["question"] and u["why"] for u in ups)


def test_rejudge_adds_followups_without_touching_findings_and_charges_the_ledger(demo_store):
    from storydesk.judge import rejudge

    store = demo_store.store
    before = {f["id"]: (f["status"], f["claim"]) for f in store.findings(demo_store.post_run, include_dropped=True)}
    cost_before = store.get_run(demo_store.post_run)["cost_usd"]
    rejudge(store, demo_store.post_run, stats_db=demo_store.stats_db, corpus_dir=REPO / "tests" / "fixtures" / "corpus",
            scorer=_scorer_with_followups(cost=0.07))
    after = {f["id"]: (f["status"], f["claim"]) for f in store.findings(demo_store.post_run, include_dropped=True)}
    assert after == before                                         # no finding changed
    assert store.get_finding(demo_store.f_checked)["followups"]
    assert abs(store.get_run(demo_store.post_run)["cost_usd"] - (cost_before + 0.07)) < 1e-9


def test_judge_prompt_names_types_and_data_limits():
    text = (REPO / "prompts" / "judge.md").read_text(encoding="utf-8")
    for word in ("rarity", "on_pace", "comparison", "context", "play-by-play", "2015-16", "projection"):
        assert word in text, word


def test_finding_page_and_email_show_suggested_followups(demo_store, tmp_path):
    from storydesk.judge import rejudge
    from storydesk.site import build_site

    rejudge(demo_store.store, demo_store.post_run, stats_db=demo_store.stats_db,
            corpus_dir=REPO / "tests" / "fixtures" / "corpus", scorer=_scorer_with_followups())
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    page = (out / "findings" / f"{demo_store.f_checked}.html").read_text(encoding="utf-8")
    assert "Suggested follow-ups" in page
    assert f"How rare is finding {demo_store.f_checked} league-wide since 2015-16?" in page
    assert re.search(r"storydesk run follow_up[^<]*--anchor\s+%d" % demo_store.f_checked, page)
    assert re.search(r"projection", page, re.I)                    # on_pace suggestions are labelled as projections
    email = (out / "outbox" / "post-game-email.html").read_text(encoding="utf-8")
    assert "Suggested follow-ups" in email
    assert len(re.findall(r'class="[^"]*suggested-followup', email)) <= 3


def test_rejudge_cli_targets_one_run_and_needs_live():
    from conftest import run_py

    out = run_py("-m", "storydesk", "rejudge", "--run-id", "3")
    assert out.returncode != 0 and "--live" in (out.stdout + out.stderr)
