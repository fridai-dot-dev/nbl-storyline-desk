Fix round. The adversarial review of your build returned needs-attention. Fix every finding below; all of them are in scope. The integrator added regression checks in `tests/test_review_fixes.py` (commit 6a249ef) and tightened D13 in `tests/test_live.py`. Never edit anything under `tests/`.

Done when `.venv/bin/python -m pytest -q` exits 0, including `tests/test_review_fixes.py`.

## Findings to fix

1. **critical: the MCP `write_finding` tool can't be called.** With mcp 2.3.0, `mcp_write_finding(**kwargs)` registers a single required `kwargs` field. Give every MCP tool an explicit signature that matches `tools.py`, and a one-line description, because agents see the descriptions.

2. **critical: the raw tables bypass the `as_of` views.** Only the four cutoff-safe relations (`results`, `box_team`, `box_player`, `pbp`) may be reachable from `stats_sql`, finding rechecks and chart queries. That includes subqueries and CTEs, and excludes `information_schema`, `duckdb_*` functions and other table functions. Use an allowlist, or a connection or catalog that contains only the safe relations; your choice. Rechecks and chart queries must use the identical restriction.

3. **high: lifecycle events can satisfy the smoke proof.** Only PostToolUse writes `tool_calls` rows with real tool names. Record SubagentStart and SubagentStop separately, either under a distinct non-`mcp__desk__` tool label or in their own table, so that D13 counts only real `mcp__desk__*` calls.

4. **high: the live deadline and ledger aren't end to end.** `run_live` gains three parameters: `client_factory=None` (default `ClaudeSDKClient`), `judge_scorer=None` and `time_limit_s=None` (default from `RUN_TYPES`). Then:
   - Measure monotonic wall time from before prepare through gates and judging, give each phase only the time that remains, and store that elapsed time as `duration_s`.
   - On timeout, call `interrupt()`, then drain the interrupted response for a bounded grace period (about 30 s) to get its `ResultMessage` cost and usage.
   - Finalise every run in try/finally with status `complete`, `incomplete`, `timeout` or `error`, plus real elapsed time, cost and usage. Re-raise unexpected exceptions after finalising.

5. **high: context-dependent runs start without the findings they extend.**
   - `prepare_run(..., anchor_finding_id=None)`:
     - follow-up digests include the anchor finding's ID, claim, evidence (URLs, refs, quotes) and lineage
     - post-game digests include the pre-game run's shipped findings, plus feedback and directives
     - supplemental digests include the post-game run's shipped findings and never dropped ones
     - an unknown anchor, or one from a different game, raises `ValueError`
   - The lead must copy the relevant slice into every specialist task message, because specialists see only that message.

6. **high: coverage and the judge are never executed.**
   - After the agent run, check `RUN_TYPES[run_type]["required_sources"]`. If any source is missing and time remains, send exactly one top-up query on the same client. If it's still missing, the status is `incomplete`.
   - Then make exactly one judge call. `judge_scorer(findings, coverage_texts) -> (scores_by_finding_id, cost_usd)`. The default is one no-tool Claude call using `prompts/judge.md`.
   - Choose `coverage_texts` from pre-cutoff media and transcripts by team and title terms, not by match UUID.
   - Add the judge's cost and usage to the run's ledger entry.

7. **medium: the prompts lack the operational contract.** Add `prompts/contract.md`, included in the lead's system prompt and in every specialist's prompt. It covers:
   - the four relations and their key columns, including the `box_team` `p1_score`–`p4_score`, `name` and `home_away`; the `pbp` `score_home`/`score_away`, `period` and `period_type`; and the `results` `match_time_utc` and team names
   - the `write_finding` payload and the four kinds
   - evidence conventions: for stats, the URL is the actual data source (the nblr_data release CSV URL for results and box scores, the NBL match API URL for `pbp`) and the ref names the rows, for example `match_id=…; name=…` or `action_id=…`
   - the chart contract: a query returning `label`, `value` and `highlight`, with exactly one highlighted row, whose value equals the finding's number
   - the "since at least 2015-16" wording, and the sensitivity categories
   - target finding counts per run type: about 5–8 for pre-game, 6–10 for post-game, 2–4 for supplemental, 1–3 for follow-up
   - audiences: leadership, producers, social, broadcast, partners
   - an instruction that specialist task messages must carry the cutoff, the IDs and the relevant digest and prior-finding context

8. **medium: the default pre-game cutoff is wrong.** Add `cli.default_as_of(run_type, *, stats_db, game_id) -> str`, returning ISO UTC with a `+00:00` offset:
   - pre-game: scheduled tip-off (`match_time_utc`) minus 3 hours
   - post-game: the completed event, truncated to the second
   - supplemental: the end plus 45 minutes
   - follow-up: the end

   The CLI uses it whenever `--as-of` is omitted.

End with the report the brief asks for: the done-command output, the files changed, any calls you made that the design didn't, and anything you left alone.
