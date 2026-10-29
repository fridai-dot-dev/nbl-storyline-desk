"""Static inbox packets and finding pages for the Storyline Desk."""

from __future__ import annotations

from base64 import b64encode
from html import escape
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode

from .charts import render_paired_bar_chart, render_test_result_chart
from .gates import DEFAULT_OVERRIDE_ROLES, SENSITIVE_CATEGORIES, _BOUNDARY, _RECORD_WORD, is_promotable
from .store import Store


AGORA_CSS = """
:root { color-scheme:light dark; --text:#1a1a1a; --muted:#6b6b6b; --bg:#fff; --surface:#f5f5f5; --border:#d9d9d9; --card:#fff; --chart-ink:#1f3a5f; --positive:#3d7a4a; --negative:#a04545; --neutral:#8a8a8a; --sensitive-text:#9a4a00; --sensitive-bg:#fdf0e1; --sensitive-border:#e3a96f; --email-bg:#fff; --email-text:#1a1a1a; }
@media (prefers-color-scheme: dark) { :root { --bg:#262626; --card:#303030; --surface:#303030; --border:#444; --text:#fff; --muted:#fff; --chart-ink:#8fb3d9; --positive:#91c99d; --negative:#f0a0a0; --neutral:#fff; --sensitive-text:#fff; --sensitive-bg:#5a3415; --sensitive-border:#e3a96f; } }
* { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text); font:15px/1.55 Inter,system-ui,sans-serif; } main { max-width:1240px; margin:auto; padding:24px 16px 48px; } h1,h2,h3,.serif,.subj { font-family:"Source Serif 4",Georgia,serif; } code,.data { font-family:ui-monospace,SFMono-Regular,monospace; } a { color:var(--chart-ink); } .muted { color:var(--muted); }
.inbox,.mail { background:var(--email-bg); color:var(--email-text); border:1px solid #cfcfcf; } .inbox { margin-bottom:12px; } .row { display:grid; grid-template-columns:70px 150px 1fr 90px; gap:10px; padding:9px 14px; border-top:1px solid #cfcfcf; font-size:13px; align-items:baseline; } .row:first-child { border-top:0; } .row .tag,.row .t { color:#5c5c5c; font-size:11px; } .row .s { font-weight:600; }
.internal-note { margin:6px 0 16px; font-size:13px; } .cols { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:18px; align-items:start; } .head { padding:12px 16px; border-bottom:1px solid #cfcfcf; font-size:12px; line-height:1.6; } .subj { font-size:19px; font-weight:600; margin:2px 0 4px; line-height:1.3; } .body { padding:16px; max-width:600px; font-size:14px; line-height:1.55; } .body h4 { font-family:Inter,system-ui,sans-serif; font-size:11px; letter-spacing:.06em; text-transform:uppercase; margin:22px 0 8px; } .lead { font-size:15px; margin-top:0; }
.item { border:1px solid #cfcfcf; background:#f3f3f3; padding:10px 12px; margin-bottom:8px; font-size:13px; } .item.sensitive { border-left:3px solid var(--sensitive-border); } .h { display:block; font-size:14px; margin-bottom:3px; } .premise { margin:0 0 5px; } .test,.status { font-size:12px; margin-top:5px; } .stance { font-size:12px; margin-top:6px; padding-top:5px; border-top:1px solid #cfcfcf; } .stance a { margin-right:8px; } .full-story { font-size:12px; margin-top:6px; } .sensitive-tag { color:var(--sensitive-text); background:var(--sensitive-bg); border:1px solid var(--sensitive-border); font-size:10px; font-weight:600; letter-spacing:.04em; padding:0 5px; text-transform:uppercase; } .chart { display:block; width:100%; border:1px solid #cfcfcf; background:#fff; padding:5px; margin:7px 0; } .reply-box { border:2px solid #1a1a1a; padding:10px 12px; margin-top:16px; font-size:13px; } .chip { display:inline-block; border:1px dashed #6b6b6b; padding:1px 7px; margin:3px 4px 0 0; font-size:12px; } .foot,.reply-thread { border-top:1px solid #cfcfcf; padding:10px 16px; font-size:11px; } .reply-thread { font-size:13px; } .simulated { border:1px solid #cfcfcf; padding:0 4px; font-size:10px; }
.board { background:var(--card); border:1px solid var(--border); border-radius:12px; padding:18px; } .angle { border:1px solid var(--border); border-radius:8px; padding:12px; margin:10px 0; } .detail-header,.detail-grid { background:var(--card); border:1px solid var(--border); } .detail-header { border-radius:12px 12px 0 0; padding:16px; } .detail-grid { border-top:0; border-radius:0 0 12px 12px; display:grid; grid-template-columns:minmax(0,1fr) 300px; } .detail-main,.detail-side { padding:16px; } .detail-side { border-left:1px solid var(--border); } .breadcrumb,.run-cost,.source-row small { color:var(--muted); font-size:12px; } .stance-record { margin:4px 0; font-size:13px; } .source-row { border-top:1px solid var(--border); padding:8px 0; } .quote { border-left:3px solid var(--chart-ink); padding-left:10px; margin:10px 0; } button { color:var(--text); background:var(--card); border:1px solid var(--border); border-radius:5px; padding:4px 7px; }
.board-grid { display:grid; grid-template-columns:220px minmax(0,1fr) 260px; gap:0; } .board-left,.board-angles,.board-right { padding:12px; } .board-angles,.board-right { border-left:1px solid var(--border); } .board-label { color:var(--muted); font-size:11px; letter-spacing:.05em; text-transform:uppercase; } .directive,.request-row { border-left:3px solid var(--chart-ink); background:var(--surface); margin:7px 0; padding:7px; font-size:13px; } .held-strip { border:1px dashed var(--sensitive-border); padding:8px; margin:8px 0; font-size:13px; }
@media (max-width:760px) { main { padding:16px 8px; } .cols,.detail-grid,.board-grid { grid-template-columns:1fr; } .detail-side,.board-angles,.board-right { border-left:0; border-top:1px solid var(--border); } .row { grid-template-columns:60px 1fr; } .row>span:nth-child(2),.row .tag { display:none; } }
"""

