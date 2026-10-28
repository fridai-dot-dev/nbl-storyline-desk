"""Shared fixtures. Interfaces used here are frozen by the design (docs/superpowers/specs) and the build brief."""
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"
CORPUS = FIX / "corpus"

OPENER = "36dbeb55-58ad-11f1-a69b-43a6b5595d3e"  # NBL27 R1: Melbourne United 95-97 Adelaide 36ers
PRE = "2026-09-19T06:30:00+00:00"   # pre-game cutoff (tip-off 09:30Z)
POST = "2026-09-19T11:26:37+00:00"  # post-game cutoff: the final period's End event (the final whistle)
SUPP = "2026-09-19T12:20:00+00:00"  # supplemental cutoff (pressers done)

Q3_ADL = (
    "SELECT p3_score FROM box_team "
    f"WHERE match_id = '{OPENER}' AND name = 'Adelaide 36ers'"
)
Q3_CHART = " UNION ALL ".join(
    f"SELECT 'Q{q}' AS label, p{q}_score AS value, {'true' if q == 3 else 'false'} AS highlight "
    f"FROM box_team WHERE match_id = '{OPENER}' AND name = 'Adelaide 36ers'"
    for q in (1, 2, 3, 4)
)
EV_STATS = {"source_type": "stats", "url": f"https://www.nbl.com.au/game/{OPENER}", "ref": "box_team:Adelaide 36ers"}
EV_COMMENTARY = {
    "source_type": "commentary",
    "url": "https://example.test/broadcast#t=5400",
    "ref": "2026-09-19T10:55:00+00:00",
    "quote": "Adelaide have won the third quarter on the back of their bench.",
}
EV_FAN = {
    "source_type": "fans",
    "url": "https://example.test/thread/c2",
    "ref": "2026-09-19T11:25:30+00:00",
    "quote": "What a finish, the bench won it for Adelaide",
}


@pytest.fixture(scope="session")
def stats_db(tmp_path_factory):
    from storydesk.data import build_stats_db

    db = tmp_path_factory.mktemp("stats") / "stats.duckdb"
    build_stats_db(
        db,
        results_csv=FIX / "results.csv",
        box_team_csv=FIX / "box_team.csv",
        box_player_csv=FIX / "box_player.csv",
        match_json_paths=[FIX / "match_opener.json"],
    )
    return db


@pytest.fixture
def store(tmp_path):
    from storydesk.store import Store

    s = Store(tmp_path / "store.db")
    s.init()
    return s


def make_ctx(stats_db, store, run_type, as_of):
    from storydesk.tools import ToolContext

    run_id = store.start_run(run_type, OPENER, as_of, route="test")
    return ToolContext(stats_db=stats_db, store=store, corpus_dir=CORPUS, run_id=run_id, as_of=as_of)


@pytest.fixture
def post_ctx(stats_db, store):
    return make_ctx(stats_db, store, "post_game", POST)


@pytest.fixture
def pre_ctx(stats_db, store):
    return make_ctx(stats_db, store, "pre_game", PRE)


def fake_result(cost, duration_s):
    """Stand-in for claude_agent_sdk.ResultMessage with the fields the runner records."""
    return SimpleNamespace(
        subtype="success",
        is_error=False,
        total_cost_usd=cost,
        duration_ms=int(duration_s * 1000),
        num_turns=12,
        model_usage={"claude-opus-5-5": {"inputTokens": 1000, "outputTokens": 200}},
        terminal_reason=None,
        result="done",
    )


