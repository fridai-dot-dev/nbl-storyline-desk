"""The site follows the approved mockups in docs/design/mockups: a three-column producer board, an email-shaped
leadership briefing and a two-column finding page, with a labelled simulated feedback round (2026-10-29).

The published site had drifted into single-column lists, and the simulated round the design planned was never run."""
import html
import json
import re
import sqlite3

import pytest

from conftest import OPENER, REPO


def _build(ns, tmp_path):
    from storydesk.site import build_site

    out = tmp_path / "site"
    build_site(ns.store, ns.stats_db, out, game_id=OPENER)
    return out


def _read(out, rel):
    return (out / rel).read_text(encoding="utf-8")


def _pos(html, cls):
    """Start of the first element whose class list begins with `cls`, or -1."""
    match = re.search(rf'class="{re.escape(cls)}(?=[ "])', html)
    return match.start() if match else -1


_ANGLE = re.compile(r'<article\b([^>]*\bclass="angle(?=[ "])[^>]*)>(.*?)</article>', re.S)


def _angle_cards(index):
    cards = {}
    for match in _ANGLE.finditer(index):
        attrs, body = match.groups()
        fid = int(re.search(r'data-finding="(\d+)"', attrs).group(1))
        audience = re.search(r'data-audience="([^"]*)"', attrs).group(1).split()
        cards[fid] = {"audience": audience, "body": body, "pos": match.start()}
    return cards


def _columns(index):
    left, angles, right = (_pos(index, name) for name in ("board-left", "board-angles", "board-right"))
    return tuple(html.unescape(part) for part in (index[left:angles], index[angles:right], index[right:]))


# ---------- the producer board (producer-board-v2.html) ----------

def test_board_has_the_mockups_three_columns(demo_store, tmp_path):
    index = _read(_build(demo_store, tmp_path), "index.html")
    board = _pos(index, "board")
    left, angles, right = (_pos(index, name) for name in ("board-left", "board-angles", "board-right"))
    assert -1 < board < left < angles < right, "the board, then its left, angles and right columns, in that order"
    assert "From leadership" in index[left:angles] and "Active directives" in index[left:angles]
    assert "Angles for" in index[angles:right]
    assert "Ask the next run" in index[right:]


def test_role_switch_offers_every_audience_on_the_board(demo_store, tmp_path):
    index = _read(_build(demo_store, tmp_path), "index.html")
    select = re.search(r'<select[^>]*\bid="role-switch"[^>]*>(.*?)</select>', index, re.S)
    assert select, "the mockup's 'Viewing as' switch"
    options = re.findall(r'<option[^>]*\bvalue="([^"]*)"', select.group(1))
    cards = _angle_cards(index)
    assert cards
    on_board = set().union(*(card["audience"] for card in cards.values()))
    assert options[0] == "all" and set(options[1:]) == on_board and len(options) == len(set(options))
    for fid, card in cards.items():
        assert card["audience"] == demo_store.store.get_finding(fid)["audience"], fid
    assert "<script" in index and "?role=" not in index        # filtered in the page, never by query links


def test_angle_cards_carry_their_chart_usage_and_the_four_buttons(demo_store, tmp_path):
    demo_store.store.add_feedback(demo_store.f_attr, role="Social lead", action="using it", simulated=True)
    cards = _angle_cards(_read(_build(demo_store, tmp_path), "index.html"))
    assert {demo_store.f_checked, demo_store.f_attr} <= set(cards)
    assert "<svg" in cards[demo_store.f_checked]["body"]               # the chart sits in the card
    assert "Social lead: using it" in cards[demo_store.f_attr]["body"]
    assert "no one using yet" in cards[demo_store.f_checked]["body"]
    for fid, card in cards.items():
        for label in ("Using it", "Already had it", "Not for us", "Ask a follow-up"):
            assert label in card["body"], (fid, label)
        assert f'href="findings/{fid}.html"' in card["body"]


def test_unsigned_held_items_sit_in_a_strip_after_the_angles(demo_store, tmp_path):
    index = _read(_build(demo_store, tmp_path), "index.html")
    cards = _angle_cards(index)
    assert demo_store.f_held not in cards                              # held with no sign-off is not an angle
    assert demo_store.f_fan in cards                                   # signed off for producers, so usable
    assert "Signed off for producers" in cards[demo_store.f_fan]["body"]
    strip_at, right = _pos(index, "held-strip"), _pos(index, "board-right")
    assert max(card["pos"] for card in cards.values()) < strip_at < right
    strip = index[strip_at:right]
    assert f'href="findings/{demo_store.f_held}.html"' in strip and "officiating" in strip
    assert "<svg" not in strip and "Using it" not in strip           # a compact strip, not full cards


