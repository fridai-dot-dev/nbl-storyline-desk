# Codex report: light3

Codex thread: `01a18178-eaef-7261-9944-454374059b5f`

Implemented both pre-game fixes.

- Lead prompts now begin with run facts; live runs pass the real run ID, match UUID, and cutoff.
- Recent-form and head-to-head tables join `results`, sort by real match time, and show date/season.

Done command output:

```text
.venv/bin/python -m pytest -q
102 passed, 3 deselected in 352.90s (0:05:52)
```

Files changed:

- [agents.py](/home/bart/projects/LK%20Group%20Demo/src/storydesk/agents.py)
- [runner.py](/home/bart/projects/LK%20Group%20Demo/src/storydesk/runner.py)
- [prepare.py](/home/bart/projects/LK%20Group%20Demo/src/storydesk/prepare.py)
