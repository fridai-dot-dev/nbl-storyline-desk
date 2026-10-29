"""R1 chart checks limited to the approved paired-bar and result-against-test-line forms (rows 23-24)."""

from __future__ import annotations

import xml.etree.ElementTree as ET


# Assumed renderer signatures:
# render_paired_bar_chart(title, team_names, measures, values, *, width=..., height=...)
# render_test_result_chart(title, metric, threshold, direction, actual, outcome, *, width=..., height=...)


def _local(node) -> str:
    return node.tag.split("}")[-1]


def test_r1_row_23_two_team_comparison_is_paired_bars_with_no_advantage_series():
    import storydesk.charts as charts

    render = getattr(charts, "render_paired_bar_chart", None)
    assert callable(render), "paired two-team bar renderer is missing"
    svg = render(
        "Where each team scored",
        team_names=("Adelaide 36ers", "Melbourne United"),
        measures=("Points from three", "Points from two"),
        values=((39, 38), (21, 58)),
        width=600,
        height=260,
    )
    root = ET.fromstring(svg)
    bars = [node for node in root.iter() if _local(node) == "rect" and node.get("data-team")]
    assert len(bars) == 4
    assert {node.get("data-team") for node in bars} == {"Adelaide 36ers", "Melbourne United"}
    assert {node.get("data-measure") for node in bars} == {"Points from three", "Points from two"}
    for measure in ("Points from three", "Points from two"):
        assert len([node for node in bars if node.get("data-measure") == measure]) == 2
    assert "advantage" not in svg.lower()


def test_r1_row_24_result_chart_has_solid_two_pixel_labelled_test_line():
    import storydesk.charts as charts

    render = getattr(charts, "render_test_result_chart", None)
    assert callable(render), "result-against-test renderer is missing"
    svg = render(
        "Did Cotton stay below the line?",
        metric="Bryce Cotton points",
        threshold=21,
        direction="at_most",
        actual=26,
        outcome="contradicted",
        width=600,
        height=150,
    )
    root = ET.fromstring(svg)
    lines = [node for node in root.iter() if _local(node) == "line" and "test-line" in node.get("class", "").split()]
    assert len(lines) == 1
    line = lines[0]
    assert line.get("stroke-width") in {"2", "2px"}
    assert line.get("stroke-dasharray") in {None, "", "none"}
    styles = " ".join((node.text or "") for node in root.iter() if _local(node) == "style").lower()
    assert "test-line" not in styles or "stroke-dasharray" not in styles
    visible = " ".join((node.text or "") for node in root.iter() if _local(node) == "text")
    assert "test line" in visible.lower() and "21" in visible