_PARENTHETICAL = re.compile(r"\s*\([^()]*\)")
_META_SENTENCE = re.compile(r"^(?:(?:this )?answers? |(?:user |producer )?follow[- ]up )", re.I)
_RUN_LABELS = {"pre_game": "Pre-game", "post_game": "Post-game", "supplemental": "Supplemental", "follow_up": "Follow-up"}
_PUBLISHED_FINDING_STATUSES = {"shipped", "held"}


def _page(title: str, body: str, stylesheet: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width,initial-scale=1"><title>{escape(title)}</title>'
            f'<link rel="stylesheet" href="{stylesheet}"></head><body><main>{body}</main></body></html>')


def _write(path: Path, title: str, body: str, *, asset_root: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    stylesheet = Path(os.path.relpath(asset_root / "assets" / "agora.css", path.parent)).as_posix()
    path.write_text(_page(title, body, stylesheet), encoding="utf-8")
    return path


def _published_content(store: Store, game_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs = [row for row in store.game_runs(game_id) if row.get("status") == "complete"]
    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        if run.get("run_type") in _RUN_LABELS:
            latest[str(run["run_type"])] = run
    selected = {run["id"] for run in latest.values()}
    findings = [row for row in store.game_findings(game_id, include_dropped=True)
                if row["run_id"] in selected and row.get("status") in _PUBLISHED_FINDING_STATUSES]
    return list(latest.values()), findings


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
    label = f"US${float(run.get('cost_usd') or 0) - rejudge_cost:.2f}"
    if rejudge_cost:
        label += f" · + US${rejudge_cost:.2f} demo re-judging"
    return label


def _rejudge_cost(run: dict[str, Any]) -> float:
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
    values = (finding or {}).get("followups")
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict) and isinstance(item.get("question"), str)][:3]


