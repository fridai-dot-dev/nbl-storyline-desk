"""Pre-publish: the landing page is the GM's first impression, sign-offs must be visible, and demo re-judging is
separated whatever shape its usage was recorded in (2026-10-29)."""
import re

from conftest import OPENER

REPO_URL = "https://github.com/fridai-dot-dev/nbl-storyline-desk"


def _build(ns, tmp_path):
    from storydesk.site import build_site

    out = tmp_path / "site"
    build_site(ns.store, ns.stats_db, out, game_id=OPENER)
    return out


def test_signoffs_are_visible_where_the_item_appears(demo_store, tmp_path):
    demo_store.store.add_signoff(demo_store.f_held, approver="Bart Lind (demo approver)", audience="producers")
    out = _build(demo_store, tmp_path)
    page = (out / "findings" / f"{demo_store.f_held}.html").read_text(encoding="utf-8")
    assert "Signed off for producers" in page and "Bart Lind (demo approver)" in page
    assert not re.search(r"Held · officiating · needs sign-off(?! for partners)", page)  # remaining audience named
    email = (out / "outbox" / "post-game-email.html").read_text(encoding="utf-8")
    assert "Signed off for producers" in email


def test_rejudge_cost_is_separated_for_either_usage_shape(demo_store, tmp_path):
    run = demo_store.store.get_run(demo_store.pre_run if hasattr(demo_store, "pre_run") else demo_store.post_run)
    usage = dict(run["model_usage"])
    usage["rejudge"] = {"claude-opus-5-5": {"costUSD": 0.62}}          # a single dict, not a list
    demo_store.store.finish_run(run["id"], status="complete", cost_usd=run["cost_usd"] + 0.62,
                                duration_s=run["duration_s"], model_usage=usage, num_agents=run["num_agents"],
                                route=run["route"])
    out = _build(demo_store, tmp_path)
    index = (out / "index.html").read_text(encoding="utf-8")
    assert f"US${run['cost_usd']:.2f}" in index and "US$0.62" in index


def test_landing_page_is_a_guided_path(demo_store, tmp_path):
    out = _build(demo_store, tmp_path)
    index = (out / "index.html").read_text(encoding="utf-8")
    for label in ("Pre-game", "Post-game", "Follow-up"):
        assert label in index, label
    assert "pre_game" not in index and "post_game" not in index        # human labels, not run-type keys
    assert 'href="outbox/post-game-email.html"' in index
    nothing = [f for run in (demo_store.post_run,) for f in demo_store.store.findings(run) if f["kind"] == "nothing_found"]
    for f in nothing:                                                   # searches with no result aren't headline findings
        assert f'findings/{f["id"]}.html' not in index.split("Searched, nothing found")[0]
    assert REPO_URL in index                                            # links back to the repo, its docs and build log
    assert "build-log" in index
