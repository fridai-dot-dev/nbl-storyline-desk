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


def _axis_label(x: float, y: float, label: str, *, rotate: bool) -> str:
    if not rotate:
        return _text(x, y, label)
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="end" '
        f'transform="rotate(-45 {x:.2f} {y:.2f})">{escape(label)}</text>'
    )


def render_bar_chart(title: str, labels: Iterable[str], values: Iterable[float], highlight_index: int, y_label: str | None = None) -> str:
    labels, values = list(labels), [float(value) for value in values]
    _validate(labels, values, highlight_index)
    display_labels = [_display_label(str(label)) for label in labels]
    rotate_labels = any(len(label) > 8 for label in display_labels)
    width, height, left, right, top, bottom = 680, 340, 56, 20, 38, 68
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
        marks.append(_text(x + bar_width / 2, y - 6 if value >= 0 else y + bar_height + 14, f"{value:g}"))
        labels_svg.append(_axis_label(x + bar_width / 2, height - 30, display_label, rotate=rotate_labels))
    ylabel = _text(16, 22, y_label or "Value", anchor="start")
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(title)}" data-baseline="{baseline:.2f}">'
        f'<title>{escape(title)}</title><style>.bar{{fill:#2667a0}}.muted{{opacity:.28}}.highlight{{opacity:1}}'
        f'text{{font:12px system-ui,sans-serif;fill:#475569}}.axis{{stroke:#94a3b8}}</style>'
        f'<line class="axis" x1="{left}" y1="{baseline:.2f}" x2="{width-right}" y2="{baseline:.2f}"/>{ylabel}'
        f'{"".join(marks)}{"".join(labels_svg)}</svg>'
    )


def render_line_chart(title: str, labels: Iterable[str], values: Iterable[float], highlight_index: int, y_label: str | None = None) -> str:
    labels, values = list(labels), [float(value) for value in values]
    _validate(labels, values, highlight_index)
    display_labels = [_display_label(str(label)) for label in labels]
    rotate_labels = any(len(label) > 8 for label in display_labels)
    width, height, left, right, top, bottom = 680, 340, 56, 20, 38, 68
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
        marks.append(_text(x, y - 10, f"{value:g}"))
        labels_svg.append(_axis_label(x, height - 30, display_label, rotate=rotate_labels))
    ylabel = _text(16, 22, y_label or "Value", anchor="start")
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(title)}" data-baseline="{baseline:.2f}">'
        f'<title>{escape(title)}</title><style>.line{{fill:none;stroke:#2667a0;stroke-width:3}}.point{{fill:#2667a0}}'
        f'.muted{{opacity:.32}}.highlight{{opacity:1}}text{{font:12px system-ui,sans-serif;fill:#475569}}.axis{{stroke:#94a3b8}}</style>'
        f'<line class="axis" x1="{left}" y1="{baseline}" x2="{width-right}" y2="{baseline}"/>{ylabel}'
        f'<polyline class="line" points="{path}"/>{"".join(marks)}{"".join(labels_svg)}</svg>'
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
    visible = " ".join((node.text or "") for node in root.iter() if node.tag.split("}")[-1] == "text")
    for mark in marks:
        label, value = mark.attrib.get("data-label"), mark.attrib.get("data-value")
        if value is None:
            problems.append("mark lacks data-value")
        if label not in visible and _display_label(label) not in visible:
            problems.append(f"label {label!r} is not visible")
        if mark.tag.split("}")[-1] == "rect":
            try:
                if not math.isclose(float(mark.attrib["y"]) + float(mark.attrib["height"]), baseline, abs_tol=0.01):
                    problems.append("bar does not start at zero")
            except (KeyError, ValueError):
                problems.append("bar geometry is invalid")
    return problems
