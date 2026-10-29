"""Small dependency-free SVG charts used in packets and finding pages."""

from __future__ import annotations

from html import escape
import math
import re
import xml.etree.ElementTree as ET
from typing import Iterable


SVG_NS = "http://www.w3.org/2000/svg"


def _validate(labels: list[str], values: list[float], highlight_index: int) -> None:
    if not labels or len(labels) != len(values):
        raise ValueError("labels and values must be non-empty and equally sized")
    if not 0 <= highlight_index < len(labels):
        raise ValueError("highlight_index is outside the data")


def _text(x: float, y: float, value: str, *, anchor: str = "middle") -> str:
    return f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}">{escape(value)}</text>'


_SEASON = re.compile(r"^(\d{4})-(\d{4})$")


def _display_label(label: str) -> str:
    """Keep dense season axes legible without changing the underlying category."""
    if match := _SEASON.fullmatch(label):
        return f"{match.group(1)[-2:]}-{match.group(2)[-2:]}"
    return label


_GLYPH = 7.0       # generous width of a 12px system-font glyph, so labels never touch the edge
_DIAGONAL = 0.7071
_ANCHOR = 12       # rotated labels hang this far below the axis
_PAD = 6
_COMPACT_WIDTH = 480


def _shorten(label: str, max_chars: int) -> str:
    return label if len(label) <= max_chars else f"{label[:max(max_chars - 1, 1)].rstrip()}…"


def _axis_label(x: float, y: float, label: str, *, rotate: bool) -> str:
    if not rotate:
        return f'<text x="{x:.2f}" y="{y + 4:.2f}" text-anchor="middle" data-axis-label="x">{escape(label)}</text>'
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="end" '
        f'transform="rotate(-45 {x:.2f} {y:.2f})" data-axis-label="x">{escape(label)}</text>'
    )


def _axis_layout(
    labels: list[str], width: int, height: int, left: int, right: int, top: int,
) -> tuple[bool, int, int, list[str]]:
    """Rotate labels only when they overflow their slot, and shorten them only when the canvas can't hold them.

    Returns whether to rotate, the bottom margin, the left margin and the labels to display."""
    slot = (width - left - right) / len(labels)
    min_plot = max(70, round((height - top) / 3))
    if len(labels) <= 2 or all(len(label) * _GLYPH <= slot for label in labels):
        fitted = [_shorten(label, max(3, int(slot / _GLYPH))) for label in labels]
        return False, min(68, height - top - min_plot), left, fitted
    # Rotated, right-aligned labels reach down and to the left of their anchor by the same diagonal amount.
    room = height - top - min_plot - _ANCHOR - _PAD
    fitted = [_shorten(label, max(3, int(room / (_GLYPH * _DIAGONAL)))) for label in labels]
    reach = max(len(label) for label in fitted) * _GLYPH * _DIAGONAL
    bottom = math.ceil(reach + _ANCHOR + _PAD)
    adjusted_left = min(max(left, math.ceil(reach + _PAD)), width - right - 100)
    return True, bottom, adjusted_left, fitted


def _y_label(y_label: str | None, width: int) -> str:
    return _text(16, 22, _shorten(y_label or "Value", int((width - 20) / 6.5)), anchor="start")


def render_bar_chart(
    title: str,
    labels: Iterable[str],
    values: Iterable[float],
    highlight_index: int,
    y_label: str | None = None,
    *,
    width: int = 680,
    height: int = 340,
) -> str:
    labels, values = list(labels), [float(value) for value in values]
    _validate(labels, values, highlight_index)
    left, right, top = 56, 20, 38
    rotate_labels, bottom, left, display_labels = _axis_layout(
        [_display_label(str(label)) for label in labels], width, height, left, right, top,
    )
    compact = width < _COMPACT_WIDTH
    baseline = height - bottom
    max_value = max(max(values), 0.0)
    min_value = min(min(values), 0.0)
    span = max(max_value - min_value, 1.0)
    baseline = top + (max_value / span) * (height - top - bottom)
    usable_width = width - left - right
    slot = usable_width / len(labels)
    bar_width = slot * 0.62
    marks, labels_svg = [], []
    for index, (label, display_label, value) in enumerate(zip(labels, display_labels, values)):
        x = left + slot * index + (slot - bar_width) / 2
        y_value = top + ((max_value - value) / span) * (height - top - bottom)
        y, bar_height = (y_value, baseline - y_value) if value >= 0 else (baseline, y_value - baseline)
        css = "bar highlight" if index == highlight_index else "bar muted"
        marks.append(
            f'<rect class="{css}" x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
            f'data-label="{escape(str(label))}" data-value="{value}"/>'
        )
        if index == highlight_index or not compact:  # compact charts name only the highlighted value
            marks.append(_text(x + bar_width / 2, y - 6 if value >= 0 else y + bar_height + 14, f"{value:g}"))
        labels_svg.append(_axis_label(x + bar_width / 2, baseline + _ANCHOR, display_label, rotate=rotate_labels))
    ylabel = _y_label(y_label, width)
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(title)}" data-baseline="{baseline:.2f}" data-label-room="{bottom}">'
        f'<title>{escape(title)}</title><style>.bar{{fill:#2667a0}}rect.muted{{opacity:.28}}.highlight{{opacity:1}}'
        f'@media (prefers-color-scheme:dark){{rect.muted{{fill:#78b9e6;opacity:.74}}rect.highlight{{fill:#a8dcff}}}}'
        f'text{{font:12px system-ui,sans-serif;fill:currentColor}}.axis{{stroke:#94a3b8}}</style>'
        f'<line class="axis" x1="{left}" y1="{baseline:.2f}" x2="{width-right}" y2="{baseline:.2f}"/>{ylabel}'
        f'{"".join(marks)}{"".join(labels_svg)}</svg>'
    )


