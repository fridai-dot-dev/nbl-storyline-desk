"""Regression checks for Sol's final pre-publication review (2026-10-29)."""
import asyncio
import html
import re
import time
from pathlib import Path

import pytest

from conftest import CORPUS, EV_STATS, OPENER, POST, REPO, fake_result, make_ctx
from test_review_fixes import FakeClient, _digest_text

QUESTION = "Was this Adelaide's best quarter of the game?"


class FollowUpClient(FakeClient):
    """FakeClient's "write" covers post-game sources; a follow-up also requires media."""

    def _write_findings(self):
        from storydesk.store import Store
        from storydesk.tools import ToolContext, write_finding

        super()._write_findings()
        env = self.options.mcp_servers["desk"]["env"]
        ctx = ToolContext(stats_db=env["STORYDESK_STATS_DB"], store=Store(env["STORYDESK_STORE"]),
                          corpus_dir=env["STORYDESK_CORPUS"], run_id=int(env["STORYDESK_RUN_ID"]),
                          as_of=env["STORYDESK_AS_OF"])
        write_finding(ctx, agent="media", source_type="media", kind="nothing_found",
                      claim="No media items mentioned the third quarter", evidence=[])


def _follow_up(ns, tmp_path, behaviour, client_cls=FollowUpClient, **kw):
    from storydesk.runner import run_live

    def factory(options):
        return client_cls(options, behaviour)

    return asyncio.run(run_live(
        "follow_up", game_id=OPENER, as_of=POST, stats_db=ns.stats_db, store=ns.store, corpus_dir=CORPUS,
        digest_dir=tmp_path / f"digest-{behaviour}", client_factory=factory, question=QUESTION,
        anchor_finding_id=ns.f_attr, asked_by="NBL Now producer", judge_scorer=lambda f, c: ({}, 0.0), **kw))


def _requests(ns):
    return ns.store.requests_for_anchor(ns.f_attr)


# ---------- high: only a complete run answers a follow-up request ----------

@pytest.mark.parametrize("behaviour,kw", [("hang", {"time_limit_s": 0.3}), ("empty", {})])
def test_unfinished_follow_up_leaves_the_request_pending(demo_store, tmp_path, behaviour, kw):
    run_id = _follow_up(demo_store, tmp_path, behaviour, **kw)
    assert demo_store.store.get_run(run_id)["status"] in {"timeout", "incomplete"}
    [request] = _requests(demo_store)
    assert request["answered_run_id"] is None


def test_failed_follow_up_leaves_the_request_pending(demo_store, tmp_path):
    with pytest.raises(RuntimeError):
        _follow_up(demo_store, tmp_path, "raise")
    [request] = _requests(demo_store)
    assert request["answered_run_id"] is None


def test_retry_completes_the_pending_request_instead_of_duplicating_it(demo_store, tmp_path):
    _follow_up(demo_store, tmp_path, "empty")
    run_id = _follow_up(demo_store, tmp_path, "write")
    assert demo_store.store.get_run(run_id)["status"] == "complete"
    [request] = _requests(demo_store)
    assert request["answered_run_id"] == run_id


# ---------- medium: the deadline stays a deadline when interrupt stalls or fails ----------

class StallingInterruptClient(FakeClient):
    async def interrupt(self):
        self.interrupted.set()
        await asyncio.Event().wait()  # the SDK's control request never answers


class FailingInterruptClient(FakeClient):
    async def interrupt(self):
        self.interrupted.set()
        raise RuntimeError("Control request timeout: interrupt")


@pytest.mark.parametrize("client_cls", [StallingInterruptClient, FailingInterruptClient])
def test_timeout_survives_a_stalled_or_failing_interrupt(monkeypatch, store, stats_db, tmp_path, client_cls):
    from storydesk import runner

    monkeypatch.setattr(runner, "INTERRUPT_GRACE_S", 0.2, raising=True)
    start = time.monotonic()
    run_id = asyncio.run(runner.run_live(
        "post_game", game_id=OPENER, as_of=POST, stats_db=stats_db, store=store, corpus_dir=CORPUS,
        digest_dir=tmp_path / "digest", client_factory=lambda o: client_cls(o, "hang"),
        judge_scorer=lambda f, c: ({}, 0.0), time_limit_s=0.3))
    elapsed = time.monotonic() - start
    run = store.get_run(run_id)
    assert run["status"] == "timeout"
    assert elapsed < 3.0, f"timeout took {elapsed:.1f}s to finalise"


async def test_enforce_deadline_bounds_a_stalled_interrupt(monkeypatch):
    from storydesk import runner

    monkeypatch.setattr(runner, "INTERRUPT_GRACE_S", 0.2, raising=True)

    async def slow():
        await asyncio.sleep(30)

    async def stalled():
        await asyncio.Event().wait()

    start = time.monotonic()
    status, result = await runner.enforce_deadline(slow(), 0.2, stalled)
    assert (status, result) == ("timeout", None)
    assert time.monotonic() - start < 3.0


# ---------- medium: evidence links are web links or inert text ----------

