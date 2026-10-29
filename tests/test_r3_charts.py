"""R3 checks for reviewdesk's own SVG charts (donut, line, scatter): form, structure, and numbers from the data."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from test_r3_support import NUMBER, REVIEWDESK

SVG = "{http://www.w3.org/2000/svg}"
SLICES = [("Freshness", 24), ("Service", 21), ("Wait time", 17), ("Other", 38)]
POINTS = [("7 Sep", 4.4), ("14 Sep", 4.5), ("21 Sep", 4.3), ("28 Sep", 3.9)]
SCATTER = [("14", 31, 9), ("22", 29, 11), ("12", 22, 3), ("31", 21, 1)]


def _parse(svg: str) -> ET.Element:
    root = ET.fromstring(svg)
    assert root.tag == f"{SVG}svg"
    return root


def _texts(root: ET.Element) -> list[str]:
    return ["".join(node.itertext()) for node in root.iter() if node.tag in (f"{SVG}text", f"{SVG}title")]


def _allowed(*values) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        tokens |= set(NUMBER.findall(str(value)))
    return tokens


def _by_class(root: ET.Element, tag: str, cls: str) -> list[ET.Element]:
    return [node for node in root.iter(f"{SVG}{tag}") if cls in node.get("class", "").split()]


def test_r3_donut_draws_one_slice_per_part_and_labels_them_from_the_data():
    from reviewdesk.charts import render_donut

    root = _parse(render_donut(SLICES, title="Theme mix this week", centre_label="412 reviews", unit="%"))
    assert root.get("data-chart") == "donut"
    assert root.find(f"{SVG}title").text == "Theme mix this week"
    assert len(_by_class(root, "path", "slice")) == len(SLICES)
    text = " ".join(_texts(root))
    assert "412 reviews" in text
    for label, value in SLICES:
        assert f"{label} {value}%" in text, label
    assert set(NUMBER.findall(text)) <= _allowed(*[value for _label, value in SLICES], "412")


def test_r3_line_draws_the_series_and_a_labelled_baseline():
    from reviewdesk.charts import render_line

    root = _parse(render_line(POINTS, title="Store rating by week", baseline=4.4, baseline_label="3-month baseline 4.4"))
    assert root.get("data-chart") == "line"
    series = _by_class(root, "polyline", "series")
    assert len(series) == 1
    assert len(re.findall(r"-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?", series[0].get("points", ""))) == len(POINTS)
    assert len(_by_class(root, "line", "baseline")) == 1
    text = " ".join(_texts(root))
    assert "3-month baseline 4.4" in text
    for label, value in (POINTS[0], POINTS[-1]):
        assert label in text and str(value) in text
    assert set(NUMBER.findall(text)) <= _allowed(*[f"{label} {value}" for label, value in POINTS], "3-month baseline 4.4")


def test_r3_scatter_draws_one_point_per_item_with_axis_titles():
    from reviewdesk.charts import render_scatter

    root = _parse(render_scatter(SCATTER, title="Staffing against waits", x_label="Transactions per staff hour",
                                 y_label="Wait-time complaints"))
    assert root.get("data-chart") == "scatter"
    assert len(_by_class(root, "circle", "point")) == len(SCATTER)
    text = " ".join(_texts(root))
    assert "Transactions per staff hour" in text and "Wait-time complaints" in text
    for label, _x, _y in SCATTER:
        assert label in text
    assert set(NUMBER.findall(text)) <= _allowed(*[f"{label} {x} {y}" for label, x, y in SCATTER])


@pytest.mark.parametrize("name,args,kw", [
    ("render_donut", (SLICES,), {"title": "t", "centre_label": "c", "unit": "%"}),
    ("render_line", (POINTS,), {"title": "t", "baseline": 4.4, "baseline_label": "b"}),
    ("render_scatter", (SCATTER,), {"title": "t", "x_label": "x", "y_label": "y"}),
])
def test_r3_charts_are_deterministic_and_email_safe(name, args, kw):
    from reviewdesk import charts

    first, second = getattr(charts, name)(*args, **kw), getattr(charts, name)(*args, **kw)
    assert first == second
    assert "<script" not in first.lower() and "<foreignobject" not in first.lower()
    root = _parse(first)
    assert root.get("role") == "img" and root.get("viewBox")


def test_r3_reviewdesk_never_imports_storydesk():
    for path in REVIEWDESK.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(?:from|import)\s+storydesk\b", text, re.M), path.name
