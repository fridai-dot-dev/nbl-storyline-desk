# Sol adversarial review: round 1 (gpt-5.6-sol)

Verdict: **needs-attention**

## [critical] write_finding cannot be called through the installed MCP server
File: `src/storydesk/mcp_server.py`

With mcp 2.3.0, the **kwargs signature registers an input schema containing one required field named `kwargs`. A normal call with agent/source_type/claim/etc. fails schema validation; nesting those fields under `kwargs` then passes an unexpected `kwargs` argument to tools.write_finding. Specialists therefore cannot persist any finding on the live path.

Recommendation: Give mcp_write_finding an explicit signature matching tools.write_finding. Add a test against server.list_tools() and server.call_tool() using the installed MCP version, not only the hard-coded --list-tools output.

## [critical] stats_sql can bypass every as_of view through raw tables
File: `src/storydesk/data.py`

as_of_connection adds filtered temporary views but leaves raw_results, raw_box_team, raw_box_player, raw_pbp and match_ends visible in the same catalog. `_validate_select` permits `SELECT ... FROM raw_results`, so agents can read future matches directly. Recheck and chart execution use the same connection without a relation allowlist, meaning a post-cutoff claim can recheck and reach the site.

Recommendation: Restrict parsed SQL to the four approved relations, including nested queries and table functions, or expose a separate database/catalog containing only cutoff-safe relations. Apply the identical restriction to finding rechecks and chart queries.

## [high] SubagentStop events can falsely satisfy the MCP smoke proof
File: `src/storydesk/agents.py`

The shared callback writes every SubagentStop into tool_calls with the specialist's agent_id and agent_type, using `SubagentStop` as the tool name. Consequently, merely spawning and stopping all specialists produces attributable tool-call rows even if none reached the Desk MCP server. This can conceal the broken write_finding registration and other MCP failures.

Recommendation: Distinguish lifecycle events from tool calls, and make D13 count only attributable PostToolUse records whose tool is an actual `mcp__desk__*` tool. Validate at least one real server call per specialist.

## [high] The live deadline and ledger are not end-to-end or reliable on failure
File: `src/storydesk/runner.py`

The 1500-second timer starts only after digest preparation, option construction and SDK connection, and it ends before gates and judging. The stored duration comes from ResultMessage.duration_ms rather than wall time from preparation through gates. On timeout, interrupt() is followed by immediate cancellation instead of draining the SDK 0.2.174 ResultMessage, losing total_cost_usd and model_usage; other exceptions bypass record_result entirely and leave the run pending. A late run can therefore be labelled complete and within the cap, while timeout/error spend is unrecorded.

Recommendation: Measure monotonic wall time around the complete prepare-to-gates/judge pipeline, pass only the remaining budget to each phase, drain the interrupted response for a bounded grace period, and finalize every run in try/finally with actual elapsed time, status, cost and usage.

## [high] Context-dependent runs start without the findings they extend
File: `src/storydesk/agents.py`

build_prompt supplies only the generic digest and run brief; follow-ups receive only an anchor ID and question. It has no store access to include the anchor claim or evidence. The digest similarly contains no pre-game findings/feedback for post-game and no post-game findings for supplemental, while read_findings is scoped to the new run. Thus the lead cannot reliably determine 'what moved', what is new, or what evidence the follow-up extends. Specialists are also not told to receive the relevant context in their task message.

Recommendation: Build run-specific context containing the relevant prior findings, evidence, feedback and IDs; inject it into the lead prompt and require the lead to copy the necessary slice into each specialist task. Validate follow-up anchor/game/cutoff lineage and create/answer the request record transactionally.

## [high] Required coverage and the independent judge are not executed
File: `src/storydesk/runner.py`

run_live ignores RUN_TYPES.required_sources and the return from apply_gates, so a successful SDK result with zero findings is still recorded complete. It calls score_findings without a scorer, which deterministically leaves audience_fit and direction null instead of making the required independent judge call. Its coverage corpus search also queries media with the game UUID, which does not match ordinary team/title text and is empty for the supplied corpus, making novelty default to 1.0.

Recommendation: Before completion, enforce source coverage or run a bounded top-up, then perform exactly one no-tool judge call using pre-cutoff coverage selected by team/title terms. Aggregate that call's cost and usage into the run ledger and fail visibly when required outputs remain absent.

## [medium] Specialist prompts omit the operational contract needed for a bounded run
File: `prompts/stats.md`

The stats prompt asks for SQL and findings without supplying the four table schemas, important column names, the exact evidence URL/ref convention, or the chart query contract (`label`, `value`, `highlight`, exactly one highlight). The prompt set also lacks concrete finding-count and audience targets. With eight specialist turns and empty MCP descriptions, agents must discover these contracts by trial and error, increasing invalid calls and making a useful 25-minute packet unlikely.

Recommendation: Add a compact shared contract to the lead and specialist prompts: table/column schema, write_finding payload, evidence conventions, chart schema, per-run target counts and intended audiences, plus an instruction that specialist task messages must carry all relevant digest and prior-finding context.

## [medium] The default pre-game cutoff is nearly an hour earlier than the approved cutoff
File: `src/storydesk/cli.py`

The CLI derives pre-game as_of by subtracting six hours from completion. For the approved game this yields 05:35:07 UTC, not the designed 06:30 UTC three hours before the 09:30 tip-off. A default live run therefore omits roughly the last 55 minutes of eligible pre-game chatter and media context.

Recommendation: Derive the cutoff from the scheduled tip-off (`match_time_utc - 3 hours`) or use the approved explicit cutoff, rather than estimating it from game completion.

## Summary

Do not ship. The live writer is unusable with installed MCP 2.3.0, cutoff isolation is bypassable, the smoke proof can false-green, and the live orchestration does not satisfy the design’s context, deadline, cost, coverage, or judging guarantees.
