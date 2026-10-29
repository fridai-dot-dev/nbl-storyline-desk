"""R3 checks for the Daniel's Donuts PRD (decision rows 38, 39, 47, 48 and the DD copy rules)."""

from __future__ import annotations

import re

import pytest

from conftest import REPO
from test_r3_support import DD_DESCRIPTION, OFFER, PRD, REGIONS

SECTIONS = (
    "framing", "users and recipients", "data sources by tier", "specialists", "threads", "gates",
    "weekly email", "meeting mode", "sdk features", "roadmap", "what lk provides", "risks", "the offer",
)
DOC_URL = re.compile(r"https://(?:code|platform)\.claude\.com/docs/\S+")


@pytest.fixture(scope="module")
def prd() -> str:
    assert PRD.exists(), "docs/daniels-donuts/prd.md is missing"
    return PRD.read_text(encoding="utf-8")


def _headings(text: str, level: int = 2) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(rf"^{'#' * level} (.+)$", text, re.M)]


def _section(text: str, name: str) -> str:
    match = re.search(rf"^## [^\n]*{re.escape(name)}[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S | re.I)
    assert match, f"no '## …{name}…' section"
    return match.group(1)


def test_r3_row_38_no_store_count_and_no_nationwide(prd):
    assert not re.search(r"\bnationwide\b", prd, re.I)
    assert not re.search(r"\b\d+\s+stores\b", prd, re.I), re.search(r".{30}\b\d+\s+stores\b.{10}", prd, re.I | re.S)
    assert not re.search(r"\b(?:about|around|over|nearly)\s+\d+\s+(?:stores|locations|outlets|sites)\b", prd, re.I)


def test_r3_row_38_offer_line_is_verbatim(prd):
    assert OFFER in prd


def test_r3_row_38_stores_are_numbered_with_a_region(prd):
    mentions = list(re.finditer(r"\bStore (\d+)\b", prd))
    assert mentions, "the PRD names at least one numbered store"
    for match in mentions:
        rest = prd[match.end():]
        assert any(rest.startswith(f" · {region}") for region in REGIONS), prd[match.start():match.end() + 40]


def test_r3_copy_network_not_nationwide_and_no_real_places(prd):
    assert re.search(r"\bthe whole network\b", prd)
    assert "Albury" not in prd


def test_r3_copy_no_we_without_a_subject(prd):
    assert not re.findall(r"\bwe\b|\bwe'", prd, re.I)


def test_r3_row_39_framing_uses_the_approved_description(prd):
    assert DD_DESCRIPTION in _section(prd, "Framing")


def test_r3_row_39_every_section_present_in_design_order(prd):
    headings = [heading.lower() for heading in _headings(prd)]
    positions = []
    for name in SECTIONS:
        hits = [index for index, heading in enumerate(headings) if name in heading]
        assert hits, f"missing '## …{name}…' (have: {headings})"
        positions.append(hits[0])
    assert positions == sorted(positions), f"sections out of the §4K order: {headings}"


def test_r3_row_39_data_sources_by_tier_with_access_routes(prd):
    section = _section(prd, "Data sources by tier")
    tiers = [heading.lower() for heading in _headings(section, 3)]
    for tier in ("customer voice", "operations", "commercial", "context"):
        assert any(tier in heading for heading in tiers), tiers
    for source in ("Google Business Profile API", "Uber Eats", "DoorDash", "Menulog", "Instagram", "TikTok",
                   "Facebook", "complaints inbox", "QR survey", "POS", "roster", "stock-out", "waste",
                   "petrol-station kiosk", "food court", "manager change", "promotions calendar", "membership",
                   "campaign", "weather", "holidays", "Melbourne United", "competitor"):
        assert source.lower() in section.lower(), source
    assert re.search(r"every review", section, re.I), "owner access pulls every review, not just the public few"
    assert section.lower().count("access") >= 4, "each tier names its access route"


def test_r3_row_39_specialists_and_judge(prd):
    section = _section(prd, "Specialists").lower()
    for role in ("lead", "customer voice", "operations", "product", "marketing", "context", "judge"):
        assert role in section, role
    for phrase in ("coincides with", "consistent with", "tested"):
        assert f'"{phrase}"' in section or f"“{phrase}”" in section, phrase
    for window in ("last month", "last 3 months", "store", "region", "network"):
        assert window in section, window
    assert "next week" in section and "risk" in section, "marketing runs a risk check on next week's promos"


def test_r3_row_39_threads_gates_email_and_meeting_mode(prd):
    threads = _section(prd, "Threads").lower()
    for idea in ("spike", "training", "side effect", "data first", "allergen", "quiet"):
        assert idea in threads, idea
    gates = _section(prd, "Gates").lower()
    for idea in ("recheck", "minimum", "named staff", "performance", "stance", "comment"):
        assert idea in gates, idea
    email = _section(prd, "weekly email").lower()
    assert "monday" in email and "7 am" in email and "store manager" in email
    meeting = _section(prd, "Meeting mode").lower()
    assert "resume" in meeting and "ops meeting" in meeting


def test_r3_row_39_roadmap_phases(prd):
    roadmap = _section(prd, "Roadmap")
    phases = re.findall(r"^\d+\. ", roadmap, re.M)
    assert len(phases) == 4, roadmap
    lowered = roadmap.lower()
    assert "5-store pilot" in lowered and "human analyst" in lowered
    for idea in ("all stores", "ops meeting", "campaign", "training", "roster", "waste", "labour", "review replies",
                 "menu", "pricing", "new-site", "moved the numbers"):
        assert idea in lowered, idea


def test_r3_row_39_what_lk_provides_risks_and_offer(prd):
    assert _section(prd, "What LK provides").strip()
    risks = _section(prd, "Risks").lower()
    for risk in ("privacy", "staff", "caus"):
        assert risk in risks, risk
    assert OFFER in _section(prd, "The offer")


def _sdk_rows(prd: str) -> list[str]:
    section = _section(prd, "SDK features")
    rows = [line for line in section.splitlines() if line.startswith("|")]
    assert len(rows) >= 3, "the SDK features section is a table"
    return [row for row in rows[2:] if row.strip("| ")]   # skip the header and the |---| rule


def test_r3_row_48_every_sdk_feature_cites_a_doc_or_is_marked_unverified(prd):
    rows = _sdk_rows(prd)
    assert len(rows) >= 6, rows
    for row in rows:
        assert DOC_URL.search(row) or "unverified" in row.lower(), row


def test_r3_row_48_the_six_new_features_each_have_a_row(prd):
    rows = "\n".join(_sdk_rows(prd)).lower()
    for feature in ("structured output", "message batches", "sandbox", "can_use_tool", "fork_session", "skills"):
        assert feature in rows, feature


def test_r3_row_47_prd_explains_why_project_settings_not_user(prd):
    assert 'setting_sources=["project"]' in prd and "setting_sources=[]" in prd
    lowered = prd.lower()
    assert '"user"' in prd and "version-controlled" in lowered and "reviewed" in lowered


def test_r3_outline_is_a_pointer_to_the_prd():
    outline = (REPO / "docs" / "daniels-donuts-outline.md").read_text(encoding="utf-8")
    assert len([line for line in outline.splitlines() if line.strip()]) == 1
    assert "daniels-donuts/prd.md" in outline
