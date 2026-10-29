Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md` first.

Goal: a match's end time, which drives `as_of` visibility in `storydesk.data` and the default cutoffs in `storydesk.cli.default_as_of`, is now the **final whistle**. It's taken from the match payload in this order:
1. the timestamp of the `play_by_play` event with `action_type == "period"` and `sub_type == "End"` in the highest period, truncated to the second
2. failing that, the `system_action_type == "game_game_completed"` event, truncated to the second
3. failing that, `results.match_time_utc` plus 3 hours

For the opener this gives 2026-09-19T11:26:37 UTC. The `game_game_completed` event at 11:35:07 is the official stats sign-off and is no longer the end time. Payload timestamps are UTC with no offset. Some events lack keys such as `sub_type`, so read them defensively.

Done when `.venv/bin/python -m pytest -q` exits 0. The checks that changed are in `tests/conftest.py` (POST), `tests/test_review_fixes.py::test_default_cutoffs` and `tests/fixtures/corpus/`. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**`.

End with the done-command output and the files changed.
