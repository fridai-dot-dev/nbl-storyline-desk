# Product requirements: NBL Storyline Desk

## Problem and why now

We need fast, connected storylines when a game creates several competing explanations. Producers, social, broadcast and leadership work on different inputs and tight timelines. OptaAI-style stat storytelling is useful prior art. We lead with the part it does not prove for this demo: links across stats, commentary, media and fans, plus a collaboration layer for direction and sign-off.

The demo post-game executive summary says Adelaide won 97-95 and made 13 threes to Melbourne’s 7, an 18-point edge from deep. The corresponding finding is headed “Adelaide’s threes outscored Melbourne’s by 18 points in a two-point game.” It is a concrete example of a checked angle, not a claim about the whole season.

## Users and jobs

- Leadership needs a briefing, a way to steer the next run, and a view of cost and timing.
- Producers need ranked show angles, proof, held-status signals and follow-up questions.
- Social needs usable, sourced angles and a clear boundary around fan material.
- Broadcast needs moments, context and claims it can check before use.
- Partners need only signed-off findings suited to their audience.

## Scope

We run pre-game, post-game, supplemental and on-demand follow-up research. Pre-game identifies watch points. Post-game produces the leadership email first. Supplemental adds press-conference and fresh reaction material. Follow-ups attach new findings to an existing anchor. The static site has the email, producer board and finding pages with evidence, charts, trail and suggested follow-ups. The outbox is local; it does not send email.

## Requirements

- **Speed:** post-game output exists within 30 minutes of the final whistle. Code gives the run 25 minutes. The published post-game run took 180.3 seconds and cost US$2.16 at API prices.
- **Accuracy:** every checked number re-runs from its saved SQL before release, and a mismatch drops the finding.
- **Sign-off:** sensitive findings are held until the named audience has signed off.
- **Auditability:** every finding has evidence. Runs preserve cutoff, cost, duration, route, model usage and tool-call trail.

## Success metrics

We measure usage through “Using it”, novelty through “Already had it”, audience fit through “Not for us”, time from whistle to briefing, and cost per game. In the demo, feedback is simulated and must stay labelled as such. A pilot establishes targets after we see real baselines.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Wrong or late input | Freeze each run at `as_of`, recheck numbers, and label data boundaries. |
| Sensitive claim reaches the wrong audience | Hold categories and require audience-specific sign-off. |
| Auto-caption error | Quote attributed claims and recheck numbers against statistics where possible. |
| Storyline is obvious | Judge novelty against pre-cutoff coverage and collect real “Already had it” feedback. |
| Cost or latency grows | Cap budget, turns and wall-clock time; compare fixed-game scorecards. |
| Low trust in fan material | Strip handles and treat quoted fan material as held. |

## Rollout

Start with one club’s games or one full round. Use LK feeds and real users. Review after each game. Then extend to the season only if the pilot proves timing, accuracy, use and cost.

## Open questions

Who owns final editorial and partner sign-off? Which LK channel replaces the local outbox? What live feed fields and transcript latency are available? Which audiences need a separate board? Does Opta cover the NBL, and what does it cost? What pilot success threshold justifies season rollout?
