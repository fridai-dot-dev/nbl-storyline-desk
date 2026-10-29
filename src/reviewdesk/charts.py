"""Small email-safe SVG charts for the Review Desk: donut, line and scatter.

Every chart is a plain, deterministic SVG with no script. Text in a chart holds only the
labels and numbers it was given (printed with ``str``): no computed ticks, totals or rounding.
Positions are computed, but they live in attributes, never in text.
"""

from __future__ import annotations

import math
import textwrap
from collections.abc import Sequence
from html import escape

WIDTH = 600
INK, POSITIVE, NEGATIVE, NEUTRAL = "#1f3a5f", "#3d7a4a", "#a04545", "#8a8a8a"
PALETTE = (INK, "#6f8fb3", NEUTRAL, "#b8b8b8", "#8fb59a", "#c49a9a", POSITIVE, NEGATIVE)
TEXT, MUTED, RULE = "#1a1a1a", "#5c5c5c", "#cfcfcf"
FONT = "Inter, Helvetica, Arial, sans-serif"


def _n(value: float) -> str:
    """A coordinate: one decimal at most, no trailing zero, never ``-0``."""
    return format(round(value, 1) + 0.0, "g")


def _esc(value: object) -> str:
    return escape(str(value), quote=True)


def _heading(title: str) -> tuple[str, float]:
    """The visible chart title, wrapped to the chart width, and the y where the drawing starts."""
    lines = textwrap.wrap(title, width=78, break_on_hyphens=False) or [title]
    text = "".join(
        f'<text x="16" y="{22 + 18 * index}" font-size="12" font-weight="600" fill="{TEXT}">{_esc(line)}</text>'
        for index, line in enumerate(lines)
    )
    return text, 16 + 18 * len(lines) + 12


def _svg(chart: str, height: float, title: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" data-chart="{chart}" role="img" '
        f'viewBox="0 0 {WIDTH} {_n(height)}" width="{WIDTH}" height="{_n(height)}" font-family="{FONT}">'
        f'<title>{_esc(title)}</title><rect width="{WIDTH}" height="{_n(height)}" fill="#fff"/>{body}</svg>\n'
    )


def _text(x: float, y: float, content: object, *, size: int = 12, fill: str = TEXT, anchor: str = "start",
          weight: str = "400", extra: str = "") -> str:
    return (f'<text x="{_n(x)}" y="{_n(y)}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{extra}>{_esc(content)}</text>')


def _span(low: float, high: float, share: float = 0.15) -> tuple[float, float]:
    """Pad a data range so points never sit on the frame; a flat range gets a unit of room."""
    pad = (high - low) * share or 0.5
    return low - pad, high + pad


def render_donut(slices: Sequence[tuple[str, float]], *, title: str, centre_label: str, unit: str = "") -> str:
    head, top = _heading(title)
    cx, cy, outer, inner = 110.0, top + 100, 90.0, 56.0
    total = sum(value for _label, value in slices)
    angle = -math.pi / 2
    shapes, legend = [], []
    legend_top = max(top, cy - 13 * len(slices))
    for index, (label, value) in enumerate(slices):
        colour = PALETTE[index % len(PALETTE)]
        sweep = min(2 * math.pi * value / total, 2 * math.pi - 1e-4) if total else 0.0
        end = angle + sweep
        large = 1 if sweep > math.pi else 0

        def point(radius: float, theta: float) -> str:
            return f"{_n(cx + radius * math.cos(theta))},{_n(cy + radius * math.sin(theta))}"

        shapes.append(
            f'<path class="slice" fill="{colour}" stroke="#fff" stroke-width="2" '
            f'd="M{point(outer, angle)} A{_n(outer)},{_n(outer)} 0 {large} 1 {point(outer, end)} '
            f'L{point(inner, end)} A{_n(inner)},{_n(inner)} 0 {large} 0 {point(inner, angle)} Z"/>'
        )
        row = legend_top + 13 + 26 * index
        legend.append(f'<rect x="240" y="{_n(row - 11)}" width="12" height="12" fill="{colour}"/>'
                      + _text(260, row, f"{label} {value}{unit}", size=14))
        angle = end
    centre = _text(cx, cy + 5, centre_label, size=14, weight="600", anchor="middle")
    height = max(cy + outer, legend_top + 26 * len(slices)) + 16
    return _svg("donut", height, title, head + "".join(shapes) + centre + "".join(legend))


