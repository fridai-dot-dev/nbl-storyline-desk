# Cost

The table uses `runs.cost_usd` from [the published SQLite store](../published/store.db). These are API-price ledger values, including judge work where recorded. The completed runs were made on a Claude subscription, not charged to an API key.

| Run | Store ID | Run cost (one judge pass) | Ledger total incl. demo rejudges | Duration |
| --- | ---: | ---: | ---: | ---: |
| Pre-game | 2 | US$1.21 | US$1.83 | 150.8 s |
| Post-game | 5 | US$2.16 | US$3.11 | 180.3 s |
| Supplemental | 6 | US$1.77 | US$2.21 | 198.8 s |
| Follow-up | 7 | US$1.54 | US$1.96 | 195.0 s |

**Run cost** is the cost of the run as it would happen in production: the agents plus their one judge pass. The **ledger total** also includes extra judge passes we re-ran during the demo, to add headlines, suggested follow-ups and the exec summary to runs that had already finished. Those are build-time costs, not per-run costs. The store also keeps incomplete runs 3 and 4, which stopped at a subscription limit, and a smoke check (run 1). None of them count towards the estimates.

## Per game and season

Assumption: each game gets one pre-game run, one post-game run, one supplemental run, and two producer follow-ups.

`1.21 + 2.16 + 1.77 + (2 × 1.54) = US$8.22`

That's **about US$8 per game** at API prices. For 165 regular-season games it comes to **about US$1,360**. This is a planning estimate from one game's runs, not a quote. Runs on busier nights, or with more follow-ups, will cost more.

The measured post-game run took 180.3 seconds. It is well inside the 25-minute code limit and the product’s 30-minute whistle-to-briefing deadline. The supplemental run took longer than post-game, but it is not on the immediate deadline.

## Cost levers

- Set effort per role before changing the topology. The current lead is Opus and specialists are Sonnet.
- A Sonnet lead is the clearest cheaper comparison. It needs a fixed-game scorecard comparison before use.
- Reuse prepared digests and cache stable coverage. The system already prepares the starting set once.
- Run fewer follow-ups. They are the variable part of the per-game estimate.
- Share one published digest or briefing across leadership, production and social where the audience fit is the same.

Subscription use was a demo convenience. The published runs used Bart’s Claude login while the ledger reports API-equivalent cost. Production should use an API key, or an approved Bedrock or Vertex route, so usage is owned by LK and has normal operational controls. Subscription limits can change and are not a production capacity plan.

Not costed here: engineering and editorial time, Genius or other data feeds, transcription, storage, hosting, observability, security review, email or Slack services, and support.

## Vendor comparison

Stats Perform does not publish OptaAI pricing. We should ask any vendor:

- What is priced per match, season, user, data feed, API call and graphics render?
- Does the fee include live basketball data, historical data, transcript or social ingestion, and storage?
- What service level applies from final whistle to briefing?
- Can we export raw evidence, prompts, audit trails and feedback data?
- Can we add our own cross-source research, approval workflow and evaluation set?
- What are model, overage, implementation and exit costs?

The decision is not price alone. It is fit, quality, support and how quickly we can improve the workflow with LK users. See [architecture](architecture.md) for the controls behind the estimate.