def render_line_chart(
    title: str,
    labels: Iterable[str],
    values: Iterable[float],
    highlight_index: int,
    y_label: str | None = None,
    *,
    width: int = 680,
    height: int = 340,
) -> str:
    labels, values = list(labels), [float(value) for value in values]
    _validate(labels, values, highlight_index)
    left, right, top = 56, 20, 38
    rotate_labels, bottom, left, display_labels = _axis_layout(
        [_display_label(str(label)) for label in labels], width, height, left, right, top,
    )
    compact = width < _COMPACT_WIDTH
    baseline = height - bottom
    minimum, maximum = min(values), max(values)
    span = max(maximum - minimum, 1.0)
    usable_width = width - left - right
    step = usable_width / max(len(labels) - 1, 1)
    coordinates = [(left + index * step, top + ((maximum - value) / span) * (height - top - bottom)) for index, value in enumerate(values)]
    path = " ".join(f"{x:.2f},{y:.2f}" for x, y in coordinates)
    marks, labels_svg = [], []
    for index, ((x, y), label, display_label, value) in enumerate(zip(coordinates, labels, display_labels, values)):
        css = "point highlight" if index == highlight_index else "point muted"
        marks.append(f'<circle class="{css}" cx="{x:.2f}" cy="{y:.2f}" r="5" data-label="{escape(str(label))}" data-value="{value}"/>')
        if index == highlight_index or not compact:
            marks.append(_text(x, y - 10, f"{value:g}"))
        labels_svg.append(_axis_label(x, baseline + _ANCHOR, display_label, rotate=rotate_labels))
    ylabel = _y_label(y_label, width)
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(title)}" data-baseline="{baseline:.2f}" data-label-room="{bottom}">'
        f'<title>{escape(title)}</title><style>.line{{fill:none;stroke:#2667a0;stroke-width:3}}.point{{fill:#2667a0}}'
        f'circle.muted{{opacity:.32}}.highlight{{opacity:1}}'
        f'@media (prefers-color-scheme:dark){{circle.muted{{fill:#78b9e6;opacity:.72}}circle.highlight{{fill:#a8dcff}}}}'
        f'text{{font:12px system-ui,sans-serif;fill:currentColor}}.axis{{stroke:#94a3b8}}</style>'
        f'<line class="axis" x1="{left}" y1="{baseline}" x2="{width-right}" y2="{baseline}"/>{ylabel}'
        f'<polyline class="line" points="{path}"/>{"".join(marks)}{"".join(labels_svg)}</svg>'
    )


