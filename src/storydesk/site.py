"""Static inbox packets and finding pages for the Storyline Desk."""

from __future__ import annotations

from base64 import b64encode
from html import escape
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode

from .charts import render_bar_chart, render_line_chart, render_test_result_chart
from .data import as_of_connection
from .gates import DEFAULT_OVERRIDE_ROLES, SENSITIVE_CATEGORIES, _BOUNDARY, _RECORD_WORD, is_promotable
from .sqlsafe import validate_safe_sql
from .store import Store
from .tools import ToolContext, get_game


AGORA_CSS = """
:root { color-scheme:light dark; --text:#1a1a1a; --muted:#6b6b6b; --bg:#fff; --surface:#f5f5f5; --border:#d9d9d9; --card:#fff; --chart-ink:#1f3a5f; --positive:#3d7a4a; --negative:#a04545; --neutral:#8a8a8a; --sensitive-text:#9a4a00; --sensitive-bg:#fdf0e1; --sensitive-border:#e3a96f; --email-bg:#fff; --email-text:#1a1a1a; }
@media (prefers-color-scheme: dark) { :root { --bg:#262626; --card:#303030; --surface:#303030; --border:#444; --text:#fff; --muted:#fff; --chart-ink:#8fb3d9; --positive:#91c99d; --negative:#f0a0a0; --neutral:#fff; --sensitive-text:#fff; --sensitive-bg:#5a3415; --sensitive-border:#e3a96f; } }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text); font:15px/1.55 Inter,system-ui,sans-serif; } main { max-width:1240px; margin:auto; padding:24px 16px 48px; } h1,h2,h3,.serif,.subj { font-family:"Source Serif 4",Georgia,serif; } code,.data { font-family:ui-monospace,SFMono-Regular,monospace; } a { color:var(--chart-ink); } .muted { color:var(--muted); }
.inbox,.mail { background:var(--email-bg); color:var(--email-text); border:1px solid #cfcfcf; } .inbox { margin-bottom:12px; } .row { display:grid; grid-template-columns:70px 150px 1fr 90px; gap:10px; padding:9px 14px; border-top:1px solid #cfcfcf; font-size:13px; align-items:baseline; } .row:first-child { border-top:0; } .row .tag,.row .t { color:#5c5c5c; font-size:11px; } .row .s { font-weight:600; }
.internal-note { margin:6px 0 16px; font-size:13px; } .cols { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:18px; align-items:start; } .head { padding:12px 16px; border-bottom:1px solid #cfcfcf; font-size:12px; line-height:1.6; } .subj { font-size:19px; font-weight:600; margin:2px 0 4px; line-height:1.3; } .body { padding:16px; max-width:600px; font-size:14px; line-height:1.55; } .body h4 { font-family:Inter,system-ui,sans-serif; font-size:11px; letter-spacing:.06em; text-transform:uppercase; margin:22px 0 8px; } .lead { font-size:15px; margin-top:0; }
.item { border:1px solid #cfcfcf; background:#f3f3f3; padding:10px 12px; margin-bottom:8px; font-size:13px; } .item.sensitive { border-left:3px solid var(--sensitive-border); } .h { display:block; font-size:14px; margin-bottom:3px; } .premise { margin:0 0 5px; } .test,.status { font-size:12px; margin-top:5px; } .stance { font-size:12px; margin-top:6px; padding-top:5px; border-top:1px solid #cfcfcf; } .stance a { margin-right:8px; } .full-story { font-size:12px; margin-top:6px; } .sensitive-tag { color:var(--sensitive-text); background:var(--sensitive-bg); border:1px solid var(--sensitive-border); font-size:10px; font-weight:600; letter-spacing:.04em; padding:0 5px; text-transform:uppercase; } .chart { display:block; width:100%; border:1px solid #cfcfcf; background:#fff; padding:5px; margin:7px 0; } .reply-box { border:2px solid #1a1a1a; padding:10px 12px; margin-top:16px; font-size:13px; } .chip { display:inline-block; border:1px dashed #6b6b6b; padding:1px 7px; margin:3px 4px 0 0; font-size:12px; } .foot,.reply-thread { border-top:1px solid #cfcfcf; padding:10px 16px; font-size:11px; } .reply-thread { font-size:13px; } .simulated { border:1px solid #cfcfcf; padding:0 4px; font-size:10px; }
.board { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; } .angle { border:1px solid var(--border); border-radius:8px; padding:12px; margin:10px 0; } .detail-header,.detail-grid { background:var(--card); border:1px solid var(--border); } .detail-header { border-radius:12px 12px 0 0; padding:16px; } .detail-grid { border-top:0; border-radius:0 0 12px 12px; display:grid; grid-template-columns:minmax(0,1fr) 300px; } .detail-main,.detail-side { padding:16px; } .detail-side { border-left:1px solid var(--border); } .breadcrumb,.run-cost,.source-row small { color:var(--muted); font-size:12px; } .stance-record { margin:4px 0; font-size:13px; } .source-row { border-top:1px solid var(--border); padding:8px 0; } .quote { border-left:3px solid var(--chart-ink); padding-left:10px; margin:10px 0; } button { color:var(--text); background:var(--card); border:1px solid var(--border); border-radius:5px; padding:4px 7px; }
.board-grid { display:grid; grid-template-columns:220px minmax(0,1fr) 260px; gap:0; } .board-left,.board-angles,.board-right { padding:12px; } .board-angles,.board-right { border-left:1px solid var(--border); } .board-label { color:var(--muted); font-size:11px; letter-spacing:.05em; text-transform:uppercase; } .directive,.request-row { border-left:3px solid var(--chart-ink); background:var(--surface); margin:7px 0; padding:7px; font-size:13px; } .held-strip { border:1px dashed var(--sensitive-border); padding:8px; margin:8px 0; font-size:13px; }
svg { max-width:100%; height:auto; } pre { white-space:pre-wrap; overflow:auto; margin:6px 0; } .mail a { color:#1f3a5f; }
.pill { display:inline-block; border:1px solid var(--border); border-radius:99px; padding:1px 8px; font-size:12px; line-height:1.4; margin:2px 4px 2px 0; white-space:nowrap; }
.pill.held { white-space:normal; color:var(--sensitive-text); background:var(--sensitive-bg); border-color:var(--sensitive-border); }
.table-wrap { overflow-x:auto; } .runs-table { border-collapse:collapse; width:100%; font-size:13px; } .runs-table td,.runs-table th { text-align:left; padding:6px 8px; border-bottom:1px solid var(--border); vertical-align:top; } .runs-section { margin-top:28px; } .runs-section details { margin:10px 0; }
.board-top { display:flex; flex-wrap:wrap; gap:6px 16px; justify-content:space-between; padding:10px 14px; margin:-18px -18px 0; border-bottom:1px solid var(--border); background:var(--surface); border-radius:12px 12px 0 0; } .board-summary { padding:10px 0; border-bottom:1px solid var(--border); font-size:13px; } .board-summary details { margin-top:6px; } .board-label.gap { margin-top:18px; }
.angle-title { font-weight:700; } .angle-claim { font-size:13px; margin:4px 0 8px; } .angle-evidence { display:grid; grid-template-columns:minmax(0,320px) 1fr; gap:12px; align-items:start; background:var(--surface); border-radius:7px; padding:8px 10px; } .angle-evidence.chartless { display:block; } .evidence-summary { font-size:12px; }
.chart-card { border:1px solid var(--border); border-radius:9px; padding:12px; margin:14px 0; } .chart-title { font-weight:700; margin-bottom:6px; } .how-we-know { margin-top:8px; background:var(--surface); border-radius:6px; padding:6px 10px; font-size:12px; } .how-we-know details { margin-top:4px; }
.timeline { border-left:2px solid var(--border); margin-left:6px; padding-left:16px; } .timeline-step { margin:10px 0; font-size:13px; } .timeline-step p { margin:3px 0; } .step-tag { background:var(--surface); border:1px solid var(--border); font-size:10px; font-weight:700; letter-spacing:.05em; padding:0 5px; border-radius:4px; text-transform:uppercase; }
.follow-card { border:1px dashed var(--border); border-radius:8px; margin:8px 0; padding:9px; } .follow-card > strong { display:block; line-height:1.35; } .follow-card p { font-size:13px; margin:4px 0; } .request-answers { margin:4px 0 0; padding-left:16px; font-size:12px; } .request-row small,.directive small { display:block; font-size:12px; } .quote small { display:block; font-size:12px; margin-top:4px; } .quote blockquote { margin:0; } .stance-records { font-size:12px; margin-top:5px; } .result-link { font-size:12px; margin-top:5px; }
@media (max-width:760px) { main { padding:16px 8px; } .cols,.detail-grid,.board-grid { grid-template-columns:1fr; } .detail-side,.board-angles,.board-right { border-left:0; border-top:1px solid var(--border); } .row { grid-template-columns:60px 1fr; } .row>span:nth-child(2),.row .tag { display:none; } .angle-evidence { grid-template-columns:1fr; } }
"""

