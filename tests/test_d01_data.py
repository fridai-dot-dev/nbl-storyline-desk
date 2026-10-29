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


def test_build_handles_numeric_and_uuid_match_ids(tmp_path):
    """Real nblR files mix numeric FIBA ids (older seasons) with UUIDs (newer ones)."""
    import csv

    from conftest import FIX
    from storydesk.data import build_stats_db

    rows = list(csv.reader(open(FIX / "box_player.csv", newline="", encoding="utf-8")))
    header, body = rows[0], rows[1:]
    old = list(body[0])
    old[header.index("match_id")] = "2155555"
    old[header.index("season")] = "2016-2017"
    mixed = tmp_path / "box_player.csv"
    with open(mixed, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows([old] * 25000 + body)  # UUIDs first appear past DuckDB's ~20k-row sniffing sample, as in the real file

    db = tmp_path / "mixed.duckdb"
    build_stats_db(db, results_csv=FIX / "results.csv", box_team_csv=FIX / "box_team.csv",
                   box_player_csv=mixed, match_json_paths=[FIX / "match_opener.json"])
    assert db.exists()


def test_box_team_rescrapes_are_deduplicated(tmp_path, store):
    """nblR's box_team has a few near-identical rescrapes (same match and team); count each team once."""
    import csv

    from conftest import FIX, OPENER, POST
    from storydesk.data import build_stats_db
    from storydesk.tools import ToolContext, stats_sql

    rows = list(csv.reader(open(FIX / "box_team.csv", newline="", encoding="utf-8")))
    header, body = rows[0], rows[1:]
    i_match, i_fouls = header.index("match_id"), header.index("fouls")
    victim = next(r for r in body if r[i_match] == OPENER)
    rescrape = list(victim)
    rescrape[i_fouls] = "0"
    path = tmp_path / "box_team.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(body + [rescrape])

    db = tmp_path / "dedupe.duckdb"
    build_stats_db(db, results_csv=FIX / "results.csv", box_team_csv=path, box_player_csv=FIX / "box_player.csv",
                   match_json_paths=[FIX / "match_opener.json"])
    ctx = ToolContext(stats_db=db, store=store, corpus_dir=FIX / "corpus",
                      run_id=store.start_run("post_game", OPENER, POST, route="test"), as_of=POST)
    out = stats_sql(ctx, f"SELECT count(*), max(fouls) FROM box_team WHERE match_id = '{OPENER}' AND name = '{victim[header.index('name')]}'")
    n, fouls = out["rows"][0]
    assert n == 1
    assert fouls == int(victim[i_fouls])  # the real foul count wins over the zeroed rescrape
