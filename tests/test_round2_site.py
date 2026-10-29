"""Round 2: what the first real site build showed (2026-10-28).

Exec-facing pages need short headlines (the full claim belongs on the detail page), held items must be visibly held,
"What happened" needs the run's own summary, follow-ups must record their request, smoke runs stay off the site,
and long category labels must not collide on charts.
"""
import asyncio
import re
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest

from conftest import CORPUS, EV_STATS, OPENER, POST, Q3_ADL, fake_result, make_ctx, run_py


@pytest.fixture
def site(demo_store, tmp_path):
    from storydesk.site import build_site

    smoke = make_ctx(demo_store.stats_db, demo_store.store, "smoke", POST)
    from storydesk.tools import write_finding
    demo_store.smoke_finding = write_finding(
        smoke, agent="stats", source_type="stats", kind="checked", number=26, query=Q3_ADL,
        claim="Smoke check: Adelaide scored 26 in Q3", evidence=[EV_STATS])
    from storydesk.gates import apply_gates
    apply_gates(demo_store.store, smoke.run_id, stats_db=demo_store.stats_db, as_of=POST)  # shipped, so only the
    out = tmp_path / "site"                                                                 # run type keeps it off
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    return demo_store, out


# ---------- headlines ----------

def test_write_finding_takes_a_short_headline(post_ctx, store):
    from storydesk.tools import ToolError, write_finding

    fid = write_finding(post_ctx, agent="stats", source_type="stats", kind="checked", number=26, query=Q3_ADL,
                        claim="Adelaide scored 26 points in the third quarter, their best quarter of the night.",
                        headline="Adelaide's 26-point third quarter", evidence=[EV_STATS])
    assert store.get_finding(fid)["headline"] == "Adelaide's 26-point third quarter"
    with pytest.raises(ToolError):
        write_finding(post_ctx, agent="stats", source_type="stats", kind="checked", number=26, query=Q3_ADL,
                      claim="x", headline="word " * 40, evidence=[EV_STATS])


def test_headline_fallback_is_short_and_clean():
    from storydesk.site import headline_for

    assert headline_for({"headline": "Given headline", "claim": "Long claim."}) == "Given headline"
    derived = headline_for({"headline": None, "claim": (
        "CONFIRMED: Adelaide won Q1 25-23 at Melbourne tonight, their 5th straight first-quarter win over Melbourne "
        "United (2025-01-04 27-17, then 29-23, 27-22 and 17-14 in 2025-26 box rows, now 25-23). The streak was broken "
        "before that.")})
    assert "(" not in derived and len(derived.split()) <= 25
    assert derived.startswith("CONFIRMED: Adelaide won Q1 25-23")


def test_judge_supplies_missing_headlines(demo_store):
    from storydesk.judge import score_findings

    fid = demo_store.f_attr
    assert not demo_store.store.get_finding(fid).get("headline")

    def scorer(findings, coverage):
        return {f["id"]: {"novelty": 0.5, "audience_fit": 0.5, "direction": 0.5,
                          "headline": f"Headline for {f['id']}"} for f in findings}

    score_findings(demo_store.store, demo_store.post_run, [], scorer)
    assert demo_store.store.get_finding(fid)["headline"] == f"Headline for {fid}"


def test_rejudge_command_needs_live():
    out = run_py("-m", "storydesk", "rejudge", "--run-id", "1")
    assert out.returncode != 0 and "--live" in (out.stdout + out.stderr)


def test_pages_lead_with_headline_and_keep_the_full_claim(site):
    ns, out = site
    ns.store.set_headline(ns.f_checked, "Adelaide's 26-point third quarter")
    from storydesk.site import build_site
    build_site(ns.store, ns.stats_db, out, game_id=OPENER)
    page = (out / "findings" / f"{ns.f_checked}.html").read_text(encoding="utf-8")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S).group(1)
    assert "Adelaide's 26-point third quarter" in h1
    assert ns.store.get_finding(ns.f_checked)["claim"] in page
    email = (out / "outbox" / "post-game-email.html").read_text(encoding="utf-8")
    assert "Adelaide's 26-point third quarter" in email