def render_line(points: Sequence[tuple[str, float]], *, title: str, baseline: float, baseline_label: str) -> str:
    head, top = _heading(title)
    left, right = 44.0, 556.0
    plot_top, plot_bottom = top + 34, top + 174
    values = [value for _label, value in points]
    low, high = _span(min([*values, baseline]), max([*values, baseline]))

    def y_of(value: float) -> float:
        return plot_bottom - (value - low) / (high - low) * (plot_bottom - plot_top)

    def x_of(index: int) -> float:
        return left + (right - left) * index / (len(points) - 1) if len(points) > 1 else (left + right) / 2

    base_y = y_of(baseline)
    body = [
        head,
        f'<line class="axis" x1="{_n(left)}" y1="{_n(plot_bottom)}" x2="{_n(right)}" y2="{_n(plot_bottom)}" stroke="{RULE}"/>',
        f'<line class="baseline" x1="{_n(left)}" y1="{_n(base_y)}" x2="{_n(right)}" y2="{_n(base_y)}" '
        f'stroke="{NEUTRAL}" stroke-width="1.5" stroke-dasharray="6 4"/>',
        _text(right, base_y - 7, baseline_label, size=12, fill=MUTED, anchor="end",
              extra=' stroke="#fff" stroke-width="3" paint-order="stroke"'),
        '<polyline class="series" fill="none" stroke="%s" stroke-width="2.5" stroke-linejoin="round" points="%s"/>'
        % (INK, " ".join(f"{_n(x_of(i))},{_n(y_of(v))}" for i, v in enumerate(values))),
    ]
    marked = {0, len(points) - 1}
    for index, (label, value) in enumerate(points):
        x, y = x_of(index), y_of(value)
        body.append(f'<circle class="dot" cx="{_n(x)}" cy="{_n(y)}" r="3.5" fill="{INK}"/>')
        body.append(_text(x, plot_bottom + 22, label, fill=MUTED, anchor="middle"))
        if index in marked:
            body.append(_text(x, y - 10, value, size=13, fill=INK, anchor="middle", weight="600",
                              extra=' stroke="#fff" stroke-width="3" paint-order="stroke"'))
    return _svg("line", plot_bottom + 38, title, "".join(body))


def render_scatter(points: Sequence[tuple[str, float, float]], *, title: str, x_label: str, y_label: str) -> str:
    head, top = _heading(title)
    left, right = 70.0, 570.0
    plot_top, plot_bottom = top + 10, top + 250
    xs, ys = [x for _l, x, _y in points], [y for _l, _x, y in points]
    x_low, x_high = _span(min(xs), max(xs), 0.12)
    y_low, y_high = _span(min(ys), max(ys), 0.12)
    body = [
        head,
        f'<line class="axis" x1="{_n(left)}" y1="{_n(plot_top)}" x2="{_n(left)}" y2="{_n(plot_bottom)}" stroke="{MUTED}"/>',
        f'<line class="axis" x1="{_n(left)}" y1="{_n(plot_bottom)}" x2="{_n(right)}" y2="{_n(plot_bottom)}" stroke="{MUTED}"/>',
        _text((left + right) / 2, plot_bottom + 34, x_label, size=13, fill=MUTED, anchor="middle"),
        _text(18, (plot_top + plot_bottom) / 2, y_label, size=13, fill=MUTED, anchor="middle",
              extra=f' transform="rotate(-90 18 {_n((plot_top + plot_bottom) / 2)})"'),
    ]
    for label, x, y in points:
        px = left + (x - x_low) / (x_high - x_low) * (right - left)
        py = plot_bottom - (y - y_low) / (y_high - y_low) * (plot_bottom - plot_top)
        body.append(f'<circle class="point" cx="{_n(px)}" cy="{_n(py)}" r="6" fill="{INK}" fill-opacity="0.85"/>')
        body.append(_text(px + 10, py - 8, label, size=12, fill=TEXT))
    return _svg("scatter", plot_bottom + 46, title, "".join(body))
