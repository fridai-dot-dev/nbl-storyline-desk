"""R5 charts: a donut, a scatter and a line, each built by code only from the rows of a SQL query.

Renderer unit tests, a site test on the fixture stats DB, the failing-query rules, and an integration test
against the real data/stats.duckdb and the shipped published/extra-charts.json (skipped when the DB is absent).
"""

from __future__ import annotations

import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conftest import OPENER, POST, REPO
from test_r1_support import build_r1_site, parse_html, seed_r1_store

# The Agora tokens from the design (§4D) and site.py's :root. White is the page plate.
PALETTE = {"#1a1a1a", "#6b6b6b", "#ffffff", "#f5f5f5", "#d9d9d9", "#1f3a5f", "#3d7a4a", "#a04545", "#8a8a8a"}

REAL_DB = REPO / "data" / "stats.duckdb"
REAL_STORE = REPO / "published" / "store.db"
REAL_CHARTS = REPO / "published" / "extra-charts.json"

DONUT_SQL = (
    "select label, value from ("
    f"select 1 as ord, 'Threes' as label, three_pointers_made*3 as value from box_team where match_id='{OPENER}' and name='Adelaide 36ers' "
    f"union all select 2, 'Twos', two_pointers_made*2 from box_team where match_id='{OPENER}' and name='Adelaide 36ers' "
    f"union all select 3, 'Free throws', free_throws_made from box_team where match_id='{OPENER}' and name='Adelaide 36ers'"
    ") order by ord"
)
SCATTER_SQL = (
    "select first_name || ' ' || family_name || ', ' || points || ' pts in ' || minutes as label, "
    "(cast(split_part(minutes,':',1) as int)*60+cast(split_part(minutes,':',2) as int))/60.0 as x, points as y "
    "from box_player where minutes is not null order by x, label"
)
LINE_SQL = (
    "select strftime(r.match_time_utc, '%Y-%m-%d') as label, t.score as value "
    "from box_team t join results r on r.match_id = t.match_id "
    "where t.name = 'Adelaide 36ers' and t.opp_name = 'Melbourne United' order by r.match_time_utc"
)


# ---------------------------------------------------------------- helpers

def _local(node) -> str:
    return node.tag.split("}")[-1]


def _root(svg: str):
    return ET.fromstring(svg)


def _marks(root, mark: str):
    return [node for node in root.iter() if node.get("data-mark") == mark]


def _texts(root) -> list[str]:
    return [node.text or "" for node in root.iter() if _local(node) == "text"]


def _colours(svg: str) -> set[str]:
    """Every colour an SVG names, in attributes, style attributes and style elements."""
    found = {_hex(match) for match in re.findall(r"#[0-9a-fA-F]{3,8}\b", svg)}
    root = _root(svg)
    for node in root.iter():
        for attribute in ("fill", "stroke"):
            value = node.get(attribute)
            assert value in (None, "none") or value.startswith("#"), f"{attribute}={value!r} is not a palette hex"
    assert "currentcolor" not in svg.lower() and "rgb(" not in svg.lower() and "hsl(" not in svg.lower()
    return found


def _hex(value: str) -> str:
    value = value.lower()
    if len(value) == 4:
        value = "#" + "".join(ch * 2 for ch in value[1:])
    return value


def _number(text: str) -> float:
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    assert match, text
    return float(match.group(0).replace(",", ""))


def _angle(x: float, y: float, cx: float, cy: float) -> float:
    """Degrees clockwise from twelve o'clock."""
    return math.degrees(math.atan2(x - cx, -(y - cy))) % 360


def _inline_charts(html: str) -> list[ET.Element]:
    """The extra charts (those carrying data-chart) drawn inline on a page."""
    roots = [_root(chunk) for chunk in re.findall(r"<svg\b.*?</svg>", html, flags=re.S)]
    return [root for root in roots if root.get("data-chart")]


def _assert_basic(svg: str, title: str) -> ET.Element:
    root = _root(svg)
    assert _local(root) == "svg"
    assert float(root.get("width")) <= 600
    assert root.get("viewBox") and root.get("role") == "img"
    assert root.get("aria-label") == title
    first = list(root)[0]
    assert _local(first) == "title" and first.text == title
    assert _colours(svg) <= PALETTE
    return root


# ---------------------------------------------------------------- renderer: donut

