Repo: /home/bart/projects/LK Group Demo, a git repo on branch `round-1`. Read `lessons.md`, `docs/superpowers/specs/2026-10-28-nbl-storyline-desk-design.md` and everything under `docs/reviews/`. Then do these four housekeeping tasks so the work history is observable when the repo is published. Don't change anything under `src/`, `tests/` or `prompts/`. Don't push anywhere.

## 1. `docs/build-log.md`: a one-page timeline

Write it for the GM – AI at LK Group, who wants to see how the work was done. Use `git log` (commit hashes in backticks, with times) and the facts below. Plain, short sentences: no hype and no em dashes. Structure:

- **Process:** Decide (brainstorm, deepen pass, plausibility check, design) → Prove (failing checks first) → Build (Codex Terra) → Review (Codex Sol adversarial review, one fix round) → Live runs → a check for each surprise, then a fix.
- **Before the build:**
  - The plausibility check found prior art: Stats Perform's OptaAI Studio, Lega Basket Serie A's LUCA, and Genius Sports as the NBL's data partner. So the pitch leads with cross-source links and the collaboration layer.
  - The technical sanity-check had 10 assumptions, with divergences on MCP tool inheritance in sub-agents, the unreadable `pbp.rds`, and Pro plan limits. See `docs/reviews/2026-10-28-sanity-check-findings.md`.
  - The builder check raised 7 questions; see `docs/reviews/2026-10-28-builder-check.md`.
- **Build:**
  - Round-1 Prove suite, then the Terra build: 75 checks passing.
  - Sol's adversarial review: 2 critical, 4 high and 2 medium findings (see `docs/reviews/2026-10-28-sol-review-round-1.md`). The integrator wrote regression checks, then the Sol fix round followed: 95 checks.
- **What live runs exposed,** each turned into a failing check and then a fix. Cite the commits:
  1. Real data mixed numeric and UUID match IDs, and contained duplicate box rows (`289e92d`).
  2. The first smoke run lost tool-call attribution rows to SQLite lock contention under parallel specialists, and a specialist used an unknown source type (`c5645b3`, `87a8039`).
  3. The final whistle (11:26:37 UTC) is not the stats sign-off (11:35:07 UTC). The 30-minute cap runs from the whistle (`71438af`, `50662da`).
  4. A pure-Python parse of a 370 MB R file crashed WSL. Lesson: cap memory, and never parse `pbp.rds`.
  5. The first pre-game run hit the Pro session limit. The lead hadn't been told its cutoff or run ID, and "recent form" was sorted by a column that is always NA (`07dad92`, `bdd7760`).
  6. The first post-game run ended while background specialists were still working, because in streaming mode a result arrives before they finish. Search also returned the earliest matches, hiding the fourth quarter (`ab1f548`, `3005d57`).
  7. The first real site build needed headlines, held badges and run summaries. Smoke runs leaked onto the site, and follow-up requests weren't recorded (`b538bdb`, `45ae505`).
  8. A session-limit error was stored as a run summary, and failed runs reached the site (`57cc044`, `e734c55`).
  9. A record claim buried inside another finding wasn't rechecked. Now there is one checked number per finding (`e734c55`).
  10. Bart's idea: suggested follow-ups (rarity, on_pace, comparison, context), added through the existing judge pass with no extra agent runs (`04a1b7a`, `851120e`).
  11. Polish: an exec summary, rendered editor notes, a deduplicated email, chart labels, and a CSS class collision that faded text (`4ca8865`, `727b34a`).
- **The published run.** Cost is at API prices, run on Bart's Claude subscription, and includes the judge passes.

  | Run | ID | Duration | Cost |
  |---|---|---|---|
  | Pre-game | 2 | 151 s | US$1.83 |
  | Post-game | 5 | 180 s | US$3.11 |
  | Supplemental | 6 | 199 s | US$2.21 |
  | Follow-up | 7 | 195 s | US$1.96 |

  Runs 3 and 4 stopped at the Pro session limit. They stay in the store and are left off the site.
- **Checks:** 133 offline checks pass, and the 3 live checks (D10, D11, D13) pass against the published store.
- **Collaboration:** Bart chose the game, the follow-up question (the bench paradox) and the suggested-follow-up feature. Name the other decisions he made, as listed in the design's section 6.

## 2. `docs/reviews/README.md`

An index of the review trail, one line per file, saying what each is and why it exists: Sol's review, the sanity-check, the builder check, the Codex prompts, and the Codex reports. Mention that `docs/handoffs/` holds the round-1 build brief.

## 3. Publish the run snapshot

- Change `.gitignore` so `site/` is committed, since it's the built static site.
- Create `published/`, containing:
  - `published/store.db`: a copy of `store/demo.db`.
  - `published/digests/`: each published run's starting digest, regenerated with the project's own code. Run `PYTHONPATH=src .venv/bin/python` with `storydesk.prepare.prepare_run` for these:

    | Run | Cutoff | Anchor |
    |---|---|---|
    | pre_game | 2026-09-19T06:30:00+00:00 | |
    | post_game | 2026-09-19T11:26:37+00:00 | |
    | supplemental | 2026-09-19T12:50:00+00:00 | |
    | follow_up | 2026-09-19T11:26:37+00:00 | 34 |

    Each uses game `36dbeb55-58ad-11f1-a69b-43a6b5595d3e`, stats DB `data/stats.duckdb` and corpus `data/corpus`, and writes to `published/digests/<run_type>/`. Pass a copy of the store, never the live one.
  - `published/README.md`: what each artifact is.
- Keep these ignored: `data/raw`, `data/corpus` (the raw transcripts and the full chat stay out of a public repo), `data/logs`, the `store/` archives and the `*.jsonl` spools.
- Verify that no secret, `.env` file or private working file gets committed.

## 4. Commits and the merge

- Commit the docs and the snapshot on `round-1` as two separate commits with clear messages. End each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Then merge `round-1` into `main` with a no-fast-forward merge commit, so every commit and its timestamp stay visible. Don't squash.

Done when:
- `git log --oneline --graph main | head -40` shows the merge with the full branch history
- `git status` is clean
- `.venv/bin/python -m pytest -q` still exits 0

End with those outputs and the list of committed paths.
