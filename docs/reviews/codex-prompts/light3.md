Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md` first.

Two fixes, both found in the first live pre-game run:

1. **The lead isn't told the run's facts.** `storydesk.agents.build_prompt` gains keyword arguments `run_id=None, game_id=None, as_of=None`. When they're given, the prompt opens with a short "Run facts" block that states:
   - the run ID, the match UUID and the exact `as_of` cutoff
   - for post-game runs, that the briefing deadline is the cutoff plus 30 minutes
   - an instruction to copy these facts verbatim into every specialist task, and never to invent an ID or assume the cutoff is tip-off

   `runner.run_live` passes the real values.

2. **Recent form is ordered by a column that's always NA.** In `storydesk.prepare`, recent form and any other "latest games" queries order by `box_team.match_time`, which is NA throughout nblR's data. Order by the match's real time instead (join `results` on `match_id` and use `match_time_utc`), newest first, and include the date and season in the table. The `as_of` views still apply. Check the rest of `prepare.py` for the same mistake.

Done when `.venv/bin/python -m pytest -q` exits 0. The new checks are in `tests/test_pregame_fixes.py`. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**` and `prompts/**`.

End with the done-command output and the files changed.