UNSAFE = ["javascript:alert(1)", " JaVaScRiPt:alert(1)", "java\tscript:alert(1)", "data:text/html,<b>x</b>",
          "vbscript:msgbox(1)", "mcp__desk__search_transcripts", "search_fans://until=2026-09-19"]
_SCHEME = re.compile(r"^([a-z][a-z0-9+.-]*):")


def _unsafe_hrefs(page_html):
    bad = []
    for raw in re.findall(r'href="([^"]*)"', page_html):
        value = re.sub(r"[\x00-\x20]", "", html.unescape(raw)).lower()  # browsers drop these before parsing
        scheme = _SCHEME.match(value)
        if scheme and scheme.group(1) not in {"http", "https"}:
            bad.append(raw)
        elif not scheme and not re.match(r"^(\.\./|[\w./-]+\.html|#|[\w-]+/)", value):
            bad.append(raw)  # a bare tool name or query is not a link
    return bad


def test_evidence_links_are_web_links_or_inert_text(demo_store, tmp_path):
    from storydesk.gates import apply_gates
    from storydesk.runner import record_result
    from storydesk.site import build_site
    from storydesk.tools import write_finding

    ctx = make_ctx(demo_store.stats_db, demo_store.store, "post_game", POST)
    evidence = [{"source_type": "commentary", "url": url, "ref": POST, "quote": "Quote"} for url in UNSAFE]
    evidence.append({"source_type": "commentary", "url": "https://example.test/broadcast?t=90", "ref": POST,
                     "quote": "Safe quote"})
    fid = write_finding(ctx, agent="commentary", source_type="commentary", kind="attributed",
                        claim="Commentators called the third quarter the turning point", evidence=evidence)
    apply_gates(demo_store.store, ctx.run_id, stats_db=demo_store.stats_db, as_of=POST)
    record_result(demo_store.store, ctx.run_id, fake_result(1.0, 120), route="sdk", num_agents=5)
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)

    page = (out / "findings" / f"{fid}.html").read_text(encoding="utf-8")
    assert _unsafe_hrefs(page) == []
    assert 'href="https://example.test/broadcast?t=90"' in page
    assert "mcp__desk__search_transcripts" in page          # the reference is still shown, as text
    for other in out.rglob("*.html"):
        assert _unsafe_hrefs(other.read_text(encoding="utf-8")) == [], other.name


def test_committed_site_has_no_unsafe_or_broken_links():
    for page in (REPO / "site").rglob("*.html"):
        assert _unsafe_hrefs(page.read_text(encoding="utf-8")) == [], page.relative_to(REPO)


# ---------- the agents guessed stats source URLs (all 404); code links the real source ----------

RELEASES = "https://github.com/JaseZiv/nblr_data/releases/tag/"
PROVENANCE = "https://github.com/fridai-dot-dev/nbl-storyline-desk/blob/main/docs/data-provenance.md"
GUESSED = ("github.com/nblr/", "github.com/nblr-data/", "api.nbl.com.au")


@pytest.mark.parametrize("url,ref,expected", [
    ("https://github.com/nblr/nblr_data/releases/box_player.csv", "match_id=X; name=Cole Anthony", RELEASES + "pbp"),
    ("https://github.com/nblr-data/releases/results.csv", "match_id=X", RELEASES + "match_results"),
    ("https://www.nbl.com.au/game/X", "box_team:Adelaide 36ers", RELEASES + "box_team"),
    ("https://api.nbl.com.au/matches/X/playbyplay", "match_id=X; action_id=12", PROVENANCE),
    ("https://example.test/anything", "a total with no table named", PROVENANCE),
])
def test_stats_evidence_links_to_the_real_data_source(demo_store, tmp_path, url, ref, expected):
    from storydesk.gates import apply_gates
    from storydesk.runner import record_result
    from storydesk.site import build_site
    from storydesk.tools import write_finding

    ctx = make_ctx(demo_store.stats_db, demo_store.store, "post_game", POST)
    fid = write_finding(ctx, agent="media", source_type="media", kind="qualitative",
                        claim="Previews called the bench the difference",
                        evidence=[{"source_type": "stats", "url": url, "ref": ref},
                                  {"source_type": "media", "url": "https://example.test/news/a", "ref": POST}])
    apply_gates(demo_store.store, ctx.run_id, stats_db=demo_store.stats_db, as_of=POST)
    record_result(demo_store.store, ctx.run_id, fake_result(1.0, 120), route="sdk", num_agents=5)
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    page = (out / "findings" / f"{fid}.html").read_text(encoding="utf-8")
    assert f'href="{expected}"' in page
    assert ref in html.unescape(page)                                   # the exact rows are still named
    assert 'href="https://example.test/news/a"' in page                 # non-stats links are untouched


def test_committed_site_links_stats_evidence_to_real_sources():
    for page in (REPO / "site").rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert not [g for g in GUESSED if g in text], page.relative_to(REPO)


# ---------- medium: the game digest names both teams in the score line ----------

def test_game_digest_score_line_names_both_teams(demo_store, tmp_path):
    text = _digest_text("post_game", POST, demo_store, tmp_path)
    assert "Final score: Melbourne United 95 – 97 Adelaide 36ers" in text
