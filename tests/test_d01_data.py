"""D1: the chosen game's play-by-play loads and reconciles; stats are visible only up to a run's cutoff."""
import pytest

from conftest import OPENER, POST, PRE


def quarters_from_pbp(rows):
    # rows: (period, max score_home, max score_away), cumulative scores -> per-quarter points
    home, away, ph, pa = [], [], 0, 0
    for _, h, a in rows:
        home.append(h - ph)
        away.append(a - pa)
        ph, pa = h, a
    return home, away


def test_pbp_quarters_reconcile_with_box_team(post_ctx):
    from storydesk.tools import stats_sql

    pbp = stats_sql(post_ctx, (
        "SELECT period, max(score_home), max(score_away) FROM pbp "
        f"WHERE match_id = '{OPENER}' AND period_type = 'regular' GROUP BY period ORDER BY period"
    ))
    home, away = quarters_from_pbp(pbp["rows"])
    assert home == [23, 25, 22, 25]
    assert away == [25, 24, 26, 22]

    box = stats_sql(post_ctx, (
        "SELECT home_away, p1_score, p2_score, p3_score, p4_score, score FROM box_team "
        f"WHERE match_id = '{OPENER}' ORDER BY home_away DESC"
    ))
    assert box["columns"][0] == "home_away"
    by_side = {r[0]: [int(x) for x in r[1:]] for r in box["rows"]}
    assert by_side["home"] == [23, 25, 22, 25, 95]
    assert by_side["away"] == [25, 24, 26, 22, 97]


def test_pbp_has_the_full_game(post_ctx):
    from storydesk.tools import stats_sql

    out = stats_sql(post_ctx, f"SELECT count(*), max(score_home), max(score_away) FROM pbp WHERE match_id = '{OPENER}'")
    n, h, a = out["rows"][0]
    assert n >= 900
    assert (h, a) == (95, 97)


@pytest.mark.parametrize("table", ["results", "box_team", "box_player", "pbp"])
def test_game_is_invisible_before_its_cutoff(pre_ctx, table):
    from storydesk.tools import stats_sql

    out = stats_sql(pre_ctx, f"SELECT count(*) FROM {table} WHERE match_id = '{OPENER}'")
    assert out["rows"][0][0] == 0


@pytest.mark.parametrize("table", ["results", "box_team", "pbp"])
def test_game_is_visible_at_post_game_cutoff(post_ctx, table):
    from storydesk.tools import stats_sql

    out = stats_sql(post_ctx, f"SELECT count(*) FROM {table} WHERE match_id = '{OPENER}'")
    assert out["rows"][0][0] >= 1


def test_history_visible_and_future_hidden(pre_ctx, post_ctx):
    from storydesk.tools import stats_sql

    assert stats_sql(pre_ctx, "SELECT count(*) FROM results WHERE season = '2025-2026'")["rows"][0][0] > 0
    assert stats_sql(post_ctx, "SELECT count(*) FROM results WHERE season = '2026-2027'")["rows"][0][0] == 1
    later = stats_sql(post_ctx, "SELECT count(*) FROM box_team WHERE season = '2026-2027'")
    assert later["rows"][0][0] == 2  # only the opener's two team rows exist at its own cutoff


def test_get_game_hides_result_before_tip_off(pre_ctx, post_ctx):
    from storydesk.tools import get_game

    before = get_game(pre_ctx, OPENER)
    assert before["status"] == "scheduled"
    assert before["home_team"] == "Melbourne United" and before["away_team"] == "Adelaide 36ers"
    assert before.get("home_score") is None and before.get("away_score") is None
    assert not before.get("quarters")

    after = get_game(post_ctx, OPENER)
    assert after["status"] == "complete"
    assert (after["home_score"], after["away_score"]) == (95, 97)
    assert after["quarters"] == {"home": [23, 25, 22, 25], "away": [25, 24, 26, 22]}