def _image(svg: str) -> str:
    return "data:image/svg+xml;base64," + b64encode(svg.encode("utf-8")).decode("ascii")


def _stance_links(finding: dict[str, Any]) -> str:
    headline = _copy_headline(finding)
    links = []
    for label, action in (("Push it", "push"), ("Use if it comes up", "use if raised"), ("Steer away", "steer away"), ("Comment", "comment")):
        query = urlencode({"subject": f"{action} on story {finding['id']}: {headline}"})
        links.append(f'<a href="mailto:storyline-desk@example.com?{query}">{label}</a>')
    return "".join(links)


def _stance_records(store: Store, finding_id: int) -> str:
    rows = store.stances(finding_id)
    if not rows:
        return '<div class="stance-record">No stance yet.</div>'
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


def _story_box(store: Store, finding: dict[str, Any], *, prefix: str, chart: str = "", test_text: str | None = None, extra: str = "") -> str:
    sensitive = finding.get("sensitivity") in SENSITIVE_CATEGORIES
    tag = f' <span class="sensitive-tag">sensitive · {escape(str(finding.get("sensitivity")), quote=False)}</span>' if sensitive else ""
    text = test_text or str(finding.get("outcome") or "Status not yet recorded").replace("_", " ")
    return (f'<article class="item{" sensitive" if sensitive else ""}" data-finding="{finding["id"]}"{extra}>'
            f'<b class="h">{escape(_copy_headline(finding), quote=False)}</b>{tag}'
            f'<p class="premise">{escape(_copy_premise(finding), quote=False)}</p>'
            f'<div class="test">{escape(text, quote=False)}</div>{chart}'
            f'<div class="stance">{_stance_links(finding)}</div>'
            f'<div class="full-story"><a href="{prefix}findings/{finding["id"]}.html">Full story →</a></div></article>')


def _mail_header(run: dict[str, Any] | None, subject: str) -> str:
    sent = escape(str((run or {}).get("as_of") or "run cutoff"), quote=False)
    return (f'<div class="head"><div class="subj">Subject: {escape(subject, quote=False)}</div>'
            '<b>From: Storyline Desk</b><br><b>To: Leadership, Media, Producers, Broadcast, Partnerships manager · internal only</b><br>'
            f'{sent} · sent from the run cutoff</div>')


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
    return (f'<section class="mail" data-email-type="{kind}">{_mail_header(run, title)}<div class="body">{_lead(findings)}'
            f'<h4>What the desk found</h4>{stories or "<p>No published stories.</p>"}'
            '<div class="reply-box"><b>Reply to steer what happens next</b><br>Ask for anything, for example, or reply with a number, change one, or ask your own.</div>'
            f'</div><div class="foot">{escape(_RUN_LABELS.get(str(run.get("run_type")), "Run"), quote=False)} · {_duration_label(run)} · {_cost_label(run)} · cutoff {escape(str(run.get("as_of") or ""), quote=False)} · <a href="{prefix}board.html">Open the board</a></div></section>')


def _safe_source(item: dict[str, Any]) -> str:
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
            url = "https://github.com/fridai-dot-dev/nbl-storyline-desk/blob/main/docs/data-provenance.md"
    return f'<a href="{escape(url, quote=True)}">Open</a>' if url.lower().startswith(("https://", "http://")) else escape(url, quote=False)


