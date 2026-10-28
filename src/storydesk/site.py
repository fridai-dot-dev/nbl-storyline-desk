"""Self-contained static packets for the click-through demo."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any

from .charts import render_bar_chart, render_line_chart
from .data import as_of_connection
from .gates import visible_findings
from .sqlsafe import validate_safe_sql
from .store import Store
from .tools import ToolContext, get_game


_HANDLE = re.compile(r"(?:\bu/[A-Za-z0-9_-]+|@[A-Za-z0-9_-]+)")

CSS = """
:root { color-scheme: light dark; --bg:#f8fafc; --card:#fff; --text:#172033; --muted:#627085; --line:#dbe3ec; --accent:#2667a0; --held:#9a5d00; }
@media (prefers-color-scheme: dark) { :root { --bg:#101722; --card:#192332; --text:#e9eff8; --muted:#aebbd0; --line:#314055; --accent:#76b7eb; --held:#ffc76c; } }
* { box-sizing:border-box } body { margin:0; background:var(--bg); color:var(--text); font:16px/1.5 system-ui,-apple-system,sans-serif; }
main { max-width:960px; margin:auto; padding:2.4rem 1.25rem 4rem } a { color:var(--accent) } .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1rem 1.1rem; margin:.9rem 0; }
h1 { line-height:1.15 } h2 { margin-top:1.8rem } .muted { color:var(--muted) } .pill { display:inline-block; border:1px solid var(--line); border-radius:99px; padding:.08rem .5rem; font-size:.78rem; margin:.1rem .2rem .1rem 0; }
.held { color:var(--held); border-color:var(--held) } .buttons button { border:1px solid var(--line); background:var(--card); color:var(--text); border-radius:6px; padding:.32rem .55rem; margin:.15rem .25rem .1rem 0; }
blockquote { border-left:3px solid var(--accent); margin:.75rem 0; padding:.3rem .75rem; background:color-mix(in srgb, var(--card) 85%, var(--accent)); } details pre { white-space:pre-wrap; overflow:auto; } table { border-collapse:collapse; width:100% } td,th { text-align:left; padding:.4rem; border-bottom:1px solid var(--line) }
"""


def _page(title: str, body: str) -> str:
    return f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{escape(title)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>"


def _write(path: Path, title: str, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_page(title, body), encoding="utf-8")
    return path


_PARENTHETICAL = re.compile(r"\s*\([^()]*\)")
_META_SENTENCE = re.compile(
    r"^(?:this )?answers? (?:the )?(?:producer )?(?:follow[- ]up )?question\b", re.IGNORECASE,
)


def headline_for(finding: dict[str, Any]) -> str:
    """Return the editor-supplied headline, or a compact, readable claim fallback."""
    headline = finding.get("headline")
    if isinstance(headline, str) and headline.strip():
        return headline.strip()
    claim = str(finding.get("claim") or "")
    while _PARENTHETICAL.search(claim):
        claim = _PARENTHETICAL.sub("", claim)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", claim.strip()) if part.strip()]
    while len(sentences) > 1 and _META_SENTENCE.match(sentences[0]):
        sentences.pop(0)
    words = (sentences[0] if sentences else claim).split()
    return " ".join(words[:25])


def _status_badge(finding: dict[str, Any]) -> str:
    if finding["status"] == "held":
        category = finding.get("sensitivity") or "sensitive"
        return f'<span class="pill held">Held · {escape(category)} · needs sign-off</span>'
    return f'<span class="pill">{escape(finding["status"])}</span>'


def _cost_label(run: dict[str, Any]) -> str:
    label = f"US${float(run.get('cost_usd') or 0):.2f} at API prices"
    if run.get("route") == "sdk":
        label += " (run on a Claude subscription)"
    return label


def _chart(stats_db: str | Path, finding: dict[str, Any], as_of: str) -> str:
    chart = finding.get("chart")
    if not chart or finding.get("number") is None:
        return ""
    try:
        sql = validate_safe_sql(chart["query"])
    except (KeyError, TypeError, ValueError):
        return ""
    con = as_of_connection(stats_db, as_of)
    try:
        cursor = con.execute(sql)
        columns = [item[0].lower() for item in cursor.description]
        if not {"label", "value", "highlight"} <= set(columns):
            return ""
        lookup = {name: columns.index(name) for name in ("label", "value", "highlight")}
        rows = cursor.fetchall()
    except Exception:
        return ""
    finally:
        con.close()
    selected = [index for index, row in enumerate(rows) if bool(row[lookup["highlight"]])]
    if len(selected) != 1:
        return ""
    try:
        if abs(float(rows[selected[0]][lookup["value"]]) - float(finding["number"])) > 1e-6:
            return ""
        labels = [str(row[lookup["label"]]) for row in rows]
        values = [float(row[lookup["value"]]) for row in rows]
    except (TypeError, ValueError):
        return ""
    render = render_bar_chart if chart["type"] == "bar" else render_line_chart
    return render(finding["claim"], labels, values, selected[0], chart["y_label"])


def _finding_card(finding: dict[str, Any], href: str) -> str:
    tags = " ".join(f"<span class=\"pill\">{escape(tag)}</span>" for tag in finding["audience"])
    return (
        f"<article class=\"card\"><a href=\"{href}\"><strong>{escape(headline_for(finding), quote=False)}</strong></a><br>"
        f"{_status_badge(finding)}{tags}"
        "<div class=\"buttons\"><button>Back it</button><button>Comment</button><button>Make it a directive</button><button>Drop</button></div></article>"
    )


def _finding_page(store: Store, stats_db: str | Path, finding: dict[str, Any], pages: set[int]) -> str:
    run = store.get_run(finding["run_id"])
    chart = _chart(stats_db, finding, run["as_of"])
    evidence = store.evidence(finding["id"])
    evidence_html = "".join(
        f"<blockquote>{escape(_HANDLE.sub('', item.get('quote') or 'Evidence recorded without a quote.'))}<br>"
        f"<small>{escape(item['source_type'])} · <a href=\"{escape(item['url'], quote=True)}\">source</a> · {escape(item['ref'])}</small></blockquote>"
        for item in evidence
    ) or "<p class=\"muted\">No quote was required for this source.</p>"
    query_html = ""
    if finding.get("query"):
        query_html = f"<details><summary>How we know · rechecked by code</summary><pre>{escape(finding['query'])}</pre></details>"
    elif finding["kind"] == "checked":
        query_html = "<p class=\"muted\">Recheck data unavailable.</p>"
    trail = []
    if finding.get("parent_id") in pages:
        parent = store.get_finding(finding["parent_id"])
        trail.append(f"<li>From <a href=\"{parent['id']}.html\">{escape(headline_for(parent), quote=False)}</a></li>")
    for child in store.game_findings(run["game_id"]):
        if child.get("parent_id") == finding["id"] and child["id"] in pages:
            trail.append(f"<li>Leads to <a href=\"{child['id']}.html\">{escape(headline_for(child), quote=False)}</a></li>")
    trail_html = "<ul>" + "".join(trail) + "</ul>" if trail else "<p class=\"muted\">No linked finding yet.</p>"
    requests = store.requests_for_anchor(finding["id"])
    requests_html = "".join(
        f"<div class=\"card\"><strong>{escape(request['question'], quote=False)}</strong> · asked by {escape(request['asked_by'], quote=False)}"
        + (f"<br>Answered in run {request['answered_run_id']}." if request["answered_run_id"] else "") + "</div>"
        for request in requests
    ) or "<p class=\"muted\">No follow-up requests yet.</p>"
    return (
        f"<p><a href=\"../index.html\">Storyline Desk</a> · Finding {finding['id']}</p><h1>{escape(headline_for(finding), quote=False)}</h1>"
        f"<p>{escape(finding['claim'], quote=False)}</p><p>{_status_badge(finding)}"
        + " ".join(f"<span class=\"pill\">{escape(tag)}</span>" for tag in finding["audience"]) + "</p>"
        f"<section class=\"card\">{chart or '<p class=\"muted\">No chart was released for this finding.</p>'}{query_html}</section>"
        f"<h2>How the agents got here</h2>{trail_html}<h2>Evidence</h2>{evidence_html}"
        f"<h2>Follow-up requests</h2>{requests_html}"
    )


def build_site(store: Store, stats_db: str | Path, out_dir: str | Path, *, game_id: str) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    runs = [run for run in store.game_runs(game_id) if run["run_type"] != "smoke"]
    findings = [item for item in store.game_findings(game_id) if item["status"] in {"shipped", "held"}]
    findings = [item for item in findings if item["run_id"] in {run["id"] for run in runs}]
    pages = {item["id"] for item in findings}
    output: list[Path] = []
    for finding in findings:
        output.append(_write(out / "findings" / f"{finding['id']}.html", headline_for(finding), _finding_page(store, stats_db, finding, pages)))

    pre_runs = [run for run in runs if run["run_type"] == "pre_game"]
    pre_findings = visible_findings(store, pre_runs[-1]["id"], "internal") if pre_runs else []
    output.append(_write(
        out / "pre-game.html", "Pre-game briefing",
        "<p><a href=\"index.html\">Storyline Desk</a></p><h1>Pre-game briefing</h1>"
        + ("".join(_finding_card(item, f"findings/{item['id']}.html") for item in pre_findings) or "<p class=\"muted\">No pre-game findings yet.</p>"),
    ))

    post_runs = [run for run in runs if run["run_type"] == "post_game"]
    post = post_runs[-1] if post_runs else None
    if post:
        ctx = ToolContext(stats_db=stats_db, store=store, corpus_dir="", run_id=post["id"], as_of=post["as_of"])
        game = get_game(ctx, game_id)
        score = f"{escape(game['home_team'])} {game.get('home_score', '–')} – {game.get('away_score', '–')} {escape(game['away_team'])}"
        quarters = game.get("quarters") or {}
        quarter_scores = " · ".join(
            f"{escape(game[side + '_team'])} {'–'.join(str(value) for value in quarters.get(side, []) if value is not None)}"
            for side in ("home", "away")
            if quarters.get(side)
        )
        post_findings = visible_findings(store, post["id"], "internal")
        moved = [item for item in post_findings if item.get("parent_id") in {pre['id'] for pre in pre_findings}]
        pulse = [item for item in post_findings if item["source_type"] in {"commentary", "fans"}]
        directives = store.directives()
        minutes = int(round((post.get("duration_s") or 0) / 60))
        feedback = store.feedback()
        email = (
            "<p><a href=\"../index.html\">Storyline Desk</a></p><h1>Post-game leadership briefing</h1>"
            f"<section class=\"card\"><h2>{score}</h2><p>Briefing ready {minutes} min after full time · {_cost_label(post)}</p></section>"
            f"<h2>What happened</h2><p>{escape(post.get('summary') or 'No lead summary was recorded for this run.', quote=False)}</p>"
            f"<p><strong>Final score:</strong> {score}<br><strong>Quarter scores:</strong> {quarter_scores or 'Not available'}</p>"
            "<h2>What moved since pre-game</h2>" + ("".join(_finding_card(item, f"../findings/{item['id']}.html") for item in moved) or "<p class=\"muted\">No linked pre-game movement recorded.</p>")
            + "<h2>In-game pulse</h2>" + ("".join(_finding_card(item, f"../findings/{item['id']}.html") for item in pulse) or "<p class=\"muted\">No in-game pulse finding.</p>")
            + "<h2>Angles for the next 48 hours</h2>" + "".join(_finding_card(item, f"../findings/{item['id']}.html") for item in post_findings)
            + "<h2>Directives</h2>" + ("".join(f"<div class=\"card\">{escape(item['text'])}</div>" for item in directives) or "<p class=\"muted\">No active directives.</p>")
            + "<p class=\"muted\">Feedback shown here is simulated.</p>" + "".join(
                f"<p><em>simulated</em> {escape(item['role'])}: {escape(item['action'])}</p>" for item in feedback if item["simulated"]
            )
        )
    else:
        email = "<p><a href=\"../index.html\">Storyline Desk</a></p><h1>Post-game leadership briefing</h1><p class=\"muted\">No post-game run yet.</p>"
    output.append(_write(out / "outbox" / "post-game-email.html", "Post-game leadership briefing", email))

    links = "".join(f"<li><a href=\"findings/{finding['id']}.html\">{escape(headline_for(finding), quote=False)}</a></li>" for finding in findings)
    index = (
        "<h1>NBL Storyline Desk</h1><p>An agent-powered, cutoff-safe research layer for NBL media.</p>"
        "<p><a href=\"pre-game.html\">Pre-game briefing</a> · <a href=\"outbox/post-game-email.html\">Post-game leadership email</a></p>"
        "<h2>How it works</h2><p>Specialists research across stats, commentary, media and fans; code rechecks numbers, holds sensitive material and records usage.</p>"
        "<h2>Findings</h2><ul>" + links + "</ul><h2>Cost per run</h2><ul>" + "".join(
            f"<li>{escape(run['run_type'])}: {_cost_label(run)}</li>" for run in runs
        ) + "</ul>"
    )
    output.append(_write(out / "index.html", "NBL Storyline Desk", index))
    return output
