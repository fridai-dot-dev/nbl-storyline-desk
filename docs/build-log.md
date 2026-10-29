# Round-1 build log

This is the observable history of the NBL Storyline Desk demo.

History was rewritten once before publishing, to remove private working notes. Every commit was kept, and the hashes cited here are the rewritten ones.

## Process

Decide: brainstorm, deepen pass, plausibility check and design. Then Prove: failing checks first. Then Build: Codex Terra. Then Review: Codex Sol adversarial review and one fix round. Then live runs. Each surprise became a failing check, then a fix.

## Before the build

The plausibility check found relevant prior art: Stats Perform's OptaAI Studio, Lega Basket Serie A's LUCA, and Genius Sports as the NBL's data partner. The pitch therefore leads with cross-source links and the collaboration layer.

The technical sanity-check recorded 10 assumptions. It found divergences on MCP-tool inheritance in sub-agents, unreadable `pbp.rds`, and Pro plan limits. See [the findings](reviews/2026-10-28-sanity-check-findings.md). The builder check raised seven questions before implementation. See [the builder check](reviews/2026-10-28-builder-check.md).

## Build and review

The Prove suite was committed at `12da304` (2026-10-28 11:03 +07:00). Terra's round-1 build then passed 75 checks.

Sol's adversarial review found 2 critical, 4 high and 2 medium issues. See [the review](reviews/2026-10-28-sol-review-round-1.md). The integrator added regression checks at `6a249ef` (11:49). Sol's fix round followed, and the build and the fixes were committed together at `a58d645` (12:12), with 95 checks passing.

## What live runs exposed

Each item below became a failing check before it was fixed.

1. Real data mixed numeric and UUID match IDs, and included duplicate box rows. `289e92d` (12:19:29).
2. The first smoke run lost tool-call attribution rows to SQLite lock contention under parallel specialists. A specialist also used an unknown source type. `c5645b3` (12:24:15), `87a8039` (12:39:24).
3. The final whistle, 11:26:37 UTC, is not the stats sign-off, 11:35:07 UTC. The 30-minute cap runs from the whistle. `71438af` (12:51:02), `50662da` (13:11:44).
4. A pure-Python parse of a 370 MB R file crashed WSL. The lesson is to cap memory and never parse `pbp.rds`.
5. The first pre-game run hit the Pro session limit. The lead had not been told its cutoff or run ID. “Recent form” was sorted by a column that is always `NA`. `07dad92` (14:45:46), `bdd7760` (15:00:11).
6. The first post-game run ended while background specialists were still working because streaming reports a result before they finish. Search also returned the earliest matches and hid the fourth quarter. `ab1f548` (15:06:30), `3005d57` (15:29:53).
7. The first real site build needed headlines, held badges and run summaries. Smoke runs leaked onto the site, and follow-up requests were not recorded. `b538bdb` (15:45:35), `45ae505` (16:10:20).
8. A session-limit error was stored as a run summary, and failed runs reached the site. `57cc044` (19:44:43), `e734c55` (20:05:31).
9. A record claim buried inside another finding was not rechecked. Now every finding has one checked number. `e734c55` (20:05:31).
10. Bart proposed suggested follow-ups: rarity, on-pace, comparison and context. They run in the existing judge pass with no extra agent runs. `04a1b7a` (20:23:55), `851120e` (21:29:09).
11. Polish added an exec summary, rendered editor notes, a deduplicated email, chart labels, and fixed a CSS class collision that faded text. `4ca8865` (21:33:55), `727b34a` (21:58:26).
12. Sol's final pre-publication review found:
    - failed follow-ups marked as answered
    - a deadline that could overrun while waiting on an interrupt
    - unchecked link schemes
    - a malformed score line in the starting digests

    A link check also found that every stats source link was a URL the agents had guessed, and none resolved. Code now links stats evidence to the real nblR release.

## The published run

Cost is at API prices. The runs used Bart's Claude subscription. Run cost includes each run's own judge pass. Re-judging is the demo re-scoring finished runs after the judge gained suggested follow-ups, so a live game wouldn't pay it. The ledger keeps both.

| Run | ID | Duration | Run cost | Demo re-judging | Ledger total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pre-game | 2 | 151 s | US$1.21 | US$0.62 | US$1.83 |
| Post-game | 5 | 180 s | US$2.16 | US$0.95 | US$3.11 |
| Supplemental | 6 | 199 s | US$1.77 | US$0.44 | US$2.21 |
| Follow-up | 7 | 195 s | US$1.54 | US$0.42 | US$1.96 |

Runs 3 and 4 stopped at the Pro session limit. They remain in the store and are excluded from the site.

## Checks and collaboration

155 offline checks pass. The three live checks, D10, D11 and D13, pass against the published store.

Bart chose the game, the follow-up question called the bench paradox, and the suggested-follow-up feature. His other recorded decisions were: NBL rather than Daniel's Donuts; four run types and follow-up research as a headline feature; a pitch led by cross-source links and collaboration; the build-versus-buy criteria; email for leadership and a board for producers; hidden queries; the accepted deepen answers and definition of a disappointing run; graphics as a future direction; no Claude API spend, with Claude Code as fallback; Apify where useful; and a public repository and site that show the work in full.
