"""Self-contained static packets for the click-through demo."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any

from .charts import render_bar_chart, render_line_chart
from .data import as_of_connection
from .gates import _BOUNDARY, _RECORD_WORD
from .sqlsafe import validate_safe_sql
from .store import Store
from .tools import ToolContext, get_game


_HANDLE = re.compile(r"(?:\bu/[A-Za-z0-9_-]+|@[A-Za-z0-9_-]+)")

CSS = """
:root { color-scheme:light dark; --bg:#f8fafc; --card:#fff; --surface:#f1f5f9; --text:#172033; --muted:#627085; --line:#dbe3ec; --accent:#2667a0; --held:#9a5d00; --ok-bg:#e4f4e8; --ok:#176b35; --lead-bg:#e2effb; --lead:#14568d; --hold-bg:#fff1d9; --button-bg:#fff; }
@media (prefers-color-scheme:dark) { :root { --bg:#101722; --card:#192332; --surface:#142031; --text:#e9eff8; --muted:#b9c5d8; --line:#3a4a61; --accent:#82c4f4; --held:#ffd17a; --ok-bg:#143c26; --ok:#9ee6b6; --lead-bg:#17395a; --lead:#a9d6fb; --hold-bg:#493313; --button-bg:#192332; } }
* { box-sizing:border-box } body { margin:0; background:var(--bg); color:var(--text); font:16px/1.5 system-ui,-apple-system,sans-serif; }
main { max-width:1240px; margin:auto; padding:2.4rem 1.25rem 4rem } a { color:var(--accent) } h1 { line-height:1.15; margin:.2rem 0 .6rem } h2 { margin-top:1.8rem } h3 { margin:.3rem 0 }
.muted { color:var(--muted) } .pill { display:inline-block; border:1px solid var(--line); border-radius:99px; padding:.08rem .5rem; font-size:.74rem; line-height:1.35; margin:.1rem .2rem .1rem 0; white-space:nowrap; }.kind { background:var(--ok-bg); border-color:var(--ok-bg); color:var(--ok) }.lead { background:var(--lead-bg); border-color:var(--lead-bg); color:var(--lead) }.held { color:var(--held); border-color:var(--held); background:var(--hold-bg) }.simulated { background:var(--surface); color:var(--muted) }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1rem 1.1rem; margin:.8rem 0; }.buttons { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.55rem }.buttons button, button { border:1px solid var(--line); background:var(--button-bg); color:var(--text); border-radius:6px; padding:.32rem .55rem; font:inherit; font-size:.76rem; }.buttons button:first-child { border-color:var(--accent) }.buttons button.primary,button.primary { background:var(--accent); border-color:var(--accent); color:var(--bg) }.later-button:disabled { color:var(--muted); border-style:dashed; cursor:not-allowed; }
blockquote { border-left:3px solid var(--accent); margin:.75rem 0; padding:.3rem .75rem; background:var(--surface); } pre { white-space:pre-wrap; overflow:auto; margin:.45rem 0; } table { border-collapse:collapse; width:100% } td,th { text-align:left; padding:.45rem; border-bottom:1px solid var(--line); vertical-align:top }
.board { background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:hidden; font-size:.88rem; }.board-top { display:flex; flex-wrap:wrap; gap:.6rem 1rem; justify-content:space-between; align-items:center; padding:.7rem .95rem; border-bottom:1px solid var(--line); background:var(--surface); }.board-score { font-size:1rem }.board-top select { border:1px solid var(--line); border-radius:6px; padding:.18rem .45rem; color:var(--text); background:var(--card) }.board-grid { display:grid; grid-template-columns:220px minmax(0,1fr) 260px }.board-left,.board-angles,.board-right { padding:.9rem }.board-angles,.board-right { border-left:1px solid var(--line) }.board-label { margin:0 0 .55rem; color:var(--muted); font-size:.7rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase }.board-label.gap { margin-top:1.15rem }.leadership-item,.directive,.request-row { border-left:3px solid var(--accent); border-radius:0 6px 6px 0; background:var(--surface); margin:.45rem 0; padding:.38rem .55rem }.leadership-item small,.directive small,.request-row small { display:block; color:var(--muted); font-size:.72rem }.signoff-links,.request-answers { margin:.25rem 0 0; padding-left:1rem; font-size:.75rem }.angle { border:1px solid var(--line); border-radius:9px; padding:.7rem; margin:.65rem 0 }.angle-title { font-size:.94rem; font-weight:700 }.angle-claim { color:var(--muted); display:-webkit-box; font-size:.8rem; margin:.3rem 0 .55rem; overflow:hidden; -webkit-box-orient:vertical; -webkit-line-clamp:2 }.angle-evidence { display:grid; grid-template-columns:minmax(0,320px) 1fr; gap:.75rem; align-items:start; background:var(--surface); border-radius:7px; padding:.55rem .65rem }.angle-evidence.chartless { display:block }.angle-evidence svg,.chart-card svg { display:block; max-width:100%; height:auto; color:var(--text) }.evidence-summary { color:var(--muted); font-size:.75rem }.usage-chips { display:flex; flex-wrap:wrap; gap:.25rem; margin-top:.45rem }.held-strip { border:1px dashed var(--held); background:var(--hold-bg); border-radius:8px; margin:.8rem 0; padding:.45rem .6rem; font-size:.78rem }.held-strip div + div { border-top:1px solid var(--line); margin-top:.35rem; padding-top:.35rem }.board-footer { border-top:1px solid var(--line); background:var(--surface); color:var(--muted); padding:.55rem .9rem; font-size:.75rem }.ask-box textarea { width:100%; min-height:5.5rem; resize:vertical; border:1px solid var(--line); border-radius:7px; padding:.5rem; color:var(--text); background:var(--card); font:inherit; font-size:.8rem }.ask-box p { color:var(--muted); font-size:.75rem; margin:.3rem 0 .55rem }
.runs-table { font-size:.85rem }.table-wrap { overflow-x:auto }.pill.held { white-space:normal }.email { max-width:640px; margin:0 auto; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1rem 1.1rem }.mail-meta { border-bottom:1px solid var(--line); color:var(--muted); font-size:.82rem; padding-bottom:.65rem; margin-bottom:.8rem }.mail-meta strong { color:var(--text) }.email h2 { color:var(--muted); font-size:.72rem; letter-spacing:.07em; text-transform:uppercase; margin:1.2rem 0 .45rem }.email-angle { border:1px solid var(--line); border-radius:8px; padding:.6rem .65rem; margin:.5rem 0 }.email-angle p { margin:.25rem 0; font-size:.82rem }.held-row { border-left:3px solid var(--held); padding:.35rem .55rem; margin:.5rem 0 }.held-row > a { display:block; font-size:.88rem }.held-meta { align-items:center; display:flex; flex-wrap:wrap; gap:.3rem .5rem; margin-top:.3rem }.held-meta .muted { font-size:.72rem }.held-meta .buttons { margin:0 0 0 auto }.compact-row { border-bottom:1px solid var(--line); padding:.38rem 0; font-size:.83rem }.email-footer { margin-top:1rem; border-top:1px solid var(--line); padding-top:.65rem; color:var(--muted); font-size:.78rem }.email-footer p { margin:.25rem 0 }
.detail-header { background:var(--card); border:1px solid var(--line); border-radius:12px 12px 0 0; padding:.8rem 1rem; }.breadcrumb { color:var(--muted); font-size:.75rem; margin-bottom:.35rem }.detail-title-row { display:flex; justify-content:space-between; gap:.8rem; align-items:start }.detail-title-copy { min-width:0 }.detail-lead { font-size:.95rem; margin:.55rem 0 .2rem }.detail-actions { display:flex; flex:0 0 auto; flex-wrap:nowrap; gap:.35rem; justify-content:flex-end }.run-cost { color:var(--muted); font-size:.78rem; margin:.5rem 0 0 }.detail-grid { display:grid; grid-template-columns:minmax(0,1fr) 300px; border:1px solid var(--line); border-top:0; border-radius:0 0 12px 12px; background:var(--card) }.detail-main,.detail-side { padding:1rem }.detail-side { border-left:1px solid var(--line) }.detail-side h2 { color:var(--muted); font-size:.68rem; letter-spacing:.07em; text-transform:uppercase }.chart-card { border:1px solid var(--line); border-radius:9px; padding:.7rem }.chart-title { font-weight:700; margin-bottom:.45rem }.how-we-know { margin-top:.6rem; background:var(--surface); border-radius:6px; padding:.4rem .55rem; font-size:.76rem }.how-we-know details { margin-top:.35rem }.timeline { border-left:2px solid var(--line); margin-left:.4rem; padding-left:1rem }.timeline-step { position:relative; margin:.65rem 0 }.timeline-step::before { background:var(--accent); border:2px solid var(--card); border-radius:50%; content:""; height:10px; left:-1.4rem; position:absolute; top:.35rem; width:10px }.timeline-step p { color:var(--muted); font-size:.8rem; margin:.2rem 0 }.step-tag { background:var(--surface); color:var(--muted); font-size:.65rem; font-weight:700; letter-spacing:.05em; padding:.05rem .3rem; border-radius:4px }.quote { border-left:3px solid var(--accent); border-radius:0 7px 7px 0; background:var(--surface); padding:.4rem .55rem; margin:.45rem 0 }.quote blockquote { background:transparent; border:0; margin:0; padding:0 }.quote small { color:var(--muted); display:block; font-size:.73rem; margin-top:.25rem }.follow-card { border:1px dashed var(--line); border-radius:8px; margin:.5rem 0; padding:.55rem }.follow-card > strong { display:block; font-size:.95rem; line-height:1.35 }.follow-card p { color:var(--muted); font-size:.8rem; margin:.25rem 0 }.source-row { display:flex; align-items:start; justify-content:space-between; gap:.5rem; border-bottom:1px solid var(--line); padding:.4rem 0; font-size:.8rem }.source-row small { color:var(--muted); display:block }
@media (max-width:1050px) { .board-grid { display:flex; flex-direction:column }.board-angles { order:1 }.board-left { order:2 }.board-right { order:3 }.board-angles,.board-right { border-left:0; border-top:1px solid var(--line) } } @media (max-width:900px) { .detail-grid { grid-template-columns:1fr }.detail-side { border-left:0; border-top:1px solid var(--line) } } @media (max-width:700px) { main { padding:1.3rem .75rem 2rem }.angle-evidence { grid-template-columns:1fr }.held-meta .buttons { margin-left:0 }.detail-title-row { display:block }.detail-actions { flex-wrap:wrap; justify-content:start; margin-top:.6rem } }
"""


def _page(title: str, body: str) -> str:
    return f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{escape(title)}</title><style>{CSS}</style></head><body><main>{body}</main></body></html>"


def _write(path: Path, title: str, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_page(title, body), encoding="utf-8")
    return path


_MD_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*$")
_MD_BULLET = re.compile(r"^[-*+]\s+(.+)$")
_MD_NUMBERED = re.compile(r"^\d+[.)]\s+(.+)$")
_MD_BOLD = re.compile(r"(?:\*\*|__)(.+?)(?:\*\*|__)")


def _markdown_html(text: str | None) -> str:
    """Render the small editorial Markdown subset without admitting raw HTML."""
    escaped = escape(text or "", quote=False)

    def inline(value: str) -> str:
        return _MD_BOLD.sub(lambda match: f"<strong>{match.group(1)}</strong>", value)

    blocks: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    list_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_kind, list_items
        if list_kind:
            blocks.append(f"<{list_kind}>" + "".join(f"<li>{inline(item)}</li>" for item in list_items) + f"</{list_kind}>")
            list_kind, list_items = None, []

    for line in escaped.splitlines():
        line = line.strip()
        if not line:
            flush_paragraph()
            flush_list()
        elif heading := _MD_HEADING.match(line):
            flush_paragraph()
            flush_list()
            blocks.append(f"<h3>{inline(heading.group(1))}</h3>")
        elif bullet := _MD_BULLET.match(line):
            flush_paragraph()
            if list_kind not in {None, "ul"}:
                flush_list()
            list_kind = "ul"
            list_items.append(bullet.group(1))
        elif numbered := _MD_NUMBERED.match(line):
            flush_paragraph()
            if list_kind not in {None, "ol"}:
                flush_list()
            list_kind = "ol"
            list_items.append(numbered.group(1))
        else:
            flush_list()
            paragraph.append(line)
    flush_paragraph()
    flush_list()
    return "".join(blocks) or "<p>No editor notes were recorded for this run.</p>"


_PARENTHETICAL = re.compile(r"\s*\([^()]*\)")
_META_SENTENCE = re.compile(
    r"^(?:(?:this )?answers? (?:the )?(?:producer )?(?:follow[- ]up )?question"
    r"|(?:user |producer )?follow[- ]up (?:to|on|for) finding \d+)\b",
    re.IGNORECASE,
)
_PRIMARY_RUN_TYPES = ("pre_game", "post_game", "supplemental")
_PUBLISHED_FINDING_STATUSES = {"shipped", "held"}
_HELD_AUDIENCES = ("producers", "partners")
_RUN_LABELS = {
    "pre_game": "Pre-game",
    "post_game": "Post-game",
    "supplemental": "Supplemental",
    "follow_up": "Follow-up",
}
_REPO_URL = "https://github.com/fridai-dot-dev/nbl-storyline-desk"


def _evidence_source_html(item: dict[str, Any]) -> str:
    """Link evidence only to browser-safe web URLs and canonical stats sources."""
    url = str(item.get("url") or "")
    if item.get("source_type") == "stats":
        relation = f"{url} {item.get('ref') or ''}".lower()
        releases = "https://github.com/JaseZiv/nblr_data/releases/tag/"
        if "box_player" in relation:
            url = releases + "pbp"
        elif "box_team" in relation:
            url = releases + "box_team"
        elif "results" in relation:
            url = releases + "match_results"
        else:
            url = f"{_REPO_URL}/blob/main/docs/data-provenance.md"
        return f'<a href="{escape(url, quote=True)}">source</a>'

    parsed = re.sub(r"[\x00-\x20\x7f]", "", url).lower()
    if parsed.startswith(("http:", "https:")):
        return f'<a href="{escape(url, quote=True)}">source</a>'
    return escape(url, quote=False)


def _published_content(store: Store, game_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return the complete, current runs and findings allowed into a site build."""
    all_runs = store.game_runs(game_id)
    all_findings = store.game_findings(game_id, include_dropped=True)
    published_run_ids: set[int] = set()

    for run_type in _PRIMARY_RUN_TYPES:
        complete = [run for run in all_runs if run["run_type"] == run_type and run["status"] == "complete"]
        if complete:
            published_run_ids.add(complete[-1]["id"])

    anchors_by_run: dict[int, set[int]] = {}
    for request in store.requests():
        if request["answered_run_id"] is not None:
            anchors_by_run.setdefault(request["answered_run_id"], set()).add(request["anchor_finding_id"])
    for finding in all_findings:
        if finding.get("parent_id") is not None and finding["run_id"] not in anchors_by_run:
            anchors_by_run.setdefault(finding["run_id"], set()).add(finding["parent_id"])

    follow_ups = [
        run for run in all_runs if run["run_type"] == "follow_up" and run["status"] == "complete"
    ]
    while True:
        published_finding_ids = {
            finding["id"] for finding in all_findings
            if finding["run_id"] in published_run_ids and finding["status"] in _PUBLISHED_FINDING_STATUSES
        }
        newly_published = [
            run["id"] for run in follow_ups
            if run["id"] not in published_run_ids
            and anchors_by_run.get(run["id"], set()) & published_finding_ids
        ]
        if not newly_published:
            break
        published_run_ids.update(newly_published)

    runs = [run for run in all_runs if run["id"] in published_run_ids]
    findings = [
        finding for finding in all_findings
        if finding["run_id"] in published_run_ids and finding["status"] in _PUBLISHED_FINDING_STATUSES
    ]
    return runs, findings


def headline_for(finding: dict[str, Any]) -> str:
    """Return the editor-supplied headline, or a compact, readable claim fallback."""
    headline = finding.get("headline")
    if isinstance(headline, str) and headline.strip():
        headline = headline.strip()
        claim = str(finding.get("claim") or "")
        boundary = _BOUNDARY.search(claim)
        if _RECORD_WORD.search(headline) and boundary and not _BOUNDARY.search(headline):
            return f"{headline} ({boundary.group()})"
        return headline
    claim = str(finding.get("claim") or "")
    while _PARENTHETICAL.search(claim):
        claim = _PARENTHETICAL.sub("", claim)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", claim.strip()) if part.strip()]
    while len(sentences) > 1 and _META_SENTENCE.match(sentences[0]):
        sentences.pop(0)
    words = (sentences[0] if sentences else claim).split()
    return " ".join(words[:25])


def _first_sentence(value: Any) -> str:
    """Return the claim's first substantive sentence, skipping lead-ins such as "User follow-up to finding 34."."""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", str(value or "").strip()) if part.strip()]
    while len(sentences) > 1 and _META_SENTENCE.match(sentences[0]):
        sentences.pop(0)
    return sentences[0] if sentences else ""


def _signoffs_html(finding: dict[str, Any]) -> str:
    signoffs = finding.get("signoffs") or []
    lines = [
        f'<div class="muted">Signed off for {escape(str(item["audience"]))} by {escape(str(item["approver"]), quote=False)}</div>'
        for item in signoffs
        if isinstance(item, dict) and item.get("audience") and item.get("approver")
    ]
    return "".join(lines)


def _status_badge(finding: dict[str, Any]) -> str:
    if finding["status"] == "held":
        category = finding.get("sensitivity") or "sensitive"
        signed_audiences = {
            str(item["audience"]) for item in finding.get("signoffs") or []
            if isinstance(item, dict) and item.get("audience")
        }
        waiting = [audience for audience in _HELD_AUDIENCES if audience not in signed_audiences]
        suffix = f" for {', '.join(waiting)}" if waiting else ""
        return f'<span class="pill held">Held · {escape(category)} · needs sign-off{escape(suffix)}</span>'
    return f'<span class="pill">{escape(finding["status"])}</span>'


def _kind_label(finding: dict[str, Any]) -> str:
    kind = str(finding.get("kind") or "finding")
    labels = {"checked": "stats checked", "attributed": "attributed", "qualitative": "qualitative"}
    return labels.get(kind, kind.replace("_", " "))


def _kind_badge(finding: dict[str, Any]) -> str:
    return f'<span class="pill kind">{escape(_kind_label(finding), quote=False)}</span>'


def _audience_pill(finding: dict[str, Any], *, prefix: str = "For: ") -> str:
    audience = [str(item) for item in finding.get("audience") or [] if str(item).strip()]
    if not audience:
        return ""
    return f'<span class="pill">{escape(prefix + ", ".join(audience), quote=False)}</span>'


def _remaining_audiences(finding: dict[str, Any]) -> list[str]:
    signed = {
        str(item["audience"]) for item in finding.get("signoffs") or []
        if isinstance(item, dict) and item.get("audience")
    }
    return [audience for audience in _HELD_AUDIENCES if audience not in signed]


def _usage_rows(store: Store, finding_id: int) -> list[dict[str, Any]]:
    return [
        item for item in store.feedback(finding_id)
        if item.get("action") in {"using it", "already had it", "not for us"}
    ]


def _usage_html(store: Store, finding_id: int) -> str:
    rows = _usage_rows(store, finding_id)
    if not rows:
        return '<div class="usage-chips"><span class="pill simulated">no one using yet · simulated</span></div>'
    chips = []
    for item in rows:
        simulated = " · simulated" if item.get("simulated") else ""
        chips.append(
            f'<span class="pill simulated">{escape(str(item.get("role") or ""), quote=False)}: '
            f'{escape(str(item.get("action") or ""), quote=False)}{simulated}</span>'
        )
    return '<div class="usage-chips">' + "".join(chips) + "</div>"


def _evidence_summary(store: Store, finding_id: int) -> str:
    evidence = store.evidence(finding_id)
    if not evidence:
        return '<span class="muted">No evidence summary is available.</span>'
    counts: dict[str, int] = {}
    for item in evidence:
        source_type = str(item.get("source_type") or "source")
        counts[source_type] = counts.get(source_type, 0) + 1
    names = {
        "stats": "stats check",
        "commentary": "commentary quote",
        "fans": "fan quote",
        "media": "media item",
    }
    parts = []
    for source_type, count in counts.items():
        name = names.get(source_type, source_type.replace("_", " ") + " source")
        parts.append(f"{count} {escape(name, quote=False)}{'s' if count != 1 else ''}")
    return "<strong>Evidence:</strong> " + " · ".join(parts)


def _feedback_buttons(labels: tuple[str, ...], *, primary_first: bool = True) -> str:
    buttons = []
    for index, label in enumerate(labels):
        css = ' class="primary"' if primary_first and index == 0 else ""
        buttons.append(f"<button{css}>{escape(label, quote=False)}</button>")
    return '<div class="buttons">' + "".join(buttons) + "</div>"


def _backing_pill(store: Store, finding_id: int) -> str:
    for item in reversed(store.feedback(finding_id)):
        if item.get("action") != "back":
            continue
        simulated = " · simulated" if item.get("simulated") else ""
        return (
            f'<span class="pill lead">backed by '
            f'{escape(str(item.get("role") or "leadership"), quote=False)}{simulated}</span>'
        )
    return ""


def _open_evidence_html(item: dict[str, Any], label: str = "Open") -> str:
    source = _evidence_source_html(item)
    if source.startswith('<a href='):
        return re.sub(r">source</a>$", f">{escape(label, quote=False)}</a>", source)
    return source


def _cost_label(run: dict[str, Any]) -> str:
    rejudge_cost = _rejudge_cost(run)
    run_cost = float(run.get("cost_usd") or 0) - rejudge_cost
    label = f"US${run_cost:.2f} at API prices"
    if run.get("route") == "sdk":
        label += " (run on a Claude subscription)"
    if rejudge_cost:
        label += f" · + US${rejudge_cost:.2f} demo re-judging (judge re-run after the run finished)"
    return label


def _rejudge_cost(run: dict[str, Any]) -> float:
    """Return later judge reruns kept in the cumulative run ledger."""
    usage = run.get("model_usage")
    if not isinstance(usage, dict):
        return 0.0
    rejudge = usage.get("rejudge")
    passes = rejudge if isinstance(rejudge, list) else [rejudge]
    cost = 0.0
    for pass_usage in passes:
        if not isinstance(pass_usage, dict):
            continue
        for model_usage in pass_usage.values():
            if not isinstance(model_usage, dict):
                continue
            try:
                cost += float(model_usage.get("costUSD") or 0)
            except (TypeError, ValueError):
                continue
    return cost


def _chart(
    stats_db: str | Path,
    finding: dict[str, Any],
    as_of: str,
    *,
    width: int = 680,
    height: int = 340,
    title: str | None = None,
) -> str:
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
    return render(
        title or finding["claim"], labels, values, selected[0], chart["y_label"], width=width, height=height,
    )


def _finding_card(finding: dict[str, Any], href: str) -> str:
    return (
        f'<article class="card"><a href="{href}"><strong>{escape(headline_for(finding), quote=False)}</strong></a><br>'
        f'{_kind_badge(finding)}{_status_badge(finding)}{_audience_pill(finding)}'
        f'<p class="muted">{escape(str(finding.get("claim") or ""), quote=False)}</p>{_signoffs_html(finding)}</article>'
    )


_FOLLOWUP_LABELS = {
    "rarity": "Rarity",
    "on_pace": "On pace",
    "comparison": "Comparison",
    "context": "Context",
}


def _followups(finding: dict[str, Any]) -> list[dict[str, str]]:
    """Defend the static site against malformed legacy ledger values."""
    items = finding.get("followups")
    if not isinstance(items, list):
        return []
    output: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind, question, why = item.get("type"), item.get("question"), item.get("why")
        if kind not in _FOLLOWUP_LABELS or not isinstance(question, str) or not isinstance(why, str):
            continue
        if question.strip() and why.strip():
            output.append({"type": kind, "question": question.strip(), "why": why.strip()})
    return output


def _shell_quote_question(question: str) -> str:
    """Quote a generated question safely for the displayed POSIX-shell command."""
    escaped = question.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("$", "\\$").replace("`", "\\`").replace("\n", " ")
    return f'"{escaped}"'


def _followups_html(finding: dict[str, Any], game_id: str, *, collapsed: bool = False) -> str:
    items = _followups(finding)
    if not items:
        return "<p class=\"muted\">No suggested follow-ups yet.</p>"
    cards = []
    for item in items:
        projection = '<span class="pill projection">Projection</span>' if item["type"] == "on_pace" else ""
        command = (
            f"python -m storydesk run follow_up --game {game_id} --anchor {finding['id']} "
            f"--question {_shell_quote_question(item['question'])} --live"
        )
        command_html = (
            f"<details><summary>Run it locally</summary><pre><code>{escape(command, quote=False)}</code></pre></details>"
            if collapsed else f"<pre><code>{escape(command, quote=False)}</code></pre>"
        )
        cards.append(
            f'<article class="{"follow-card" if collapsed else "card"}"><p><span class="pill">'
            f'{escape(_FOLLOWUP_LABELS[item["type"]])}</span>{projection}</p>'
            f"<strong>{escape(item['question'], quote=False)}</strong><p class=\"muted\">{escape(item['why'], quote=False)}</p>"
            f"{command_html}</article>"
        )
    return "".join(cards)


def _judge_score(finding: dict[str, Any]) -> float:
    values = []
    for field in ("novelty", "audience_fit", "direction"):
        try:
            values.append(float(finding[field]))
        except (KeyError, TypeError, ValueError):
            continue
    return sum(values) / len(values) if values else 0.0


def _leadership_followups_html(findings: list[dict[str, Any]]) -> str:
    candidates = [
        (_judge_score(finding), finding["id"], position, finding, item)
        for finding in findings
        for position, item in enumerate(_followups(finding))
    ]
    if not candidates:
        return "<p class=\"muted\">No suggested follow-ups yet.</p>"
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    cards = []
    for _score, finding_id, _position, finding, item in candidates[:3]:
        projection = ' <span class="pill projection">Projection</span>' if item["type"] == "on_pace" else ""
        cards.append(
            f'<article class="card suggested-followup"><p><span class="pill">{escape(_FOLLOWUP_LABELS[item["type"]])}</span>{projection} '
            f'<a href="../findings/{finding_id}.html">{escape(headline_for(finding), quote=False)}</a></p>'
            f"<strong>{escape(item['question'], quote=False)}</strong><p class=\"muted\">{escape(item['why'], quote=False)}</p></article>"
        )
    return "".join(cards)


def _finding_page(
    store: Store, stats_db: str | Path, finding: dict[str, Any], pages: set[int], published_run_ids: set[int],
) -> str:
    run = store.get_run(finding["run_id"])
    chart = _chart(stats_db, finding, run["as_of"])
    evidence = store.evidence(finding["id"])
    chart_query = finding.get("query") or (finding.get("chart") or {}).get("query")
    query_html = (
        f'<details><summary>Show the query</summary><pre>{escape(str(chart_query), quote=False)}</pre></details>'
        if chart_query else '<span class="muted">Recheck data unavailable.</span>'
    )

    chain: list[dict[str, Any]] = []
    parent_id = finding.get("parent_id")
    seen = {finding["id"]}
    while parent_id in pages and parent_id not in seen:
        parent = store.get_finding(parent_id)
        chain.append(parent)
        seen.add(parent_id)
        parent_id = parent.get("parent_id")
    chain.reverse()
    trail = [
        f'<div class="timeline-step"><span class="step-tag">{escape(str(item.get("source_type") or "finding"), quote=False)}</span> '
        f'{escape(headline_for(item), quote=False)} · <a href="{item["id"]}.html">Open</a></div>'
        for item in chain
    ]
    for item in evidence:
        quote = _HANDLE.sub("", str(item.get("quote") or "")).strip()
        title = escape(str(item.get("ref") or item.get("source_type") or "Evidence"), quote=False)
        description = f'<p>{escape(quote, quote=False)}</p>' if quote else ""
        source = _open_evidence_html(item)
        trail.append(
            f'<div class="timeline-step"><span class="step-tag">{escape(str(item.get("source_type") or "source"), quote=False)}</span> '
            f'{title}{description}' + (f' <span class="muted">· {source}</span>' if source else "") + "</div>"
        )
    children = [
        child for child in store.game_findings(run["game_id"])
        if child.get("parent_id") == finding["id"] and child["id"] in pages
    ]
    for child in children:
        trail.append(
            f'<div class="timeline-step"><span class="step-tag">{escape(str(child.get("source_type") or "finding"), quote=False)}</span> '
            f'{escape(headline_for(child), quote=False)} · <a href="{child["id"]}.html">Open</a></div>'
        )
    trail_html = '<div class="timeline">' + "".join(trail) + "</div>"

    quotes = []
    for item in evidence:
        if item.get("source_type") == "stats" or not item.get("quote"):
            continue
        quote = _HANDLE.sub("", str(item["quote"])).strip()
        quotes.append(
            f'<div class="quote"><blockquote>{escape(quote, quote=False)}</blockquote><small>'
            f'<span class="pill">{escape(str(item.get("source_type") or "source"), quote=False)}</span> '
            f'{escape(str(item.get("ref") or ""), quote=False)} · {_open_evidence_html(item)}</small></div>'
        )
    quotes_html = "".join(quotes) or '<p class="muted">No quoted non-stats evidence is recorded for this finding.</p>'

    sources: list[str] = []
    seen_sources: set[str] = set()
    for item in evidence:
        source = _evidence_source_html(item)
        if source in seen_sources:
            continue
        seen_sources.add(source)
        sources.append(
            f'<div class="source-row"><div><span class="step-tag">{escape(str(item.get("source_type") or "source"), quote=False)}</span>'
            f'<small>{escape(str(item.get("ref") or ""), quote=False)}</small></div>{_open_evidence_html(item, "open ↗")}</div>'
        )
    sources_html = "".join(sources) or '<p class="muted">No original source is recorded.</p>'

    requests = [
        request for request in store.requests_for_anchor(finding["id"])
        if request["answered_run_id"] is None or request["answered_run_id"] in published_run_ids
    ]
    request_blocks = []
    for request in requests:
        answer_links = []
        if request["answered_run_id"]:
            for answer in store.findings(request["answered_run_id"]):
                if answer["id"] in pages:
                    answer_links.append(
                        f'<a href="{answer["id"]}.html">{escape(headline_for(answer), quote=False)}</a> '
                        f'· {escape(str(answer.get("claim") or ""), quote=False)}'
                    )
        state = "answered by the follow-up run" if answer_links else "awaiting an answer"
        answers = '<ul class="request-answers">' + "".join(f"<li>{link}</li>" for link in answer_links) + "</ul>" if answer_links else ""
        request_blocks.append(
            f'<div class="follow-card"><strong>{escape(str(request["question"]), quote=False)}</strong>'
            f'<p>Asked by {escape(str(request["asked_by"]), quote=False)} · {state}</p>{answers}</div>'
        )
    requests_html = "".join(request_blocks) or '<p class="muted">No follow-up requests yet.</p>'
    suggested_html = _followups_html(finding, run["game_id"], collapsed=True)
    try:
        ctx = ToolContext(stats_db=stats_db, store=store, corpus_dir="", run_id=run["id"], as_of=run["as_of"])
        game = get_game(ctx, run["game_id"])
        score = f"{escape(game['home_team'])} {game.get('home_score', '–')} – {game.get('away_score', '–')} {escape(game['away_team'])}"
    except Exception:
        score = "Score unavailable"
    chart_title = str((finding.get("chart") or {}).get("y_label") or headline_for(finding))
    return (
        '<section class="detail-header">'
        f'<div class="breadcrumb"><a href="../index.html">Board</a> › {score} › Finding {finding["id"]}</div>'
        '<div class="detail-title-row"><div class="detail-title-copy">'
        f'<h1>{escape(headline_for(finding), quote=False)}</h1>{_kind_badge(finding)}{_status_badge(finding)}{_audience_pill(finding)}{_usage_html(store, finding["id"])}'
        f'{_signoffs_html(finding)}<p class="detail-lead">{escape(str(finding.get("claim") or ""), quote=False)}</p>'
        f'<p class="run-cost">Run cost: {_cost_label(run)}</p></div>'
        '<div class="detail-actions"><button class="primary">Using it</button><button>Already had it</button><button>Not for us</button><button>Comment</button><button class="later-button" disabled>Make a graphic · later</button></div>'
        '</div></section><div class="detail-grid"><section class="detail-main">'
        '<section class="chart-card">'
        f'<div class="chart-title">{escape(chart_title, quote=False)}</div>'
        + (chart or '<p class="muted">No chart was released for this finding.</p>')
        + f'<div class="how-we-know"><strong>How we know · rechecked by code</strong>{query_html}</div></section>'
        f'<h2>How the agents got here</h2>{trail_html}</section><aside class="detail-side">'
        f'<h2>What people said</h2>{quotes_html}<h2 aria-label="Suggested follow-ups">Follow the lead</h2>{suggested_html}{requests_html}'
        f'<h2>Original sources</h2>{sources_html}</aside></div>'
    )


def _run_label(run: dict[str, Any]) -> str:
    return _RUN_LABELS.get(str(run.get("run_type") or ""), str(run.get("run_type") or "run").replace("_", " ").title())


def _duration_label(run: dict[str, Any]) -> str:
    minutes, seconds = divmod(int(round(float(run.get("duration_s") or 0))), 60)
    return f"{minutes}m {seconds:02d}s"


def _num_agents_label(run: dict[str, Any]) -> str:
    value = run.get("num_agents") or 0
    try:
        value = int(value)
    except (TypeError, ValueError, OverflowError):
        value = str(value)
    return escape(str(value), quote=False)


def _score_for_run(store: Store, stats_db: str | Path, run: dict[str, Any], game_id: str) -> tuple[str, str]:
    """Return the score and quarter line without manufacturing either one."""
    try:
        ctx = ToolContext(stats_db=stats_db, store=store, corpus_dir="", run_id=run["id"], as_of=run["as_of"])
        game = get_game(ctx, game_id)
    except Exception:
        return "Score unavailable", "Quarter scores unavailable"
    score = f"{escape(game['home_team'])} {game.get('home_score', '–')} – {game.get('away_score', '–')} {escape(game['away_team'])}"
    quarters = game.get("quarters") or {}
    quarter_scores = " · ".join(
        f"{escape(game[side + '_team'])} {'–'.join(str(value) for value in quarters.get(side, []) if value is not None)}"
        for side in ("home", "away") if quarters.get(side)
    )
    return score, quarter_scores or "Quarter scores unavailable"


def _directive_rows(store: Store) -> list[dict[str, Any]]:
    return [directive for directive in store.directives() if directive.get("status") == "active"]


def _directives_html(store: Store) -> str:
    directives = _directive_rows(store)
    if not directives:
        return '<p class="muted">No directives yet</p>'
    output = []
    for directive in directives:
        meta = [escape(str(directive.get("owner_role") or ""), quote=False)]
        if directive.get("mandatory"):
            meta.append("mandatory")
        if directive.get("expires"):
            meta.append(f"expires {escape(str(directive['expires']), quote=False)}")
        if directive.get("simulated"):
            meta.append("simulated")
        output.append(
            f'<div class="directive">{escape(str(directive.get("text") or ""), quote=False)}'
            f'<small>{" · ".join(meta)}</small></div>'
        )
    return "".join(output)


def _leadership_feed_html(store: Store, findings: list[dict[str, Any]]) -> str:
    actions = {"back": "Backed", "comment": "Commented", "drop": "Dropped"}
    rows = []
    finding_ids = {finding["id"] for finding in findings}
    for feedback in store.feedback():
        action = actions.get(str(feedback.get("action") or ""))
        if not action or feedback.get("finding_id") not in finding_ids:
            continue
        finding_id = feedback.get("finding_id")
        headline = next((headline_for(item) for item in findings if item["id"] == finding_id), f"Finding {finding_id}")
        text = str(feedback.get("text") or "").strip()
        simulated = ' <span class="pill simulated">simulated</span>' if feedback.get("simulated") else ""
        rows.append(
            f'<div class="leadership-item"><strong>{escape(str(feedback.get("role") or ""), quote=False)}</strong> '
            f'{action} <a href="findings/{int(finding_id)}.html">{escape(headline, quote=False)}</a>{simulated}'
            + (f'<small>{escape(text, quote=False)}</small>' if text else "") + "</div>"
        )
    grouped_signoffs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for finding in findings:
        for signoff in finding.get("signoffs") or []:
            approver = str(signoff.get("approver") or "").strip()
            audience = str(signoff.get("audience") or "").strip()
            if approver and audience:
                grouped_signoffs.setdefault((approver, audience), []).append(finding)
    for (approver, audience), signed_findings in grouped_signoffs.items():
        count = len(signed_findings)
        links = "".join(
            f'<li><a href="findings/{finding["id"]}.html">{escape(headline_for(finding), quote=False)}</a></li>'
            for finding in signed_findings
        )
        rows.append(
            f'<div class="leadership-item"><strong>{escape(approver, quote=False)}</strong> signed off '
            f'{count} held {"item" if count == 1 else "items"} for {escape(audience, quote=False)}'
            f'<ul class="signoff-links">{links}</ul></div>'
        )
    return "".join(rows) or '<p class="muted">No leadership feedback yet.</p>'


def _request_rows_html(store: Store, pages: set[int], *, prefix: str) -> str:
    rows = []
    for request in store.requests():
        if request.get("anchor_finding_id") not in pages:
            continue
        answer_links = []
        if request.get("answered_run_id"):
            for finding in store.findings(request["answered_run_id"]):
                if finding["id"] in pages:
                    answer_links.append(f'<a href="{prefix}findings/{finding["id"]}.html">{escape(headline_for(finding), quote=False)}</a>')
        state = "answered by the follow-up run" if answer_links else "awaiting answer"
        answers = '<ul class="request-answers">' + "".join(f"<li>{link}</li>" for link in answer_links) + "</ul>" if answer_links else ""
        rows.append(
            f'<div class="request-row">{escape(str(request.get("question") or ""), quote=False)}'
            f'<small>asked by {escape(str(request.get("asked_by") or ""), quote=False)} · {state}</small>{answers}</div>'
        )
    return "".join(rows) or '<p class="muted">No follow-up requests yet.</p>'


def _angle_card_html(store: Store, stats_db: str | Path, finding: dict[str, Any], run: dict[str, Any]) -> str:
    audience = " ".join(str(item) for item in finding.get("audience") or [])
    chart = _chart(
        stats_db, finding, run["as_of"], width=320, height=190, title=headline_for(finding),
    )
    evidence_class = "angle-evidence" if chart else "angle-evidence chartless"
    chart_html = f'<div>{chart}</div>' if chart else ""
    status = _status_badge(finding) if finding.get("status") == "held" else ""
    return (
        f'<article class="angle angle-{escape(str(finding.get("status") or ""), quote=True)}" data-finding="{finding["id"]}" '
        f'data-audience="{escape(audience, quote=True)}"><div class="angle-title"><a href="findings/{finding["id"]}.html">'
        f'{escape(headline_for(finding), quote=False)}</a></div>{_kind_badge(finding)}'
        f'<span class="pill">{escape(_run_label(run), quote=False)}</span>{status}{_backing_pill(store, finding["id"])}{_signoffs_html(finding)}'
        f'<p class="angle-claim">{escape(_first_sentence(finding.get("claim")), quote=False)}</p>'
        f'<div class="{evidence_class}">{chart_html}<div class="evidence-summary">{_evidence_summary(store, finding["id"])}</div></div>'
        f'{_usage_html(store, finding["id"])}{_feedback_buttons(("Using it", "Already had it", "Not for us", "Ask a follow-up"))}</article>'
    )


def _held_strip_html(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return ""
    items = []
    for finding in findings:
        category = escape(str(finding.get("sensitivity") or "sensitive"), quote=False)
        items.append(
            f'<div><a href="findings/{finding["id"]}.html">{escape(headline_for(finding), quote=False)}</a> '
            f'· held · {category} · waiting for sign-off</div>'
        )
    return '<div class="held-strip">' + "".join(items) + "</div>"


def _email_angle_html(finding: dict[str, Any]) -> str:
    return (
        f'<article class="email-angle"><a href="../findings/{finding["id"]}.html"><strong>{escape(headline_for(finding), quote=False)}</strong></a> '
        f'{_kind_badge(finding)}<p>{escape(str(finding.get("claim") or ""), quote=False)}</p>'
        f'<p>For: {escape(", ".join(str(item) for item in finding.get("audience") or []), quote=False)}</p>'
        f'{_feedback_buttons(("Back it", "Comment", "Make it a directive", "Drop"))}</article>'
    )


def _email_held_html(finding: dict[str, Any]) -> str:
    waiting = _remaining_audiences(finding)
    approval = f'Approve for {waiting[0]}' if waiting else "Approve for sign-off"
    return (
        f'<div class="held-row"><a href="../findings/{finding["id"]}.html"><strong>{escape(headline_for(finding), quote=False)}</strong></a>'
        f'<div class="held-meta">{_status_badge(finding)}{_signoffs_html(finding)}'
        f'{_feedback_buttons((approval, "Keep internal"), primary_first=False)}</div></div>'
    )


def build_site(store: Store, stats_db: str | Path, out_dir: str | Path, *, game_id: str) -> list[Path]:
    """Build the approved board, leadership email and finding-detail packets."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    runs, findings = _published_content(store, game_id)
    for finding in findings:
        finding["signoffs"] = store.signoffs(finding["id"])
    published_run_ids = {run["id"] for run in runs}
    pages = {finding["id"] for finding in findings}
    run_by_id = {run["id"]: run for run in runs}
    output: list[Path] = []

    findings_dir = out / "findings"
    if findings_dir.exists():
        for page in findings_dir.glob("*.html"):
            page.unlink()
    for finding in findings:
        output.append(_write(
            findings_dir / f'{finding["id"]}.html', headline_for(finding),
            _finding_page(store, stats_db, finding, pages, published_run_ids),
        ))

    pre = next((run for run in runs if run["run_type"] == "pre_game"), None)
    post = next((run for run in runs if run["run_type"] == "post_game"), None)
    supplemental = next((run for run in runs if run["run_type"] == "supplemental"), None)
    pre_findings = [finding for finding in findings if pre and finding["run_id"] == pre["id"]]
    supplemental_findings = [finding for finding in findings if supplemental and finding["run_id"] == supplemental["id"]]

    output.append(_write(
        out / "pre-game.html", "Pre-game briefing",
        '<p><a href="index.html">Storyline Desk</a></p><h1>Pre-game briefing</h1>'
        + (f'<p class="muted">Run cost: {_cost_label(pre)}</p>' if pre else "")
        + ("".join(_finding_card(finding, f'findings/{finding["id"]}.html') for finding in pre_findings)
           or '<p class="muted">No pre-game findings yet.</p>'),
    ))

    if post:
        score, quarter_scores = _score_for_run(store, stats_db, post, game_id)
        post_findings = [finding for finding in findings if finding["run_id"] == post["id"]]
        pre_ids = {finding["id"] for finding in pre_findings}
        moved = [finding for finding in post_findings if finding.get("parent_id") in pre_ids]
        shown = {finding["id"] for finding in moved}
        pulse = [
            finding for finding in post_findings
            if finding["status"] == "shipped" and finding.get("source_type") in {"commentary", "fans"}
            and finding["id"] not in shown
        ]
        shown.update(finding["id"] for finding in pulse)
        angles = sorted(
            (finding for finding in post_findings if finding["status"] == "shipped" and finding["id"] not in shown),
            key=lambda finding: (-_judge_score(finding), finding["id"]),
        )[:5]
        shown.update(finding["id"] for finding in angles)
        held = [finding for finding in findings if finding["status"] == "held" and finding["id"] not in shown]
        shown.update(finding["id"] for finding in held)
        addendum = [finding for finding in supplemental_findings if finding["id"] not in shown]
        minutes = int(round(float(post.get("duration_s") or 0) / 60))
        moved_html = "".join(
            f'<tr><td>{escape(headline_for(store.get_finding(finding["parent_id"])), quote=False)}</td><td>'
            f'<a href="../findings/{finding["id"]}.html">{escape(headline_for(finding), quote=False)}</a></td><td>{_kind_badge(finding)}</td></tr>'
            for finding in moved
        )
        pulse_html = "".join(
            f'<div class="compact-row"><a href="../findings/{finding["id"]}.html">{escape(headline_for(finding), quote=False)}</a> '
            f'· {escape(str(finding.get("claim") or ""), quote=False)}</div>' for finding in pulse
        )
        addendum_html = "".join(
            f'<div class="compact-row"><a href="../findings/{finding["id"]}.html">{escape(headline_for(finding), quote=False)}</a> '
            f'· {escape(_first_sentence(finding.get("claim")), quote=False)}</div>' for finding in addendum
        )
        angle_count = f'{len(angles)} {"angle" if len(angles) == 1 else "angles"}'
        email = (
            '<div class="email"><div class="mail-meta"><strong>From:</strong> NBL Storyline Desk<br>'
            '<strong>To:</strong> League leadership<br>'
            f'<strong>Subject:</strong> {score}: what moved, and {angle_count} for your call<br>'
            f'<strong>Sent:</strong> {minutes} min from a cutoff frozen at the final whistle</div>'
            f'<h1>{score}</h1><p class="muted">{_run_label(post)} · {_duration_label(post)} · {_cost_label(post)}</p>'
            f'<h2>What happened</h2><p>{escape(str(post.get("exec_summary") or "No executive summary was recorded for this run."), quote=False)}</p>'
            f'<p><strong>Final score:</strong> {score}<br><strong>Quarter scores:</strong> {quarter_scores}</p>'
            '<h2>What moved since pre-game</h2>' + (f'<table>{moved_html}</table>' if moved_html else '<p class="muted">No linked pre-game movement recorded.</p>')
            + '<h2>During the game (in-game pulse)</h2>' + (pulse_html or '<p class="muted">No in-game pulse finding.</p>')
            + '<h2>Angles for the next 48 hours</h2>' + ("".join(_email_angle_html(finding) for finding in angles) or '<p class="muted">No shipped angles yet.</p>')
            + '<h2>Held for sign-off</h2>' + ("".join(_email_held_html(finding) for finding in held) or '<p class="muted">No items are held for sign-off.</p>')
            + '<h2>Your directives</h2>' + _directives_html(store)
            + '<h2>Addendum: what\'s new since the briefing</h2>' + (addendum_html or '<p class="muted">No supplemental findings yet.</p>')
            + '<h2>Suggested follow-ups</h2>' + _leadership_followups_html(findings)
            + '<h2>Give direction</h2><p>Reply to this email in plain language. It goes to the next run and to the producers.</p>'
            + f'<footer class="email-footer"><p><a href="../index.html">Open the full board →</a></p><p>This run: {_num_agents_label(post)} agents, {_duration_label(post)}, {_cost_label(post)}</p>'
            f'<p>Feedback shown here is simulated.</p><details><summary>Editor\'s notes</summary>{_markdown_html(post.get("summary"))}</details></footer></div>'
        )
    else:
        email = (
            '<div class="email"><div class="mail-meta"><strong>From:</strong> NBL Storyline Desk<br><strong>To:</strong> League leadership</div>'
            '<h1>Post-game leadership briefing</h1><p class="muted">No post-game run yet.</p><h2>Suggested follow-ups</h2>'
            + _leadership_followups_html(findings) + '</div>'
        )
    output.append(_write(out / "outbox" / "post-game-email.html", "Post-game leadership briefing", email))

    run_order = {name: position for position, name in enumerate(_RUN_LABELS)}
    ordered_runs = sorted(runs, key=lambda run: (run_order.get(run["run_type"], len(run_order)), run["id"]))
    findings_by_run: dict[int, list[dict[str, Any]]] = {run["id"]: [] for run in ordered_runs}
    for finding in findings:
        findings_by_run.setdefault(finding["run_id"], []).append(finding)
    board_runs = {"post_game", "supplemental", "follow_up"}
    board_candidates = [
        finding for finding in findings
        if run_by_id.get(finding["run_id"], {}).get("run_type") in board_runs and finding["kind"] != "nothing_found"
        and (finding["status"] == "shipped" or (finding["status"] == "held" and finding.get("signoffs")))
    ]
    board_candidates.sort(key=lambda finding: (-_judge_score(finding), finding["id"]))
    held_internal = [
        finding for finding in findings
        if run_by_id.get(finding["run_id"], {}).get("run_type") in board_runs
        and finding["status"] == "held" and not finding.get("signoffs") and finding["kind"] != "nothing_found"
    ]
    audiences = sorted({str(audience) for finding in board_candidates for audience in finding.get("audience") or []})
    strongest = next((finding for finding in board_candidates if finding["kind"] == "checked"), None)
    follow_up = next((run for run in ordered_runs if run["run_type"] == "follow_up"), None)
    follow_up_finding = next(
        (finding for finding in findings_by_run.get(follow_up["id"], []) if finding["kind"] != "nothing_found"), None,
    ) if follow_up else None
    start_here = ['<li><a href="outbox/post-game-email.html">Read the post-game leadership email</a></li>', '<li><a href="pre-game.html">Open the pre-game briefing</a></li>']
    if strongest:
        start_here.append(f'<li><a href="findings/{strongest["id"]}.html">Inspect the strongest checked record: {escape(headline_for(strongest), quote=False)}</a></li>')
    if follow_up_finding:
        start_here.append(f'<li><a href="findings/{follow_up_finding["id"]}.html">See the follow-up answer: {escape(headline_for(follow_up_finding), quote=False)}</a></li>')
    score, _ = _score_for_run(store, stats_db, post, game_id) if post else ("No post-game score yet", "")
    role_options = '<option value="all">All</option>' + "".join(
        f'<option value="{escape(audience, quote=True)}">{escape(audience, quote=False)}</option>' for audience in audiences
    )
    board_cards = "".join(_angle_card_html(store, stats_db, finding, run_by_id[finding["run_id"]]) for finding in board_candidates)
    run_rows = []
    nothing_found = []
    for run in ordered_runs:
        run_findings = findings_by_run.get(run["id"], [])
        run_rows.append(
            f'<tr><td>{escape(_run_label(run), quote=False)}</td><td>{escape(str(run.get("as_of") or ""), quote=False)}</td>'
            f'<td>{_duration_label(run)}</td><td>{_cost_label(run)}</td><td>{len(run_findings)}</td></tr>'
        )
        nothing_found.extend(finding for finding in run_findings if finding["kind"] == "nothing_found")
    nothing_html = "".join(_finding_card(finding, f'findings/{finding["id"]}.html') for finding in nothing_found) or '<p class="muted">No empty searches were recorded.</p>'
    docs = {
        "repository": _REPO_URL,
        "README": f"{_REPO_URL}/blob/main/README.md",
        "build log": f"{_REPO_URL}/blob/main/docs/build-log.md",
        "architecture": f"{_REPO_URL}/blob/main/docs/architecture.md",
        "verification": f"{_REPO_URL}/blob/main/docs/verification.md",
    }
    how_built = " · ".join(f'<a href="{url}">{label}</a>' for label, url in docs.items())
    index = (
        '<h1>NBL Storyline Desk</h1><p>A cutoff-safe desk that turns an NBL game into checked storylines for leadership and producers.</p>'
        '<h2>Start here</h2><ul>' + "".join(start_here) + '</ul>'
        + '<section class="board"><div class="board-top"><div class="board-score"><strong>' + score + '</strong></div>'
        + f'<label>Viewing as <select id="role-switch">{role_options}</select></label></div><div class="board-grid">'
        + f'<section class="board-left"><h2 class="board-label">From leadership</h2>{_leadership_feed_html(store, findings)}<h2 class="board-label gap">Active directives</h2>{_directives_html(store)}</section>'
        + f'<section class="board-angles"><h2 class="board-label">Angles for <span id="role-heading">all audiences</span></h2>{board_cards}{_held_strip_html(held_internal)}</section>'
        + f'<section class="board-right"><h2 class="board-label">Ask the next run</h2><div class="ask-box"><textarea placeholder="Ask a follow-up question for the next run"></textarea><p>A local run starts <code>python -m storydesk run follow_up …</code>; this static site does not write back.</p></div>{_request_rows_html(store, pages, prefix="")}<h2 class="board-label gap">This run</h2>'
        + (f'<p>{_duration_label(post)} · {_cost_label(post)}</p>' if post else '<p class="muted">No post-game run yet.</p>')
        + '</section></div><footer class="board-footer">The buttons show the simulated round\'s state and do not write back.</footer></section>'
        + '<h2>Runs</h2><div class="table-wrap"><table class="runs-table"><thead><tr><th>Run</th><th>Cutoff</th><th>Duration</th><th>Cost</th><th>Findings</th></tr></thead><tbody>' + "".join(run_rows) + '</tbody></table></div>'
        + '<details><summary>Searched, nothing found</summary>' + nothing_html + '</details><h2>How this was built</h2><p>' + how_built + '</p>'
        + '''<script>document.addEventListener("DOMContentLoaded",function(){const select=document.getElementById("role-switch"),heading=document.getElementById("role-heading"),cards=document.querySelectorAll(".angle");if(!select)return;function filter(){const role=select.value;cards.forEach(card=>{card.hidden=role!=="all"&&!card.dataset.audience.split(" ").includes(role)});heading.textContent=role==="all"?"all audiences":role}select.addEventListener("change",filter)});</script>'''
    )
    output.append(_write(out / "index.html", "NBL Storyline Desk", index))
    return output
