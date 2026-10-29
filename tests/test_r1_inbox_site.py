"""R1 acceptance checks for the approved inbox/email design (decision rows 4-15, 18-21, 53-58)."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

from conftest import REPO
from test_r1_support import build_r1_site, load_r1_payload, one, parse_html


HONESTY_NOTE = (
    "This is a rapid build, about 1–1.5 days of full-time work, made to show Claude agent capability. "
    "The order of operations, timing, prompts and safety controls are informed guesses, not knowledge of "
    "LK's structure or priorities."
)
BANNED = ("cleared for producers", "for partners", "Approve for partners", "Keep internal")
EMAIL_TO = "Leadership, Media, Producers, Broadcast, Partnerships manager · internal only"


@pytest.fixture(scope="module")
def r1_site(tmp_path_factory, stats_db):
    return build_r1_site(tmp_path_factory.mktemp("r1-site"), stats_db)


@pytest.fixture(scope="module")
def r1_site_no_fans(tmp_path_factory, stats_db):
    return build_r1_site(tmp_path_factory.mktemp("r1-site-no-fans"), stats_db, with_fans=False)


def _read(out: Path, rel: str) -> str:
    return (out / rel).read_text(encoding="utf-8")


def _pages(out: Path) -> list[Path]:
    return sorted(out.rglob("*.html"))


def _email_nodes(out: Path):
    for page in _pages(out):
        root = parse_html(page.read_text(encoding="utf-8"))
        for mail in root.descendants(cls="mail"):
            yield page, mail


def _internal_targets(page: Path, out: Path):
    root = parse_html(page.read_text(encoding="utf-8"))
    for node in root.descendants():
        for attribute in ("href", "src"):
            value = node.attrs.get(attribute)
            if not value or value.startswith(("#", "data:", "mailto:", "http://", "https://")):
                continue
            parsed = urlsplit(value)
            yield value, (page.parent / unquote(parsed.path)).resolve()


def _section_positions(mail):
    nodes = [node for node in mail.descendants() if node.attrs.get("data-section")]
    return {node.attrs["data-section"]: index for index, node in enumerate(nodes)}


def _story_boxes(root):
    return [node for node in root.descendants(cls="item") if node.attrs.get("data-finding")]


def _css_for(page: Path) -> str:
    root = parse_html(page.read_text(encoding="utf-8"))
    chunks = [node.text() for node in root.descendants("style")]
    for link in root.descendants("link"):
        if "stylesheet" not in link.attrs.get("rel", "").split():
            continue
        href = link.attrs.get("href", "")
        if href and not href.startswith(("http://", "https://")):
            chunks.append((page.parent / urlsplit(href).path).read_text(encoding="utf-8"))
    return "\n".join(chunks)


def _normalise_css(css: str) -> str:
    return re.sub(r"\s+", "", css).lower()


def test_r1_row_4_inbox_has_exact_honesty_note(r1_site):
    _ns, out = r1_site
    assert HONESTY_NOTE in _read(out, "index.html")


def test_r1_row_5_root_is_inbox_board_moved_and_links_resolve(r1_site):
    _ns, out = r1_site
    index = parse_html(_read(out, "index.html"))
    assert index.descendants(cls="inbox"), "index.html must be the inbox, not the producer board"
    assert (out / "board.html").is_file()
    assert parse_html(_read(out, "board.html")).descendants(cls="board")
    broken = [f"{page.relative_to(out)} -> {raw}" for page in _pages(out) for raw, target in _internal_targets(page, out) if not target.exists()]
    assert broken == []


def test_r1_row_6_inbox_regions_and_four_rows_are_in_approved_order(r1_site):
    _ns, out = r1_site
    root = parse_html(_read(out, "index.html"))
    ordered = [
        node.attrs.get("data-region") or node.attrs.get("data-email-type")
        for node in root.descendants()
        if node.attrs.get("data-region") in {"inbox-strip", "internal-note"}
        or node.attrs.get("data-email-type") in {"pre_game", "post_game"}
    ]
    assert ordered == ["inbox-strip", "internal-note", "pre_game", "post_game"]
    strip = one(root, cls="inbox", data_region="inbox-strip")
    rows = strip.descendants(cls="row")
    assert [row.attrs.get("data-run-type") for row in rows] == ["pre_game", "post_game", "supplemental", "follow_up"]


def test_r1_row_7_pre_game_sections_order_and_fan_data_rule(r1_site, r1_site_no_fans):
    ns, with_out = r1_site
    _without_ns, without_out = r1_site_no_fans
    with_mail = one(parse_html(_read(with_out, "index.html")), cls="mail", data_email_type="pre_game")
    without_mail = one(parse_html(_read(without_out, "index.html")), cls="mail", data_email_type="pre_game")
    expected = ["lead", "tests", "fan-signal", "reply", "footer"]
    assert list(_section_positions(with_mail)) == expected
    assert list(_section_positions(without_mail)) == ["lead", "tests", "reply", "footer"]
    pre_ids = {str(ns.finding_ids[key]) for key in ("test_valid", "test_mismatch", "test_indeterminate")}
    tests_section = one(with_mail, data_section="tests")
    assert {box.attrs["data-finding"] for box in _story_boxes(tests_section)} == pre_ids


def test_r1_row_8_post_game_sections_order_and_sensitive_cap(r1_site):
    _ns, out = r1_site
    mail = one(parse_html(_read(out, "index.html")), cls="mail", data_email_type="post_game")
    assert list(_section_positions(mail)) == [
        "lead", "what-moved", "top-pick", "sensitive", "followups", "reply", "footer", "reply-thread",
    ]
    sensitive = one(mail, data_section="sensitive")
    shown = _story_boxes(sensitive)
    assert 1 <= len(shown) <= 4
    needs_stance = [box.attrs.get("data-needs-stance") == "true" for box in shown]
    assert needs_stance == sorted(needs_stance, reverse=True), "stories needing a stance must come first"
    assert re.search(r"\+\s*1\s+more on the board", sensitive.text(), re.I)
    top_pick = one(mail, data_section="top-pick")
    assert len(_story_boxes(top_pick)) == 1 and re.search(r"suggestion", top_pick.text(), re.I)
    followups = one(mail, data_section="followups")
    assert len(followups.descendants("li")) == 3
    assert "reply with a number, change one, or ask your own" in followups.text().lower()
    assert "simulated" in one(mail, data_section="reply-thread").text().lower()


def test_r1_row_9_every_email_story_box_has_the_complete_contract(r1_site):
    _ns, out = r1_site
    boxes = []
    for _page, mail in _email_nodes(out):
        boxes.extend(_story_boxes(mail))
    assert boxes
    for box in boxes:
        fid = box.attrs["data-finding"]
        assert box.descendants(cls="h"), f"{fid}: plain-question headline"
        assert box.descendants(cls="premise"), f"{fid}: premise"
        assert box.descendants(cls="test") or box.descendants(cls="status"), f"{fid}: test/status"
        stance = one(box, cls="stance")
        labels = stance.text().lower()
        for label in ("push it", "use if it comes up", "steer away", "comment"):
            assert label in labels, (fid, label)
        full = [a for a in box.descendants("a") if "full story" in a.text().lower()]
        assert len(full) == 1 and re.search(rf"findings/{fid}\.html(?:$|[?#])", full[0].attrs.get("href", "")), fid


def test_r1_row_10_every_email_header_names_internal_recipients(r1_site):
    _ns, out = r1_site
    headers = [one(mail, cls="head") for _page, mail in _email_nodes(out)]
    assert len(headers) >= 4
    for header in headers:
        assert EMAIL_TO in header.text()


def test_r1_row_11_email_bodies_are_light_bounded_and_script_free(r1_site):
    _ns, out = r1_site
    mails = list(_email_nodes(out))
    assert mails
    for page, mail in mails:
        assert not mail.descendants("script"), page
        assert mail.descendants(cls="body"), page
        css = _normalise_css(_css_for(page))
        assert "--email-bg:#fff" in css and "--email-text:#1a1a1a" in css
        width = re.search(r"\.body[^{}]*\{[^{}]*max-width:(\d+)px", css)
        assert width and int(width.group(1)) <= 600
        dark = "".join(re.findall(r"@media\(prefers-color-scheme:dark\)\{(.*?)\}\s*\}", css, re.S))
        assert "--email-bg:" not in dark and "--email-text:" not in dark


_NUMBER = re.compile(r"(?<![\w])\d+(?:[.,]\d+)*(?![\w])")
_CAPITAL = re.compile(r"\b[A-Z][A-Za-z'’.-]+\b")
_GRAMMAR = {"Can", "Will", "Did", "What", "How", "Should", "The", "That", "It", "Commentary", "Fans"}


def _copy_tokens(text: str) -> set[str]:
    return set(_NUMBER.findall(text)) | {word for word in _CAPITAL.findall(text) if word not in _GRAMMAR}


def _stored_source(ns, finding_ids: list[int]) -> str:
    parts = []
    for finding_id in finding_ids:
        finding = ns.store.get_finding(finding_id)
        parts.append(str(finding.get("claim") or ""))
        for evidence in ns.store.evidence(finding_id):
            parts.extend(str(evidence.get(key) or "") for key in ("quote", "ref"))
    return " ".join(parts)


def test_r1_row_12_story_copy_and_leads_only_restate_stored_sources(r1_site):
    ns, out = r1_site
    mails = [mail for _page, mail in _email_nodes(out)]
    boxes = [box for mail in mails for box in _story_boxes(mail)]
    assert boxes
    for box in boxes:
        finding_id = int(box.attrs["data-finding"])
        copy = one(box, cls="h").text() + " " + one(box, cls="premise").text()
        source = _stored_source(ns, [finding_id])
        assert _copy_tokens(copy) <= _copy_tokens(source), (finding_id, _copy_tokens(copy) - _copy_tokens(source))
    leads = [lead for mail in mails for lead in mail.descendants(cls="lead")]
    assert leads
    for lead in leads:
        ids = [int(value) for value in lead.attrs.get("data-source-findings", "").split()]
        assert ids, "email leads must name the stored findings they restate"
        source = _stored_source(ns, ids)
        assert _copy_tokens(lead.text()) <= _copy_tokens(source)


def test_r1_row_13_rendered_copy_comes_from_store_not_site_source(r1_site):
    ns, out = r1_site
    rendered = "\n".join(page.read_text(encoding="utf-8") for page in _pages(out))
    source = (REPO / "src" / "storydesk" / "site.py").read_text(encoding="utf-8")
    boxes = [box for _page, mail in _email_nodes(out) for box in _story_boxes(mail)]
    assert boxes
    for box in boxes:
        stored = ns.store.get_finding(int(box.attrs["data-finding"]))
        assert one(box, cls="h").text() == stored["plain_headline"]
        assert one(box, cls="premise").text() == stored["premise"]
    fixture_by_key = {item["key"]: item for item in ns.payload["findings"]}
    for key in ("test_valid", "top_pick", "supp_story", "follow_story"):
        item = fixture_by_key[key]
        assert item["plain_headline"] in rendered and item["premise"] in rendered
        assert item["plain_headline"] not in source and item["premise"] not in source


def test_r1_row_14_every_stance_action_is_a_prefilled_mailto(r1_site):
    _ns, out = r1_site
    boxes = [box for _page, mail in _email_nodes(out) for box in _story_boxes(mail)]
    assert boxes
    for box in boxes:
        headline = one(box, cls="h").text()
        links = one(box, cls="stance").descendants("a")
        assert len(links) >= 4
        for link in links:
            parsed = urlsplit(link.attrs.get("href", ""))
            assert parsed.scheme == "mailto" and parsed.path == "storyline-desk@example.com"
            prefilled = " ".join(value for values in parse_qs(parsed.query).values() for value in values)
            assert prefilled and headline in prefilled


def test_r1_row_15_legacy_audience_wording_is_absent(r1_site):
    _ns, out = r1_site
    pages = "\n".join(page.read_text(encoding="utf-8") for page in _pages(out)).lower()
    for phrase in BANNED:
        assert phrase.lower() not in pages, phrase


def test_r1_row_16_unapproved_sensitive_story_is_not_promoted_anywhere(r1_site):
    ns, out = r1_site
    finding_id = str(ns.finding_ids["sensitive_none"])
    post = one(parse_html(_read(out, "index.html")), cls="mail", data_email_type="post_game")
    assert finding_id not in {box.attrs.get("data-finding") for box in _story_boxes(one(post, data_section="top-pick"))}
    followups = one(post, data_section="followups")
    assert not [link for link in followups.descendants("a") if re.search(rf"findings/{finding_id}\.html", link.attrs.get("href", ""))]
    board = parse_html(_read(out, "board.html"))
    promoted = {
        node.attrs.get("data-finding") for node in board.descendants(cls="angle")
        if node.attrs.get("data-finding")
    }
    assert finding_id not in promoted
    assert finding_id in {box.attrs.get("data-finding") for box in _story_boxes(one(post, data_section="sensitive"))}


def test_r1_row_18_every_simulated_stance_is_labelled(r1_site):
    ns, out = r1_site
    fixture_by_key = {item["key"]: item for item in ns.payload["findings"]}
    simulated = [
        (key, stance) for key, item in fixture_by_key.items()
        for stance in item.get("stances", []) if stance.get("simulated")
    ]
    assert simulated
    for key, stance in simulated:
        page = parse_html(_read(out, f"findings/{ns.finding_ids[key]}.html"))
        rows = [row for row in page.descendants(cls="stance-record") if stance["role"] in row.text()]
        assert len(rows) == 1 and "simulated" in rows[0].text().lower()


def test_r1_row_19_agora_light_tokens_and_fonts_are_exact(r1_site):
    _ns, out = r1_site
    css = _normalise_css(_css_for(out / "index.html"))
    expected = {
        "--text": "#1a1a1a", "--muted": "#6b6b6b", "--bg": "#fff", "--surface": "#f5f5f5",
        "--border": "#d9d9d9", "--chart-ink": "#1f3a5f", "--positive": "#3d7a4a",
        "--negative": "#a04545", "--neutral": "#8a8a8a",
    }
    for name, value in expected.items():
        assert f"{name}:{value}" in css, name
    assert "inter" in css and "source serif 4" in css and "ui-monospace" in css


def test_r1_row_20_dark_css_uses_charcoal_and_white_for_all_text(r1_site):
    _ns, out = r1_site
    css = _normalise_css(_css_for(out / "index.html"))
    dark_blocks = re.findall(r"@media\(prefers-color-scheme:dark\)\{(.*?)\}\s*\}", css, re.S)
    assert dark_blocks
    dark = "".join(dark_blocks)
    assert "--bg:#262626" in dark and "--card:#303030" in dark and "--border:#444" in dark
    assert "--text:#fff" in dark and "--muted:#fff" in dark


def test_r1_row_21_sensitive_tag_has_exact_light_and_dark_orange_tokens(r1_site):
    _ns, out = r1_site
    css = _normalise_css(_css_for(out / "index.html"))
    for declaration in ("--sensitive-text:#9a4a00", "--sensitive-bg:#fdf0e1", "--sensitive-border:#e3a96f"):
        assert declaration in css
    dark = "".join(re.findall(r"@media\(prefers-color-scheme:dark\)\{(.*?)\}\s*\}", css, re.S))
    assert "--sensitive-bg:#5a3415" in dark and "--sensitive-border:#e3a96f" in dark
    assert "--sensitive-text:#fff" in dark


def test_r1_row_53_supplemental_and_follow_up_rows_open_matching_emails(r1_site):
    _ns, out = r1_site
    root = parse_html(_read(out, "index.html"))
    strip = one(root, cls="inbox", data_region="inbox-strip")
    for run_type in ("supplemental", "follow_up"):
        row = one(strip, cls="row", data_run_type=run_type)
        links = row.descendants("a")
        assert len(links) == 1
        target = (out / urlsplit(links[0].attrs["href"]).path).resolve()
        assert target.is_file()
        mail = one(parse_html(target.read_text(encoding="utf-8")), cls="mail", data_email_type=run_type)
        assert _story_boxes(mail), run_type


def test_r1_row_54_email_charts_are_images_and_controls_are_links_only(r1_site):
    _ns, out = r1_site
    chart_images = []
    for page, mail in _email_nodes(out):
        for forbidden in ("svg", "button", "form", "script"):
            assert not mail.descendants(forbidden), f"{page.name}: <{forbidden}> inside email"
        chart_images.extend(mail.descendants("img", "chart"))
    assert chart_images, "the paired-bar and test-result charts must render as email-safe images"
    for image in chart_images:
        src = image.attrs.get("src", "")
        assert src.startswith("data:image/") or (image.parent and src)


def test_r1_row_56_unverifiable_and_indeterminate_tests_render_text_only(r1_site):
    ns, out = r1_site
    post = one(parse_html(_read(out, "index.html")), cls="mail", data_email_type="post_game")
    moved = one(post, data_section="what-moved")
    by_test = {box.attrs.get("data-test-finding"): box for box in _story_boxes(moved)}
    valid = by_test.get(str(ns.finding_ids["test_valid"]))
    mismatch = by_test.get(str(ns.finding_ids["test_mismatch"]))
    indeterminate = by_test.get(str(ns.finding_ids["test_indeterminate"]))
    assert valid and valid.descendants("img", "chart")
    assert mismatch and not mismatch.descendants("img", "chart") and re.search(r"unverifiable|could not verify", mismatch.text(), re.I)
    assert indeterminate and not indeterminate.descendants("img", "chart") and "indeterminate" in indeterminate.text().lower()


def test_r1_row_57_conflicting_stances_are_shown_plainly(r1_site):
    ns, out = r1_site
    fid = ns.finding_ids["sensitive_conflict"]
    page = _read(out, f"findings/{fid}.html")
    assert re.search(r"Marketing\s*:\s*push", page, re.I)
    assert re.search(r"League GM\s*:\s*steer away", page, re.I)


def test_r1_row_57b_override_clearance_is_recorded_on_the_story(r1_site):
    ns, out = r1_site
    fid = ns.finding_ids["sensitive_fifth"]
    page = _read(out, f"findings/{fid}.html")
    assert "Cleared by LK director over Marketing's steer away" in page


def test_r1_row_57c_missing_fan_data_promises_the_section_on_a_fresh_run(r1_site_no_fans):
    _ns, out = r1_site_no_fans
    pre = one(parse_html(_read(out, "index.html")), cls="mail", data_email_type="pre_game")
    assert not [node for node in pre.descendants() if node.attrs.get("data-section") == "fan-signal"]
    assert re.search(r"fan.{0,100}fresh run|fresh run.{0,100}fan", pre.text(), re.I | re.S)


def test_r1_row_58_every_site_page_uses_one_shared_token_stylesheet(r1_site):
    _ns, out = r1_site
    shared: set[Path] | None = None
    for page in _pages(out):
        root = parse_html(page.read_text(encoding="utf-8"))
        styles = {
            (page.parent / urlsplit(link.attrs["href"]).path).resolve()
            for link in root.descendants("link")
            if "stylesheet" in link.attrs.get("rel", "").split()
            and link.attrs.get("href") and not link.attrs["href"].startswith(("http://", "https://"))
        }
        assert styles and all(path.is_file() for path in styles), page.relative_to(out)
        shared = styles if shared is None else shared & styles
    assert shared, "all generated HTML pages must share the Agora token stylesheet"
