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
    highlight_index: int | None,
    y_label: str | None = None,
    *,
    width: int = 680,
    height: int = 340,
    reference: float | None = None,
    reference_label: str | None = None,
) -> str:
    """A line over the given categories.

    With `reference` the chart is drawn in the Agora form instead (palette colours on a white plate, sparse date
    ticks, a dashed reference line at that value); `highlight_index` may then be None. Without it the output is
    the original theme-following chart, unchanged."""
    if reference is not None:
        return _render_trend_chart(title, list(labels), list(values), highlight_index, y_label, reference,
                                   reference_label, width=width, height=height)
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


# ---------------------------------------------------------------------------------------------------------------
# Agora charts for the post-run findings: a donut, a scatter and a dense trend line. They use only the design's
# palette tokens on a white plate and carry data-* attributes. Colours and fonts are inline `style`/attributes on
# elements with no class, because the older charts' <style> blocks are global once they sit inline on a page.

_INK, _NEUTRAL, _NEGATIVE, _POSITIVE = "#1f3a5f", "#8a8a8a", "#a04545", "#3d7a4a"
_TEXT, _MUTED, _BORDER, _PLATE = "#1a1a1a", "#6b6b6b", "#d9d9d9", "#ffffff"
_SLICES = (_INK, _NEUTRAL, _POSITIVE, _NEGATIVE)
_FONT = "font-family:Inter,system-ui,sans-serif"
_HALO = f"paint-order:stroke;stroke:{_PLATE};stroke-width:3px;stroke-linejoin:round"


def _num(value: float) -> str:
    """A full-precision number for a data-* attribute (39, not 39.0)."""
    value = float(value)
    return str(int(value)) if value.is_integer() else repr(value)


def _fmt(value: float) -> str:
    """A number as a reader sees it: 1,310 and 21.21."""
    value = float(value)
    return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}".rstrip("0").rstrip(".")


def _finite(values: Iterable[float], what: str) -> list[float]:
    numbers = [float(value) for value in values]
    if not all(math.isfinite(number) for number in numbers):
        raise ValueError(f"{what} must be finite numbers")
    return numbers


def _data(**attributes: object) -> str:
    return "".join(f' data-{name.replace("_", "-")}="{escape(str(value))}"' for name, value in attributes.items() if value is not None)


def _atext(x: float, y: float, content: str, *, anchor: str = "middle", size: int = 12, weight: int = 400,
           fill: str = _TEXT, halo: bool = False, **data: object) -> str:
    style = f"{_FONT};font-size:{size}px;font-weight:{weight};fill:{fill}" + (f";{_HALO}" if halo else "")
    return f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" style="{style}"{_data(**data)}>{escape(content)}</text>'


def _plate(kind: str, title: str, width: int, height: int, body: str, **root_data: object) -> str:
    """The shared frame: title element, white plate with a hairline border, and a visible heading."""
    heading = _atext(16, 24, _shorten(title, int((width - 32) / 7.6)), anchor="start", size=14, weight=600, mark="heading")
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title)}" data-chart="{kind}"{_data(**root_data)}><title>{escape(title)}</title>'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" fill="{_PLATE}" stroke="{_BORDER}"/>'
        f"{heading}{body}</svg>"
    )


def _nice_ticks(low: float, high: float, target: int = 5) -> list[float]:
    """Round tick values that cover [low, high]."""
    span = high - low if high > low else max(abs(high), 1.0)
    raw = span / max(target, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if raw <= m * magnitude)
    first = math.floor(low / step + 1e-9)
    last = math.ceil(high / step - 1e-9)
    if last == first:
        last += 1
    return [round(index * step, 10) for index in range(first, last + 1)]


def _axes(left: float, right: float, top: float, bottom: float, y_ticks: list[float], y_at, width: int, height: int,
          y_label: str | None) -> list[str]:
    """Horizontal gridlines, the value labels beside them and the y-axis name above the plot."""
    parts = []
    for tick in y_ticks:
        y = y_at(tick)
        parts.append(f'<line x1="{left:.2f}" y1="{y:.2f}" x2="{width - right:.2f}" y2="{y:.2f}" stroke="{_BORDER}" stroke-width="1"/>')
        parts.append(_atext(left - 8, y + 4, _fmt(tick), anchor="end", fill=_MUTED, axis_label="y"))
    if y_label:
        parts.append(_atext(left, top - 12, _shorten(y_label, int((width - left) / 7)), anchor="start", fill=_MUTED, mark="y-label"))
    return parts


def _check_highlight(highlight_index: int | None, count: int) -> None:
    if highlight_index is not None and not 0 <= highlight_index < count:
        raise ValueError("highlight_index is outside the data")


