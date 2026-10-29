"""D8: the static site builds from the store, every internal link resolves, and the rules hold on the page."""
import re
from pathlib import Path

import pytest

from conftest import OPENER


@pytest.fixture
def site(demo_store, tmp_path):
    from storydesk.site import build_site

    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    return demo_store, out


def _html_files(out):
    return sorted(out.rglob("*.html"))


def _links(path):
    return re.findall(r'(?:href|src)="([^"]+)"', path.read_text(encoding="utf-8"))


def test_core_pages_exist(site):
    ns, out = site
    for rel in ("index.html", "board.html"):  # the inbox holds the pre-game and post-game emails; the board moved
        assert (out / rel).exists(), rel
    for fid in (ns.f_checked, ns.f_attr, ns.f_held, ns.f_fan, ns.f_child, ns.pre_finding):
        assert (out / "findings" / f"{fid}.html").exists(), fid
    assert not (out / "findings" / f"{ns.f_wrong}.html").exists()  # dropped findings get no page


def test_every_internal_link_resolves(site):
    _, out = site
    for page in _html_files(out):
        for link in _links(page):
            if link.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target = (page.parent / link.split("#")[0]).resolve()
            assert target.exists(), f"{page.relative_to(out)} -> {link}"


def test_checked_finding_page_has_a_valid_chart(site):
    from storydesk.charts import check_chart

    ns, out = site
    claim = ns.store.get_finding(ns.f_checked)["claim"]
    html = (out / "findings" / f"{ns.f_checked}.html").read_text(encoding="utf-8")
    svgs = re.findall(r"<svg.*?</svg>", html, flags=re.S)
    assert svgs, "checked finding with a chart spec should render a chart"
    assert check_chart(svgs[0], claim) == []


def test_trail_links_child_to_anchor(site):
    ns, out = site
    page = out / "findings" / f"{ns.f_child}.html"
    targets = {(page.parent / l.split("#")[0]).resolve() for l in _links(page) if not l.startswith("http")}
    assert (out / "findings" / f"{ns.f_checked}.html").resolve() in targets


def test_held_items_show_as_held_and_handles_never_appear(site):
    ns, out = site
    held_page = (out / "findings" / f"{ns.f_held}.html").read_text(encoding="utf-8").lower()
    assert "sensitive · officiating" in held_page
    email = (out / "index.html").read_text(encoding="utf-8")
    assert "sensitive · officiating" in email.lower()
    for page in _html_files(out):
        text = page.read_text(encoding="utf-8")
        assert "test_handle" not in text, page
    fan_page = (out / "findings" / f"{ns.f_fan}.html").read_text(encoding="utf-8")
    assert "the bench won it for Adelaide" in fan_page


def test_email_reports_speed_cost_and_labels_simulated_feedback(site):
    ns, out = site
    email = (out / "index.html").read_text(encoding="utf-8")
    assert re.search(r"cutoff[^<]{0,80}(whistle|full time)", email, re.I)  # replays never claim live timing
    assert "$" in email
    assert ns.store.get_finding(ns.f_checked)["claim"] in email
    assert "simulated" in email.lower()


def test_pre_game_page_lists_pre_game_findings(site):
    ns, out = site
    page = (out / "index.html").read_text(encoding="utf-8")
    assert ns.store.get_finding(ns.pre_finding)["claim"] in page


def test_follow_up_answer_is_shown_with_its_question(site):
    ns, out = site
    anchor_page = (out / "findings" / f"{ns.f_checked}.html").read_text(encoding="utf-8")
    assert "Was this Adelaide's best quarter of the game?" in anchor_page
    assert ns.store.get_finding(ns.f_child)["claim"] in anchor_page