def render_paired_bar_chart(
    title: str,
    team_names: tuple[str, str] | list[str],
    measures: tuple[str, ...] | list[str],
    values: tuple[tuple[float, float], ...] | list[tuple[float, float]],
    *,
    width: int = 680,
    height: int = 340,
) -> str:
    """Render exactly two series for a team comparison, never a derived margin."""
    teams, labels, pairs = list(team_names), list(measures), [tuple(pair) for pair in values]
    if len(teams) != 2 or not labels or len(labels) != len(pairs) or any(len(pair) != 2 for pair in pairs):
        raise ValueError("paired bars require two teams and one two-value pair per measure")
    numeric = [float(value) for pair in pairs for value in pair]
    maximum = max(max(numeric), 1.0)
    left, right, top, bottom = 158, 46, 34, 30
    plot_width = width - left - right
    group_height = max(30, (height - top - bottom) / len(labels))
    bars, text = [], []
    for index, (measure, pair) in enumerate(zip(labels, pairs)):
        y = top + index * group_height
        text.append(_text(8, y + 15, str(measure), anchor="start"))
        for team_index, (team, value) in enumerate(zip(teams, pair)):
            value = float(value)
            bar_y = y + 20 + team_index * 13
            bar_width = plot_width * value / maximum
            fill = "#1f3a5f" if team_index == 0 else "#8a8a8a"
            bars.append(
                f'<rect x="{left}" y="{bar_y:.2f}" width="{bar_width:.2f}" height="10" fill="{fill}" '
                f'data-team="{escape(str(team))}" data-measure="{escape(str(measure))}" data-value="{value:g}"/>'
            )
            text.append(_text(left + bar_width + 5, bar_y + 9, f"{value:g}", anchor="start"))
    legend = (
        f'<text x="{left}" y="{height - 7}" text-anchor="start">{escape(str(teams[0]))}</text>'
        f'<text x="{left + max(120, len(teams[0]) * 8)}" y="{height - 7}" text-anchor="start">{escape(str(teams[1]))}</text>'
    )
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title)}"><title>{escape(title)}</title><style>'
        'text{font:12px Inter,system-ui,sans-serif;fill:#1a1a1a}'
        '</style>' + "".join(bars) + "".join(text) + legend + "</svg>"
    )


def render_test_result_chart(
    title: str,
    metric: str,
    threshold: float,
    direction: str,
    actual: float,
    outcome: str,
    *,
    width: int = 680,
    height: int = 150,
) -> str:
    """Show a checked result as a dot against a clearly labelled test line."""
    threshold, actual = float(threshold), float(actual)
    low, high = min(0.0, threshold, actual), max(1.0, threshold, actual)
    padding = max((high - low) * 0.12, 1.0)
    low, high = low - padding, high + padding
    left, right, y = 36, 36, 70
    scale = lambda value: left + (float(value) - low) / (high - low) * (width - left - right)
    line_x, actual_x = scale(threshold), scale(actual)
    colour = "#3d7a4a" if outcome == "confirmed" else "#a04545"
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title)}"><title>{escape(title)}</title><style>'
        'text{font:12px Inter,system-ui,sans-serif;fill:#1a1a1a}.axis{stroke:#cfcfcf;stroke-width:2}'
        '</style>'
        f'<text x="{left}" y="24" text-anchor="start">{escape(metric)}</text>'
        f'<line class="axis" x1="{left}" y1="{y}" x2="{width-right}" y2="{y}"/>'
        f'<line class="test-line" x1="{line_x:.2f}" y1="44" x2="{line_x:.2f}" y2="96" stroke="#000" stroke-width="2"/>'
        f'<text x="{line_x + 5:.2f}" y="112" text-anchor="start">test line: {threshold:g}</text>'
        f'<circle cx="{actual_x:.2f}" cy="{y}" r="7" fill="{colour}" data-actual="{actual:g}"/>'
        f'<text x="{actual_x:.2f}" y="{y - 13}" text-anchor="middle">{actual:g}</text></svg>'
    )


def check_chart(svg: str, expected_title: str) -> list[str]:
    problems: list[str] = []
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return ["invalid SVG"]
    tag = root.tag.split("}")[-1]
    if tag != "svg":
        return ["root is not svg"]
    children = list(root)
    if not children or children[0].tag.split("}")[-1] != "title" or children[0].text != expected_title:
        problems.append("title is missing or incorrect")
    try:
        baseline = float(root.attrib["data-baseline"])
    except (KeyError, ValueError):
        problems.append("baseline is missing")
        baseline = math.nan
    marks = [node for node in root.iter() if node.attrib.get("data-label") is not None]
    if not marks:
        problems.append("no labelled marks")
        return problems
    highlights = [node for node in marks if "highlight" in node.attrib.get("class", "").split()]
    if len(highlights) != 1:
        problems.append("chart needs exactly one highlight")
    texts = [node.text or "" for node in root.iter() if node.tag.split("}")[-1] == "text"]
    visible = " ".join(texts)
    shortened = [text for text in texts if text.endswith("…")]
    for mark in marks:
        label, value = mark.attrib.get("data-label"), mark.attrib.get("data-value")
        if value is None:
            problems.append("mark lacks data-value")
        if label not in visible and _display_label(label) not in visible and not any(
            text.endswith("…") and _display_label(label).startswith(text[:-1]) for text in shortened
        ):
            problems.append(f"label {label!r} is not visible")
        if mark.tag.split("}")[-1] == "rect":
            try:
                if not math.isclose(float(mark.attrib["y"]) + float(mark.attrib["height"]), baseline, abs_tol=0.01):
                    problems.append("bar does not start at zero")
            except (KeyError, ValueError):
                problems.append("bar geometry is invalid")
    return problems