_HANDLE = re.compile(r"(?:\bu/[A-Za-z0-9_-]+|@[A-Za-z0-9_-]+)")
_PARENTHETICAL = re.compile(r"\s*\([^()]*\)")
_META_SENTENCE = re.compile(
    r"^(?:(?:this )?answers? (?:the )?(?:producer )?(?:follow[- ]up )?question"
    r"|(?:user |producer )?follow[- ]up (?:to|on|for) finding \d+)\b",
    re.IGNORECASE,
)
_PRIMARY_RUN_TYPES = ("pre_game", "post_game", "supplemental")
_RUN_LABELS = {"pre_game": "Pre-game", "post_game": "Post-game", "supplemental": "Supplemental", "follow_up": "Follow-up"}
_PUBLISHED_FINDING_STATUSES = {"shipped", "held"}
_FOLLOWUP_LABELS = {"rarity": "Rarity", "on_pace": "On pace", "comparison": "Comparison", "context": "Context"}
_REPO_URL = "https://github.com/fridai-dot-dev/nbl-storyline-desk"
_ASK_ADDRESS = "storyline-desk@example.com"


def _page(title: str, body: str, stylesheet: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{escape(title)}</title>'
            f'<link rel="stylesheet" href="{stylesheet}"></head><body><main>{body}</main></body></html>')


