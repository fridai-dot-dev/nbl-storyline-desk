Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md` first. The new checks are in `tests/test_round2b_runs.py`.

1. **Error text never becomes a summary.** `record_result` stores `runs.summary` only for a successful result. A run cut off by the subscription's session limit returned an error result whose text was that message, and it was stored as the summary.

2. **The site publishes only the latest complete run of each type.**
   - For each of pre-game, post-game and supplemental, the site uses only the latest run whose status is `complete`.
   - Runs that are failed, incomplete, timed out or superseded never reach the site, and neither do their findings.
   - Follow-up runs are included when complete and their anchor finding is published.
   - Smoke runs stay excluded. Apply this in one place and use it for every page.

3. **Supplemental findings appear as an addendum.** The leadership email gains an "Addendum: what's new since the briefing" section for the published supplemental run's findings, with headline, tags, held badges and links. Supplemental findings get finding pages like the others.

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**`.

End with the done-command output and the files changed.