@pytest.fixture
def demo_store(stats_db, store):
    """A small, realistic run history: pre-game, post-game (gated), a follow-up, simulated feedback."""
    from storydesk.gates import apply_gates
    from storydesk.runner import record_result
    from storydesk.tools import write_finding

    ns = SimpleNamespace(store=store, stats_db=stats_db)

    pre = make_ctx(stats_db, store, "pre_game", PRE)
    ns.pre_finding = write_finding(
        pre, agent="media", source_type="media", kind="qualitative",
        claim="Previews frame Melbourne's defence against Adelaide's bench as the matchup to watch",
        evidence=[{"source_type": "media", "url": "https://example.test/news/preview", "ref": "2026-09-18"}],
        audience=["producers", "social"],
    )
    apply_gates(store, pre.run_id, stats_db=stats_db, as_of=PRE)
    record_result(store, pre.run_id, fake_result(0.91, 640), route="sdk", num_agents=5)

    post = make_ctx(stats_db, store, "post_game", POST)
    ns.post_run = post.run_id
    ns.f_checked = write_finding(
        post, agent="stats", source_type="stats", kind="checked",
        claim="Adelaide scored 26 points in the third quarter", number=26, query=Q3_ADL,
        chart={"type": "bar", "query": Q3_CHART, "y_label": "Adelaide points"},
        evidence=[EV_STATS], audience=["leadership", "producers"],
    )
    ns.f_wrong = write_finding(
        post, agent="stats", source_type="stats", kind="checked",
        claim="Adelaide scored 30 points in the third quarter", number=30, query=Q3_ADL,
        evidence=[EV_STATS],
    )
    ns.f_attr = write_finding(
        post, agent="commentary", source_type="commentary", kind="attributed",
        claim="Commentators credited Adelaide's bench for the third quarter",
        evidence=[EV_COMMENTARY], parent_id=ns.f_checked, audience=["producers"],
    )
    ns.f_held = write_finding(
        post, agent="fans", source_type="fans", kind="qualitative", sensitivity="officiating",
        claim="Fans questioned the officiating in the final two minutes",
        evidence=[{"source_type": "fans", "url": "https://example.test/thread/c1", "ref": "2026-09-19T11:00:00+00:00"}],
    )
    ns.f_fan = write_finding(
        post, agent="fans", source_type="fans", kind="qualitative", sensitivity="fan_quote",
        claim="Fans credited Adelaide's bench for the win", evidence=[EV_FAN], audience=["social"],
    )
    write_finding(post, agent="media", source_type="media", kind="nothing_found",
                  claim="No pre-cutoff media coverage mentioned the third quarter", evidence=[])
    apply_gates(store, post.run_id, stats_db=stats_db, as_of=POST)
    store.add_signoff(ns.f_fan, approver="Head of social", audience="producers")
    store.add_feedback(ns.f_checked, role="CEO", action="back", text="Lead with this", simulated=True)
    record_result(store, post.run_id, fake_result(2.10, 1180), route="sdk", num_agents=5)

    ns.request = store.add_request(ns.f_checked, asked_by="NBL Now producer",
                                   question="Was this Adelaide's best quarter of the game?")
    fu = make_ctx(stats_db, store, "follow_up", POST)
    ns.follow_run = fu.run_id
    ns.f_child = write_finding(
        fu, agent="stats", source_type="stats", kind="checked", parent_id=ns.f_checked,
        claim="Adelaide's 26-point third quarter was its highest-scoring quarter of the game",
        number=26,
        query=("SELECT greatest(p1_score, p2_score, p3_score, p4_score) FROM box_team "
               f"WHERE match_id = '{OPENER}' AND name = 'Adelaide 36ers'"),
        evidence=[EV_STATS], audience=["producers"],
    )
    apply_gates(store, fu.run_id, stats_db=stats_db, as_of=POST)
    store.answer_request(ns.request, fu.run_id)
    record_result(store, fu.run_id, fake_result(0.42, 210), route="sdk", num_agents=2)
    return ns


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def run_py(*args, timeout=120):
    """Run `python <args>` from the repo root with src/ importable (no install needed)."""
    env = {**os.environ, "PYTHONPATH": str(REPO / "src")}
    return subprocess.run([sys.executable, *args], cwd=REPO, capture_output=True, text=True, timeout=timeout, env=env)
