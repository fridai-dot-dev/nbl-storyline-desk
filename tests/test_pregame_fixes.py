"""Checks from the first live pre-game run (2026-10-28).

The lead wasn't told the run's cutoff, ID or match, so it guessed "cutoff = tip-off" and invented a run ID. The
digest's recent-form table ordered by box_team.match_time, which is NA in nblR, so it listed old seasons as "recent".
"""
import csv
import re

from conftest import CORPUS, FIX, OPENER, PRE

TEAMS = {"Melbourne United", "Adelaide 36ers"}


def test_lead_prompt_states_the_run_facts(tmp_path):
    from storydesk.agents import build_prompt

    text = build_prompt("pre_game", digest_dir=tmp_path, run_id=42, game_id=OPENER, as_of=PRE)
    assert PRE in text
    assert re.search(r"\b42\b", text)
    assert OPENER in text


def test_recent_form_lists_the_latest_games_first(stats_db, store, tmp_path):
    from storydesk.prepare import prepare_run

    with open(FIX / "box_team.csv", newline="", encoding="utf-8") as f:
        boxed = {r["match_id"] for r in csv.DictReader(f)}
    with open(FIX / "results.csv", newline="", encoding="utf-8") as f:
        played = [r for r in csv.DictReader(f)
                  if r["match_id"] in boxed and r["match_status"] == "COMPLETE"
                  and {r["home_team_name"], r["away_team_name"]} & TEAMS and r["match_time_utc"] < "2026-09-19T06:30"]
    latest = max(played, key=lambda r: r["match_time_utc"])

    out = prepare_run("pre_game", game_id=OPENER, as_of=PRE, stats_db=stats_db, store=store,
                      corpus_dir=CORPUS, out_dir=tmp_path / "digest")
    form = (out / "form.md").read_text(encoding="utf-8")
    table_rows = [line for line in form.splitlines() if line.startswith("|") and "---" not in line][1:]
    assert table_rows, "recent form table is empty"
    assert latest["match_id"] in table_rows[0], f"expected the latest game ({latest['match_time_utc']}) first"