def test_angles_are_ranked_and_open_after_the_game(demo_store, tmp_path):
    store = demo_store.store
    store.update_finding(demo_store.f_attr, novelty=0.9, audience_fit=0.9, direction=0.9)
    store.update_finding(demo_store.f_checked, novelty=0.1, audience_fit=0.1, direction=0.1)
    cards = _angle_cards(_read(_build(demo_store, tmp_path), "index.html"))
    assert cards[demo_store.f_attr]["pos"] < cards[demo_store.f_checked]["pos"]
    assert demo_store.pre_finding not in cards                         # pre-game items live in the pre-game briefing


def test_leadership_column_shows_reactions_and_signoffs(demo_store, tmp_path):
    left, _, _ = _columns(_read(_build(demo_store, tmp_path), "index.html"))
    assert "Lead with this" in left and "CEO" in left                  # the fixture's simulated reaction
    assert "simulated" in left.lower()
    assert "Head of social" in left                                    # a real sign-off is a decision too
    assert "No directives yet" in left


def test_active_directives_show_owner_expiry_and_the_simulated_label(demo_store, tmp_path):
    store = demo_store.store
    store.add_directive("Head of marketing", "Build the Cole Anthony arrival story", expires="2026-10-05", simulated=True)
    store.add_directive("League GM", "Keep officiating talk internal", mandatory=True, simulated=True)
    left, _, _ = _columns(_read(_build(demo_store, tmp_path), "index.html"))
    directives = left[left.index("Active directives"):]
    for text in ("Build the Cole Anthony arrival story", "Head of marketing", "2026-10-05",
                 "Keep officiating talk internal", "mandatory"):
        assert text in directives, text
    assert "simulated" in directives.lower()
    assert "No directives yet" not in left


def test_right_column_asks_the_next_run_and_tracks_requests(demo_store, tmp_path):
    _, _, right = _columns(_read(_build(demo_store, tmp_path), "index.html"))
    assert "<textarea" in right
    assert "Was this Adelaide's best quarter of the game?" in right
    assert f'href="findings/{demo_store.f_child}.html"' in right       # the answer is one click away


# ---------- the leadership email (leadership-view.html, option A) ----------

def _email(ns, tmp_path):
    return _read(_build(ns, tmp_path), "outbox/post-game-email.html")