def _write(path: Path, title: str, body: str, *, asset_root: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    stylesheet = Path(os.path.relpath(asset_root / "assets" / "agora.css", path.parent)).as_posix()
    path.write_text(_page(title, body, stylesheet), encoding="utf-8")
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

    follow_ups = [run for run in all_runs if run["run_type"] == "follow_up" and run["status"] == "complete"]
    while True:
        published_finding_ids = {
            finding["id"] for finding in all_findings
            if finding["run_id"] in published_run_ids and finding["status"] in _PUBLISHED_FINDING_STATUSES
        }
        newly_published = [
            run["id"] for run in follow_ups
            if run["id"] not in published_run_ids and anchors_by_run.get(run["id"], set()) & published_finding_ids
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
    """A safe compact fallback until a copy pass supplies plain_headline."""
    headline = str(finding.get("plain_headline") or finding.get("headline") or "").strip()
    if headline:
        claim = str(finding.get("claim") or "")
        boundary = _BOUNDARY.search(claim)
        if _RECORD_WORD.search(headline) and boundary and not _BOUNDARY.search(headline):
            return f"{headline} ({boundary.group()})"
        return headline
    claim = str(finding.get("claim") or "")
    while _PARENTHETICAL.search(claim):
        claim = _PARENTHETICAL.sub("", claim)
    pieces = [part.strip() for part in re.split(r"(?<=[.!?])\s+", claim) if part.strip()]
    while len(pieces) > 1 and _META_SENTENCE.match(pieces[0]):
        pieces.pop(0)
    return " ".join((pieces[0] if pieces else claim).split()[:25])


def _first_sentence(value: Any) -> str:
    """The claim's first substantive sentence, skipping lead-ins such as "User follow-up to finding 34."."""
    pieces = [part.strip() for part in re.split(r"(?<=[.!?])\s+", str(value or "")) if part.strip()]
    while len(pieces) > 1 and _META_SENTENCE.match(pieces[0]):
        pieces.pop(0)
    return pieces[0] if pieces else ""


def _copy_headline(finding: dict[str, Any]) -> str:
    return str(finding.get("plain_headline") or headline_for(finding)).strip()


def _copy_premise(finding: dict[str, Any]) -> str:
    return str(finding.get("premise") or _first_sentence(finding.get("claim"))).strip()


def _duration_label(run: dict[str, Any] | None) -> str:
    seconds = int(round(float((run or {}).get("duration_s") or 0)))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m {seconds:02d}s"


def _cost_label(run: dict[str, Any] | None) -> str:
    run = run or {}
    rejudge_cost = _rejudge_cost(run)
    label = f"US${float(run.get('cost_usd') or 0) - rejudge_cost:.2f} at API prices"
    if run.get("route") == "sdk":
        label += " (run on a Claude subscription)"
    if rejudge_cost:
        label += f" · + US${rejudge_cost:.2f} demo re-judging (judge re-run after the run finished)"
    return label


def _rejudge_cost(run: dict[str, Any]) -> float:
    """Later judge reruns kept in the cumulative run ledger."""
    usage = run.get("model_usage")
    if not isinstance(usage, dict):
        return 0.0
    records = usage.get("rejudge")
    values = records if isinstance(records, list) else [records]
    total = 0.0
    for record in values:
        if not isinstance(record, dict):
            continue
        for value in record.values():
            if isinstance(value, dict):
                try:
                    total += float(value.get("costUSD") or 0)
                except (TypeError, ValueError):
                    pass
    return total


def _judge_score(finding: dict[str, Any]) -> float:
    values = []
    for name in ("novelty", "audience_fit", "direction"):
        try:
            values.append(float(finding.get(name)))
        except (TypeError, ValueError):
            pass
    return sum(values) / len(values) if values else 0.0


def _followups(finding: dict[str, Any] | None) -> list[dict[str, str]]:
    """Defend the static site against malformed legacy ledger values."""
    items = (finding or {}).get("followups")
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
    return output[:3]


def _shell_quote_question(question: str) -> str:
    """Quote a generated question safely for the displayed POSIX-shell command."""
    escaped = question.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("$", "\\$").replace("`", "\\`").replace("\n", " ")
    return f'"{escaped}"'


def _image(svg: str) -> str:
    return "data:image/svg+xml;base64," + b64encode(svg.encode("utf-8")).decode("ascii")


def _chart(
    stats_db: str | Path, finding: dict[str, Any], as_of: str, *, width: int = 680, height: int = 340,
    title: str | None = None,
) -> str:
    """Draw the finding's own chart, only if its query reproduces the finding's number."""
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
    return render(title or finding["claim"], labels, values, selected[0], chart["y_label"], width=width, height=height)


def _score_for_run(store: Store, stats_db: str | Path, run: dict[str, Any], game_id: str) -> tuple[str, str]:
    """The score and quarter line as plain text, without manufacturing either one."""
    try:
        ctx = ToolContext(stats_db=stats_db, store=store, corpus_dir="", run_id=run["id"], as_of=run["as_of"])
        game = get_game(ctx, game_id)
    except Exception:
        return "Score unavailable", "Quarter scores unavailable"
    score = f"{game['home_team']} {game.get('home_score', '–')} – {game.get('away_score', '–')} {game['away_team']}"
    quarters = game.get("quarters") or {}
    quarter_scores = " · ".join(
        f"{game[side + '_team']} {'–'.join(str(value) for value in quarters.get(side, []) if value is not None)}"
        for side in ("home", "away") if quarters.get(side)
    )
    return score, quarter_scores or "Quarter scores unavailable"


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


def _open_evidence_html(item: dict[str, Any], label: str = "Open") -> str:
    source = _evidence_source_html(item)
    if source.startswith("<a href="):
        return re.sub(r">source</a>$", f">{escape(label, quote=False)}</a>", source)
    return source


def _kind_badge(finding: dict[str, Any]) -> str:
    kind = str(finding.get("kind") or "finding")
    label = {"checked": "stats checked", "attributed": "attributed", "qualitative": "qualitative"}.get(kind, kind.replace("_", " "))
    return f'<span class="pill kind">{escape(label, quote=False)}</span>'


def _status_badge(store: Store, finding: dict[str, Any]) -> str:
    if finding.get("sensitivity") not in SENSITIVE_CATEGORIES:
        return ""
    state = "stance set" if is_promotable(store, finding["id"]) else "awaiting a stance"
    return f'<span class="pill held">sensitive · {escape(str(finding.get("sensitivity")), quote=False)} · {state}</span>'


def _evidence_summary(store: Store, finding_id: int) -> str:
    counts: dict[str, int] = {}
    for item in store.evidence(finding_id):
        source_type = str(item.get("source_type") or "source")
        counts[source_type] = counts.get(source_type, 0) + 1
    if not counts:
        return '<span class="muted">No evidence summary is available.</span>'
    names = {"stats": "stats check", "commentary": "commentary quote", "fans": "fan quote", "media": "media item"}
    parts = [f"{count} {escape(names.get(kind, kind.replace('_', ' ') + ' source'), quote=False)}{'s' if count != 1 else ''}"
             for kind, count in counts.items()]
    return "<strong>Evidence:</strong> " + " · ".join(parts)


def _stance_links(finding: dict[str, Any]) -> str:
    headline = _copy_headline(finding)
    links = []
    for label, action in (("Push it", "push"), ("Use if it comes up", "use if raised"), ("Steer away", "steer away"), ("Comment", "comment")):
        query = urlencode({"subject": f"{action} on story {finding['id']}: {headline}"})
        links.append(f'<a href="mailto:{_ASK_ADDRESS}?{query}">{label}</a>')
    return "".join(links)


def _stance_records(store: Store, finding_id: int, *, empty: bool = True) -> str:
    rows = store.stances(finding_id)
    if not rows:
        return '<div class="stance-record">No stance yet.</div>' if empty else ""
    records = []
    blockers = [row for row in rows if row.get("stance") == "steer_away"]
    clearers = [row for row in rows if row.get("role") in DEFAULT_OVERRIDE_ROLES and row.get("stance") in {"push", "use_if_raised"}]
    for row in rows:
        comment = f' · “{escape(str(row["comment"]), quote=False)}”' if row.get("comment") else ""
        simulated = ' <span class="simulated">simulated</span>' if row.get("simulated") else ""
        records.append(f'<div class="stance-record">{escape(str(row["role"]), quote=False)}: '
                       f'{escape(str(row["stance"]).replace("_", " "), quote=False)}{comment}{simulated}</div>')
    for clearer in clearers:
        for blocker in blockers:
            if blocker["role"] != clearer["role"] or blocker["role"] in DEFAULT_OVERRIDE_ROLES:
                records.append(f'<div class="stance-clearance">Cleared by {escape(str(clearer["role"]), quote=False)} over '
                               f'{escape(str(blocker["role"]), quote=False)}\'s steer away</div>')
    return "".join(records)


def _story_box(store: Store, finding: dict[str, Any], *, prefix: str, chart: str = "", test_text: str | None = None, extra: str = "", after: str = "") -> str:
    sensitive = finding.get("sensitivity") in SENSITIVE_CATEGORIES
    tag = f' <span class="sensitive-tag">sensitive · {escape(str(finding.get("sensitivity")), quote=False)}</span>' if sensitive else ""
    text = test_text or str(finding.get("outcome") or "Status not yet recorded").replace("_", " ")
    records = _stance_records(store, finding["id"], empty=False)
    records_html = f'<div class="stance-records">{records}</div>' if records else ""
    return (f'<article class="item{" sensitive" if sensitive else ""}" data-finding="{finding["id"]}"{extra}>'
            f'<b class="h">{escape(_copy_headline(finding), quote=False)}</b>{tag}'
            f'<p class="premise">{escape(_copy_premise(finding), quote=False)}</p>'
            f'<div class="test">{escape(text, quote=False)}</div>{chart}{after}{records_html}'
            f'<div class="stance">{_stance_links(finding)}</div>'
            f'<div class="full-story"><a href="{prefix}findings/{finding["id"]}.html">Full story →</a></div></article>')


def _mail_header(run: dict[str, Any] | None, subject: str, kind: str = "") -> str:
    as_of = escape(str((run or {}).get("as_of") or "run cutoff"), quote=False)
    if kind == "post_game":
        minutes = int(round(float((run or {}).get("duration_s") or 0) / 60))
        sent = f"sent {minutes} min from a cutoff frozen at the final whistle"
    else:
        sent = "sent from the run cutoff"
    return (f'<div class="head"><div class="subj">Subject: {escape(subject, quote=False)}</div>'
            '<b>From: Storyline Desk</b><br><b>To: Leadership, Media, Producers, Broadcast, Partnerships manager · internal only</b><br>'
            f'{as_of} · {sent}</div>')


def _lead(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return '<p class="lead serif" data-section="lead" data-source-findings="">No finding is available for this run.</p>'
    return (f'<p class="lead serif" data-section="lead" data-source-findings="{findings[0]["id"]}">'
            f'{escape(str(findings[0].get("claim") or ""), quote=False)}</p>')


def _has_fan_data(store: Store, findings: list[dict[str, Any]]) -> bool:
    return any(item.get("source_type") == "fans" or any(row.get("source_type") == "fans" for row in store.evidence(item["id"])) for item in findings)


def _test_chart(pre: dict[str, Any], result: dict[str, Any] | None) -> tuple[str, str]:
    if pre.get("outcome") == "indeterminate":
        return "", "Indeterminate: the available result cannot answer this test."
    try:
        actual, threshold = float(pre["actual"]), float(pre["threshold"])
        linked_value = float((result or {}).get("number"))
    except (KeyError, TypeError, ValueError):
        return "", "Could not verify this test against the linked result."
    if abs(actual - linked_value) > 1e-6:
        return "", "Could not verify this test against the linked result."
    svg = render_test_result_chart(_copy_headline(pre), str(pre.get("metric") or "test"), threshold,
                                   str(pre.get("test_direction") or "at_most"), actual,
                                   str(pre.get("outcome") or "indeterminate"), width=520, height=150)
    return f'<img class="chart" alt="{escape(_copy_headline(pre), quote=True)}" src="{_image(svg)}">', str(pre.get("outcome") or "result").replace("_", " ")


def _generic_email(store: Store, run: dict[str, Any], findings: list[dict[str, Any]], title: str, *, prefix: str, kind: str) -> str:
    stories = "".join(_story_box(store, item, prefix=prefix) for item in findings if item.get("kind") != "nothing_found")
    return (f'<section class="mail" data-email-type="{kind}">{_mail_header(run, title, kind)}<div class="body">{_lead(findings)}'
            f'<h4>What the desk found</h4>{stories or "<p>No published stories.</p>"}'
            '<div class="reply-box"><b>Reply to steer what happens next</b><br>Ask for anything, for example, or reply with a number, change one, or ask your own.</div>'
            f'</div><div class="foot">{escape(_RUN_LABELS.get(str(run.get("run_type")), "Run"), quote=False)} · {_duration_label(run)} · {_cost_label(run)} · cutoff {escape(str(run.get("as_of") or ""), quote=False)} · <a href="{prefix}board.html">Open the board</a></div></section>')


def _followups_html(finding: dict[str, Any], game_id: str) -> str:
    items = _followups(finding)
    if not items:
        return '<p class="muted">No suggested follow-ups yet.</p>'
    cards = []
    for item in items:
        projection = '<span class="pill projection">Projection</span>' if item["type"] == "on_pace" else ""
        command = (f"python -m storydesk run follow_up --game {game_id} --anchor {finding['id']} "
                   f"--question {_shell_quote_question(item['question'])} --live")
        cards.append(
            f'<article class="follow-card"><p><span class="pill">{escape(_FOLLOWUP_LABELS[item["type"]])}</span>{projection}</p>'
            f'<strong>{escape(item["question"], quote=False)}</strong><p>{escape(item["why"], quote=False)}</p>'
            f'<details><summary>Run it locally</summary><pre><code>{escape(command, quote=False)}</code></pre></details></article>')
    return "".join(cards)


def _request_blocks(store: Store, finding: dict[str, Any], pages: set[int], published_run_ids: set[int]) -> str:
    blocks = []
    for request in store.requests_for_anchor(finding["id"]):
        if request["answered_run_id"] is not None and request["answered_run_id"] not in published_run_ids:
            continue
        links = []
        if request["answered_run_id"]:
            for answer in store.findings(request["answered_run_id"]):
                if answer["id"] in pages:
                    links.append(f'<a href="{answer["id"]}.html">{escape(_copy_headline(answer), quote=False)}</a> '
                                 f'· {escape(str(answer.get("claim") or ""), quote=False)}')
        state = "answered by the follow-up run" if links else "awaiting an answer"
        answers = '<ul class="request-answers">' + "".join(f"<li>{link}</li>" for link in links) + "</ul>" if links else ""
        blocks.append(f'<div class="follow-card"><strong>{escape(str(request["question"]), quote=False)}</strong>'
                      f'<p>Asked by {escape(str(request["asked_by"]), quote=False)} · {state}</p>{answers}</div>')
    return "".join(blocks) or '<p class="muted">No follow-up requests yet.</p>'


def _finding_page(store: Store, stats_db: str | Path, finding: dict[str, Any], pages: set[int], published_run_ids: set[int]) -> str:
    run = store.get_run(finding["run_id"])
    game_id = run["game_id"]
    evidence = store.evidence(finding["id"])
    chart = _chart(stats_db, finding, run["as_of"])
    chart_query = finding.get("query") or (finding.get("chart") or {}).get("query")
    query_html = (f'<details><summary>Show the query</summary><pre>{escape(str(chart_query), quote=False)}</pre></details>'
                  if chart_query else '<span class="muted">Recheck data unavailable.</span>')

    chain: list[dict[str, Any]] = []
    parent_id, seen = finding.get("parent_id"), {finding["id"]}
    while parent_id in pages and parent_id not in seen:
        parent = store.get_finding(parent_id)
        chain.append(parent)
        seen.add(parent_id)
        parent_id = parent.get("parent_id")
    chain.reverse()
    trail = [f'<div class="timeline-step"><span class="step-tag">{escape(str(item.get("source_type") or "finding"), quote=False)}</span> '
             f'{escape(_copy_headline(item), quote=False)} · <a href="{item["id"]}.html">Open</a></div>' for item in chain]
    for item in evidence:
        quote = _HANDLE.sub("", str(item.get("quote") or "")).strip()
        title = escape(str(item.get("ref") or item.get("source_type") or "Evidence"), quote=False)
        description = f"<p>{escape(quote, quote=False)}</p>" if quote else ""
        source = _open_evidence_html(item)
        trail.append(f'<div class="timeline-step"><span class="step-tag">{escape(str(item.get("source_type") or "source"), quote=False)}</span> '
                     f'{title}{description}' + (f' <span class="muted">· {source}</span>' if source else "") + "</div>")
    for child in store.game_findings(game_id):
        if child.get("parent_id") == finding["id"] and child["id"] in pages:
            trail.append(f'<div class="timeline-step"><span class="step-tag">{escape(str(child.get("source_type") or "finding"), quote=False)}</span> '
                         f'{escape(_copy_headline(child), quote=False)} · <a href="{child["id"]}.html">Open</a></div>')
    trail_html = '<div class="timeline">' + "".join(trail) + "</div>"

    quotes = []
    for item in evidence:
        if item.get("source_type") == "stats" or not item.get("quote"):
            continue
        quote = _HANDLE.sub("", str(item["quote"])).strip()
        quotes.append(f'<div class="quote"><blockquote>{escape(quote, quote=False)}</blockquote><small>'
                      f'<span class="pill">{escape(str(item.get("source_type") or "source"), quote=False)}</span> '
                      f'{escape(str(item.get("ref") or ""), quote=False)} · {_open_evidence_html(item)}</small></div>')
    quotes_html = "".join(quotes) or '<p class="muted">No quoted non-stats evidence is recorded for this finding.</p>'

    sources, seen_sources = [], set()
    for item in evidence:
        source = _evidence_source_html(item)
        if source in seen_sources:
            continue
        seen_sources.add(source)
        sources.append(f'<div class="source-row"><div><span class="step-tag">{escape(str(item.get("source_type") or "source"), quote=False)}</span> '
                       f'<small>{escape(str(item.get("ref") or ""), quote=False)}</small></div>{_open_evidence_html(item, "open ↗")}</div>')
    sources_html = "".join(sources) or '<p class="muted">No original source is recorded.</p>'

    score, _ = _score_for_run(store, stats_db, run, game_id)
    chart_title = str((finding.get("chart") or {}).get("y_label") or _copy_headline(finding))
    return (
        '<section class="detail-header"><div class="breadcrumb"><a href="../board.html">Board</a> › '
        f'{escape(score, quote=False)} › Finding {finding["id"]}</div><h1>{escape(_copy_headline(finding), quote=False)}</h1>'
        f'{_kind_badge(finding)}{_status_badge(store, finding)}{_stance_records(store, finding["id"])}'
        f'<p>{escape(_copy_premise(finding), quote=False)}</p><p class="run-cost">Run cost: {_cost_label(run)}</p>'
        '<div class="detail-actions"><button>Push it</button><button>Use if it comes up</button><button>Steer away</button><button>Comment</button></div></section>'
        '<div class="detail-grid"><section class="detail-main"><h2>Full finding</h2>'
        f'<p>{escape(str(finding.get("claim") or ""), quote=False)}</p>'
        f'<section class="chart-card"><div class="chart-title">{escape(chart_title, quote=False)}</div>'
        + (chart or '<p class="muted">No chart was released for this finding.</p>')
        + f'<div class="how-we-know"><strong>How we know · rechecked by code</strong>{query_html}</div></section>'
        f'<h2>How the agents got here</h2>{trail_html}</section><aside class="detail-side"><h2>What people said</h2>{quotes_html}'
        f'<h2 aria-label="Suggested follow-ups">Follow the lead</h2>{_followups_html(finding, game_id)}'
        f'{_request_blocks(store, finding, pages, published_run_ids)}<h2>Original sources</h2>{sources_html}</aside></div>')


def _request_rows_html(store: Store, pages: set[int], *, prefix: str) -> str:
    rows = []
    for request in store.requests():
        if request.get("anchor_finding_id") not in pages:
            continue
        links = []
        if request.get("answered_run_id"):
            for finding in store.findings(request["answered_run_id"]):
                if finding["id"] in pages:
                    links.append(f'<a href="{prefix}findings/{finding["id"]}.html">{escape(_copy_headline(finding), quote=False)}</a>')
        state = "answered by the follow-up run" if links else "awaiting answer"
        answers = '<ul class="request-answers">' + "".join(f"<li>{link}</li>" for link in links) + "</ul>" if links else ""
        rows.append(f'<div class="request-row">{escape(str(request.get("question") or ""), quote=False)}'
                    f'<small>asked by {escape(str(request.get("asked_by") or ""), quote=False)} · {state}</small>{answers}</div>')
    return "".join(rows) or '<p class="muted">No follow-up requests yet.</p>'


def _angle_card_html(store: Store, stats_db: str | Path, finding: dict[str, Any], run: dict[str, Any]) -> str:
    chart = _chart(stats_db, finding, run["as_of"], width=320, height=190, title=_copy_headline(finding))
    evidence_class = "angle-evidence" if chart else "angle-evidence chartless"
    chart_html = f"<div>{chart}</div>" if chart else ""
    return (f'<article class="angle" data-finding="{finding["id"]}"><div class="angle-title"><a href="findings/{finding["id"]}.html">'
            f'{escape(_copy_headline(finding), quote=False)}</a></div>{_kind_badge(finding)}'
            f'<span class="pill">{escape(_RUN_LABELS.get(str(run.get("run_type")), "Run"), quote=False)}</span>{_status_badge(store, finding)}'
            f'<p class="angle-claim">{escape(_copy_premise(finding), quote=False)}</p>'
            f'<div class="{evidence_class}">{chart_html}<div class="evidence-summary">{_evidence_summary(store, finding["id"])}</div></div>'
            f'{_stance_records(store, finding["id"])}</article>')


def _inbox_row(time: str, subject: str, kind: str, href: str | None) -> str:
    """One inbox row; it links only to an email that exists."""
    label = escape(subject, quote=False)
    subject_html = f'<a href="{href}">{label}</a>' if href else f"{label} (not run yet)"
    return (f'<div class="row" data-run-type="{kind}"><span class="t">{time}</span><span>Storyline Desk</span>'
            f'<span class="s">{subject_html}</span><span class="tag">{kind.replace("_", "-")}</span></div>')


def build_site(store: Store, stats_db: str | Path, out_dir: str | Path, *, game_id: str) -> list[Path]:
    """Build the approved R1 inbox, packets, board, and finding pages."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    stylesheet = assets / "agora.css"
    stylesheet.write_text(AGORA_CSS, encoding="utf-8")
    runs, findings = _published_content(store, game_id)
    published_run_ids = {run["id"] for run in runs}
    run_by_id = {run["id"]: run for run in runs}
    pages = {item["id"] for item in findings}
    output: list[Path] = [stylesheet]
    for page in (out / "findings").glob("*.html") if (out / "findings").exists() else ():
        page.unlink()
    for finding in findings:
        output.append(_write(out / "findings" / f'{finding["id"]}.html', _copy_headline(finding),
                             _finding_page(store, stats_db, finding, pages, published_run_ids), asset_root=out))

    by_type = {kind: next((run for run in reversed(runs) if run.get("run_type") == kind), None)
               for kind in ("pre_game", "post_game", "supplemental", "follow_up")}
    by_run = {run["id"]: [item for item in findings if item["run_id"] == run["id"]] for run in runs}
    pre, post = by_type["pre_game"], by_type["post_game"]
    pre_findings = by_run.get(pre["id"], []) if pre else []
    post_findings = by_run.get(post["id"], []) if post else []
    pre_stories = [item for item in pre_findings if item.get("kind") != "nothing_found"]
    results = {item.get("parent_id"): item for item in post_findings if item.get("parent_id")}
    post_score = _score_for_run(store, stats_db, post, game_id)[0] if post else "No post-game score yet"
    post_subject = f"{post_score}: what moved" if post and post_score != "Score unavailable" else "Post-game: what moved"

    pre_body = _lead(pre_stories) + '<section data-section="tests"><h4>What we\'ll test tonight</h4>'
    pre_body += "".join(_story_box(store, item, prefix="") for item in pre_stories) + '</section>'
    if _has_fan_data(store, pre_stories):
        pre_body += '<section data-section="fan-signal"><h4>What fans said after each team\'s last games</h4><p>Stored comments from recent team videos appear here.</p></section>'
    else:
        pre_body += '<p>Fan material appears on a fresh run, when collector data is available.</p>'
    pre_body += ('<div class="reply-box" data-section="reply"><b>Reply to steer tonight\'s run</b><br>Ask for anything in plain words. For example: '
                 '<span class="chip">Watch a player</span><span class="chip">Skip an angle</span><span class="chip">Add a question</span></div>'
                 f'<div class="foot" data-section="footer">Pre-game run · {_duration_label(pre)} · {_cost_label(pre)} · cutoff {escape(str((pre or {}).get("as_of") or ""), quote=False)} · <a href="board.html">Open the board</a></div>')
    pre_mail = f'<section class="mail" id="pre-game" data-email-type="pre_game">{_mail_header(pre, "Tonight: storylines to test", "pre_game")}<div class="body">{pre_body}</div></section>'

    moved = []
    for item in pre_stories:
        result = results.get(item["id"])
        chart, status = _test_chart(item, result)
        # The tested storyline remains the story being tracked; for an
        # above-threshold mismatch, the linked result is the only copy record
        # that contains the derived first whole-number result.
        display = result if item.get("test_direction") == "above" and result else item
        link = (f'<div class="result-link">Result: <a href="findings/{result["id"]}.html">{escape(_copy_headline(result), quote=False)}</a></div>'
                if result and display is not result else "")
        moved.append(_story_box(store, display, prefix="", chart=chart, test_text=status, extra=f' data-test-finding="{item["id"]}"', after=link))
    promotable = [item for item in post_findings if item.get("kind") != "nothing_found" and is_promotable(store, item["id"])]
    promotable.sort(key=lambda item: (-_judge_score(item), item["id"]))
    top = promotable[0] if promotable else None
    sensitive = [item for item in post_findings if item.get("sensitivity") in SENSITIVE_CATEGORIES]
    sensitive.sort(key=lambda item: (is_promotable(store, item["id"]), item["id"]))
    shown, left = sensitive[:4], max(0, len(sensitive) - 4)
    top_chart = ""
    if top:
        top_svg = _chart(stats_db, top, post["as_of"], width=520, height=260, title=_copy_headline(top))
        if top_svg:
            top_chart = f'<img class="chart" alt="{escape(_copy_headline(top), quote=True)}" src="{_image(top_svg)}">'
    top_html = _story_box(store, top, prefix="", chart=top_chart, test_text="Ranked first as a suggestion for the internal teams.") if top else '<p>No top pick is promotable yet.</p>'
    followup_html = '<ol>' + "".join(f'<li class="suggested-followup">{escape(item["question"], quote=False)}</li>' for item in _followups(top)) + '</ol>'
    post_body = _lead([top] if top else post_findings)
    post_body += '<section data-section="what-moved"><h4>What moved since this afternoon</h4>' + "".join(moved) + '</section>'
    post_body += '<section data-section="top-pick"><h4>The desk\'s top pick</h4>' + top_html + f'<p>{len(post_findings) - (1 if top else 0)} more stories are on the board.</p></section>'
    post_body += '<section data-section="sensitive"><h4>Sensitive stories: set a stance</h4>' + "".join(_story_box(store, item, prefix="") for item in shown) + f'<p>+ {left} more on the board</p></section>'
    post_body += '<section data-section="followups" aria-label="Suggested follow-ups"><h4>Questions worth asking next</h4><p>Reply with a number, change one, or ask your own.</p>' + followup_html + '</section>'
    post_body += '<div class="reply-box" data-section="reply"><b>Reply to steer what happens next</b><br>Ask for anything, for example, or set a stance.</div>'
    post_body += f'<div class="foot" data-section="footer">Post-game run · {_duration_label(post)} · {_cost_label(post)} · cutoff {escape(str((post or {}).get("as_of") or ""), quote=False)} · <a href="board.html">Open the board</a></div><div class="reply-thread" data-section="reply-thread"><span class="simulated">simulated</span> The reply thread records the next question.</div>'
    post_mail = f'<section class="mail" id="post-game" data-email-type="post_game">{_mail_header(post, post_subject, "post_game")}<div class="body">{post_body}</div></section>'

    for kind, filename, title in (("supplemental", "supplemental.html", "Addendum: what's new since the briefing"), ("follow_up", "follow-up.html", "Follow-up answer")):
        run = by_type[kind]
        if run:
            body = _generic_email(store, run, by_run.get(run["id"], []), title, prefix="../", kind=kind)
            output.append(_write(out / "emails" / filename, title, body, asset_root=out))

    rows = (("4:30 pm", "Tonight: storylines to test", "pre_game", "#pre-game"), ("9:29 pm", post_subject, "post_game", "#post-game"),
            ("10:53 pm", "Supplemental addendum", "supplemental", "emails/supplemental.html"), ("11:41 pm", "Follow-up answer", "follow_up", "emails/follow-up.html"))
    inbox_rows = "".join(_inbox_row(time, subject, kind, href if by_type[kind] else None) for time, subject, kind, href in rows)
    honesty = ("This is a rapid build, about 1–1.5 days of full-time work, made to show Claude agent capability. The order of operations, timing, prompts and safety controls are informed guesses, not knowledge of LK's structure or priorities.")

    run_order = {name: position for position, name in enumerate(_RUN_LABELS)}
    ordered_runs = sorted(runs, key=lambda run: (run_order.get(run["run_type"], len(run_order)), run["id"]))
    run_rows, nothing_found = [], []
    for run in ordered_runs:
        run_findings = by_run.get(run["id"], [])
        run_rows.append(f'<tr><td>{escape(_RUN_LABELS.get(run["run_type"], run["run_type"]), quote=False)}</td><td>{escape(str(run.get("as_of") or ""), quote=False)}</td>'
                        f'<td>{_duration_label(run)}</td><td>{_cost_label(run)}</td><td>{len(run_findings)}</td></tr>')
        nothing_found.extend(item for item in run_findings if item.get("kind") == "nothing_found")
    nothing_html = "".join(f'<div class="compact-row"><a href="findings/{item["id"]}.html">{escape(_copy_headline(item), quote=False)}</a></div>' for item in nothing_found) or '<p class="muted">No empty searches were recorded.</p>'
    docs = {"repository": _REPO_URL, "README": f"{_REPO_URL}/blob/main/README.md", "build log": f"{_REPO_URL}/blob/main/docs/build-log.md",
            "architecture": f"{_REPO_URL}/blob/main/docs/architecture.md", "verification": f"{_REPO_URL}/blob/main/docs/verification.md"}
    how_built = " · ".join(f'<a href="{url}">{label}</a>' for label, url in docs.items())
    runs_section = ('<section class="runs-section"><h2>Runs</h2><div class="table-wrap"><table class="runs-table"><thead><tr><th>Run</th><th>Cutoff</th><th>Duration</th><th>Cost</th><th>Findings</th></tr></thead><tbody>'
                    + "".join(run_rows) + '</tbody></table></div><details><summary>Searched, nothing found</summary>' + nothing_html
                    + '</details><h2>How this was built</h2><p>' + how_built + '</p></section>')
    index = ('<h1>The night in one inbox</h1><section class="inbox" data-region="inbox-strip">' + inbox_rows + '</section>'
             '<p class="internal-note" data-region="internal-note">Everyone on this list is internal. Anyone can set a stance: push it, use it if it comes up, or steer away. ' + honesty + '</p><div class="cols">' + pre_mail + post_mail + '</div>' + runs_section)
    output.append(_write(out / "index.html", "The night in one inbox", index, asset_root=out))

    cards, held = [], []
    for item in sorted(findings, key=lambda candidate: (-_judge_score(candidate), candidate["id"])):
        if item.get("kind") == "nothing_found":
            continue
        if is_promotable(store, item["id"]):
            cards.append(_angle_card_html(store, stats_db, item, run_by_id[item["run_id"]]))
        else:
            held.append(f'<div><a href="findings/{item["id"]}.html">{escape(_copy_headline(item), quote=False)}</a> · sensitive story awaiting a stance</div>')
    directives = []
    for directive in store.directives():
        if directive.get("status") != "active":
            continue
        details = [str(directive.get("owner_role") or "")]
        if directive.get("mandatory"):
            details.append("mandatory")
        if directive.get("expires"):
            details.append(str(directive["expires"]))
        if directive.get("simulated"):
            details.append("simulated")
        directives.append(f'<div class="directive">{escape(str(directive.get("text") or ""), quote=False)}<br><small>{escape(" · ".join(details), quote=False)}</small></div>')
    stances = "".join(_stance_records(store, item["id"]) for item in findings if store.stances(item["id"])) or '<p class="muted">No stance yet.</p>'
    if post:
        summary = (f'<div class="board-summary"><strong>What happened</strong><p>{escape(str(post.get("exec_summary") or "No executive summary was recorded for this run."), quote=False)}</p>'
                   f'<details><summary>Editor\'s notes</summary>{_markdown_html(post.get("summary"))}</details></div>')
        this_run = f'<p>{_duration_label(post)} · {_cost_label(post)}</p>'
    else:
        summary, this_run = "", '<p class="muted">No post-game run yet.</p>'
    ask = urlencode({"subject": "Question for the next run"})
    board = ('<h1>Storyline board</h1><p><a href="index.html">Back to the inbox</a></p><section class="board">'
             f'<div class="board-top"><div class="board-score"><strong>{escape(post_score, quote=False)}</strong></div></div>{summary}<div class="board-grid">'
             '<aside class="board-left"><h2 class="board-label">From the desk</h2>' + stances +
             '<h2 class="board-label">Active directives</h2>' + ("".join(directives) or '<p class="muted">No directives yet.</p>') +
             '</aside><section class="board-angles"><h2 class="board-label">Angles for the internal teams</h2>' + "".join(cards) +
             ('<div class="held-strip">' + "".join(held) + '</div>' if held else '') +
             '</section><aside class="board-right"><h2 class="board-label">Ask the next run</h2>'
             f'<p><a href="mailto:{_ASK_ADDRESS}?{ask}">Ask a question for the next run</a>, or reply through any story’s stance link to set a direction.</p>'
             + _request_rows_html(store, pages, prefix="") + '<h2 class="board-label gap">This run</h2>' + this_run + '</aside></div></section>')
    output.append(_write(out / "board.html", "Storyline board", board, asset_root=out))
    return output
