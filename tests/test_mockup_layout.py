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
        cards[fid] = {"body": body, "pos": match.start()}
    return cards


def _columns(index):
    left, angles, right = (_pos(index, name) for name in ("board-left", "board-angles", "board-right"))
    return tuple(html.unescape(part) for part in (index[left:angles], index[angles:right], index[right:]))


# ---------- the producer board (producer-board-v2.html) ----------

def test_board_has_the_mockups_three_columns(demo_store, tmp_path):
    board = _read(_build(demo_store, tmp_path), "board.html")
    board_at = _pos(board, "board")
    left, angles, right = (_pos(board, name) for name in ("board-left", "board-angles", "board-right"))
    assert -1 < board_at < left < angles < right, "the board, then its left, angles and right columns, in that order"
    assert "Active directives" in board[left:angles] and "From the desk" not in board  # unattributed stance list removed (Bart, 2026-10-30)
    assert "Angles for" in board[angles:right]
    assert "Ask the next run" in board[right:]


def test_board_shows_shared_stances_without_audience_filtering(demo_store, tmp_path):
    demo_store.store.set_stance(demo_store.f_attr, "Social lead", "use_if_raised", "Useful if asked.")
    board = _read(_build(demo_store, tmp_path), "board.html")
    assert "Social lead: use if raised" in html.unescape(board)
    assert "role-switch" not in board and "?role=" not in board


def test_angle_cards_link_to_the_full_story_and_show_stances(demo_store, tmp_path):
    demo_store.store.set_stance(demo_store.f_attr, "Social lead", "push", simulated=True)
    cards = _angle_cards(_read(_build(demo_store, tmp_path), "board.html"))
    assert {demo_store.f_checked, demo_store.f_attr} <= set(cards)
    assert "Social lead: push" in cards[demo_store.f_attr]["body"]
    assert "<svg" in cards[demo_store.f_checked]["body"]               # the chart sits in the board card (restored by Claude)
    for fid, card in cards.items():
        assert f'href="findings/{fid}.html"' in card["body"]


def test_sensitive_items_without_a_stance_sit_in_a_strip_after_the_angles(demo_store, tmp_path):
    board = _read(_build(demo_store, tmp_path), "board.html")
    cards = _angle_cards(board)
    assert demo_store.f_held not in cards
    strip_at, right = _pos(board, "held-strip"), _pos(board, "board-right")
    assert max(card["pos"] for card in cards.values()) < strip_at < right
    strip = board[strip_at:right]
    assert f'href="findings/{demo_store.f_held}.html"' in strip and "sensitive story awaiting a stance" in strip


def test_angles_are_ranked_and_open_after_the_game(demo_store, tmp_path):
    store = demo_store.store
    store.update_finding(demo_store.f_attr, novelty=0.9, audience_fit=0.9, direction=0.9)
    store.update_finding(demo_store.f_checked, novelty=0.1, audience_fit=0.1, direction=0.1)
    cards = _angle_cards(_read(_build(demo_store, tmp_path), "board.html"))
    assert cards[demo_store.f_attr]["pos"] < cards[demo_store.f_checked]["pos"]
    assert demo_store.pre_finding in cards


def test_board_stances_sit_on_their_own_story_card(demo_store, tmp_path):
    # Bart, 2026-10-30: stances show on the card they belong to, never as an unattributed sidebar list.
    demo_store.store.set_stance(demo_store.f_checked, "League CEO", "push", "Lead with this", simulated=True)
    board = _read(_build(demo_store, tmp_path), "board.html")
    left, _, _ = _columns(board)
    assert "League CEO: push" not in left and "No directives yet" in left
    cards = _angle_cards(board)
    assert "League CEO: push" in cards[demo_store.f_checked]["body"] and "simulated" in cards[demo_store.f_checked]["body"].lower()


def test_active_directives_show_owner_expiry_and_the_simulated_label(demo_store, tmp_path):
    store = demo_store.store
    store.add_directive("Head of marketing", "Build the Cole Anthony arrival story", expires="2026-10-05", simulated=True)
    store.add_directive("League GM", "Wait on officiating until the footage is reviewed", mandatory=True, simulated=True)
    left, _, _ = _columns(_read(_build(demo_store, tmp_path), "board.html"))
    directives = left[left.index("Active directives"):]
    for text in ("Build the Cole Anthony arrival story", "Head of marketing", "2026-10-05",
                 "Wait on officiating until the footage is reviewed"):
        assert text in directives, text
    assert "simulated" in directives.lower()
    assert "No directives yet" not in left