def test_email_has_an_email_header_and_a_reply_to_direct_footer(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    head = re.sub(r"<[^>]+>", "|", email[:email.index("What happened")])
    assert re.search(r"From:\|*\s*NBL Storyline Desk", head)
    assert re.search(r"To:\|*\s*\w", head)
    subject = re.search(r"Subject:\|*([^|]*)", head).group(1)
    assert "95" in subject and "97" in subject, subject
    direction = email[email.index("Give direction"):]
    assert re.search(r"reply", direction, re.I)
    assert re.search(r'href="\.\./index\.html"[^>]*>[^<]*board', email, re.I)


def test_what_moved_pairs_the_pre_game_line_with_the_result(demo_store, tmp_path):
    store = demo_store.store
    moved = store.add_finding(
        run_id=demo_store.post_run, parent_id=demo_store.pre_finding, agent="media", source_type="media",
        kind="qualitative", claim="Adelaide's bench decided the matchup previews had framed", audience=["producers"],
        headline="Adelaide's bench decided the previewed matchup",
    )
    store.add_evidence(moved, [{"source_type": "media", "url": "https://example.test/news/recap", "ref": "2026-09-19"}])
    store.update_finding(moved, status="shipped")
    email = _email(demo_store, tmp_path)
    section = email.split("What moved since pre-game", 1)[1].split("<h2", 1)[0]
    assert "<table" in section
    row = next(r for r in re.findall(r"<tr\b.*?</tr>", section, re.S) if f"findings/{moved}.html" in r)
    pre = store.get_finding(demo_store.pre_finding)
    from storydesk.site import headline_for
    assert headline_for(pre) in html.unescape(row)                                    # what pre-game said, beside what happened
    assert f"findings/{demo_store.pre_finding}.html" not in section    # each finding is linked once in the email


def test_held_items_in_the_email_are_compact_rows_with_decisions(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    held = email.split("Held for sign-off", 1)[1].split("<h2", 1)[0]
    assert '<article class="card' not in held
    rows = re.findall(r'<div class="held-row\b.*?</div>', held, re.S)
    links = re.findall(r'href="\.\./findings/(\d+)\.html"', held)
    assert rows and len(rows) == len(links)
    assert "Approve for" in held and "Keep internal" in held


def test_email_angles_name_their_audience(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    angles = email.split("Angles for the next 48 hours", 1)[1].split("<h2", 1)[0]
    assert "For: leadership, producers" in angles                      # f_checked's audience, as on the mockup


# ---------- the finding page (finding-detail.html) ----------

def _finding_html(ns, tmp_path, fid):
    return _read(_build(ns, tmp_path), f"findings/{fid}.html")


def test_finding_page_has_a_main_column_and_a_sidebar(demo_store, tmp_path):
    page = _finding_html(demo_store, tmp_path, demo_store.f_checked)
    main, side = _pos(page, "detail-main"), _pos(page, "detail-side")
    assert -1 < main < side
    header = page[:main]
    assert "<h1>" in header
    for label in ("Using it", "Already had it", "Not for us", "Comment"):
        assert label in header, label
    assert re.search(r"<button[^>]*disabled[^>]*>\s*Make a graphic", header)
    body = page[main:side]
    assert "<svg" in body and "How we know" in body and "How the agents got here" in body
    sidebar = page[side:]
    assert sidebar.index("What people said") < sidebar.index("Follow the lead") < sidebar.index("Original sources")


def test_quotes_sit_under_what_people_said(demo_store, tmp_path):
    out = _build(demo_store, tmp_path)
    page = _read(out, f"findings/{demo_store.f_attr}.html")
    sidebar = page[_pos(page, "detail-side"):]
    said = html.unescape(sidebar[sidebar.index("What people said"):sidebar.index("Follow the lead")])
    assert "Adelaide have won the third quarter on the back of their bench." in said
    for other in out.rglob("*.html"):
        assert "Evidence recorded without a quote" not in other.read_text(encoding="utf-8"), other.name


def test_original_sources_list_each_source_once(demo_store, tmp_path):
    page = _finding_html(demo_store, tmp_path, demo_store.f_checked)
    sources = page[page.index("Original sources"):]
    assert sources.count('href="https://github.com/JaseZiv/nblr_data/releases/tag/box_team"') == 1


def test_trail_falls_back_to_the_sources_the_agents_checked(demo_store, tmp_path):
    page = _finding_html(demo_store, tmp_path, demo_store.f_held)  # no parent, no children
    main = page[_pos(page, "detail-main"):_pos(page, "detail-side")]
    trail = main[main.index("How the agents got here"):]
    assert "No linked finding yet" not in page
    assert "2026-09-19T11:00:00+00:00" in trail and re.search(r"fans", trail, re.I)


def test_follow_the_lead_keeps_the_local_command_collapsed(demo_store, tmp_path):
    demo_store.store.set_followups(demo_store.f_checked, [
        {"type": "rarity", "question": "How often does Adelaide score 26 in a quarter?", "why": "Shows how rare it is."},
    ])
    page = _finding_html(demo_store, tmp_path, demo_store.f_checked)
    sidebar = page[_pos(page, "detail-side"):]
    lead = sidebar[sidebar.index("Follow the lead"):sidebar.index("Original sources")]
    assert "How often does Adelaide score 26 in a quarter?" in lead
    commands = [m.start() for m in re.finditer(r"storydesk run follow_up", page)]
    assert commands
    for at in commands:                                                # shown only when someone opens it
        assert page.rfind("<details", 0, at) > page.rfind("</details>", 0, at), "command outside <details>"


# ---------- charts: rotated labels hang from the axis and stay on the canvas ----------

LONG_LABELS = ["Anthony 30 pts (21:50)", "Lual-Acuil Jr 33 pts (23:02)", "Jackson-Cartwright 33 pts (23:23)",
               "Cotton 31 pts (23:46)", "Ili 30 pts (24:06)", "Bruton 30 pts (24:25)"]


@pytest.mark.parametrize("kind", ["bar", "line"])
def test_rotated_labels_hang_from_the_axis_and_stay_on_the_canvas(kind):
    import xml.etree.ElementTree as ET

    from storydesk.charts import render_bar_chart, render_line_chart

    render = render_bar_chart if kind == "bar" else render_line_chart
    svg = render("Seconds played", LONG_LABELS, [1310, 1382, 1403, 1426, 1446, 1465], 0, "Seconds played")
    root = ET.fromstring(svg)
    width, height = float(root.get("width")), float(root.get("height"))
    baseline = float(root.get("data-baseline"))
    labels = [n for n in root.iter() if n.tag.split("}")[-1] == "text" and n.get("data-axis-label") == "x"]
    assert labels and all("rotate(-45" in (n.get("transform") or "") for n in labels)
    for node in labels:
        x, y = float(node.get("x")), float(node.get("y"))
        reach = len(node.text) * 6.5 * 0.7071                          # rough system-font width along the diagonal
        assert 0 < y - baseline <= 24, f"{node.text!r} starts {y - baseline:.0f}px below the axis"
        assert y + reach <= height and x - reach >= 0 and x <= width, f"{node.text!r} runs off the canvas"


# ---------- the simulated feedback round (design 5.7, labelled simulated) ----------

def _round_file(tmp_path, ns, **extra):
    data = {
        "feedback": [{"finding_id": ns.f_attr, "role": "Social lead", "action": "using it", "text": None},
                     {"finding_id": ns.f_checked, "role": "League CEO", "action": "back", "text": "Lead the call with this"}],
        "directives": [{"owner_role": "Head of marketing", "text": "Build the Cole Anthony arrival story",
                        "mandatory": False, "expires": "2026-10-05"}],
        **extra,
    }
    path = tmp_path / "round.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def test_simulate_command_replaces_the_simulated_round_and_keeps_real_rows(demo_store, tmp_path):
    from storydesk.cli import main

    store = demo_store.store
    path, data = _round_file(tmp_path, demo_store)
    store.add_feedback(demo_store.f_checked, role="NBL Now producer", action="comment", text="Real note", simulated=False)
    args = ["simulate", "--store", str(store.path), "--file", str(path)]
    assert main(args) == 0 and main(args) == 0                         # running it twice changes nothing
    simulated = [row for row in store.feedback() if row["simulated"]]
    assert sorted((r["finding_id"], r["role"], r["action"]) for r in simulated) == sorted(
        (f["finding_id"], f["role"], f["action"]) for f in data["feedback"])
    assert any(row["text"] == "Real note" and not row["simulated"] for row in store.feedback())
    directives = store.directives()
    assert [(d["owner_role"], d["text"], d["simulated"]) for d in directives] == [
        ("Head of marketing", "Build the Cole Anthony arrival story", 1)]


def test_simulate_command_refuses_unknown_findings_and_actions(demo_store, tmp_path):
    from storydesk.cli import main

    store = demo_store.store
    good, _ = _round_file(tmp_path, demo_store)
    assert main(["simulate", "--store", str(store.path), "--file", str(good)]) == 0
    before = (store.feedback(), store.directives())
    for bad in ({"finding_id": 99999, "role": "League CEO", "action": "back", "text": None},
                {"finding_id": demo_store.f_attr, "role": "League CEO", "action": "launch it", "text": None}):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"feedback": [bad], "directives": []}), encoding="utf-8")
        with pytest.raises((SystemExit, ValueError, KeyError)):
            if main(["simulate", "--store", str(store.path), "--file", str(path)]) != 0:
                raise SystemExit(1)
        assert (store.feedback(), store.directives()) == before        # nothing half-applied


