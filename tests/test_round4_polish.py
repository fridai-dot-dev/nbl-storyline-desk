"""Round 4: polish from the first real email with headlines (2026-10-28).

"What happened" showed the lead's raw markdown notes as one wall of text. Findings repeated across email sections.
Rotated chart labels were clipped even with two bars, and secondary text was too faint to read.
"""
import re
import xml.etree.ElementTree as ET

from conftest import OPENER


def _rebuild(ns, tmp_path):
    from storydesk.site import build_site

    out = tmp_path / "site"
    build_site(ns.store, ns.stats_db, out, game_id=OPENER)
    return out, (out / "outbox" / "post-game-email.html").read_text(encoding="utf-8")


def test_judge_writes_an_exec_summary_for_the_run(demo_store):
    from storydesk.judge import rejudge

    def scorer(findings, coverage):
        return {"exec_summary": "Adelaide won 97-95 at Melbourne on the back of an 18-point edge from three.",
                **{f["id"]: {"novelty": 0.5, "audience_fit": 0.5, "direction": 0.5} for f in findings}}, 0.01

    rejudge(demo_store.store, demo_store.post_run, stats_db=demo_store.stats_db,
            corpus_dir=demo_store.store.path.parent, scorer=scorer)
    assert demo_store.store.get_run(demo_store.post_run)["exec_summary"].startswith("Adelaide won 97-95")


def test_what_happened_is_short_and_editor_notes_render_as_markdown(demo_store, tmp_path):
    store = demo_store.store
    store.set_run_summary(demo_store.post_run, "# Editorial summary\n\n**What happened.** Adelaide won.\n\n- First note\n- Second note")
    store.set_exec_summary(demo_store.post_run, "Adelaide won 97-95 at Melbourne on the back of an 18-point edge from three.")
    _, email = _rebuild(demo_store, tmp_path)
    happened = email.split("What happened", 1)[1].split("<h2", 1)[0]
    assert "Adelaide won 97-95 at Melbourne" in happened
    assert "# Editorial summary" not in email and "**What happened.**" not in email   # no raw markdown anywhere
    assert re.search(r"<details[^>]*>.*Editor.?s notes.*<li>\s*First note\s*</li>", email, re.S | re.I)
    assert "<strong>What happened.</strong>" in email


def test_each_finding_appears_once_in_the_email_and_held_items_are_grouped(demo_store, tmp_path):
    _, email = _rebuild(demo_store, tmp_path)
    sections = email.split("Suggested follow-ups", 1)[0]          # suggestions may point back at their finding
    body_links = re.findall(r'href="(?:\.\./)?findings/(\d+)\.html"', sections)
    assert len(body_links) == len(set(body_links)), "a finding is linked from more than one email section"
    held = email.split("Held for sign-off", 1)
    assert len(held) == 2, "held items need their own section"
    angles = email.split("Angles for the next 48 hours", 1)[1].split("<h2", 1)[0]
    assert "Held ·" not in angles                                  # angles are shipped items only


def test_two_bars_never_rotate_and_rotated_labels_are_not_clipped():
    from storydesk.charts import render_bar_chart

    def label_nodes(svg):
        root = ET.fromstring(svg)
        return root, [n for n in root.iter() if n.tag.split("}")[-1] == "text" and n.get("data-axis-label") == "x"]

    svg = render_bar_chart("Weaker bench won 18 of 74", ["Weaker bench won", "Stronger bench won"], [18, 56],
                           highlight_index=0, y_label="Games")
    _, labels = label_nodes(svg)
    assert labels and not any("rotate(" in (t.get("transform") or "") for t in labels)

    many = [f"Season {y}-{y + 1} regular" for y in range(2015, 2027)]
    svg = render_bar_chart("Twelve long labels", many, list(range(12)), highlight_index=3, y_label="v")
    root, labels = label_nodes(svg)
    height = float(root.get("height") or root.get("viewBox").split()[3])
    for t in labels:
        assert float(t.get("y")) < height                          # labels sit inside the drawing area
    assert root.get("data-label-room"), "chart must reserve room for rotated labels"


def test_secondary_text_is_readable(demo_store, tmp_path):
    out, _ = _rebuild(demo_store, tmp_path)
    css = (out / "findings" / f"{demo_store.f_checked}.html").read_text(encoding="utf-8")
    greys = re.findall(r"--muted\s*:\s*#([0-9a-fA-F]{6})", css)
    assert greys, "pages define a --muted text colour"

    def lum(hex6):
        def ch(c):
            c = int(c, 16) / 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = (ch(hex6[i:i + 2]) for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    contrast = (1.0 + 0.05) / (lum(greys[0]) + 0.05)              # against a white background
    assert contrast >= 4.5, f"--muted #{greys[0]} contrast {contrast:.2f} is below WCAG AA"


def test_text_classes_are_never_faded(demo_store, tmp_path):
    """The chart's faded-bar rule (.muted{opacity:.28}) collided with the text class .muted."""
    out, _ = _rebuild(demo_store, tmp_path)
    for page in out.rglob("*.html"):
        css = page.read_text(encoding="utf-8")
        for rule in re.findall(r"([^{}]+)\{([^}]*)\}", css):
            selector, body = rule
            m = re.search(r"opacity\s*:\s*(0?\.\d+)", body)
            if m and float(m.group(1)) < 0.7:
                assert "svg" in selector or "rect" in selector or "circle" in selector, \
                    f"{page.name}: '{selector.strip()}' fades text-capable elements to {m.group(1)}"
