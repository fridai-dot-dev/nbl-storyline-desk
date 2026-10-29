"""R3 checks for the Daniel's Donuts sample weekly email (decision rows 40, 41, 54-DD, 58-DD and the DD copy rules).

Bart's call, 2026-10-30: the cards keep the §4B layout but not the NBL stance model or "story" wording.
Each insight card has one Comment link; drafting approval is a separate sign-off outside the email.
"""

from __future__ import annotations

import copy
import re
from urllib.parse import parse_qs, urlsplit

import pytest
from jsonschema import Draft202012Validator

from test_r3_support import (
    DD_SITE, NUMBER, SAMPLE_WEEK, WEEKLY, fixture, json_numbers, load_json, one, parse_html,
    unnumbered_store_mentions,
)

SECTION_ORDER = ["lead", "network", "threads", "sensitive", "store-managers", "meeting", "reply", "footer"]
CHART_FORMS = {"theme_mix": "donut", "rating_trend": "line", "store_scatter": "scatter"}
# The NBL desk's media framing (stories, editorial stances) means nothing to a donut chain's managers (lesson 12).
NBL_FRAMING = re.compile(r"\b(?:stances?|push it|steer away|use (?:it )?if it comes up|stor(?:y|ies))\b", re.I)


@pytest.fixture(scope="module")
def data() -> dict:
    return load_json(SAMPLE_WEEK)


@pytest.fixture(scope="module")
def page() -> str:
    assert WEEKLY.exists(), "site/daniels-donuts/weekly.html is missing: run `python -m reviewdesk render`"
    return WEEKLY.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def root(page):
    return parse_html(page)


@pytest.fixture(scope="module")
def mail(root):
    return one(root, "section", "mail", data_email_type="weekly")


def _registry(data) -> dict[int, str]:
    return {item["store"]: item["region"] for item in data["stores"]}


def _boxes(node) -> list:
    return [box for box in node.descendants("article", "item") if box.attrs.get("data-finding")]


# ---------- 41: the data validates and the page renders from it ----------

def _validator():
    from reviewdesk.schema import WEEK_SCHEMA

    Draft202012Validator.check_schema(WEEK_SCHEMA)
    return Draft202012Validator(WEEK_SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)


def test_r3_row_41_sample_week_validates_against_the_module_schema(data):
    errors = [f"{list(error.path)}: {error.message}" for error in _validator().iter_errors(data)]
    assert errors == []


@pytest.mark.parametrize("mutate,why", [
    (lambda d: d["findings"][5].pop("escalated"), "a food-safety story must record its escalation"),
    (lambda d: d["findings"][2].update(sensitivity=None), "a named-staff story is always sensitive"),
    (lambda d: d["findings"][1].update(causal="caused"), "only the judge's three causal labels"),
    (lambda d: d["findings"][1].update(causal=None), "an explanation needs a causal label"),
    (lambda d: d["findings"][0].update(headline="Freshness led the week"), "headlines are plain questions"),
    (lambda d: d["findings"][1].update(suggestion="Cut the evening bake."), "suggestions are framed as suggestions"),
    (lambda d: d["stores"][0].update(region="Melbourne CBD"), "regions come from the approved list"),
])
def test_r3_row_41_schema_holds_the_design_rules(data, mutate, why):
    broken = copy.deepcopy(data)
    mutate(broken)
    assert list(_validator().iter_errors(broken)), why


def test_r3_row_41_cross_references_resolve(data):
    registry = _registry(data)
    ids = [finding["id"] for finding in data["findings"]]
    assert len(ids) == len(set(ids))
    for finding in data["findings"]:
        assert set(finding["scope"]["stores"]) <= set(registry), finding["id"]
    for section in data["store_sections"]:
        assert section["store"] in registry and set(section["finding_ids"]) <= set(ids)
    assert data["charts"]["rating_trend"]["store"] in registry
    assert {point["store"] for point in data["charts"]["store_scatter"]["points"]} <= set(registry)
    assert sum(item["value"] for item in data["charts"]["theme_mix"]["slices"]) == 100


