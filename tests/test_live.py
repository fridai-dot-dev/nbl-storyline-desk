"""D10, D11, D13: checked against the store from real runs on Bart's login.

Marked `live` and excluded by default (pytest.ini addopts). Run deliberately with: pytest -m live
They read store/demo.db, written by `storydesk run ... --live`. No unattended loop runs these.
"""
import os
import sqlite3
from pathlib import Path

import pytest

from conftest import REPO

pytestmark = pytest.mark.live
DEMO = Path(os.environ.get("STORYDESK_DEMO_STORE", REPO / "store" / "demo.db"))
SPECIALISTS = {"stats", "commentary", "media", "fans"}


@pytest.fixture
def con():
    if not DEMO.exists():
        pytest.skip(f"no live store at {DEMO}")
    c = sqlite3.connect(DEMO)
    c.row_factory = sqlite3.Row
    return c


def test_d13_every_specialist_can_call_a_tool(con):
    run = con.execute("SELECT id FROM runs WHERE run_type = 'smoke' ORDER BY id DESC LIMIT 1").fetchone()
    assert run, "no smoke run recorded"
    # Only real desk tool calls count; lifecycle events (SubagentStart/Stop) must not satisfy this.
    rows = con.execute("SELECT DISTINCT agent_type FROM tool_calls WHERE run_id = ? AND agent_id IS NOT NULL "
                       "AND tool LIKE 'mcp__desk__%'", (run["id"],)).fetchall()
    assert SPECIALISTS <= {r["agent_type"] for r in rows}


def test_d10_post_game_inside_time_limit(con):
    run = con.execute("SELECT * FROM runs WHERE run_type = 'post_game' AND route != 'test' "
                      "ORDER BY id DESC LIMIT 1").fetchone()
    assert run, "no post-game run recorded"
    assert run["status"] == "complete"
    assert run["duration_s"] <= 1500


def test_d11_follow_ups_answer_with_checked_findings(con):
    reqs = con.execute("SELECT * FROM requests WHERE answered_run_id IS NOT NULL").fetchall()
    assert reqs, "no answered follow-up requests"
    for req in reqs:
        kids = con.execute("SELECT id, parent_id FROM findings WHERE run_id = ? AND kind = 'checked' "
                           "AND status = 'shipped'", (req["answered_run_id"],)).fetchall()
        assert kids, f"request {req['id']} has no shipped checked findings"

        def reaches_anchor(fid):
            seen = set()
            while fid and fid not in seen:
                if fid == req["anchor_finding_id"]:
                    return True
                seen.add(fid)
                row = con.execute("SELECT parent_id FROM findings WHERE id = ?", (fid,)).fetchone()
                fid = row["parent_id"] if row else None
            return False

        assert any(reaches_anchor(k["id"]) for k in kids)