def test_donut_draws_one_arc_per_slice_and_its_labels_sum_to_the_total():
    from storydesk.charts import render_donut_chart

    title = "Adelaide's 97 points by source"
    svg = render_donut_chart(title, ["Threes", "Twos", "Free throws"], [39, 38, 20], y_label="points")
    root = _assert_basic(svg, title)
    assert root.get("data-chart") == "donut" and float(root.get("data-total")) == 97

    arcs = _marks(root, "slice")
    assert [arc.get("data-label") for arc in arcs] == ["Threes", "Twos", "Free throws"]
    assert [float(arc.get("data-value")) for arc in arcs] == [39, 38, 20]
    assert all(_local(arc) == "path" and arc.get("d") for arc in arcs)

    labels = _marks(root, "slice-label")
    assert len(labels) == 3
    assert sum(_number(label.text) for label in labels) == 97
    for label in labels:
        assert label.get("data-label") in label.text
    total = _marks(root, "total")
    assert len(total) == 1 and _number(total[0].text) == 97
    assert "points" in " ".join(_texts(root))


def test_donut_arcs_are_sized_by_value_starting_at_the_top():
    from storydesk.charts import render_donut_chart

    root = _root(render_donut_chart("t", ["a", "b", "c"], [50, 30, 20]))
    cx, cy = float(root.get("data-cx")), float(root.get("data-cy"))
    expected_start = 0.0
    for arc, value in zip(_marks(root, "slice"), (50, 30, 20)):
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", arc.get("d"))]
        start = _angle(numbers[0], numbers[1], cx, cy)            # M x y
        end = _angle(numbers[7], numbers[8], cx, cy)              # A rx ry rot large sweep x y
        span = (end - start) % 360
        assert span == pytest.approx(value / 100 * 360, abs=0.6)
        assert min(abs(start - expected_start), 360 - abs(start - expected_start)) < 0.6
        expected_start += span


def test_donut_highlight_zero_slices_and_bad_input():
    from storydesk.charts import render_donut_chart

    plain = _root(render_donut_chart("t", ["a", "b"], [3, 1]))
    assert not [node for node in plain.iter() if node.get("data-highlight")]
    picked = _root(render_donut_chart("t", ["a", "b"], [3, 1], highlight_index=1))
    assert [node.get("data-label") for node in picked.iter() if node.get("data-highlight") == "true" and node.get("data-mark") == "slice"] == ["b"]

    zero = _root(render_donut_chart("t", ["a", "b", "c"], [3, 0, 1]))
    assert [arc.get("data-label") for arc in _marks(zero, "slice")] == ["a", "c"]   # a zero slice has no arc
    assert float(zero.get("data-total")) == 4

    single = _root(render_donut_chart("t", ["only"], [7]))
    assert len(_marks(single, "slice")) == 1                                         # a full ring still draws

    for labels, values in (([], []), (["a"], [1, 2]), (["a", "b"], [1, -1]), (["a", "b"], [0, 0]), (["a"], [float("nan")])):
        with pytest.raises(ValueError):
            render_donut_chart("t", labels, values)
    with pytest.raises(ValueError):
        render_donut_chart("t", ["a", "b"], [1, 2], highlight_index=5)


# ---------------------------------------------------------------- renderer: scatter

def _scatter_rows(n: int = 60):
    labels = [f"Player {i}, {30 + i % 9} pts in {25 + i % 20}:00" for i in range(n)]
    xs = [25.0 + (i * 7) % 21 + (i % 3) * 0.25 for i in range(n)]
    ys = [30 + (i * 5) % 14 for i in range(n)]
    return labels, xs, ys


def test_scatter_draws_one_circle_per_row_and_one_distinct_highlight_on_top():
    from storydesk.charts import render_scatter_chart

    labels, xs, ys = _scatter_rows()
    title = "Every 30-point game by minutes played"
    svg = render_scatter_chart(title, labels, xs, ys, 17, x_label="Minutes played", y_label="Points")
    root = _assert_basic(svg, title)
    assert root.get("data-chart") == "scatter"

    circles = [node for node in root.iter() if _local(node) == "circle"]
    dots = _marks(root, "dot")
    assert len(dots) == len(circles) == len(labels)
    assert [dot.get("data-label") for dot in dots if dot.get("data-highlight") != "true"] == [l for i, l in enumerate(labels) if i != 17]
    highlighted = [dot for dot in dots if dot.get("data-highlight") == "true"]
    assert len(highlighted) == 1 and highlighted[0].get("data-label") == labels[17]
    assert dots[-1] is highlighted[0]                                   # drawn last so it sits on top
    plain = next(dot for dot in dots if dot is not highlighted[0])
    assert highlighted[0].get("fill") != plain.get("fill")
    assert float(highlighted[0].get("r")) > float(plain.get("r"))
    assert float(highlighted[0].get("data-x")) == pytest.approx(xs[17])
    assert float(highlighted[0].get("data-y")) == ys[17]
    assert labels[17] in " ".join(_texts(root))                         # the highlight is named on the chart
    visible = " ".join(_texts(root))
    assert "Minutes played" in visible and "Points" in visible


