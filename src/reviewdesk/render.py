"""Render the sample weekly email page from a week's findings file.

The page restates the findings JSON and nothing else: fixed copy here holds no figures, and every
value from the data is escaped. The shared stylesheet (``../assets/agora.css``) does the styling;
the inline style below only covers classes that exist for Daniel's Donuts alone.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .charts import render_donut, render_line, render_scatter

STANCE_ADDRESS = "review-desk@example.com"
STANCES = (("Push it", "push"), ("Use if it comes up", "use if raised"), ("Steer away", "steer away"), ("Comment", "comment"))
CHART_FILES = {"theme_mix": "theme-mix.svg", "rating_trend": "rating-trend.svg", "store_scatter": "store-scatter.svg"}

DD_CSS = (
    ".illustrative{border:1px dashed var(--border,#d9d9d9);background:var(--surface,#f5f5f5);color:var(--text,#1a1a1a);"
    "padding:10px 14px;margin:0 0 16px;font-size:13px}"
    ".number{margin:6px 0;font-size:13px}"
    ".number b{font-variant-numeric:tabular-nums;font-size:18px;color:#1f3a5f}"
    ".causal{font-weight:600;color:#1f3a5f}"
    ".evidence .causal{color:inherit}"
    ".suggestion{margin-top:6px;border-left:3px solid #1f3a5f;padding-left:8px;font-size:12px}"
    ".escalated{margin-top:6px;border:1px solid #e3a96f;background:#fdf0e1;color:#9a4a00;padding:5px 8px;font-size:12px}"
    ".store-section{border-top:1px solid #cfcfcf;padding-top:8px;margin-top:10px}"
    ".store-section h5{margin:0 0 4px;font-size:13px}"
    ".evidence{background:var(--card,#fff);border:1px solid var(--border,#d9d9d9);padding:12px 16px;margin:0 0 12px;font-size:14px}"
    ".evidence h3{margin:0 0 6px;font-size:16px}.evidence ul{margin:6px 0;padding-left:18px}"
)


def _t(value: object) -> str:
    return escape(str(value), quote=False)


def _a(value: object) -> str:
    return escape(str(value), quote=True)


def _chart_svgs(data: dict[str, Any]) -> dict[str, str]:
    charts = data["charts"]
    mix, trend, scatter = charts["theme_mix"], charts["rating_trend"], charts["store_scatter"]
    return {
        "theme_mix": render_donut([(item["label"], item["value"]) for item in mix["slices"]],
                                  title=mix["title"], centre_label=mix["centre_label"], unit=mix["unit"]),
        "rating_trend": render_line([(item["label"], item["rating"]) for item in trend["points"]],
                                    title=trend["title"], baseline=trend["baseline"], baseline_label=trend["baseline_label"]),
        "store_scatter": render_scatter([(str(item["store"]), item["x"], item["y"]) for item in scatter["points"]],
                                        title=scatter["title"], x_label=scatter["x_label"], y_label=scatter["y_label"]),
    }


def _stance_links(finding: dict[str, Any]) -> str:
    links = []
    for label, action in STANCES:
        query = urlencode({"subject": f"{action} on story {finding['id']}: {finding['headline']}"})
        links.append(f'<a href="mailto:{STANCE_ADDRESS}?{_a(query)}">{label}</a>')
    return "".join(links)


def _story_box(data: dict[str, Any], finding: dict[str, Any]) -> str:
    sensitive = bool(finding["sensitivity"])
    tag = f' <span class="sensitive-tag">sensitive · {_t(finding["sensitivity"])}</span>' if sensitive else ""
    value, label = str(finding["number"]["value"]), str(finding["number"]["label"])
    joiner = "" if label.startswith("%") else " "
    causal = (f' Judge\'s label: <span class="causal">{_t(finding["causal"])}</span>'
              if finding["causal"] else "")
    escalated = f'<div class="escalated">Escalated: {_t(finding["escalated"])}</div>' if finding.get("escalated") else ""
    chart = ""
    if finding["chart"]:
        alt = data["charts"][finding["chart"]]["title"]
        chart = f'<img class="chart" src="charts/{CHART_FILES[finding["chart"]]}" alt="{_a(alt)}">'
    suggestion = f'<div class="suggestion">{_t(finding["suggestion"])}</div>' if finding["suggestion"] else ""
    return (
        f'<article class="item{" sensitive" if sensitive else ""}" data-finding="{_a(finding["id"])}">'
        f'<b class="h">{_t(finding["headline"])}</b>{tag}'
        f'<p class="premise">{_t(finding["premise"])}</p>'
        f'<div class="number"><b>{_t(value)}</b>{joiner}{_t(label)}</div>'
        f'<div class="test">{_t(finding["status"])}{causal}</div>'
        f'{escalated}{chart}{suggestion}'
        f'<div class="stance">{_stance_links(finding)}</div>'
        f'<div class="full-story"><a href="#evidence-{_a(finding["id"])}">Full story →</a></div></article>'
    )


def _boxes_section(data: dict[str, Any], name: str, heading: str, findings: list[dict[str, Any]]) -> str:
    if not findings:
        return ""
    boxes = "".join(_story_box(data, finding) for finding in findings)
    return f'<section data-section="{name}"><h4>{heading}</h4>{boxes}</section>'


def _store_sections(data: dict[str, Any]) -> str:
    regions = {item["store"]: item["region"] for item in data["stores"]}
    headlines = {finding["id"]: finding["headline"] for finding in data["findings"]}
    blocks = []
    for item in data["store_sections"]:
        links = "".join(f'<p><a href="#evidence-{_a(fid)}">{_t(headlines[fid])}</a></p>' for fid in item["finding_ids"])
        blocks.append(f'<div class="store-section" data-store="{item["store"]}">'
                      f'<h5>Store {item["store"]} · {_t(regions[item["store"]])}</h5><p>{_t(item["note"])}</p>{links}</div>')
    if not blocks:
        return ""
    return ('<section data-section="store-managers"><h4>For store managers</h4>'
            "<p>Each store manager's section lists the stories that touch their store, with the evidence one link away.</p>"
            + "".join(blocks) + "</section>")


def _meeting(data: dict[str, Any]) -> str:
    meeting = data["meeting"]
    questions = "".join(f"<li>{_t(question)}</li>" for question in meeting["questions"])
    return (f'<section data-section="meeting"><h4>For {_t(meeting["day"])}\'s ops meeting</h4>'
            f'<p>{_t(meeting["note"])}</p><ol>{questions}</ol></section>')


def _mail(data: dict[str, Any]) -> str:
    findings = data["findings"]
    sensitive = sorted((item for item in findings if item["sensitivity"]),
                       key=lambda item: item["sensitivity"] != "food safety")
    plain = [item for item in findings if not item["sensitivity"]]
    network = [item for item in plain if item["thread"] == "network"]
    threads = [item for item in plain if item["thread"] != "network"]
    footer = " · ".join(_t(data["footer"][key]) for key in ("run", "data_to", "cost"))
    return (
        f'<section class="mail" id="weekly" data-email-type="weekly">'
        f'<div class="head"><div class="subj">Subject: {_t(data["subject"])}</div>'
        f'<b>From: {_t(data["desk"])}</b><br><b>To: {_t(data["recipients"])}</b><br>{_t(data["sent"])}</div>'
        f'<div class="body"><p class="lead serif" data-section="lead">{_t(data["lead"])}</p>'
        + _boxes_section(data, "network", "Across the network", network)
        + _boxes_section(data, "threads", "What else changed", threads)
        + _boxes_section(data, "sensitive", "Sensitive stories: set a stance", sensitive)
        + _store_sections(data)
        + _meeting(data)
        + '<div class="reply-box" data-section="reply"><b>Reply to steer this week\'s work</b><br>'
          'Ask for anything in plain words, or set a stance on any story above.</div></div>'
        + f'<div class="foot" data-section="footer">{footer}</div></section>'
    )


def _evidence(data: dict[str, Any]) -> str:
    entries = []
    for finding in data["findings"]:
        items = "".join(f'<li><b>{_t(item["source"])}</b>: {_t(item["detail"])}</li>' for item in finding["evidence"])
        causal = _t(finding["causal"]) if finding["causal"] else "none: no explanation claimed"
        entries.append(
            f'<div class="evidence" id="evidence-{_a(finding["id"])}"><h3>{_t(finding["headline"])}</h3>'
            f'<p>Status: {_t(finding["status"])}</p><p>Judge\'s label: <span class="causal">{causal}</span></p>'
            f'<ul>{items}</ul><p><a href="#weekly">Back to the email</a></p></div>'
        )
    return ('<section data-region="evidence"><h2>The evidence behind each story</h2>' + "".join(entries) + "</section>")


def _inbox_row(data: dict[str, Any]) -> str:
    time = str(data["sent"]).rsplit(", ", 1)[-1]
    return ('<section class="inbox" data-region="inbox-strip"><div class="row" data-run-type="weekly">'
            f'<span class="t">{_t(time)}</span><span>{_t(data["desk"])}</span>'
            f'<span class="s"><a href="#weekly">{_t(data["subject"])}</a></span><span class="tag">weekly</span></div></section>')


def _page(data: dict[str, Any]) -> str:
    banner = ('<div class="illustrative" data-region="banner">Illustrative data: a made-up week showing what the Review Desk '
              "would send Daniel's Donuts. Every figure, quote and store detail here is invented for the sample.</div>")
    note = ('<p class="internal-note" data-region="internal-note">Everyone on this list is internal, and anyone on it can '
            "set a stance on any story: push it, use it if it comes up, or steer away, with a comment. Each explanation "
            "carries the judge's label for how far it has been checked: coincides with (the two happened together), "
            "consistent with (the data fits, but other causes aren't ruled out) or tested (checked against a comparison).</p>")
    heading = f"<h1>Daniel's Donuts · {_t(data['week']['label'])}</h1>"
    body = "\n".join((banner, heading, _inbox_row(data), note, _mail(data), _evidence(data)))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{_t(data["subject"])}</title>'
        '<link rel="stylesheet" href="../assets/agora.css">'
        f"<style>{DD_CSS}</style></head><body><main>{body}</main></body></html>\n"
    )


def render_week(data: dict[str, Any], out: str | Path) -> list[Path]:
    """Write the weekly page to ``out`` and its three charts to ``out.parent/charts``; return every path written."""
    out = Path(out)
    charts_dir = out.parent / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    written = [out]
    out.write_text(_page(data), encoding="utf-8")
    for key, svg in _chart_svgs(data).items():
        path = charts_dir / CHART_FILES[key]
        path.write_text(svg, encoding="utf-8")
        written.append(path)
    return written
