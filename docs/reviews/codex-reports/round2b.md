# Codex report: round2b

Codex thread: `01a1828a-99f0-7fc1-9bb8-a72e1d86c818`

Implemented the run-publication gate and supplemental email addendum.

- Error results no longer save summaries.
- Site uses only current complete primary runs; complete follow-ups require a published anchor.
- Stale finding pages are removed on rebuild.
- Supplemental findings render in the leadership-email addendum.

Done-command output:

```text
122 passed, 3 deselected in 462.67s (0:07:42)
```

Files changed:

- `src/storydesk/runner.py`
- `src/storydesk/site.py`

Also present but untouched by me: `prompts/contract.md`, `prompts/stats.md`.
