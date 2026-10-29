# Codex report: fix

Codex thread: `01a180af-da33-7b71-82c1-5ebed5f0d34d`

Done command:

```text
$ .venv/bin/python -m pytest -q
95 passed, 3 deselected in 188.77s (0:03:08)
```

Files changed:

- [README.md](</home/bart/projects/LK Group Demo/README.md>) — package usage stub.
- [prompts/contract.md](</home/bart/projects/LK Group Demo/prompts/contract.md>) — shared operational contract.
- [prompts/lead.md](</home/bart/projects/LK Group Demo/prompts/lead.md>) — lead instructions.
- [prompts/stats.md](</home/bart/projects/LK Group Demo/prompts/stats.md>) — statistics specialist instructions.
- [prompts/commentary.md](</home/bart/projects/LK Group Demo/prompts/commentary.md>) — commentary specialist instructions.
- [prompts/media.md](</home/bart/projects/LK Group Demo/prompts/media.md>) — media specialist instructions.
- [prompts/fans.md](</home/bart/projects/LK Group Demo/prompts/fans.md>) — fan specialist instructions.
- [prompts/judge.md](</home/bart/projects/LK Group Demo/prompts/judge.md>) — independent judge instructions.
- [prompts/runs/pre_game.md](</home/bart/projects/LK Group Demo/prompts/runs/pre_game.md>) — pre-game brief.
- [prompts/runs/post_game.md](</home/bart/projects/LK Group Demo/prompts/runs/post_game.md>) — post-game brief.
- [prompts/runs/supplemental.md](</home/bart/projects/LK Group Demo/prompts/runs/supplemental.md>) — supplemental brief.
- [prompts/runs/follow_up.md](</home/bart/projects/LK Group Demo/prompts/runs/follow_up.md>) — follow-up brief.
- [prompts/runs/smoke.md](</home/bart/projects/LK Group Demo/prompts/runs/smoke.md>) — smoke-run brief.
- [src/storydesk/__init__.py](</home/bart/projects/LK Group Demo/src/storydesk/__init__.py>) — package initialization.
- [src/storydesk/__main__.py](</home/bart/projects/LK Group Demo/src/storydesk/__main__.py>) — module entry point.
- [src/storydesk/agents.py](</home/bart/projects/LK Group Demo/src/storydesk/agents.py>) — agent configuration, shared contract and lifecycle logging.
- [src/storydesk/charts.py](</home/bart/projects/LK Group Demo/src/storydesk/charts.py>) — deterministic SVG charts.
- [src/storydesk/cli.py](</home/bart/projects/LK Group Demo/src/storydesk/cli.py>) — CLI and corrected default cutoffs.
- [src/storydesk/data.py](</home/bart/projects/LK Group Demo/src/storydesk/data.py>) — DuckDB ingestion and cutoff views.
- [src/storydesk/gates.py](</home/bart/projects/LK Group Demo/src/storydesk/gates.py>) — release gates and restricted rechecks.
- [src/storydesk/judge.py](</home/bart/projects/LK Group Demo/src/storydesk/judge.py>) — finding scoring.
- [src/storydesk/mcp_server.py](</home/bart/projects/LK Group Demo/src/storydesk/mcp_server.py>) — callable, explicitly typed MCP tools and descriptions.
- [src/storydesk/prepare.py](</home/bart/projects/LK Group Demo/src/storydesk/prepare.py>) — starting digests and prior-finding context.
- [src/storydesk/runner.py](</home/bart/projects/LK Group Demo/src/storydesk/runner.py>) — deadlines, draining, coverage top-up, judging and ledger finalization.
- [src/storydesk/scorecard.py](</home/bart/projects/LK Group Demo/src/storydesk/scorecard.py>) — run scorecards.
- [src/storydesk/site.py](</home/bart/projects/LK Group Demo/src/storydesk/site.py>) — static output and restricted chart queries.
- [src/storydesk/sqlsafe.py](</home/bart/projects/LK Group Demo/src/storydesk/sqlsafe.py>) — shared four-relation SQL allowlist.
- [src/storydesk/store.py](</home/bart/projects/LK Group Demo/src/storydesk/store.py>) — SQLite ledger.
- [src/storydesk/tools.py](</home/bart/projects/LK Group Demo/src/storydesk/tools.py>) — bounded tools and finding-query validation.

Calls outside the design:

- None; no live model, network, or external API calls were made.

Left alone:

- `tests/**`, `docs/**`, `lessons.md`, and `pyproject.toml` were untouched.
- `pbp.rds` was not parsed or loaded.
- The existing pytest-asyncio configuration warning and three configured live-test deselections remain unchanged.

Goal completed in about 15 minutes 34 seconds.
