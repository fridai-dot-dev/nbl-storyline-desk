# How we would build and run this

We would work in short loops: decide the behaviour with the people who use it, prove it with checks that can fail, build a small reviewed round, then run real data early. The [build log](build-log.md) shows why. Offline checks did not expose SQLite lock contention, abandoned background specialists, the distinction between whistle and stats sign-off, or search ordering that hid the fourth quarter. Each became a failing check before its fix.

## Choices we made

We use an Opus lead and four Sonnet source specialists because editorial research needs both a shared decision point and distinct source work. The tree stops at one specialist layer so cost and behaviour stay explainable. A shared stdio MCP server makes the SDK and Claude Code fallback use the same bounded tools. DuckDB supplies cutoff-safe statistic views. SQLite holds the audit ledger and collaboration state. Static HTML keeps the published review path simple.

Code, not an agent, controls release. It rechecks numbers, applies chart and data-boundary rules, holds sensitive material, and checks coverage. The independent judge ranks findings and creates headlines and suggested questions, but cannot waive a gate.

## What live runs taught us

The completed post-game run cost US$3.11 at API prices and took 180.3 seconds. It produced “Adelaide’s threes outscored Melbourne’s by 18 points in a two-point game.” The supplemental run then found “Melbourne’s bench outscored Adelaide’s by 30 points despite the 36ers’ win.” A follow-up tested that apparent paradox: “Winning despite a 30-point bench deficit has happened 18 times since 2015-16.” The useful result is not just the copy. It is the evidence, query, cutoff and status behind it.

We also learned to treat session-limit results as failures, cap memory before heavy data work, and obtain real runs before we call the system done. See [lessons](../lessons.md).

## Prioritised backlog

1. Producer board with real feedback capture and role-specific workflow.
2. Genius live feed and live transcript ingestion.
3. Wider, licensed media corpus.
4. OpenTelemetry or LangSmith tracing, with LK privacy review.
5. Slack delivery and feedback actions.
6. Graphics generated from checked chart data.
7. Feedback-to-eval loop: turn real comments and decisions into fixtures and scorecard cases.

## A new engineer’s first week

Read the [architecture](architecture.md), [provenance](data-provenance.md), prompts and saved store. Run the offline checks and build the site from `published/store.db`. Trace one finding from page to ledger, evidence and query. Then choose one small failure-proof change, add its check, implement it and run the scorecard on the fixed game. Do not widen a source or prompt without preserving the `as_of` and release rules.
