Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md` first. The new checks are in `tests/test_round3_followups.py`.

Add **suggested follow-ups** that ride the existing single judge call per run, with no extra model calls.

1. **Judge output.** Per finding, the judge may return `followups`: a list of `{type, question, why}`. The type is one of `rarity`, `on_pace`, `comparison` or `context`.
   - `score_findings` stores up to three valid ones per finding and drops invalid types.
   - Add `Store.set_followups(finding_id, items)`, and make `get_finding()` return `followups`.

2. **Judge prompt.** Update `prompts/judge.md` to propose up to three follow-ups for findings worth extending. Describe the types:
   - **rarity:** how unusual this is, league-wide or over time.
   - **on_pace:** whether it would be notable if the trend continued. It's a projection: the checked number is always the current pace, and projections are labelled and never stated as fact.
   - **comparison:** how coverage and fans reacted to past similar situations.
   - **context:** head-to-head or season framing.

   State the data limits so it never suggests questions the data can't answer:
   - play-by-play exists only for the demo game
   - box scores and results go back to 2015-16 (results further)
   - the media and fan corpus has a fixed scope

   Keep the output JSON-only, and keep the existing scores and headline.

3. **Rejudge.** Add `storydesk.judge.rejudge(store, run_id, *, stats_db, corpus_dir, scorer=None)`.
   - It re-runs the one judge call for a finished run: scores, any missing headlines, and follow-ups.
   - It never changes findings, statuses or claims.
   - It adds the judge's cost to the run's `cost_usd`, and its usage under `model_usage`.
   - The existing CLI `rejudge --run-id N --live` calls it. Without `--live` it still exits non-zero.

4. **Site.**
   - **Finding pages** get a "Suggested follow-ups" section. Each item shows its type label, the question and the why, plus a copyable command: `python -m storydesk run follow_up --game <uuid> --anchor <id> --question "<question>" --live`, with the question safely quoted. `on_pace` items carry a visible "Projection" label.
   - **The leadership email** gets a "Suggested follow-ups" section with at most three items, the best across published findings (use the judge scores to choose). Each item uses class `suggested-followup` and links to its finding page.

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**` and `prompts/judge.md`.

End with the done-command output and the files changed.
