Repo: /home/bart/projects/LK Group Demo (Python, `src/storydesk`). Read `lessons.md`, the design (`docs/superpowers/specs/2026-10-28-nbl-storyline-desk-design.md`, section 5.6) and the mockups in `docs/design/mockups/`. The first real site build, from live runs on real NBL data, showed what exec-facing pages still need. The new checks are in `tests/test_round2_site.py`.

1. **Headlines.**
   - `write_finding` gains an optional `headline` (plain text of at most about 14 words or 120 characters; reject longer). Store it, return it from `get_finding`, and add `Store.set_headline(finding_id, text)`.
   - The judge's JSON may include a `headline` per finding, and `score_findings` fills any missing headline from it. Update `prompts/judge.md` to ask for one: plain, specific and at most 14 words, with no new facts beyond the claim.
   - Add `storydesk.site.headline_for(finding)`. It returns the stored headline, or else derives one: the first sentence of the claim with parentheticals removed, at most 25 words. Skip a leading meta sentence such as "Answers the producer follow-up question."
   - Add the `headline` field to the MCP `write_finding` tool and to `prompts/contract.md`.
   - Add a CLI `rejudge --run-id N [--live]` that re-runs the judge (scores and headlines) for a finished run. Without `--live`, exit non-zero with a message containing `--live`.

2. **Exec pages lead with headlines.** The email, the index, the pre-game page, angle cards and finding page titles show the headline. Each finding page also shows the full claim, beneath the title as the body. Keep the email scannable: headline plus tags plus buttons for each angle, and link to the detail page.

3. **Held items are visibly held.** Wherever a held finding appears, show a badge such as "Held · officiating · needs sign-off", including in the email's in-game pulse. The category must sit in the same text as the word "Held".

4. **What happened.** `record_result` stores the run's final result text, the lead's summary, as `runs.summary`. Add `Store.set_run_summary(run_id, text)` and `get_run()["summary"]`. The email's "What happened" shows the post-game run's summary, plus the final score and quarter scores from `get_game`.

5. **Cost and timing labels.** Show cost as "US$X.XX at API prices (run on a Claude subscription)" when the route is `sdk`. Keep "N min after full time".

6. **Follow-ups record their request.** `run_live` gains `asked_by=None`. For `follow_up`, it creates the request (anchor, asked by, question) at the start and calls `answer_request(request_id, run_id)` when it finishes. The CLI `run follow_up` gains `--asked-by` (default "producer").

7. **Smoke runs never appear on the site.**

8. **Long category labels must not collide.** When labels are long or numerous, shorten season labels (`2015-2016` becomes `15-16`) or rotate them. `data-label` keeps the full label, and `check_chart` still passes.

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. May change: `src/storydesk/**` and `prompts/**`.

End with the done-command output and the files changed.
