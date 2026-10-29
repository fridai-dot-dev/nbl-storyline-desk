"""Pre-publish checks (2026-10-29): untrusted text is escaped everywhere, and public pages say what really happened.

The site renders YouTube chat, auto-captions, press transcripts and agent-written text, including through a
hand-written markdown renderer. None of it may execute as HTML. Run cost must separate the demo's re-judging,
and a replayed game must not claim a live "after full time" timing.
"""
import json
import re

from conftest import EV_STATS, OPENER, POST, Q3_ADL, fake_result, make_ctx

PAYLOADS = ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>', '"><svg onload=alert(1)>']


def _poison(ns):
    from storydesk.gates import apply_gates
    from storydesk.runner import record_result
    from storydesk.tools import write_finding

    ctx = make_ctx(ns.stats_db, ns.store, "post_game", POST)
    fid = write_finding(
        ctx, agent="commentary", source_type="commentary", kind="attributed",
        claim=f"Claim with {PAYLOADS[0]} and {PAYLOADS[2]}", headline="Plain headline",
        evidence=[{"source_type": "commentary", "url": "https://example.test/broadcast", "ref": POST,
                   "quote": f"Quote {PAYLOADS[1]} {PAYLOADS[0]}"}])
    ns.store.set_headline(fid, f"Headline {PAYLOADS[1]}")  # the tool rejects this; the judge path stores directly
    apply_gates(ns.store, ctx.run_id, stats_db=ns.stats_db, as_of=POST)
    r = fake_result(1.0, 120)
    r.result = f"# Notes\n\n**Bold** {PAYLOADS[0]}\n\n- item {PAYLOADS[1]}"
    record_result(ns.store, ctx.run_id, r, route="sdk", num_agents=5)
    ns.store.set_exec_summary(ctx.run_id, f"Summary {PAYLOADS[2]}")
    ns.store.set_followups(fid, [{"type": "rarity", "question": f"Question {PAYLOADS[0]}", "why": f"Why {PAYLOADS[1]}"}])
    return fid


def test_untrusted_text_is_escaped_on_every_page(demo_store, tmp_path):
    from storydesk.site import build_site

    _poison(demo_store)
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    for page in out.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        for raw in ("<script>alert", "<img src=x", "<svg onload", "onerror=alert(1)>"):
            assert raw not in html, f"{page.relative_to(out)} renders unescaped {raw!r}"


def test_run_cost_separates_demo_rejudging(demo_store, tmp_path):
    from storydesk.site import build_site

    run = demo_store.store.get_run(demo_store.post_run)
    usage = dict(run["model_usage"])
    usage["rejudge"] = [{"claude-opus-5-5": {"costUSD": 0.45}}]
    demo_store.store.finish_run(demo_store.post_run, status="complete", cost_usd=run["cost_usd"] + 0.45,
                                duration_s=run["duration_s"], model_usage=usage, num_agents=run["num_agents"],
                                route=run["route"])
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    email = (out / "index.html").read_text(encoding="utf-8")
    assert f"US${run['cost_usd']:.2f}" in email              # the run's own cost, first
    assert re.search(r"re-?judg", email, re.I)               # demo re-judging is labelled, not folded in


def test_replay_timing_is_described_honestly(demo_store, tmp_path):
    from storydesk.site import build_site

    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    email = (out / "index.html").read_text(encoding="utf-8")
    assert "after full time" not in email.lower()
    assert re.search(r"cutoff[^<]{0,80}(whistle|full time)", email, re.I)