def test_scatter_positions_follow_the_data():
    from storydesk.charts import render_scatter_chart

    labels, xs, ys = _scatter_rows()
    root = _root(render_scatter_chart("t", labels, xs, ys, 0, x_label="Minutes", y_label="Points"))
    width, height = float(root.get("width")), float(root.get("height"))
    dots = _marks(root, "dot")
    by_x = sorted(dots, key=lambda dot: float(dot.get("data-x")))
    assert [float(d.get("cx")) for d in by_x] == sorted(float(d.get("cx")) for d in by_x)
    by_y = sorted(dots, key=lambda dot: float(dot.get("data-y")))
    assert [float(d.get("cy")) for d in by_y] == sorted((float(d.get("cy")) for d in by_y), reverse=True)
    for dot in dots:
        assert 0 < float(dot.get("cx")) < width and 0 < float(dot.get("cy")) < height
    ticks = [node.text for node in root.iter() if node.get("data-axis-label") in {"x", "y"}]
    assert len(ticks) >= 4


def test_scatter_without_a_highlight_and_bad_input():
    from storydesk.charts import render_scatter_chart

    labels, xs, ys = _scatter_rows(8)
    root = _root(render_scatter_chart("t", labels, xs, ys, None))
    assert len(_marks(root, "dot")) == 8
    assert not [node for node in root.iter() if node.get("data-highlight")]
    for args in (([], [], [], None), (["a"], [1.0, 2.0], [1], None), (["a"], [1.0], [float("inf")], None), (["a"], [1.0], [1], 3)):
        with pytest.raises(ValueError):
            render_scatter_chart("t", *args)


# ---------------------------------------------------------------- renderer: line

def _line_rows(n: int = 39):
    labels = [f"{2016 + i // 5}-{1 + i % 12:02d}-{1 + i % 27:02d}" for i in range(n)]
    values = [float(8 + (i * 11) % 29) for i in range(n)]
    return labels, values


def test_line_draws_one_point_per_row_and_a_dashed_reference_line():
    from storydesk.charts import render_line_chart

    labels, values = _line_rows()
    title = "Bryce Cotton's points against Melbourne"
    average = round(sum(values) / len(values), 2)
    svg = render_line_chart(title, labels, values, None, "Points", width=600, reference=average, reference_label=f"Average {average:g}")
    root = _assert_basic(svg, title)
    assert root.get("data-chart") == "line" and float(root.get("data-reference")) == average

    points = _marks(root, "point")
    assert len(points) == len(values) == len([n for n in root.iter() if _local(n) == "circle"])
    assert [p.get("data-label") for p in points] == labels
    assert [float(p.get("data-value")) for p in points] == values
    series = _marks(root, "series")
    assert len(series) == 1 and _local(series[0]) == "polyline"
    assert len(series[0].get("points").split()) == len(values)

    references = _marks(root, "reference")
    assert len(references) == 1 and _local(references[0]) == "line"
    dash = references[0].get("stroke-dasharray")
    assert dash and dash != "none"
    assert f"Average {average:g}" in " ".join(_texts(root))
    # The reference line sits where the axis says its value is.
    low, high = min(points, key=lambda p: float(p.get("data-value"))), max(points, key=lambda p: float(p.get("data-value")))
    slope = (float(high.get("cy")) - float(low.get("cy"))) / (float(high.get("data-value")) - float(low.get("data-value")))
    expected_y = float(low.get("cy")) + slope * (average - float(low.get("data-value")))
    assert float(references[0].get("y1")) == pytest.approx(expected_y, abs=0.6)
    assert float(references[0].get("y2")) == pytest.approx(expected_y, abs=0.6)


def test_line_axis_stays_readable_with_many_points():
    from storydesk.charts import render_line_chart

    labels, values = _line_rows()
    root = _root(render_line_chart("t", labels, values, None, "Points", width=600, reference=20.0))
    x_labels = [node for node in root.iter() if node.get("data-axis-label") == "x"]
    assert 2 <= len(x_labels) <= 10                                     # sparse ticks, not 39 rotated dates
    assert x_labels[0].text == labels[0] and x_labels[-1].text == labels[-1]
    assert not [node for node in root.iter() if node.get("transform")]