# ---------- the committed snapshot (pass only after Claude applies the round and rebuilds the site) ----------

def test_published_snapshot_carries_the_labelled_simulated_round():
    con = sqlite3.connect(f"file:{REPO / 'published' / 'store.db'}?immutable=1", uri=True)
    try:
        feedback = con.execute("SELECT simulated FROM feedback").fetchall()
        directives = con.execute("SELECT simulated FROM directives").fetchall()
    finally:
        con.close()
    planned = json.loads((REPO / "published" / "simulated-round.json").read_text(encoding="utf-8"))
    assert len(feedback) == len(planned["feedback"]) > 0 and all(row[0] == 1 for row in feedback)
    assert len(directives) == len(planned["directives"]) > 0 and all(row[0] == 1 for row in directives)
    index = (REPO / "site" / "index.html").read_text(encoding="utf-8")
    left, _, _ = _columns(index)
    assert "simulated" in left.lower() and "No directives yet" not in left


# ---------- fix round: Sol's review and Claude's visual check against the mockups ----------

def test_run_metadata_is_escaped_on_every_page(demo_store, tmp_path):
    store = demo_store.store
    run = store.get_run(demo_store.post_run)
    store.finish_run(run["id"], status="complete", cost_usd=run["cost_usd"], duration_s=run["duration_s"],
                     model_usage=run["model_usage"], num_agents="<script>alert(1)</script>", route=run["route"])
    out = _build(demo_store, tmp_path)
    for page in out.rglob("*.html"):
        assert "<script>alert(1)</script>" not in page.read_text(encoding="utf-8"), page.name


