"""R1 fix round: defects Claude found comparing the built inbox with docs/design/mockups/inbox.html (v4).

One check per numbered finding in the fix-round card (F1-F10), plus a few supporting checks for the behaviour a
finding implies. Fixtures only: nothing here reads published/ or calls a model.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

from conftest import OPENER
from test_r1_support import build_r1_site, one, parse_html, seed_r1_store

HONESTY_NOTE = (
    "This is a rapid build, about 1–1.5 days of full-time work, made to show Claude agent capability. "
    "The order of operations, timing, prompts and safety controls are informed guesses, not knowledge of "
    "LK's structure or priorities."
)
ISO = re.compile(r"\d{4}-\d\d-\d\dT")


# ---------- helpers ----------

@pytest.fixture(scope="module")
def r1_site(tmp_path_factory, stats_db):
    return build_r1_site(tmp_path_factory.mktemp("r1-fix-site"), stats_db)


def _build(ns, out: Path, game_id: str) -> Path:
    from storydesk.site import build_site

    build_site(ns.store, ns.stats_db, out, game_id=game_id)
    return out


def _variant(tmp_path, stats_db, mutate):
    """The R1 fixture store, changed by `mutate(ns)`, then built into a fresh site."""
    ns = seed_r1_store(tmp_path, stats_db)
    mutate(ns)
    return ns, _build(ns, tmp_path / "variant-site", ns.game_id)


def _sql(ns, statement: str, params=()):
    con = sqlite3.connect(ns.store.path)
    try:
        with con:
            con.execute(statement, params)
    finally:
        con.close()


def _read(out: Path, rel: str) -> str:
    return (out / rel).read_text(encoding="utf-8")


def _pages(out: Path) -> list[Path]:
    return sorted(out.rglob("*.html"))


def _mails(out: Path):
    for page in _pages(out):
        for mail in parse_html(page.read_text(encoding="utf-8")).descendants(cls="mail"):
            yield page, mail


def _mail(out: Path, kind: str):
    return one(parse_html(_read(out, "index.html")), cls="mail", data_email_type=kind)


def _boxes(root):
    return [node for node in root.descendants(cls="item") if node.attrs.get("data-finding")]


def _box(root, finding_id: int):
    return one(root, cls="item", data_finding=str(finding_id))


def _tested_box(root, pre_finding_id: int):
    """The what-moved box for a pre-game story (it may show the linked result's copy)."""
    return one(root, cls="item", data_test_finding=str(pre_finding_id))


def _subject(mail) -> str:
    return " ".join(one(mail, cls="subj").text().split())


def _header(mail) -> str:
    return " ".join(one(mail, cls="head").text().split())


def _strip_rows(out: Path) -> dict[str, object]:
    strip = one(parse_html(_read(out, "index.html")), cls="inbox", data_region="inbox-strip")
    return {row.attrs["data-run-type"]: row for row in strip.descendants(cls="row")}


def _visible_text(root) -> str:
    parts = []

    def walk(node):
        for child in node.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in {"style", "script"}:
                walk(child)

    walk(root)
    return " ".join(" ".join(parts).split())


# A tiny CSS reader: enough to compare a rule's selector list with its declarations, including inside @media.
def _blocks(css: str) -> list[tuple[str, str]]:
    blocks, depth, start, head, body_start = [], 0, 0, "", 0
    for index, char in enumerate(css):
        if char == "{":
            if depth == 0:
                head, body_start = css[start:index].strip(), index + 1
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                blocks.append((head, css[body_start:index]))
                start = index + 1
    return blocks


def _declarations(body: str) -> dict[str, str]:
    result = {}
    for item in body.split(";"):
        if ":" in item:
            name, value = item.split(":", 1)
            result[name.strip().lower()] = value.strip().lower()
    return result


def _css(out: Path) -> str:
    return _read(out, "assets/agora.css")


# ---------- F1: fonts load ----------

def _font_families(href: str) -> dict[str, set[int]]:
    query = parse_qs(urlsplit(href).query)
    families = {}
    for family in query.get("family", []):
        name, _, axes = family.partition(":")
        spec = axes.split("@", 1)[1] if "@" in axes else ""
        weights = {int(item.split(",")[-1]) for item in spec.split(";") if item.split(",")[-1].isdigit()}
        families[name] = weights
    return families


def test_f1_every_page_head_links_google_fonts_inter_and_source_serif(r1_site):
    _ns, out = r1_site
    pages = _pages(out)
    assert len(pages) > 5
    for page in pages:
        head = one(parse_html(page.read_text(encoding="utf-8")), tag="head")
        fonts = [
            link.attrs["href"] for link in head.descendants("link")
            if "stylesheet" in link.attrs.get("rel", "").split() and urlsplit(link.attrs.get("href", "")).netloc == "fonts.googleapis.com"
        ]
        assert len(fonts) == 1, f"{page.relative_to(out)}: expected one Google Fonts stylesheet in <head>, found {fonts}"
        families = _font_families(fonts[0])
        assert families.get("Inter") == {400, 500, 600}, (page.name, families)
        assert families.get("Source Serif 4") == {400, 600}, (page.name, families)
        assert parse_qs(urlsplit(fonts[0]).query).get("display") == ["swap"], page.name


# ---------- F2: the always-light email and strip keep light tokens in dark mode ----------

def test_f2_dark_mode_keeps_the_strip_and_every_mail_on_light_tokens(r1_site):
    _ns, out = r1_site
    blocks = _blocks(_css(out))
    light = next(_declarations(body) for head, body in blocks if head == ":root")
    dark_inner = [
        inner for head, body in blocks if re.sub(r"\s+", "", head) == "@media(prefers-color-scheme:dark)"
        for inner in _blocks(body)
    ]
    dark_root = next(_declarations(body) for head, body in dark_inner if head == ":root")
    scoped = [([sel.strip() for sel in head.split(",")], _declarations(body)) for head, body in dark_inner if head != ":root"]

    # The page tokens stay dark, and nothing else in the dark block may touch the page.
    assert dark_root["--text"] == "#fff" and dark_root["--bg"] == "#262626" and dark_root["--card"] == "#303030"
    assert scoped, "the dark block needs light overrides for the strip and the emails"
    for selectors, _decls in scoped:
        assert all(re.match(r"^\.(inbox|mail)\b", selector) for selector in selectors), selectors

    def effective(scope: str, token: str) -> str:
        value = dark_root.get(token, light.get(token))
        for selectors, decls in scoped:
            if scope in selectors and token in decls:
                value = decls[token]
        return value

    expected = {
        "--text": "#1a1a1a", "--chart-ink": "#1f3a5f",
        "--sensitive-text": "#9a4a00", "--sensitive-bg": "#fdf0e1", "--sensitive-border": "#e3a96f",
    }
    for scope in (".inbox", ".mail"):
        for token, value in expected.items():
            assert effective(scope, token) == value, (scope, token, effective(scope, token))
        for token in ("--muted", "--bg", "--border", "--card", "--surface"):
            assert effective(scope, token) == light[token], (scope, token)


# ---------- F3: local times and relative phrases instead of ISO strings ----------

def test_f3_headers_and_strip_show_melbourne_time_and_a_relative_phrase(r1_site):
    _ns, out = r1_site
    for page, mail in _mails(out):
        assert not ISO.search(_header(mail)), (page.name, _header(mail))
    for kind, row in _strip_rows(out).items():
        assert not ISO.search(row.text()), (kind, row.text())
    # cutoff + run duration, in Melbourne time (UTC+10 on 19 September)
    assert "Sat 4:32 pm · 3 hours before tip-off" in _header(_mail(out, "pre_game"))
    assert "Sat 9:29 pm · 3 min after the final whistle" in _header(_mail(out, "post_game"))
    supplemental = one(parse_html(_read(out, "emails/supplemental.html")), cls="mail")
    assert "Sat 10:20 pm · after the press conferences" in _header(supplemental)
    assert "Sat 9:27 pm" in _header(one(parse_html(_read(out, "emails/follow-up.html")), cls="mail"))
    times = {kind: " ".join(row.descendants(cls="t")[0].text().split()) for kind, row in _strip_rows(out).items()}
    assert times == {"pre_game": "4:32 pm", "post_game": "9:29 pm", "supplemental": "10:20 pm", "follow_up": "9:27 pm"}


def test_f3_a_different_cutoff_renders_a_different_strip_time_and_phrase(tmp_path, stats_db):
    def move_pre_cutoff(ns):
        _sql(ns, "UPDATE runs SET as_of = ? WHERE id = ?", ("2026-09-19T07:00:00+00:00", ns.run_ids["pre"]))

    ns, out = _variant(tmp_path, stats_db, move_pre_cutoff)
    assert _strip_rows(out)["pre_game"].descendants(cls="t")[0].text().strip() == "5:02 pm"
    assert "Sat 5:02 pm · 2 hours before tip-off" in _header(_mail(out, "pre_game"))
    assert not ISO.search(_read(out, "index.html").split('class="cols"')[0])


# ---------- F4: subjects and strip previews are built from the data ----------

def test_f4_subjects_are_built_from_the_stored_tests_and_stories(r1_site):
    ns, out = r1_site
    assert _subject(_mail(out, "pre_game")) == "Subject: Tonight: Melbourne United v Adelaide 36ers, 3 storylines to test"
    assert _subject(_mail(out, "post_game")) == (
        "Subject: Melbourne United 95–97 Adelaide 36ers: 1 of 2 pre-game storylines contradicted")
    supplemental = one(parse_html(_read(out, "emails/supplemental.html")), cls="mail")
    assert _subject(supplemental) == "Subject: After the press conferences: What did Trevor Gleeson say about Adelaide's bench?"
    follow = one(parse_html(_read(out, "emails/follow-up.html")), cls="mail")
    assert _subject(follow) == "Subject: Re: your follow-up: How often had Adelaide overcome a 30-point bench deficit?"


def test_f4_strip_rows_show_the_subject_and_a_muted_preview_of_the_first_story(r1_site):
    ns, out = r1_site
    root = parse_html(_read(out, "index.html"))
    rows = _strip_rows(out)
    pre_first = ns.payload["findings"][0]["plain_headline"]
    expectations = {
        "pre_game": (_subject(_mail(out, "pre_game")), pre_first),
        "post_game": (_subject(_mail(out, "post_game")), one(_boxes(_mail(out, "post_game"))[0], cls="h").text()),
    }
    for kind, filename in (("supplemental", "supplemental.html"), ("follow_up", "follow-up.html")):
        mail = one(parse_html(_read(out, f"emails/{filename}")), cls="mail")
        expectations[kind] = (_subject(mail), one(_boxes(mail)[0], cls="h").text())
    for kind, (subject, preview) in expectations.items():
        row = rows[kind]
        link = row.descendants("a")[0]
        assert link.text() == subject.removeprefix("Subject: "), kind
        if preview in link.text():   # the supplemental subject already quotes its first headline: shown once, not repeated
            assert row.text().count(preview) == 1, kind
        else:
            assert preview in row.text(), kind
            assert preview in one(row, cls="preview").text(), kind
    muted = [decl.get("color") for head, body in _blocks(_css(out)) if ".preview" in head for decl in [_declarations(body)]]
    assert muted and all(color in {"#5c5c5c", "var(--muted)"} for color in muted), muted   # the preview is quieter than the subject
    assert root  # the page parsed


def test_f4_without_structured_tests_the_post_game_subject_says_what_moved(demo_store, tmp_path):
    out = _build(demo_store, tmp_path / "site", OPENER)
    assert _subject(_mail(out, "post_game")) == "Subject: Melbourne United 95–97 Adelaide 36ers: what moved"
    assert _subject(_mail(out, "pre_game")) == "Subject: Tonight: Melbourne United v Adelaide 36ers, 1 storyline to test"


def test_f4_follow_up_subject_cuts_a_long_question_to_sixty_characters(demo_store, tmp_path):
    question = "Was this Adelaide's best quarter of the game, and how does it compare with every other quarter they played this season?"
    _sql(demo_store, "UPDATE requests SET question = ? WHERE id = ?", (question, demo_store.request))
    out = _build(demo_store, tmp_path / "site", OPENER)
    subject = _subject(one(parse_html(_read(out, "emails/follow-up.html")), cls="mail"))
    prefix = "Subject: Re: your follow-up: "
    assert subject.startswith(prefix)
    cut = subject.removeprefix(prefix)
    assert 20 < len(cut) <= 60 and question.startswith(cut.rstrip("…").rstrip())


# ---------- F5: leads are plain summaries, never raw finding bodies ----------

JARGON = re.compile(r"Finding \d+|CONFIRM:|CONTRADICT:")


def _add_jargon_to_every_claim(ns):
    for key, finding_id in ns.finding_ids.items():
        claim = ns.store.get_finding(finding_id)["claim"]
        ns.store.update_finding(
            finding_id, claim=f"{claim} That is above Finding 10's 25+ threshold. CONFIRM: it holds. CONTRADICT: it fails.")


def test_f5_leads_use_the_run_summary_and_never_a_raw_finding_body(tmp_path, stats_db):
    ns, out = _variant(tmp_path, stats_db, _add_jargon_to_every_claim)
    for page, mail in _mails(out):
        assert not JARGON.search(_visible_text(mail)), (page.name, JARGON.search(_visible_text(mail)))
    assert one(_mail(out, "post_game"), cls="lead").text() == "Adelaide won 97-95 after a decisive difference from three."
    assert one(_mail(out, "pre_game"), cls="lead").text() == "Melbourne host Adelaide with three storylines to test."


def test_f5_pre_game_lead_falls_back_to_the_top_storys_premise(tmp_path, stats_db):
    def drop_pre_summary(ns):
        _add_jargon_to_every_claim(ns)
        ns.store.set_exec_summary(ns.run_ids["pre"], None)

    ns, out = _variant(tmp_path, stats_db, drop_pre_summary)
    premise = ns.store.get_finding(ns.finding_ids["test_valid"])["premise"]
    assert one(_mail(out, "pre_game"), cls="lead").text() == premise
    for page, mail in _mails(out):
        assert not JARGON.search(_visible_text(mail)), page.name


# ---------- F6: no placeholder status lines ----------

def test_f6_status_not_yet_recorded_never_appears(r1_site, demo_store, tmp_path):
    _ns, out = r1_site
    demo_out = _build(demo_store, tmp_path / "site", OPENER)
    for site in (out, demo_out):
        for page in _pages(site):
            assert "not yet recorded" not in page.read_text(encoding="utf-8").lower(), page.name


def test_f6_true_if_false_if_appears_only_for_structured_tests(r1_site):
    ns, out = r1_site
    pre = _mail(out, "pre_game")
    valid = _box(pre, ns.finding_ids["test_valid"]).text()
    mismatch = _box(pre, ns.finding_ids["test_mismatch"]).text()
    indeterminate = _box(pre, ns.finding_ids["test_indeterminate"]).text()
    assert re.search(r"True if\s+21 or lower\s+·\s+false if\s+above 21", valid)
    assert re.search(r"True if\s+above 25\s+·\s+false if\s+25 or lower", mismatch)
    assert not re.search(r"true if|false if", indeterminate, re.I)
    for page, mail in _mails(out):
        if mail.attrs.get("data-email-type") == "pre_game":
            continue
        assert not re.search(r"true if", _visible_text(mail), re.I), page.name


def test_f6_a_text_threshold_is_a_structured_test_too(tmp_path, stats_db):
    def text_threshold(ns):
        ns.store.update_finding(
            ns.finding_ids["test_valid"], threshold="21 or fewer confirms; 25 or more contradicts", test_direction=None)

    ns, out = _variant(tmp_path, stats_db, text_threshold)
    text = _box(_mail(out, "pre_game"), ns.finding_ids["test_valid"]).text()
    assert re.search(r"True if\s+21 or fewer\s+·\s+false if\s+25 or more", text)


def test_f6_sensitive_stories_without_a_stance_say_so_and_only_they_do(r1_site):
    ns, out = r1_site
    post = _mail(out, "post_game")
    assert "No stance yet." in _box(post, ns.finding_ids["sensitive_none"]).text()
    for key in ("sensitive_use", "sensitive_override_block", "top_pick"):
        assert "No stance yet." not in _box(post, ns.finding_ids[key]).text(), key
    supplemental = one(parse_html(_read(out, "emails/supplemental.html")), cls="mail")
    assert "No stance yet." not in supplemental.text()


def test_f6_could_not_verify_appears_only_in_what_moved_and_only_for_a_test(r1_site, tmp_path, stats_db):
    ns, out = r1_site
    carriers = []
    for page, mail in _mails(out):
        for box in _boxes(mail):
            if "Could not verify this test against the linked result" in box.text():
                carriers.append((mail.attrs["data-email-type"], box.attrs.get("data-test-finding")))
    assert carriers == [("post_game", str(ns.finding_ids["test_mismatch"]))]
    moved = one(_mail(out, "post_game"), data_section="what-moved")
    assert "Could not verify" in _tested_box(moved, ns.finding_ids["test_mismatch"]).text()

    def strip_the_test(ns2):
        ns2.store.update_finding(ns2.finding_ids["test_valid"], threshold=None, actual=None, outcome=None, test_direction=None, metric=None)

    ns2, out2 = _variant(tmp_path, stats_db, strip_the_test)
    moved2 = one(_mail(out2, "post_game"), data_section="what-moved")
    box = _tested_box(moved2, ns2.finding_ids["test_valid"])
    assert "Could not verify" not in box.text() and not re.search(r"true if", box.text(), re.I)
    assert box.descendants(cls="test") or box.descendants(cls="status")   # the story still carries a status element


def test_f6_a_result_that_carries_the_numbers_verifies_a_pre_game_text_test(tmp_path, stats_db):
    """Real ledgers keep the numeric test on the post-game result; the pre-game story only has the text."""
    def numbers_on_the_result(ns):
        ns.store.update_finding(ns.finding_ids["test_valid"], threshold="21 or fewer confirms; 25 or more contradicts",
                                test_direction=None, actual=None, outcome=None)
        ns.store.update_finding(ns.finding_ids["result_valid"], threshold=25, test_direction="above", actual=26,
                                outcome="contradicts", metric="Bryce Cotton points")

    ns, out = _variant(tmp_path, stats_db, numbers_on_the_result)
    moved = one(_mail(out, "post_game"), data_section="what-moved")
    box = _tested_box(moved, ns.finding_ids["test_valid"])
    assert box.descendants("img", "chart") and "Could not verify" not in box.text() and "contradicts" in box.text()
    assert re.search(r"1 of 2 pre-game storylines contradicted", _subject(_mail(out, "post_game")))


# ---------- F7: human category labels ----------

def test_f7_fan_quote_category_reads_fan_quotes(r1_site, demo_store, tmp_path):
    ns, out = r1_site
    demo_out = _build(demo_store, tmp_path / "site", OPENER)
    for site in (out, demo_out):
        for page in _pages(site):
            text = _visible_text(parse_html(page.read_text(encoding="utf-8")))
            assert "fan_quote" not in text.lower(), page.name
    tag = one(_box(_mail(out, "post_game"), ns.finding_ids["sensitive_none"]), cls="sensitive-tag").text()
    assert tag.lower() == "sensitive · fan quotes"
    assert "sensitive · fan quotes" in _visible_text(parse_html(_read(out, f"findings/{ns.finding_ids['sensitive_none']}.html"))).lower()
    kept = one(_box(_mail(out, "post_game"), ns.finding_ids["sensitive_override_block"]), cls="sensitive-tag").text()
    assert kept.lower() == "sensitive · officiating"


# ---------- F8: the top pick explains itself from the judge's scores ----------

def test_f8_top_pick_reason_comes_from_scores_and_audiences(r1_site):
    ns, out = r1_site
    section = one(_mail(out, "post_game"), data_section="top-pick")
    text = section.text()
    assert "Ranked first as a suggestion for the internal teams" not in text
    assert re.search(r"Ranked first because it's the newest against the coverage so far and suits the most teams:\s+leadership, producers and social\.", text)
    assert "It's a suggestion, not the only story. 8 more stories are on the board." in text
    assert len(re.findall(r"more stories are on the board", text)) == 1


def test_f8_reason_changes_with_the_stored_scores_and_audiences(tmp_path, stats_db):
    def change(ns):
        ns.store.update_finding(ns.finding_ids["top_pick"], audience=["broadcast"])
        ns.store.update_finding(ns.finding_ids["result_valid"], novelty=0.99, audience_fit=0.1, direction=0.1)

    ns, out = _variant(tmp_path, stats_db, change)
    text = one(_mail(out, "post_game"), data_section="top-pick").text()
    assert "newest" not in text
    reason = re.search(r"Ranked first because[^.]*\.", text)
    assert reason and reason.group(0) == "Ranked first because it suits broadcast.", text


# ---------- F9: the finding page stance controls are the same mailto links ----------

def test_f9_finding_page_stance_actions_are_prefilled_mailto_links(r1_site):
    ns, out = r1_site
    for key in ("top_pick", "sensitive_none", "test_valid"):
        finding_id = ns.finding_ids[key]
        page = parse_html(_read(out, f"findings/{finding_id}.html"))
        header = one(page, cls="detail-header")
        assert not header.descendants("button")
        headline = ns.store.get_finding(finding_id)["plain_headline"]
        links = [a for a in header.descendants("a") if a.attrs.get("href", "").startswith("mailto:")]
        assert [a.text() for a in links] == ["Push it", "Use if it comes up", "Steer away", "Comment"], key
        for link in links:
            parsed = urlsplit(link.attrs["href"])
            assert parsed.path == "storyline-desk@example.com"
            subject = " ".join(parse_qs(parsed.query).get("subject", []))
            assert str(finding_id) in subject and headline in unquote(subject), (key, subject)


# ---------- F10: the honesty note stands apart under the stance note ----------

def test_f10_honesty_note_is_its_own_bordered_paragraph_under_the_stance_note(r1_site):
    _ns, out = r1_site
    root = parse_html(_read(out, "index.html"))
    note = one(root, cls="internal-note")
    assert "rapid build" not in note.text() and "set a stance" in note.text()
    paragraphs = [node for node in root.descendants("p") if node.text() == HONESTY_NOTE]
    assert len(paragraphs) == 1, "the honesty note must be exactly one paragraph of its own"
    honesty = paragraphs[0]
    order = [node for node in root.descendants() if node is note or node is honesty]
    assert order == [note, honesty], "the honesty note sits under the stance note"
    wanted = set(honesty.classes) - {"muted"}
    rules = [
        _declarations(body) for head, body in _blocks(_css(out))
        if any(sel.strip().lstrip(".") in wanted for sel in head.split(","))
    ]
    borders = [decl["border-left"] for decl in rules if "border-left" in decl]
    assert wanted and borders, "the honesty note needs its own class with a left border"
    assert any(re.match(r"^[2-9]px\s+solid\s+\S+", value) and "transparent" not in value for value in borders), borders