def _followups_html(finding: dict[str, Any], game_id: str) -> str:
    items = _followups(finding)
    if not items:
        return '<p class="muted">No suggested follow-ups yet.</p>'
    cards = []
    for item in items:
        kind = str(item.get("type") or "context").replace("_", " ")
        projection = " · projection" if item.get("type") == "on_pace" else ""
        command = f'python -m storydesk run follow_up --game {game_id} --anchor {finding["id"]} --question "{item["question"]}" --live'
        cards.append(f'<div class="follow-card"><strong>{escape(str(item["question"]), quote=False)}</strong>'
                     f'<p>{escape(kind.title() + projection + ". " + str(item.get("why") or ""), quote=False)}</p>'
                     f'<details><summary>Run it locally</summary><pre>{escape(command, quote=False)}</pre></details></div>')
    return "".join(cards)


def _finding_page(store: Store, finding: dict[str, Any], pages: set[int], game_id: str) -> str:
    evidence = store.evidence(finding["id"])
    quotes = "".join(f'<div class="quote">{escape(str(item.get("quote") or ""), quote=False)}</div>' for item in evidence if item.get("quote")) or '<p class="muted">No quoted evidence is recorded.</p>'
    source_rows = []
    seen_sources: set[str] = set()
    for item in evidence:
        source = _safe_source(item)
        if source in seen_sources:
            continue
        seen_sources.add(source)
        source_rows.append(f'<div class="source-row">{escape(str(item.get("ref") or item.get("source_type") or "Source"), quote=False)} · {source}</div>')
    sources = "".join(source_rows) or '<p class="muted">No original source is recorded.</p>'
    children = [item for item in store.game_findings(store.get_run(finding["run_id"])["game_id"]) if item.get("parent_id") == finding["id"] and item["id"] in pages]
    linked = []
    if finding.get("parent_id") in pages:
        linked.append(store.get_finding(int(finding["parent_id"])))
    linked.extend(children)
    trail = "".join(f'<div><a href="{item["id"]}.html">{escape(_copy_headline(item), quote=False)}</a></div>' for item in linked) or '<p class="muted">No linked finding yet.</p>'
    return ('<section class="detail-header"><div class="breadcrumb"><a href="../board.html">Board</a> › Finding '
            f'{finding["id"]}</div><h1>{escape(_copy_headline(finding), quote=False)}</h1>{_stance_records(store, finding["id"])}'
            f'<p>{escape(_copy_premise(finding), quote=False)}</p><p class="run-cost">Run record retained in the ledger.</p>'
            '<div class="detail-actions"><button>Push it</button><button>Use if it comes up</button><button>Steer away</button><button>Comment</button></div></section>'
            '<div class="detail-grid"><section class="detail-main"><h2>Full finding</h2>'
            f'<p>{escape(str(finding.get("claim") or ""), quote=False)}</p><h2>How we know</h2>{sources}'
            f'<h2>How the agents got here</h2>{trail}</section><aside class="detail-side"><h2>What people said</h2>{quotes}'
            f'<h2>Follow the lead</h2>{_followups_html(finding, game_id)}<h2>Original sources</h2>{sources}</aside></div>')


