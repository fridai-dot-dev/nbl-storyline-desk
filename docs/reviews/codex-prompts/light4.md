Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md` first. Installed SDK: claude-agent-sdk 0.2.174 in `.venv`.

Fix three problems from the first live post-game run. The new checks are in `tests/test_postgame_fixes.py`.

1. **The runner abandons background specialists.** The lead starts specialists as background agents and ends its turn. With `ClaudeSDKClient` in streaming mode, that turn's result arrives while the specialists are still working. Each one then finishes with a `TaskNotificationMessage`, and the lead resumes by itself and produces another result.
   - In `storydesk.runner.run_live`, track the `TaskStartedMessage` events whose `task_type` is `local_agent`, and the `TaskNotificationMessage` events (completed, failed or stopped).
   - Don't treat a result as final while any started task is still pending. Keep reading the client's messages, for example with `receive_messages()`, until a result arrives with no task pending.
   - Only then run the coverage check, the top-up if needed, gates and the judge.
   - The wall-clock deadline still applies throughout. On timeout, `interrupt()`, drain, and record `timeout`.
   - Cost and model usage in streaming mode are cumulative, so record the latest result's values and don't sum them. The top-up path waits for background work in the same way.

2. **Search returns the earliest matches.** `search_transcripts` and `search_fans` must rank matches by relevance (the number of distinct query tokens matched), with ties broken by recency (newest first).
   - Both accept optional `since` and `until` ISO-time window arguments. A window can narrow the run's cutoff but never widen it.
   - Expose `since` and `until` on the MCP tools as well, with descriptions, and mention the window in `prompts/contract.md` so agents can target, say, the last five minutes.
   - Use the same relevance ranking for `search_media`, which keeps its day-level date rule.

3. **The post-game digest misses the finish.** Its `commentary.md` and `fans.md` must cover the end of the game. Always include the last few items before the cutoff, even when they don't match a keyword, alongside the matched items. Keep the digest compact.

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**` and `prompts/**`.

End with the done-command output and the files changed.