def test_line_highlight_is_optional_and_the_old_form_is_unchanged():
    from storydesk.charts import render_line_chart

    labels, values = _line_rows(6)
    picked = _root(render_line_chart("t", labels, values, 2, "Points", width=600, reference=15.0))
    assert [p.get("data-label") for p in _marks(picked, "point") if p.get("data-highlight") == "true"] == [labels[2]]
    none = _root(render_line_chart("t", labels, values, None, "Points", width=600, reference=15.0))
    assert not [p for p in _marks(none, "point") if p.get("data-highlight")]

    old = render_line_chart("T", ["R1", "R2", "R3"], [1, 3, 2], 2, "Points")
    assert "#2667a0" in old and "data-mark" not in old and "data-chart" not in old   # no new styling leaks into the old form
    with pytest.raises(ValueError):
        render_line_chart("T", ["R1", "R2"], [1, 2], 7, "Points", width=600, reference=1.5)


# ---------------------------------------------------------------- the site

def _write_charts(directory: Path, entries) -> Path:
    path = directory / "extra-charts.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def _page(out: Path, finding_id: int) -> str:
    return (out / "findings" / f"{finding_id}.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def extra_site(tmp_path_factory, stats_db):
    """The R1 fixture store with one chart of each kind, found beside the store."""
    tmp = tmp_path_factory.mktemp("r5-site")
    ns = seed_r1_store(tmp, stats_db)
    ids = ns.finding_ids
    _write_charts(tmp, [
        {"finding_id": ids["top_pick"], "kind": "donut", "title": "Adelaide's 97 points by source", "sql": DONUT_SQL, "y_label": "points"},
        {"finding_id": ids["sensitive_none"], "kind": "scatter", "title": "Minutes and points in the opener", "sql": SCATTER_SQL,
         "x_label": "Minutes played", "y_label": "Points", "highlight": "Cole Anthony, 30 pts in 21:50"},
        {"finding_id": ids["test_valid"], "kind": "line", "title": "Adelaide's score against Melbourne", "sql": LINE_SQL, "y_label": "Points"},
    ])
    from storydesk.site import build_site

    out = tmp / "site"
    build_site(ns.store, ns.stats_db, out, game_id=ns.game_id)
    return ns, out


def test_site_draws_each_chart_on_its_findings_page_from_the_rows(extra_site, stats_db):
    from storydesk.data import as_of_connection

    ns, out = extra_site
    ids = ns.finding_ids

    donut = _inline_charts(_page(out, ids["top_pick"]))
    assert [chart.get("data-chart") for chart in donut] == ["donut"]
    assert [(a.get("data-label"), float(a.get("data-value"))) for a in _marks(donut[0], "slice")] == [("Threes", 39), ("Twos", 38), ("Free throws", 20)]
    assert "No chart was released" not in _page(out, ids["top_pick"])    # the chart takes the place of the missing one

    con = as_of_connection(stats_db, POST)
    try:
        players = con.execute("select count(*) from box_player where minutes is not null").fetchone()[0]
    finally:
        con.close()
    scatter = _inline_charts(_page(out, ids["sensitive_none"]))
    assert [chart.get("data-chart") for chart in scatter] == ["scatter"]
    dots = _marks(scatter[0], "dot")
    assert len(dots) == players > 10
    marked = [dot for dot in dots if dot.get("data-highlight") == "true"]
    assert [dot.get("data-label") for dot in marked] == ["Cole Anthony, 30 pts in 21:50"]
    assert round(float(marked[0].get("data-x")) * 60) == 1310
    assert "Minutes played" in " ".join(_texts(scatter[0]))

    pre = as_of_connection(stats_db, ns.payload["runs"][0]["as_of"])
    try:
        games = pre.execute(LINE_SQL).fetchall()
    finally:
        pre.close()
    line = _inline_charts(_page(out, ids["test_valid"]))
    assert [chart.get("data-chart") for chart in line] == ["line"]
    points = _marks(line[0], "point")
    assert len(points) == len(games) > 10
    assert [float(p.get("data-value")) for p in points] == [float(row[1]) for row in games]
    assert float(line[0].get("data-reference")) == pytest.approx(sum(float(row[1]) for row in games) / len(games), abs=0.006)
    assert len(_marks(line[0], "reference")) == 1


def test_site_puts_the_top_pick_chart_in_the_email_as_an_image_file(extra_site):
    ns, out = extra_site
    index = parse_html((out / "index.html").read_text(encoding="utf-8"))
    mails = {node.attrs.get("data-email-type"): node for node in index.descendants(cls="mail")}
    for mail in mails.values():
        assert mail.descendants("svg") == []                            # an email never carries an inline <svg>
    post_images = [img for img in mails["post_game"].descendants("img") if img.attrs.get("src", "").startswith("assets/")]
    assert len(post_images) == 1
    src = post_images[0].attrs["src"]
    assert re.fullmatch(r"assets/extra-chart-\d+-1\.svg", src) and str(ns.finding_ids["top_pick"]) in src
    assert post_images[0].attrs.get("alt")
    chart = _root((out / src).read_text(encoding="utf-8"))
    assert chart.get("data-chart") == "donut" and float(chart.get("data-total")) == 97
    assert float(chart.get("width")) <= 600
    # Charts for findings that are not the top pick stay on their own pages.
    assert not [img for img in mails["pre_game"].descendants("img") if img.attrs.get("src", "").startswith("assets/")]
    assert sorted(path.name for path in (out / "assets").glob("extra-chart-*")) == [Path(src).name]


def test_site_chart_sits_under_the_findings_own_chart(demo_store, tmp_path):
    from storydesk.site import build_site

    ns = demo_store
    _write_charts(ns.store.path.parent, [
        {"finding_id": ns.f_checked, "kind": "donut", "title": "Adelaide's 97 points by source", "sql": DONUT_SQL},
    ])
    out = tmp_path / "site"
    build_site(ns.store, ns.stats_db, out, game_id=OPENER)
    page = _page(out, ns.f_checked)
    own = page.index('class="bar')
    extra = page.index('data-chart="donut"')
    assert own < extra
    assert page.count('data-chart="donut"') == 1


def test_site_override_path_and_no_file_changes_nothing(tmp_path, stats_db):
    from storydesk.site import build_site

    ns = seed_r1_store(tmp_path, stats_db)
    plain = tmp_path / "plain"
    build_site(ns.store, ns.stats_db, plain, game_id=ns.game_id)
    assert not list((plain / "assets").glob("extra-chart-*"))
    assert not [p for p in plain.rglob("*.html") if "data-chart" in p.read_text(encoding="utf-8")]

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    path = _write_charts(elsewhere, [{"finding_id": ns.finding_ids["top_pick"], "kind": "donut", "title": "By source", "sql": DONUT_SQL}])
    explicit = tmp_path / "explicit"
    build_site(ns.store, ns.stats_db, explicit, game_id=ns.game_id, extra_charts=path)
    assert _inline_charts(_page(explicit, ns.finding_ids["top_pick"]))


# ---------------------------------------------------------------- failing queries

# (name, which run's finding it sits on, entry body). "pre" pages see the stats before the opener is final.
BAD_QUERIES = [
    ("syntax", "pre", {"kind": "donut", "sql": "select from where"}),
    ("not a select", "pre", {"kind": "donut", "sql": "drop table raw_box_team"}),
    ("raw table", "pre", {"kind": "donut", "sql": "select name as label, score as value from raw_box_team"}),
    ("no rows", "pre", {"kind": "donut", "sql": DONUT_SQL}),                       # the opener is not final at the pre-game cutoff
    ("missing column", "pre", {"kind": "donut", "sql": "select 1 as a"}),
    ("not numbers", "pre", {"kind": "line", "sql": "select 'a' as label, 'b' as value"}),
    ("negative slice", "pre", {"kind": "donut", "sql": "select 'a' as label, -3 as value union all select 'b', 1"}),
    ("unknown kind", "pre", {"kind": "pie", "sql": "select 'a' as label, 1 as value"}),
    ("empty sql", "pre", {"kind": "line", "sql": ""}),
    ("no sql", "pre", {"kind": "line"}),
    ("highlight not in rows", "post", {"kind": "scatter", "sql": SCATTER_SQL, "highlight": "Nobody, 99 pts in 1:00"}),
    ("scatter without y", "post", {"kind": "scatter", "sql": "select 'a' as label, 1.0 as x"}),
]


def test_failing_queries_omit_the_chart_and_the_page_still_builds(tmp_path, stats_db):
    from storydesk.site import build_site

    ns = seed_r1_store(tmp_path, stats_db)
    ids = ns.finding_ids
    target = {"pre": ids["test_valid"], "post": ids["sensitive_conflict"]}
    entries = [{"finding_id": target[run], "title": "A chart", **body} for _name, run, body in BAD_QUERIES]
    entries += [
        {"finding_id": 999999, "kind": "donut", "title": "Nowhere", "sql": "select 'a' as label, 1 as value"},
        "not an entry",
        {"kind": "donut", "title": "No finding", "sql": "select 'a' as label, 1 as value"},
        {"finding_id": ids["top_pick"], "kind": "donut", "title": "Adelaide's 97 points by source", "sql": DONUT_SQL},   # the good one
    ]
    _write_charts(tmp_path, entries)
    out = tmp_path / "site"
    build_site(ns.store, ns.stats_db, out, game_id=ns.game_id)

    for finding_id in target.values():
        page = _page(out, finding_id)
        assert _inline_charts(page) == []
        assert "No chart was released for this finding." in page            # nothing replaced the missing-chart note
    assert list((out / "findings").glob("*.html"))
    assert len(_inline_charts(_page(out, ids["top_pick"]))) == 1            # one bad entry does not take the rest down


@pytest.mark.parametrize("text", ["{not json", '{"finding_id": 1}', "", "[1, 2]", "null"])
def test_a_broken_extra_charts_file_never_stops_the_build(tmp_path, stats_db, text):
    from storydesk.site import build_site

    ns = seed_r1_store(tmp_path, stats_db)
    (tmp_path / "extra-charts.json").write_text(text, encoding="utf-8")
    out = tmp_path / "site"
    build_site(ns.store, ns.stats_db, out, game_id=ns.game_id)
    assert (out / "index.html").is_file()
    assert not [p for p in out.rglob("*.html") if "data-chart" in p.read_text(encoding="utf-8")]


# ---------------------------------------------------------------- the shipped file and the real data

def test_shipped_extra_charts_file_has_the_three_charts():
    entries = json.loads(REAL_CHARTS.read_text(encoding="utf-8"))
    assert isinstance(entries, list)
    assert {(item["finding_id"], item["kind"]) for item in entries} == {(30, "donut"), (25, "scatter"), (10, "line")}
    for item in entries:
        assert item["title"] and item["sql"].lstrip().lower().startswith(("select", "with"))
    assert REAL_STORE.parent == REAL_CHARTS.parent                         # build_site finds it beside the store, no CLI change


@pytest.mark.skipif(not REAL_DB.is_file(), reason="data/stats.duckdb is not present")
def test_real_data_renders_the_three_charts(tmp_path):
    from storydesk.site import build_site
    from storydesk.store import Store

    copy = tmp_path / "store.db"
    shutil.copy2(REAL_STORE, copy)                                          # never open the published ledger for writing
    out = tmp_path / "site"
    build_site(Store(copy), REAL_DB, out, game_id=OPENER, extra_charts=REAL_CHARTS)

    donut = _inline_charts(_page(out, 30))
    assert [chart.get("data-chart") for chart in donut] == ["donut"]
    slices = _marks(donut[0], "slice")
    assert [(a.get("data-label"), float(a.get("data-value"))) for a in slices] == [("Threes", 39), ("Twos", 38), ("Free throws", 20)]
    assert float(donut[0].get("data-total")) == 97

    scatter = _inline_charts(_page(out, 25))
    assert [chart.get("data-chart") for chart in scatter] == ["scatter"]
    dots = _marks(scatter[0], "dot")
    assert len(dots) == 370
    marked = [dot for dot in dots if dot.get("data-highlight") == "true"]
    assert len(marked) == 1 and round(float(marked[0].get("data-x")) * 60) == 1310 and float(marked[0].get("data-y")) == 30
    assert min(float(dot.get("data-x")) * 60 for dot in dots) == pytest.approx(1310)   # his is the shortest 30-point game
    assert all(float(dot.get("data-y")) >= 30 for dot in dots)

    line = _inline_charts(_page(out, 10))
    assert [chart.get("data-chart") for chart in line] == ["line"]
    points = _marks(line[0], "point")
    assert len(points) == 39
    assert float(line[0].get("data-reference")) == pytest.approx(21.21, abs=0.005)
    dates = [p.get("data-label") for p in points]
    assert dates == sorted(dates) and dates[0] >= "2015-10-01"             # in date order, since 2015-16
    assert len(_marks(line[0], "reference")) == 1

    for chart in (donut[0], scatter[0], line[0]):
        assert float(chart.get("width")) <= 600
        assert _colours(ET.tostring(chart, encoding="unicode")) <= PALETTE