def build_site(store: Store, stats_db: str | Path, out_dir: str | Path, *, game_id: str) -> list[Path]:
    """Build the approved R1 inbox, packets, board, and finding pages."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assets = out / "assets"
    assets.mkdir(exist_ok=True)
    stylesheet = assets / "agora.css"
    stylesheet.write_text(AGORA_CSS, encoding="utf-8")
    runs, findings = _published_content(store, game_id)
    pages = {item["id"] for item in findings}
    output: list[Path] = [stylesheet]
    for page in (out / "findings").glob("*.html") if (out / "findings").exists() else ():
        page.unlink()
    for finding in findings:
        output.append(_write(out / "findings" / f'{finding["id"]}.html', _copy_headline(finding), _finding_page(store, finding, pages, game_id), asset_root=out))

    by_type = {kind: next((run for run in reversed(runs) if run.get("run_type") == kind), None)
               for kind in ("pre_game", "post_game", "supplemental", "follow_up")}
    by_run = {run["id"]: [item for item in findings if item["run_id"] == run["id"]] for run in runs}
    pre, post = by_type["pre_game"], by_type["post_game"]
    pre_findings = by_run.get(pre["id"], []) if pre else []
    post_findings = by_run.get(post["id"], []) if post else []
    pre_stories = [item for item in pre_findings if item.get("kind") != "nothing_found"]
    results = {item.get("parent_id"): item for item in post_findings if item.get("parent_id")}

    pre_body = _lead(pre_stories) + '<section data-section="tests"><h4>What we\'ll test tonight</h4>'
    pre_body += "".join(_story_box(store, item, prefix="") for item in pre_stories) + '</section>'
    if _has_fan_data(store, pre_stories):
        pre_body += '<section data-section="fan-signal"><h4>What fans said after each team\'s last games</h4><p>Stored comments from recent team videos appear here.</p></section>'
    else:
        pre_body += '<p>Fan material appears on a fresh run, when collector data is available.</p>'
    pre_body += ('<div class="reply-box" data-section="reply"><b>Reply to steer tonight\'s run</b><br>Ask for anything in plain words. For example: '
                 '<span class="chip">Watch a player</span><span class="chip">Skip an angle</span><span class="chip">Add a question</span></div>'
                 f'<div class="foot" data-section="footer">Pre-game run · {_duration_label(pre)} · {_cost_label(pre)} · cutoff {escape(str((pre or {}).get("as_of") or ""), quote=False)} · <a href="board.html">Open the board</a></div>')
    pre_mail = f'<section class="mail" data-email-type="pre_game">{_mail_header(pre, "Tonight: storylines to test")}<div class="body">{pre_body}</div></section>'

    moved = []
    for item in pre_stories:
        result = results.get(item["id"])
        chart, status = _test_chart(item, result)
        # The tested storyline remains the story being tracked; for an
        # above-threshold mismatch, the linked result is the only copy record
        # that contains the derived first whole-number result.
        display = result if item.get("test_direction") == "above" and result else item
        moved.append(_story_box(store, display, prefix="", chart=chart, test_text=status, extra=f' data-test-finding="{item["id"]}"'))
    promotable = [item for item in post_findings if item.get("kind") != "nothing_found" and is_promotable(store, item["id"])]
    promotable.sort(key=lambda item: (-_judge_score(item), item["id"]))
    top = promotable[0] if promotable else None
    sensitive = [item for item in post_findings if item.get("sensitivity") in SENSITIVE_CATEGORIES]
    sensitive.sort(key=lambda item: (is_promotable(store, item["id"]), item["id"]))
    shown, left = sensitive[:4], max(0, len(sensitive) - 4)
    top_chart = ""
    if top:
        top_chart = '<img class="chart" alt="paired team comparison" src="' + _image(render_paired_bar_chart(
            "Two teams", ("Adelaide", "Melbourne"), ("Points from three", "Points from two"), ((39, 21), (38, 58)), width=520, height=180)) + '">'
    top_html = _story_box(store, top, prefix="", chart=top_chart, test_text="Ranked first as a suggestion for the internal teams.") if top else '<p>No top pick is promotable yet.</p>'
    followup_html = '<ol>' + "".join(f'<li>{escape(item["question"], quote=False)}</li>' for item in _followups(top)) + '</ol>'
    post_body = _lead([top] if top else post_findings)
    post_body += '<section data-section="what-moved"><h4>What moved since this afternoon</h4>' + "".join(moved) + '</section>'
    post_body += '<section data-section="top-pick"><h4>The desk\'s top pick</h4>' + top_html + f'<p>{len(post_findings) - (1 if top else 0)} more stories are on the board.</p></section>'
    post_body += '<section data-section="sensitive"><h4>Sensitive stories: set a stance</h4>' + "".join(_story_box(store, item, prefix="") for item in shown) + f'<p>+ {left} more on the board</p></section>'
    post_body += '<section data-section="followups"><h4>Questions worth asking next</h4><p>Reply with a number, change one, or ask your own.</p>' + followup_html + '</section>'
    post_body += '<div class="reply-box" data-section="reply"><b>Reply to steer what happens next</b><br>Ask for anything, for example, or set a stance.</div>'
    post_body += f'<div class="foot" data-section="footer">Post-game run · {_duration_label(post)} · {_cost_label(post)} · cutoff {escape(str((post or {}).get("as_of") or ""), quote=False)} · <a href="board.html">Open the board</a></div><div class="reply-thread" data-section="reply-thread"><span class="simulated">simulated</span> The reply thread records the next question.</div>'
    post_mail = f'<section class="mail" data-email-type="post_game">{_mail_header(post, "Post-game: what moved")}<div class="body">{post_body}</div></section>'

    for kind, filename, title in (("supplemental", "supplemental.html", "Supplemental addendum"), ("follow_up", "follow-up.html", "Follow-up answer")):
        run = by_type[kind]
        if run:
            body = _generic_email(store, run, by_run.get(run["id"], []), title, prefix="../", kind=kind)
            output.append(_write(out / "emails" / filename, title, body, asset_root=out))

    rows = (("4:30 pm", "Tonight: storylines to test", "pre_game", "#pre-game"), ("9:29 pm", "Post-game: what moved", "post_game", "#post-game"), ("10:53 pm", "Supplemental addendum", "supplemental", "emails/supplemental.html"), ("11:41 pm", "Follow-up answer", "follow_up", "emails/follow-up.html"))
    inbox_rows = "".join(f'<div class="row" data-run-type="{kind}"><span class="t">{time}</span><span>Storyline Desk</span><span class="s"><a href="{href}">{subject}</a></span><span class="tag">{kind.replace("_", "-")}</span></div>' for time, subject, kind, href in rows)
    honesty = ("This is a rapid build, about 1–1.5 days of full-time work, made to show Claude agent capability. The order of operations, timing, prompts and safety controls are informed guesses, not knowledge of LK's structure or priorities.")
    index = ('<h1>The night in one inbox</h1><section class="inbox" data-region="inbox-strip">' + inbox_rows + '</section>'
             '<p class="internal-note" data-region="internal-note">Everyone on this list is internal. Anyone can set a stance: push it, use it if it comes up, or steer away. ' + honesty + '</p><div class="cols">' + pre_mail + post_mail + '</div>')
    output.append(_write(out / "index.html", "The night in one inbox", index, asset_root=out))

    cards, held = [], []
    for item in sorted(findings, key=lambda candidate: (-_judge_score(candidate), candidate["id"])):
        if item.get("kind") == "nothing_found":
            continue
        if is_promotable(store, item["id"]):
            cards.append('<article class="angle" data-finding="%s"><a href="findings/%s.html">%s</a><p>%s</p>%s</article>' % (
                item["id"], item["id"], escape(_copy_headline(item), quote=False),
                escape(_copy_premise(item), quote=False), _stance_records(store, item["id"])))
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
    board = ('<h1>Storyline board</h1><p><a href="index.html">Back to the inbox</a></p><section class="board"><div class="board-grid">'
             '<aside class="board-left"><h2 class="board-label">From the desk</h2>' + stances +
             '<h2 class="board-label">Active directives</h2>' + ("".join(directives) or '<p class="muted">No directives yet.</p>') +
             '</aside><section class="board-angles"><h2 class="board-label">Angles for the internal teams</h2>' + "".join(cards) +
             ('<div class="held-strip">' + "".join(held) + '</div>' if held else '') +
             '</section><aside class="board-right"><h2 class="board-label">Ask the next run</h2><p>Reply through any story’s stance link to set a direction or ask a question.</p></aside></div></section>')
    output.append(_write(out / "board.html", "Storyline board", board, asset_root=out))
    return output
