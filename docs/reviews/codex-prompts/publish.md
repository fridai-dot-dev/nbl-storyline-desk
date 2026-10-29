Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`), branch `finish`. The new checks are in `tests/test_publish_safety.py`. Make the two failing ones pass, and keep the escaping check passing.

1. **Run cost separates demo re-judging.** A run's `cost_usd` includes any later `rejudge` passes, which `model_usage["rejudge"]` records as a list of per-model dicts carrying `costUSD`.
   - On every page that shows a run's cost (the email header, the index, the pre-game page, run summaries), show the run's own cost first: `cost_usd` minus the summed re-judge costs.
   - If re-judging happened, add a short label such as "+ US$0.45 demo re-judging (judge re-run after the run finished)".
   - Keep "at API prices (run on a Claude subscription)".

2. **Replay timing is described honestly.** These games are replayed after the fact, so never say "N min after full time". Say what's true, for example: "Run took 3 min from a cutoff frozen at the final whistle". Apply this to the email and anywhere else the site shows timing.

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/site.py`, plus `src/storydesk/**` only if needed. End with the done-command output and the files changed.
