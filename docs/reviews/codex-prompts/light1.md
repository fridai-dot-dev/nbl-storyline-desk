Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md` and `docs/handoffs/2026-10-28-round-1-core.md` for context.

Goal: make the new checks pass.

1. **Tool-call logging must not contend for the store.** The PostToolUse and lifecycle hooks in `storydesk/agents.py` must not write to SQLite during a run. In the first live run, parallel specialists lost hook rows to lock contention with the MCP server process.
   - Have the hooks append one JSON line per event to a per-run log file next to the store. Keep each line small: truncate `args_json`. The hook must return immediately even while another connection holds an exclusive lock on the store.
   - Add `storydesk.runner.ingest_tool_log(store, run_id)`. It loads that file into `tool_calls` and is idempotent, so calling it twice adds no duplicate rows.
   - `run_live` calls it in its `finally` block.

2. **Validate `source_type`.** Add `storydesk.tools.SOURCE_TYPES` = (stats, commentary, media, fans, press, directives). `write_finding` raises `ToolError` when the finding's `source_type`, or any evidence item's `source_type`, isn't in that set.
   - Name each value in backticks in `prompts/contract.md`, and say that `source_type` must be one of them.
   - Say that commentary transcripts use `commentary`, and press conferences use `press`.

Done when `.venv/bin/python -m pytest -q` exits 0. The new checks are `tests/test_smoke_fixes.py` and the updated `test_post_tool_use_hook_records_agent_identity` in `tests/test_review_fixes.py`. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**` and `prompts/contract.md`.

End with: the done-command output, the files changed, and any calls you made beyond the above.
