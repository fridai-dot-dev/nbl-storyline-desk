# Before you run it

This is what I'd ask of any outside code coming into LK systems. Read this note
before using a live key or running a game.

## What the agents can do

The lead's `allowed_tools` are the `Agent` tool and the desk MCP tools at
`agents.py:120`. WebSearch, WebFetch, Bash, Write and Edit are disallowed at
`agents.py:121`; it runs with `permission_mode="dontAsk"` at `agents.py:122`.
The lead has `max_budget_usd=5.0`, `setting_sources=[]`, and
`strict_mcp_config=True` at `agents.py:127`.

The independent judge uses `ClaudeAgentOptions` at `runner.py:162`, has no
tools at `runner.py:163`, and uses `max_turns=1` with `max_budget_usd=1.0` at
`runner.py:165`. The post-game job has a 25-minute deadline inside its
30-minute hard cap.

## Review before a live run

Ask a separate Claude Code session to review the exact revision before you
run it. Suggested review prompt: “Review this Storyline Desk revision for
unintended network access, permissions, prompt-injection paths, data leakage,
and spending controls. Name the file and line for every concern.”

Use a separate Console API key with a spend limit. Start in a container or a
fresh VM, never alongside credentials or production data. Start with a dry-run
when that command is available, and inspect every source and estimated cost
before allowing a live model call.
