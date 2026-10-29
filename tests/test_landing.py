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
    # Stances replace per-audience sign-offs: the stance and its role show wherever the item appears.
    demo_store.store.set_stance(demo_store.f_held, "Head of social", "use_if_raised", "Fine to use if asked.")
    out = _build(demo_store, tmp_path)
    page = (out / "findings" / f"{demo_store.f_held}.html").read_text(encoding="utf-8")
    assert "Head of social: use if raised" in page and "Fine to use if asked." in page
    assert not re.search(r"Held · officiating · needs sign-off(?! for partners)", page)
    email = (out / "index.html").read_text(encoding="utf-8")
    assert "Head of social: use if raised" in email


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
    visible = re.sub(r"<[^>]+>", " ", index)                            # the inbox keeps run types in data attributes
    assert "pre_game" not in visible and "post_game" not in visible    # human labels, not run-type keys
    assert 'href="#post-game"' in index
    nothing = [f for run in (demo_store.post_run,) for f in demo_store.store.findings(run) if f["kind"] == "nothing_found"]
    for f in nothing:                                                   # searches with no result aren't headline findings
        assert f'findings/{f["id"]}.html' not in index.split("Searched, nothing found")[0]
    assert REPO_URL in index                                            # links back to the repo, its docs and build log
    assert "build-log" in index