def test_r3_row_41_committed_page_and_charts_are_a_fresh_render(tmp_path, page):
    from reviewdesk.__main__ import main

    out = tmp_path / "daniels-donuts" / "weekly.html"
    assert main(["render", "--data", str(SAMPLE_WEEK), "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == page, "weekly.html was edited by hand or not re-rendered"
    fresh = sorted(path.name for path in (out.parent / "charts").glob("*.svg"))
    committed = sorted(path.name for path in (DD_SITE / "charts").glob("*.svg"))
    assert fresh == committed and fresh
    for name in fresh:
        assert (out.parent / "charts" / name).read_text(encoding="utf-8") == (DD_SITE / "charts" / name).read_text(encoding="utf-8"), name


def test_r3_row_41_every_number_on_the_page_comes_from_the_json(data, root):
    allowed = json_numbers(data)
    main_node = one(root, "main")
    text = main_node.text()
    stray = sorted(set(NUMBER.findall(text)) - allowed)
    assert stray == [], f"numbers on the page that aren't in sample-week.json: {stray}"
    title = one(root, "title").text()
    assert set(NUMBER.findall(title)) <= allowed


def test_r3_row_41_chart_labels_come_from_the_json(data):
    import xml.etree.ElementTree as ET

    allowed = json_numbers(data)
    for path in (DD_SITE / "charts").glob("*.svg"):
        svg = ET.fromstring(path.read_text(encoding="utf-8"))
        text = " ".join("".join(node.itertext()) for node in svg.iter() if node.tag.endswith(("text", "title")))
        assert set(NUMBER.findall(text)) <= allowed, path.name


# ---------- 40: banner, inbox format, story boxes, charts, sensitive stories ----------

def test_r3_row_40_illustrative_banner_comes_first(root):
    main_node = one(root, "main")
    first = main_node.elements()[0]
    assert first.attrs.get("data-region") == "banner"
    assert "Illustrative data" in first.text()


def test_r3_row_40_page_uses_the_inbox_format(data, root, mail):
    main_node = one(root, "main")
    regions = [node.attrs["data-region"] for node in main_node.descendants() if node.attrs.get("data-region")]
    assert regions[:3] == ["banner", "inbox-strip", "internal-note"], regions
    row = one(one(root, data_region="inbox-strip"), cls="row", data_run_type="weekly")
    assert data["subject"] in row.text() and "Review Desk" in row.text()
    note = one(root, data_region="internal-note").text().lower()
    assert "comment" in note and "insight" in note
    for label in ("coincides with", "consistent with", "tested"):
        assert label in note, "the judge's labels are explained before any insight uses them"
    head = one(mail, cls="head").text()
    assert f"Subject: {data['subject']}" in head and "From: Review Desk" in head
    assert f"To: {data['recipients']}" in head and data["sent"] in head
    assert mail.attrs.get("id") and row.descendants("a")[0].attrs["href"] == f"#{mail.attrs['id']}"


def test_r3_row_40_email_sections_in_order(mail):
    order = [node.attrs["data-section"] for node in mail.descendants() if node.attrs.get("data-section")]
    assert order == SECTION_ORDER


def test_r3_row_40_every_finding_is_one_insight_card_with_its_evidence_and_a_comment_link(data, root, mail):
    boxes = {box.attrs["data-finding"]: box for box in _boxes(mail)}
    assert sorted(boxes) == sorted(finding["id"] for finding in data["findings"])
    assert len(_boxes(mail)) == len(boxes), "each finding renders exactly once"
    for finding in data["findings"]:
        box = boxes[finding["id"]]
        assert one(box, "b", "h").text() == finding["headline"]
        assert one(box, "p", "premise").text() == finding["premise"]
        number = one(box, cls="number").text()
        assert finding["number"]["value"] in number and finding["number"]["label"] in number
        status = one(box, cls="test").text()
        assert finding["status"] in status
        if finding["causal"]:
            assert one(box, cls="causal").text() == finding["causal"]
        if finding["suggestion"]:
            assert one(box, cls="suggestion").text() == finding["suggestion"]
        links = one(box, cls="comment").descendants("a")
        assert [link.text() for link in links] == ["Comment"], "one Comment link per card; no stance links"
        parsed = urlsplit(links[0].attrs["href"])
        assert parsed.scheme == "mailto" and parsed.path == "review-desk@example.com"
        assert parse_qs(parsed.query)["subject"][0] == f"Comment on insight {finding['id']}: {finding['headline']}"
        assert [link.text() for link in box.descendants("a")] == ["Comment", "The evidence →"]
        evidence_link = one(box, cls="evidence-link").descendants("a")
        assert len(evidence_link) == 1 and evidence_link[0].attrs["href"] == f"#evidence-{finding['id']}"
        evidence = one(root, id=f"evidence-{finding['id']}")
        for item in finding["evidence"]:
            assert item["detail"] in evidence.text()


def test_r3_row_40_insight_cards_sit_in_their_sections(data, mail):
    def ids(section):
        return [box.attrs["data-finding"] for box in _boxes(one(mail, data_section=section))]

    by_thread = {finding["id"]: finding for finding in data["findings"]}
    assert one(one(mail, data_section="sensitive"), "h4").text() == "Sensitive insights"
    assert all(by_thread[fid]["thread"] == "network" for fid in ids("network"))
    assert {fid for fid in ids("sensitive")} == {f["id"] for f in data["findings"] if f["sensitivity"]}
    assert all(by_thread[fid]["sensitivity"] is None and by_thread[fid]["thread"] != "network" for fid in ids("threads"))
    assert ids("sensitive")[0] == next(f["id"] for f in data["findings"] if f["thread"] == "food_safety")


def test_r3_row_40_donut_line_and_scatter_render_as_chart_images(data, mail):
    import xml.etree.ElementTree as ET

    forms = []
    for finding in data["findings"]:
        box = one(mail, "article", data_finding=finding["id"])
        images = box.descendants("img", "chart")
        if not finding["chart"]:
            assert not images, finding["id"]
            continue
        assert len(images) == 1 and images[0].attrs.get("alt")
        target = (DD_SITE / urlsplit(images[0].attrs["src"]).path).resolve()
        assert target.parent == (DD_SITE / "charts").resolve() and target.exists(), images[0].attrs["src"]
        form = ET.fromstring(target.read_text(encoding="utf-8")).get("data-chart")
        assert form == CHART_FORMS[finding["chart"]]
        forms.append(form)
    assert {"donut", "line", "scatter"} <= set(forms)


def test_r3_row_40_at_least_two_sensitive_stories_with_orange_tags(data, mail):
    sensitive = [box for box in _boxes(mail) if "sensitive" in box.classes]
    kinds = set()
    for box in sensitive:
        tag = one(box, "span", "sensitive-tag").text()
        kinds |= {kind for kind in ("food safety", "named staff") if kind in tag}
    assert len(sensitive) >= 2 and kinds == {"food safety", "named staff"}
    for box in _boxes(mail):
        if "sensitive" not in box.classes:
            assert not box.descendants("span", "sensitive-tag")


def test_r3_row_40_food_safety_story_shows_its_escalation(data, mail):
    finding = next(f for f in data["findings"] if f["thread"] == "food_safety")
    box = one(mail, "article", data_finding=finding["id"])
    assert finding["escalated"] in one(box, cls="escalated").text()


def test_r3_row_40_each_store_manager_gets_a_section(data, mail):
    registry = _registry(data)
    section = one(mail, data_section="store-managers")
    blocks = section.descendants(cls="store-section")
    assert [int(block.attrs["data-store"]) for block in blocks] == [item["store"] for item in data["store_sections"]]
    for block, item in zip(blocks, data["store_sections"]):
        assert one(block, "h5").text() == f"Store {item['store']} · {registry[item['store']]}"
        assert item["note"] in block.text()
        assert [link.attrs["href"] for link in block.descendants("a")] == [f"#evidence-{fid}" for fid in item["finding_ids"]]


def test_r3_row_40_meeting_section_lists_the_questions(data, mail):
    section = one(mail, data_section="meeting")
    assert data["meeting"]["day"] in one(section, "h4").text() and data["meeting"]["note"] in section.text()
    assert [item.text() for item in section.descendants("li")] == data["meeting"]["questions"]


# ---------- 54-DD and 58-DD: email-safe body, shared stylesheet ----------

def test_r3_row_54_email_body_uses_img_charts_and_links_only(root, mail):
    for forbidden in ("svg", "button", "form", "script", "input", "iframe"):
        assert not mail.descendants(forbidden), f"<{forbidden}> inside the email"
    assert not root.descendants("script")
    for node in mail.descendants():
        assert not [name for name in node.attrs if name.startswith("on")], node.tag


def test_r3_row_58_links_the_shared_agora_stylesheet(root):
    sheets = [node.attrs.get("href") for node in root.descendants("link") if "stylesheet" in node.attrs.get("rel", "")]
    assert "../assets/agora.css" in sheets


def test_r3_email_body_stays_light(root):
    inline = " ".join(node.text() for node in root.descendants("style"))
    assert ".mail" not in inline and "prefers-color-scheme" not in inline


# ---------- copy rules (lessons 10-11, §2 anti-goals) ----------

def test_r3_copy_rules_on_the_page(data, root):
    text = one(root, "main").text()
    assert not re.search(r"\bnationwide\b", text, re.I)
    assert not re.search(r"\b\d+\s+stores\b", text, re.I)
    assert re.search(r"\bnetwork\b", text)
    assert not re.findall(r"\bwe\b|\bwe'", text, re.I)
    assert "Albury" not in text
    assert unnumbered_store_mentions(text, _registry(data)) == []
    framing = NBL_FRAMING.findall(text + " " + one(root, "title").text())
    assert framing == [], f"NBL desk framing on the Daniel's Donuts page: {framing}"


def test_r3_copy_rules_in_the_data(data):
    flat = str(data)
    assert NBL_FRAMING.findall(flat) == []
    assert unnumbered_store_mentions(flat, _registry(data)) == []
    assert not re.findall(r"\bwe\b|\bwe'", flat, re.I)
    assert not re.search(r"\bcaused\b|\bbecause of\b", flat, re.I)


def test_r3_staff_names_never_reach_the_page_or_the_data(page):
    names = fixture("roster.json")["staff_names"]
    data_text = SAMPLE_WEEK.read_text(encoding="utf-8")
    for name in names:
        assert not re.search(rf"\b{re.escape(name)}\b", page) and not re.search(rf"\b{re.escape(name)}\b", data_text), name


def test_r3_internal_links_resolve(root):
    for node in root.descendants():
        for attribute in ("href", "src"):
            value = node.attrs.get(attribute, "")
            if not value or value.startswith(("mailto:", "https://")) or value == "../assets/agora.css":
                continue
            if value.startswith("#"):
                assert root.descendants(id=value[1:]), value
            else:
                assert (DD_SITE / urlsplit(value).path).exists(), value
