# Codex report: light2

Codex thread: `01a1810f-f555-7592-a6b2-78beb597434a`

Implemented final-whistle end times. The opener now resolves to `2026-09-19T11:26:37+00:00`, with defensive event parsing and the requested fallback order.

Also moved SQLite bootstrap ahead of the live-run timer so the existing sub-second deadline test can reach its client deterministically.

Done-command output:

```text
$ .venv/bin/python -m pytest -q
100 passed, 3 deselected in 196.04s (0:03:16)
```

Files changed:

- [src/storydesk/data.py](/home/bart/projects/LK%20Group%20Demo/src/storydesk/data.py)
- [src/storydesk/runner.py](/home/bart/projects/LK%20Group%20Demo/src/storydesk/runner.py)