def test_invalid_simulated_round_creates_and_changes_nothing(demo_store, tmp_path):
    from storydesk.cli import main

    def refused(store_path, item):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"feedback": [item], "directives": []}), encoding="utf-8")
        with pytest.raises((SystemExit, ValueError, KeyError)):
            if main(["simulate", "--store", str(store_path), "--file", str(bad)]) != 0:
                raise SystemExit(1)

    fresh = tmp_path / "fresh.db"
    refused(fresh, {"finding_id": 1, "role": "League CEO", "action": "launch it", "text": None})
    refused(fresh, {"finding_id": 1, "role": "League CEO", "action": "back", "text": None})
    assert not fresh.exists()                                          # validation never creates a store
    before = demo_store.store.path.read_bytes()
    refused(demo_store.store.path, {"finding_id": 99999, "role": "League CEO", "action": "back", "text": None})
    assert demo_store.store.path.read_bytes() == before


@pytest.mark.parametrize("kind", ["bar", "line"])
def test_extreme_labels_never_invert_the_plot(kind):
    import xml.etree.ElementTree as ET

    from storydesk.charts import check_chart, render_bar_chart, render_line_chart

    render = render_bar_chart if kind == "bar" else render_line_chart
    labels = [f"{'Very long generated category name '* 2}{i}" for i in range(6)]   # about 70 characters each
    svg = render("Extreme labels", labels, [5, 7, 6, 9, 8, 4], 3, "Value")
    root = ET.fromstring(svg)
    height, baseline = float(root.get("height")), float(root.get("data-baseline"))
    assert baseline - 38 >= 100, "the plot keeps at least 100px of height"
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag == "rect" and node.get("data-label") is not None:
            assert float(node.get("height")) >= 0
        if tag == "circle":
            assert 0 <= float(node.get("cy")) <= baseline + 0.01
        if tag == "text" and node.get("data-axis-label") == "x":
            reach = len(node.text) * 6.5 * 0.7071
            assert float(node.get("y")) + reach <= height and float(node.get("x")) - reach >= 0, node.text
    assert check_chart(svg, "Extreme labels") == []                    # every category is still named


def test_board_cards_stay_short_like_the_mockup(demo_store, tmp_path):
    store = demo_store.store
    store.update_finding(demo_store.f_checked, claim=(
        "Adelaide scored 26 points in the third quarter. Their best quarter came after half-time. Bench minutes rose."))
    store.add_signoff(demo_store.f_held, approver="Head of social", audience="producers")
    index = _read(_build(demo_store, tmp_path), "index.html")
    card = _angle_cards(index)[demo_store.f_checked]["body"]
    text = html.unescape(card)
    assert "Adelaide scored 26 points in the third quarter." in text
    assert "Bench minutes rose." not in text                           # the full claim is on the finding page
    assert "box_team:Adelaide 36ers" not in text                       # evidence is summarised, not listed by ref
    assert re.search(r"\b1 stats check\b", text)
    width = re.search(r'<svg[^>]*\bwidth="([\d.]+)"', card)
    assert width and float(width.group(1)) <= 360, "the card chart is drawn at card size, so its text is legible"
    assert "backed by CEO" in text                                     # the simulated back reaction, as a lead pill
    left, _, _ = _columns(index)
    assert left.count("Head of social") == 1 and "2 held items" in left   # sign-offs grouped by approver