def test_right_column_asks_the_next_run_and_tracks_requests(demo_store, tmp_path):
    # Restored by Claude: the follow-up tracker is a core feature; asking is now a mailto link, not a textarea.
    _, _, right = _columns(_read(_build(demo_store, tmp_path), "board.html"))
    assert "Ask the next run" in right and 'href="mailto:storyline-desk@example.com' in right
    assert "Was this Adelaide's best quarter of the game?" in html.unescape(right)
    assert f'href="findings/{demo_store.f_child}.html"' in right       # the answer is one click away


# ---------- the leadership email (leadership-view.html, option A) ----------

def _email(ns, tmp_path):
    return _read(_build(ns, tmp_path), "index.html")


def test_email_has_an_email_header_and_a_reply_to_direct_footer(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    assert "From: Storyline Desk" in email and "To: Leadership, Media, Producers, Broadcast, Partnerships manager · internal only" in email
    subjects = re.findall(r"Subject:\|*([^|]*)", re.sub(r"<[^>]+>", "|", html.unescape(email)))
    assert any("95" in s and "97" in s for s in subjects), subjects   # the post-game subject carries the score (restored by Claude)
    assert "Reply to steer what happens next" in email
    assert 'href="board.html"' in email


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
    section = email.split("What moved since this afternoon", 1)[1].split("The desk's top pick", 1)[0]
    assert f'findings/{moved}.html' in section
    assert "What moved since pre-game" not in email


def test_sensitive_items_in_the_email_use_stance_links(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    sensitive = email.split("Sensitive stories: set a stance", 1)[1].split("Questions worth asking next", 1)[0]
    assert "Push it" in sensitive and "Use if it comes up" in sensitive and "Steer away" in sensitive
    assert "Approve for" not in sensitive and "Keep internal" not in sensitive


def test_email_names_internal_recipients_not_audience_clearances(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    assert "Partnerships manager · internal only" in email
    assert "For: leadership, producers" not in email


# ---------- the finding page (finding-detail.html) ----------

def _finding_html(ns, tmp_path, fid):
    return _read(_build(ns, tmp_path), f"findings/{fid}.html")


def test_finding_page_has_a_main_column_and_a_sidebar(demo_store, tmp_path):
    page = _finding_html(demo_store, tmp_path, demo_store.f_checked)
    main, side = _pos(page, "detail-main"), _pos(page, "detail-side")
    assert -1 < main < side
    header = page[:main]
    assert "<h1>" in header
    for label in ("Push it", "Use if it comes up", "Steer away", "Comment"):
        assert label in header, label
    body = page[main:side]
    assert "<svg" in body and "How we know" in body and "How the agents got here" in body   # chart restored by Claude
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
    assert "No linked finding yet" not in page                         # restored by Claude: the trail falls back to checked sources
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


# ---------- the simulated stance round (design 4C, labelled simulated) ----------

def _round_file(tmp_path, ns, **extra):
    data = {
        "stances": [{"finding_id": ns.f_attr, "role": "Social lead", "stance": "push", "comment": None, "simulated": True},
                    {"finding_id": ns.f_checked, "role": "League CEO", "stance": "push", "comment": "Lead the call with this", "simulated": True}],
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
    store.set_stance(demo_store.f_checked, "NBL Now producer", "use_if_raised", "Real note")
    args = ["simulate", "--store", str(store.path), "--file", str(path)]
    assert main(args) == 0 and main(args) == 0                         # running it twice changes nothing
    simulated = [row for fid in (demo_store.f_attr, demo_store.f_checked) for row in store.stances(fid) if row["simulated"]]
    assert sorted((r["role"], r["stance"]) for r in simulated) == sorted(
        (f["role"], f["stance"]) for f in data["stances"])
    assert any(row["comment"] == "Real note" and not row["simulated"] for row in store.stances(demo_store.f_checked))
    directives = store.directives()
    assert [(d["owner_role"], d["text"], d["simulated"]) for d in directives] == [
        ("Head of marketing", "Build the Cole Anthony arrival story", 1)]


def test_simulate_command_refuses_unknown_findings_and_stances(demo_store, tmp_path):
    from storydesk.cli import main

    store = demo_store.store
    good, _ = _round_file(tmp_path, demo_store)
    assert main(["simulate", "--store", str(store.path), "--file", str(good)]) == 0
    before = (store.stances(demo_store.f_attr), store.directives())
    for bad in ({"finding_id": 99999, "role": "League CEO", "stance": "push", "comment": None, "simulated": True},
                {"finding_id": demo_store.f_attr, "role": "League CEO", "stance": "launch it", "comment": None, "simulated": True}):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"stances": [bad], "directives": []}), encoding="utf-8")
        with pytest.raises((SystemExit, ValueError, KeyError)):
            if main(["simulate", "--store", str(store.path), "--file", str(path)]) != 0:
                raise SystemExit(1)
        assert (store.stances(demo_store.f_attr), store.directives()) == before        # nothing half-applied


# ---------- the committed snapshot (pass only after Claude applies the round and rebuilds the site) ----------

def test_published_snapshot_carries_the_labelled_simulated_round():
    planned = json.loads((REPO / "published" / "simulated-round.json").read_text(encoding="utf-8"))
    assert planned["stances"] and all(item["simulated"] is True for item in planned["stances"])
    assert {item["stance"] for item in planned["stances"]} <= {"push", "use_if_raised", "steer_away"}
    assert planned["directives"]


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
        bad.write_text(json.dumps({"stances": [item], "directives": []}), encoding="utf-8")
        with pytest.raises((SystemExit, ValueError, KeyError)):
            if main(["simulate", "--store", str(store_path), "--file", str(bad)]) != 0:
                raise SystemExit(1)

    fresh = tmp_path / "fresh.db"
    refused(fresh, {"finding_id": 1, "role": "League CEO", "stance": "launch it", "comment": None, "simulated": True})
    refused(fresh, {"finding_id": 1, "role": "League CEO", "stance": "push", "comment": None, "simulated": True})
    assert not fresh.exists()                                          # validation never creates a store
    before = demo_store.store.path.read_bytes()
    refused(demo_store.store.path, {"finding_id": 99999, "role": "League CEO", "stance": "push", "comment": None, "simulated": True})
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
    index = _read(_build(demo_store, tmp_path), "board.html")
    card = _angle_cards(index)[demo_store.f_checked]["body"]
    text = html.unescape(card)
    assert "Adelaide scored 26 points in the third quarter." in text
    assert "Bench minutes rose." not in text                           # the full claim is on the finding page
    assert "box_team:Adelaide 36ers" not in text
    width = re.search(r'<svg[^>]*\bwidth="([\d.]+)"', card)              # a compact chart, as before R1 (restored by Claude)
    assert width and float(width.group(1)) <= 360


def test_email_has_no_repeated_lead_in_and_counts_angles_in_words(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    moved = email.split("What moved since this afternoon", 1)[1].split("The desk's top pick", 1)[0]
    assert "<strong>What happened.</strong>" not in moved
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
    index = _read(_build(demo_store, tmp_path), "board.html")
    text = html.unescape(_angle_cards(index)[demo_store.f_child]["body"])
    assert "User follow-up to finding" not in text
    assert "Adelaide's 26-point third quarter was its best of the game." in text


def test_email_held_rows_put_the_headline_on_its_own_line(demo_store, tmp_path):
    email = _email(demo_store, tmp_path)
    sensitive = email.split("Sensitive stories: set a stance", 1)[1].split("Questions worth asking next", 1)[0]
    rows = re.findall(r'<article class="item sensitive"[^>]*>(.*?)</article>', sensitive, re.S)
    assert rows
    for row in rows:
        assert re.match(r'\s*<b class="h">', row), "the headline leads the box"
        stance = row.find('class="stance"')
        assert stance > row.find("</b>") > 0, "the sensitive tag, premise and stance links sit under the headline"
        assert "Steer away" in row[stance:]


def test_cards_are_well_formed(demo_store, tmp_path):
    out = _build(demo_store, tmp_path)
    for page in out.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert text.count("<article") == text.count("</article>"), page.name


def test_nothing_forces_a_phone_to_scroll_sideways(demo_store, tmp_path):
    out = _build(demo_store, tmp_path)
    index = _read(out, "index.html")
    assert re.search(r'<div class="table-wrap">\s*<table class="runs-table"', index), "the runs table scrolls in its own box"
    css = _read(out, "assets/agora.css")                               # the shared token stylesheet
    assert re.search(r"\.table-wrap\s*\{[^}]*overflow-x:\s*auto", css)
    assert re.search(r"\.pill\.held\s*\{[^}]*white-space:\s*normal", css), "long held badges wrap on a phone"