# ---------- held items, summary, cost label, smoke runs ----------

def test_email_marks_held_items_with_their_category(site):
    _, out = site
    email = (out / "outbox" / "post-game-email.html").read_text(encoding="utf-8")
    assert re.search(r"held[^<]{0,60}officiating", email, re.I), "held officiating item needs a visible badge"


def test_run_summary_feeds_what_happened(store):
    from storydesk.runner import record_result

    run_id = store.start_run("post_game", OPENER, POST, route="sdk")
    result = fake_result(1.0, 100)
    result.result = "Adelaide edged Melbourne 97-95 after winning the third quarter."
    record_result(store, run_id, result, route="sdk", num_agents=5)
    assert store.get_run(run_id)["summary"] == "Adelaide edged Melbourne 97-95 after winning the third quarter."


def test_email_shows_summary_and_labels_cost(demo_store, tmp_path):
    from storydesk.site import build_site

    demo_store.store.set_run_summary(demo_store.post_run, "Adelaide edged Melbourne in a game of five lead changes.")
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    email = (out / "outbox" / "post-game-email.html").read_text(encoding="utf-8")
    assert "Adelaide edged Melbourne in a game of five lead changes." in email
    assert re.search(r"API prices", email)


def test_smoke_runs_stay_off_the_site(site):
    ns, out = site
    assert not (out / "findings" / f"{ns.smoke_finding}.html").exists()
    for page in out.rglob("*.html"):
        assert "Smoke check" not in page.read_text(encoding="utf-8")


# ---------- follow-ups record their request ----------

class QuietClient:
    def __init__(self, options):
        self.options = options

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def query(self, prompt):
        self.prompt = prompt

    async def interrupt(self):
        pass

    async def receive_response(self):
        yield fake_result(0.2, 10)

    async def receive_messages(self):
        yield fake_result(0.2, 10)


def test_follow_up_run_records_and_answers_its_request(demo_store, tmp_path):
    from storydesk.runner import run_live

    q = "Where does this rank league-wide?"
    run_id = asyncio.run(run_live(
        "follow_up", game_id=OPENER, as_of=POST, stats_db=demo_store.stats_db, store=demo_store.store,
        corpus_dir=CORPUS, digest_dir=tmp_path / "d", question=q, anchor_finding_id=demo_store.f_checked,
        asked_by="NBL Now producer", client_factory=QuietClient, judge_scorer=lambda f, c: ({}, 0.0),
        time_limit_s=10))
    reqs = [r for r in demo_store.store.requests() if r["question"] == q]
    assert len(reqs) == 1
    assert reqs[0]["anchor_finding_id"] == demo_store.f_checked
    assert reqs[0]["answered_run_id"] == run_id
    assert reqs[0]["asked_by"] == "NBL Now producer"


# ---------- chart labels ----------

def test_long_category_labels_do_not_collide():
    from storydesk.charts import check_chart, render_bar_chart

    labels = [f"{y}-{y + 1}" for y in range(2015, 2027)]
    title = "Adelaide's three-point attempts per game reached 28.2 in 2025-26"
    svg = render_bar_chart(title, labels, [20.6, 19.2, 17.5, 21.9, 21.3, 24.8, 24.9, 25.6, 23.3, 24.9, 28.2, 30.0],
                           highlight_index=10, y_label="Adelaide 3PA per game")
    assert check_chart(svg, title) == []
    texts = [n for n in ET.fromstring(svg).iter() if n.tag.split("}")[-1] == "text" and (n.text or "").strip()]
    label_texts = [t for t in texts if any((t.text or "").strip() in (l, l[2:], f"{l[2:4]}-{l[7:]}") for l in labels)]
    assert label_texts, "category labels missing"
    rotated = all("rotate(" in (t.get("transform") or "") for t in label_texts)
    shortened = all(len((t.text or "").strip()) <= 7 for t in label_texts)
    assert rotated or shortened
