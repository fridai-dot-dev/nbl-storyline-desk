"""D4: every chart states the claim as its title, labels every mark, highlights this game, starts bars at zero."""
import xml.etree.ElementTree as ET


def _strip(tag):
    return tag.split("}", 1)[-1]


def _parse(svg):
    root = ET.fromstring(svg)
    assert _strip(root.tag) == "svg"
    return root, list(root.iter())


TITLE = "Adelaide scored 26 points in the third quarter"
LABELS = ["Q1", "Q2", "Q3", "Q4"]
VALUES = [25, 24, 26, 22]


def test_bar_chart_follows_the_rule():
    from storydesk.charts import check_chart, render_bar_chart

    svg = render_bar_chart(TITLE, LABELS, VALUES, highlight_index=2, y_label="Adelaide points")
    root, nodes = _parse(svg)
    titles = [n.text for n in nodes if _strip(n.tag) == "title"]
    assert titles and titles[0] == TITLE

    marks = [n for n in nodes if n.get("data-label") is not None]
    assert [m.get("data-label") for m in marks] == LABELS
    assert [float(m.get("data-value")) for m in marks] == [float(v) for v in VALUES]
    highlighted = [m for m in marks if "highlight" in (m.get("class") or "").split()]
    assert len(highlighted) == 1 and highlighted[0].get("data-label") == "Q3"

    texts = " ".join((n.text or "") for n in nodes if _strip(n.tag) == "text")
    for label in LABELS:
        assert label in texts

    baseline = float(root.get("data-baseline"))
    for m in marks:
        assert _strip(m.tag) == "rect"
        assert abs(float(m.get("y")) + float(m.get("height")) - baseline) < 0.01  # bars start at zero

    assert check_chart(svg, TITLE) == []
    assert check_chart(svg, "A different claim") != []


def test_line_chart_follows_the_rule():
    from storydesk.charts import check_chart, render_line_chart

    rate = [98.0, 96.0, 101.0, 107.0, 112.0, 115.0]
    svg = render_line_chart("United conceded 115 points per 100 possessions", [f"R{i}" for i in range(1, 7)],
                            rate, highlight_index=5, y_label="Points per 100 possessions")
    _, nodes = _parse(svg)
    points = [n for n in nodes if n.get("data-label") is not None]
    assert len(points) == 6
    assert sum("highlight" in (p.get("class") or "").split() for p in points) == 1
    assert check_chart(svg, "United conceded 115 points per 100 possessions") == []


def test_check_chart_catches_broken_charts():
    from storydesk.charts import check_chart

    no_title = '<svg xmlns="http://www.w3.org/2000/svg" data-baseline="100"><rect data-label="Q1" data-value="5" class="highlight" y="95" height="5"/></svg>'
    no_labels = f'<svg xmlns="http://www.w3.org/2000/svg" data-baseline="100"><title>{TITLE}</title><rect y="90" height="10" class="highlight"/></svg>'
    two_highlights = (f'<svg xmlns="http://www.w3.org/2000/svg" data-baseline="100"><title>{TITLE}</title>'
                      '<rect data-label="Q1" data-value="5" class="highlight" y="95" height="5"/>'
                      '<rect data-label="Q2" data-value="6" class="highlight" y="94" height="6"/></svg>')
    floating_bar = (f'<svg xmlns="http://www.w3.org/2000/svg" data-baseline="100"><title>{TITLE}</title>'
                    '<rect data-label="Q1" data-value="5" class="highlight" y="50" height="5"/></svg>')
    for bad in (no_title, no_labels, two_highlights, floating_bar):
        assert check_chart(bad, TITLE) != []