def render_donut_chart(
    title: str,
    labels: Iterable[str],
    values: Iterable[float],
    highlight_index: int | None = None,
    y_label: str | None = None,
    *,
    width: int = 600,
    height: int = 300,
) -> str:
    """Parts of a whole: one arc per slice, a label per slice, and the total in the middle.

    `y_label` names the unit under the total. A slice of zero has no arc and no label."""
    labels, values = [str(label) for label in labels], _finite(values, "slice values")
    if not labels or len(labels) != len(values):
        raise ValueError("labels and values must be non-empty and equally sized")
    if any(value < 0 for value in values) or sum(values) <= 0:
        raise ValueError("slice values must not be negative and must have a positive total")
    _check_highlight(highlight_index, len(labels))
    total = sum(values)
    radius = min((height - 40) / 2 - 8, 110.0)
    inner = radius * 0.6
    cx, cy = 24 + radius + 16, 36 + (height - 36) / 2
    shown = [index for index, value in enumerate(values) if value > 0]

    def point(angle: float, rad: float) -> str:
        theta = math.radians(angle)
        return f"{cx + rad * math.sin(theta):.2f} {cy - rad * math.cos(theta):.2f}"

    arcs, rows, start = [], [], 0.0
    legend_x = cx + radius + 48
    legend_top = cy - (len(shown) - 1) * 14
    for position, index in enumerate(shown):
        colour = _SLICES[position % len(_SLICES)]
        span = values[index] / total * 360
        end = start + span
        if len(shown) == 1:   # a single slice is a whole ring, which one SVG arc cannot draw
            d = (f"M {point(0, radius)} A {radius:.2f} {radius:.2f} 0 1 1 {point(180, radius)} "
                 f"A {radius:.2f} {radius:.2f} 0 1 1 {point(360, radius)} Z "
                 f"M {point(0, inner)} A {inner:.2f} {inner:.2f} 0 1 0 {point(180, inner)} "
                 f"A {inner:.2f} {inner:.2f} 0 1 0 {point(360, inner)} Z")
        else:
            large = int(span > 180)
            d = (f"M {point(start, radius)} A {radius:.2f} {radius:.2f} 0 {large} 1 {point(end, radius)} "
                 f"L {point(end, inner)} A {inner:.2f} {inner:.2f} 0 {large} 0 {point(start, inner)} Z")
        picked = index == highlight_index
        arcs.append(
            f'<path d="{d}" fill="{colour}" fill-rule="evenodd" stroke="{_PLATE}" stroke-width="2"'
            f'{_data(mark="slice", label=labels[index], value=_num(values[index]), highlight="true" if picked else None)}>'
            f"<title>{escape(labels[index])}: {_fmt(values[index])}</title></path>"
        )
        row_y = legend_top + position * 28
        rows.append(f'<rect x="{legend_x:.2f}" y="{row_y - 10:.2f}" width="12" height="12" fill="{colour}"/>')
        rows.append(_atext(legend_x + 20, row_y, f"{labels[index]}: {_fmt(values[index])}", anchor="start", size=13,
                           weight=600 if picked else 400, mark="slice-label", label=labels[index], value=_num(values[index])))
        start = end
    centre = [_atext(cx, cy + 6, _fmt(total), size=22, weight=600, mark="total")]
    if y_label:
        centre.append(_atext(cx, cy + 24, _shorten(y_label, int(inner * 1.6 / 7)), fill=_MUTED, mark="unit"))
    return _plate("donut", title, width, height, "".join(arcs) + "".join(rows) + "".join(centre),
                  total=_num(total), cx=f"{cx:.2f}", cy=f"{cy:.2f}")


