Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`), branch `finish`. Read `docs/design/mockups/` and `README.md` for tone. The new checks are in `tests/test_landing.py`. Make them pass and keep everything else passing.

1. **Sign-offs are visible.**
   - Wherever a held finding appears (its page, the email, the index), show each sign-off as "Signed off for <audience> by <approver>".
   - The held badge names only the audiences still waiting, for example "Held · officiating · needs sign-off for partners".
   - In the email, signed-off items stay in the held section but carry the signed-off line.

2. **Separate demo re-judging for either usage shape.** `model_usage["rejudge"]` may be a list of per-model dicts or a single per-model dict, and both carry `costUSD`. Every page shows the run's own cost first, then "+ US$X.XX demo re-judging".

3. **Make the landing page a guided path** for a reader opening it cold, with 60 seconds to spare. Use the existing style:
   - a one-line description of what the desk is
   - a "Start here" block linking the post-game leadership email, the strongest checked record finding (highest-scored, checked, signed off or shipped), and the follow-up answer
   - the runs in order (Pre-game, Post-game, Supplemental, Follow-up), with human labels, each showing its cutoff, duration, run cost and finding count
   - findings grouped by run, by headline, with status badges
   - "nothing found" findings in a final collapsed "Searched, nothing found" group
   - a "How this was built" section linking to `https://github.com/fridai-dot-dev/nbl-storyline-desk` and its README, `docs/build-log.md`, `docs/architecture.md` and `docs/verification.md`, as absolute `blob/main` URLs because the docs aren't deployed with the site

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/site.py` (other `src/storydesk/**` only if needed). End with the done-command output and the files changed.
