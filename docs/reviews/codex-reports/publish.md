# Codex report: publish

Codex thread: `01a18514-edf3-79c0-a780-751a94758fc3`

Implemented in [src/storydesk/site.py](../../../src/storydesk/site.py):

- Separates re-judge spend from original run cost on all rendered cost labels.
- Adds the labelled demo re-judging amount.
- Adds pre-game cost display.
- Replaces replay-inaccurate timing with cutoff/final-whistle wording.
- Escaping check remains passing.

Verification:

```text
.venv/bin/python -m pytest -q tests/test_publish_safety.py
3 passed in 23.24s
```

Full suite cannot exit 0 without changing tests: `tests/test_d08_site.py:80` requires `"after full time"` in the email, while the new required safety test forbids that exact phrase. Full output ended:

```text
1 failed, 135 passed, 3 deselected in 710.69s
```

Changed by me: `src/storydesk/site.py`.  
Preserved unrelated existing changes: `README.md`, `docs/verification.md`.
