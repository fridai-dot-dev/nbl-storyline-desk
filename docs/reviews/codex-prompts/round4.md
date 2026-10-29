Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md` and the mockups in `docs/design/mockups/` (the email is option A in `leadership-view.html`). The new checks are in `tests/test_round4_polish.py`. They come from reviewing the first real leadership email.

1. **Exec summary.** The judge's JSON may include a top-level `exec_summary` for the run: two or three plain sentences, at most about 70 words, with no internal jargon, IDs or budget talk. `rejudge` and `score_findings` store it via `Store.set_exec_summary(run_id, text)`, and `get_run()` returns it. Ask for it in `prompts/judge.md`, alongside the existing scores, headlines and follow-ups. Keep the output JSON-only.

2. **What happened.**
   - The email's "What happened" shows the post-game run's exec summary, then the final score and quarter scores.
   - The lead's long summary moves to a collapsed `<details>` section titled "Editor's notes" at the end of the email.
   - Render it as markdown: headings, bold, bullet and numbered lists, and paragraphs. Escape HTML first, and write the renderer yourself, with no dependency. Raw markdown symbols must never appear on any page.

3. **One appearance per finding.** Every published finding appears in at most one email section above "Suggested follow-ups". The sections are:
   - **What moved since pre-game:** findings linked to a pre-game parent.
   - **Angles for the next 48 hours:** shipped findings only, ranked by the judge's scores, at most five.
   - **In-game pulse:** shipped commentary and fan items not already shown.
   - **Held for sign-off:** every held item, once, with its badge.
   - **Addendum**, **Suggested follow-ups**, then **Editor's notes**.

4. **Chart labels.**
   - Rotate x labels only when they wouldn't fit horizontally. Two bars never rotate.
   - When labels rotate, reserve enough bottom room so none is clipped. Record it as a `data-label-room` attribute on the svg.
   - Mark x-axis label text elements with `data-axis-label="x"`.

5. **No faded text.** The chart's faded-bar rule (`.muted{opacity:.28}`) collides with the text class `.muted`, so suggested-follow-up reasons render at 28% opacity. Scope the bar fading to svg marks only, and keep text contrast at WCAG AA.

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**` and `prompts/judge.md`.

End with the done-command output and the files changed.
