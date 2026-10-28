"""D2 recheck, D3 coverage, D5 sensitive hold, data-boundary phrasing."""
import pytest

from conftest import EV_STATS, OPENER, POST, Q3_ADL


def _checked(ctx, claim, number, query=Q3_ADL, **kw):
    from storydesk.tools import write_finding

    return write_finding(ctx, agent="stats", source_type="stats", kind="checked",
                         claim=claim, number=number, query=query, evidence=[EV_STATS], **kw)


def _statuses(store, run_id):
    return {f["id"]: f["status"] for f in store.findings(run_id, include_dropped=True)}


# ---------- D2 ----------

def test_recheck_drops_wrong_numbers_and_ships_right_ones(post_ctx, store, stats_db):
    from storydesk.gates import apply_gates, recheck_finding

    good = _checked(post_ctx, "Adelaide scored 26 points in the third quarter", 26)
    bad = _checked(post_ctx, "Adelaide scored 30 points in the third quarter", 30)
    frac = _checked(post_ctx, "Adelaide averaged 24.25 points a quarter", 24.25,
                    query=f"SELECT avg(x) FROM (SELECT unnest([p1_score, p2_score, p3_score, p4_score]) AS x "
                          f"FROM box_team WHERE match_id = '{OPENER}' AND name = 'Adelaide 36ers')")
    summary = apply_gates(store, post_ctx.run_id, stats_db=stats_db, as_of=POST)

    st = _statuses(store, post_ctx.run_id)
    assert st[good] == "shipped" and st[frac] == "shipped"
    assert st[bad] == "dropped"
    shipped_checked = [f for f in store.findings(post_ctx.run_id) if f["kind"] == "checked"]
    assert shipped_checked and all(recheck_finding(stats_db, POST, f) for f in shipped_checked)
    assert summary["recheck_pass_rate"] == 1.0
    assert summary["dropped"] >= 1


def test_recheck_cannot_see_past_the_cutoff(post_ctx, store, stats_db):
    from storydesk.gates import apply_gates

    future = _checked(post_ctx, "Adelaide played a game in October", 1,
                      query="SELECT count(*) > 0 FROM results WHERE match_time_utc >= '2026-10-01' "
                            "AND (home_team_name = 'Adelaide 36ers' OR away_team_name = 'Adelaide 36ers')")
    apply_gates(store, post_ctx.run_id, stats_db=stats_db, as_of=POST)
    assert _statuses(store, post_ctx.run_id)[future] == "dropped"


# ---------- D3 ----------

def test_coverage_reports_missing_sources(post_ctx, store):
    from storydesk.gates import coverage
    from storydesk.tools import write_finding

    _checked(post_ctx, "Adelaide scored 26 points in the third quarter", 26)
    write_finding(post_ctx, agent="media", source_type="media", kind="nothing_found",
                  claim="No pre-cutoff coverage mentioned the third quarter", evidence=[])
    cov = coverage(store, post_ctx.run_id, ["stats", "media", "fans"])
    assert cov["stats"] == 1
    assert cov["media"] == "nothing found"
    assert cov["fans"] == 0


# ---------- D5 ----------

def test_sensitive_findings_are_held_until_signed_off_per_audience(post_ctx, store, stats_db):
    from storydesk.gates import SENSITIVE_CATEGORIES, apply_gates, visible_findings
    from storydesk.tools import write_finding

    assert {"conflict", "injury", "officiating", "legal", "fan_quote"} <= set(SENSITIVE_CATEGORIES)
    fid = write_finding(post_ctx, agent="fans", source_type="fans", kind="qualitative", sensitivity="officiating",
                        claim="Fans questioned the officiating in the final two minutes",
                        evidence=[{"source_type": "fans", "url": "https://example.test/thread/c1",
                                   "ref": "2026-09-19T11:00:00+00:00"}])
    apply_gates(store, post_ctx.run_id, stats_db=stats_db, as_of=POST)
    assert store.get_finding(fid)["status"] == "held"

    def ids(aud):
        return {f["id"] for f in visible_findings(store, post_ctx.run_id, aud)}

    assert fid in ids("internal")
    assert fid not in ids("producers") and fid not in ids("partners")
    store.add_signoff(fid, approver="NBL GM", audience="producers")
    assert fid in ids("producers")
    assert fid not in ids("partners")


# ---------- data boundary ----------

@pytest.mark.parametrize("claim,needs,ok", [
    # A record claim whose "since" reaches the start of the box-score/pbp data (2015-16) must say "since at least".
    ("Most fourth-quarter points against United since 2015-16", True, False),
    ("Most fourth-quarter points against United since at least 2015-16", True, True),
    ("Most points in a quarter against United since 2015/16", True, False),
    # "since 2019" names the previous occurrence, inside the data: no boundary needed.
    ("Adelaide's first win in Melbourne since 2019", False, True),
    ("Adelaide scored 26 points in the third quarter", False, True),
])
def test_data_boundary_phrasing(claim, needs, ok):
    from storydesk.gates import boundary_ok, needs_boundary

    assert needs_boundary(claim) is needs
    assert boundary_ok(claim) is ok


def test_gate_drops_record_claim_without_boundary(post_ctx, store, stats_db):
    from storydesk.gates import apply_gates

    fid = _checked(post_ctx, "Adelaide's most third-quarter points in Melbourne since 2015-16", 26)
    apply_gates(store, post_ctx.run_id, stats_db=stats_db, as_of=POST)
    assert store.get_finding(fid)["status"] == "dropped"