def render_scatter_chart(
    title: str,
    labels: Iterable[str],
    xs: Iterable[float],
    ys: Iterable[float],
    highlight_index: int | None = None,
    x_label: str | None = None,
    y_label: str | None = None,
    *,
    width: int = 600,
    height: int = 360,
) -> str:
    """Two measures across many items: one circle per row, and the highlighted row drawn last in its own colour."""
    labels, xs, ys = [str(label) for label in labels], _finite(xs, "x values"), _finite(ys, "y values")
    if not labels or not len(labels) == len(xs) == len(ys):
        raise ValueError("labels, xs and ys must be non-empty and equally sized")
    _check_highlight(highlight_index, len(labels))
    left, right, top, bottom = 52, 22, 56, 56
    x_ticks, y_ticks = _nice_ticks(min(xs), max(xs)), _nice_ticks(min(ys), max(ys))
    x_low, x_high, y_low, y_high = x_ticks[0], x_ticks[-1], y_ticks[0], y_ticks[-1]
    x_at = lambda value: left + (value - x_low) / (x_high - x_low) * (width - left - right)
    y_at = lambda value: top + (y_high - value) / (y_high - y_low) * (height - top - bottom)
    parts = _axes(left, right, top, bottom, y_ticks, y_at, width, height, y_label)
    parts.append(f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" y2="{height - bottom}" stroke="{_NEUTRAL}" stroke-width="1"/>')
    for tick in x_ticks:
        parts.append(_atext(x_at(tick), height - bottom + 18, _fmt(tick), fill=_MUTED, axis_label="x"))
    if x_label:
        parts.append(_atext((left + width - right) / 2, height - 14, _shorten(x_label, 60), fill=_MUTED, mark="x-label"))
    order = [index for index in range(len(labels)) if index != highlight_index]
    if highlight_index is not None:
        order.append(highlight_index)   # last, so it sits on top of the crowd
    for index in order:
        picked = index == highlight_index
        parts.append(
            f'<circle cx="{x_at(xs[index]):.2f}" cy="{y_at(ys[index]):.2f}" r="{6 if picked else 3.5}" '
            f'fill="{_NEGATIVE if picked else _INK}"'
            + (f' stroke="{_PLATE}" stroke-width="1.5"' if picked else ' fill-opacity="0.4"')
            + f'{_data(mark="dot", label=labels[index], x=_num(xs[index]), y=_num(ys[index]), highlight="true" if picked else None)}>'
            f"<title>{escape(labels[index])}</title></circle>"
        )
    if highlight_index is not None:
        px, py = x_at(xs[highlight_index]), y_at(ys[highlight_index])
        text = _shorten(labels[highlight_index], 44)
        right_side = px > width * 0.55
        label_y = top + 14
        parts.insert(0, f'<line x1="{px:.2f}" y1="{py:.2f}" x2="{px:.2f}" y2="{label_y + 4:.2f}" stroke="{_NEGATIVE}" stroke-width="1"/>')
        parts.append(_atext(px + 6 if right_side else px - 6, label_y, text, anchor="end" if right_side else "start",
                            weight=600, halo=True, mark="highlight-label"))
    return _plate("scatter", title, width, height, "".join(parts), n=len(labels))


def _render_trend_chart(
    title: str,
    labels: list[str],
    values: list[float],
    highlight_index: int | None,
    y_label: str | None,
    reference: float,
    reference_label: str | None,
    *,
    width: int,
    height: int,
) -> str:
    labels, values, reference = [str(label) for label in labels], _finite(values, "values"), float(reference)
    if not labels or len(labels) != len(values):
        raise ValueError("labels and values must be non-empty and equally sized")
    if not math.isfinite(reference):
        raise ValueError("reference must be a finite number")
    _check_highlight(highlight_index, len(labels))
    left, right, top, bottom = 48, 100, 56, 44   # the right margin holds the reference label
    ticks = _nice_ticks(min(0.0, min(values), reference), max(max(values), reference))
    low, high = ticks[0], ticks[-1]
    y_at = lambda value: top + (high - value) / (high - low) * (height - top - bottom)
    plot = width - left - right
    step = plot / max(len(values) - 1, 1)
    x_at = lambda index: left + (index * step if len(values) > 1 else plot / 2)
    parts = _axes(left, right, top, bottom, ticks, y_at, width, height, y_label)
    parts.append(f'<line x1="{left}" y1="{y_at(low):.2f}" x2="{width - right}" y2="{y_at(low):.2f}" stroke="{_NEUTRAL}" stroke-width="1"/>')
    # Sparse x ticks, always the first and last (anchored inward so they stay inside the plate), so dense
    # date labels never collide or need rotating.
    slot = max(len(label) for label in labels) * 7.0 + 40
    count = min(len(labels), max(2, int(plot // slot) + 1))
    last = len(labels) - 1
    for index in sorted({round(k * last / max(count - 1, 1)) for k in range(count)}):
        anchor = "start" if index == 0 and last else "end" if index == last and last else "middle"
        parts.append(_atext(x_at(index), height - bottom + 18, labels[index], anchor=anchor, fill=_MUTED, axis_label="x"))
    ref_y = y_at(reference)
    parts.append(
        f'<line x1="{left}" y1="{ref_y:.2f}" x2="{width - right}" y2="{ref_y:.2f}" stroke="{_NEUTRAL}" stroke-width="1.5" '
        f'stroke-dasharray="6 4"{_data(mark="reference", value=_num(reference))}/>'
    )
    parts.append(_atext(width - right + 8, ref_y + 4, _shorten(reference_label or _fmt(reference), 14), anchor="start",
                        weight=600, mark="reference-label"))
    path = " ".join(f"{x_at(index):.2f},{y_at(value):.2f}" for index, value in enumerate(values))
    parts.append(f'<polyline points="{path}" fill="none" stroke="{_INK}" stroke-width="2" stroke-linejoin="round"{_data(mark="series")}/>')
    for index, (label, value) in enumerate(zip(labels, values)):
        picked = index == highlight_index
        parts.append(
            f'<circle cx="{x_at(index):.2f}" cy="{y_at(value):.2f}" r="{5 if picked else 3}" fill="{_NEGATIVE if picked else _INK}"'
            f'{_data(mark="point", label=label, value=_num(value), highlight="true" if picked else None)}>'
            f"<title>{escape(label)}: {_fmt(value)}</title></circle>"
        )
        if picked:
            parts.append(_atext(x_at(index), y_at(value) - 11, _fmt(value), weight=600, halo=True, mark="highlight-label"))
    return _plate("line", title, width, height, "".join(parts), reference=_num(reference), n=len(values))


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