def test_email_has_no_repeated_lead_in_and_counts_angles_in_words(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    happened = email.split("What happened", 1)[1].split("<h2", 1)[0]
    assert "<strong>What happened.</strong>" not in happened
    assert not re.search(r"\b1 angles\b", email)


# ---------- second fix round (Claude, at Bart's request): defects left after Sol's fix round ----------

def _axis_texts(svg):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(svg)
    labels = [n for n in root.iter() if n.tag.split("}")[-1] == "text" and n.get("data-axis-label") == "x"]
    return root, labels


@pytest.mark.parametrize("kind", ["bar", "line"])
def test_full_size_charts_keep_their_labels_whole(kind):
    from storydesk.charts import render_bar_chart, render_line_chart

    render = render_bar_chart if kind == "bar" else render_line_chart
    _, labels = _axis_texts(render("Seconds played", LONG_LABELS, [1310, 1382, 1403, 1426, 1446, 1465], 0, "Seconds"))
    assert [n.text for n in labels] == LONG_LABELS                     # shortened only when the canvas can't fit them


@pytest.mark.parametrize("size", [(680, 340), (320, 190)])
@pytest.mark.parametrize("kind", ["bar", "line"])
def test_rotated_labels_clear_the_canvas_edge_with_room_to_spare(kind, size):
    from storydesk.charts import check_chart, render_bar_chart, render_line_chart

    render = render_bar_chart if kind == "bar" else render_line_chart
    width, height = size
    svg = render("Seconds played", LONG_LABELS, [1310, 1382, 1403, 1426, 1446, 1465], 0, "Seconds",
                 width=width, height=height)
    root, labels = _axis_texts(svg)
    for node in labels:
        reach = len(node.text) * 7.0 * 0.7071                          # a wider, safer glyph estimate than 6.5px
        x, y = float(node.get("x")), float(node.get("y"))
        assert y + reach + 4 <= height and x - reach - 4 >= 0, f"{node.text!r} touches the edge at {size}"
    assert check_chart(svg, "Seconds played") == []                    # shortened labels still name their category


def test_compact_charts_label_only_the_highlighted_value():
    import xml.etree.ElementTree as ET

    from storydesk.charts import render_bar_chart

    values = [69.8, 66.9, 66.2, 72.2, 66.8, 70, 73, 81, 74.9, 77.3, 75]
    labels = [f"{y}-{y + 1}" for y in range(2015, 2026)]
    for width, height, expected in ((320, 190, ["74.9"]), (680, 340, [f"{v:g}" for v in values])):
        root = ET.fromstring(render_bar_chart("Starter share", labels, values, 8,
                                              "Adelaide starter share of points (%), season average",
                                              width=width, height=height))
        texts = [n for n in root.iter() if n.tag.split("}")[-1] == "text" and n.get("data-axis-label") is None]
        shown = [n.text for n in texts if re.fullmatch(r"[\d.]+", n.text or "")]
        assert shown == expected, (width, shown)
        y_label = next(n for n in texts if not re.fullmatch(r"[\d.]+", n.text or ""))
        assert float(y_label.get("x")) + len(y_label.text) * 6.5 <= width, "the y label fits the canvas"


def test_card_descriptions_skip_meta_lead_ins(demo_store, tmp_path):
    store = demo_store.store
    store.update_finding(demo_store.f_child, claim=(
        "User follow-up to finding 2. Adelaide's 26-point third quarter was its best of the game. It came off the bench."))
    index = _read(_build(demo_store, tmp_path), "index.html")
    text = html.unescape(_angle_cards(index)[demo_store.f_child]["body"])
    assert "User follow-up to finding" not in text
    assert "Adelaide's 26-point third quarter was its best of the game." in text


def test_email_held_rows_put_the_headline_on_its_own_line(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    held = email.split("Held for sign-off", 1)[1].split("<h2", 1)[0]
    rows = re.findall(r'<div class="held-row[^"]*">(.*?)(?=<div class="held-row|$)', held, re.S)
    assert rows
    for row in rows:
        assert re.match(r'\s*<a href="\.\./findings/\d+\.html">', row), "the headline leads the row"
        meta = row.find('class="held-meta')
        assert meta > row.find("</a>") > 0, "badge, sign-off note and buttons sit on a line under the headline"
        assert "Keep internal" in row[meta:]


def test_cards_are_well_formed(demo_store, tmp_path):
    out = _build(demo_store, tmp_path)
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert text.count("<article") == text.count("</article>"), page.name


def test_nothing_forces_a_phone_to_scroll_sideways(demo_store, tmp_path):
    out = _build(demo_store, tmp_path)
    index = _read(out, "index.html")
    assert re.search(r'<div class="table-wrap">\s*<table class="runs-table"', index), "the runs table scrolls in its own box"
    css = re.search(r"<style>(.*?)</style>", index, re.S).group(1)
    assert re.search(r"\.table-wrap\s*\{[^}]*overflow-x:\s*auto", css)
    assert re.search(r"\.pill\.held\s*\{[^}]*white-space:\s*normal", css), "long held badges wrap on a phone"
