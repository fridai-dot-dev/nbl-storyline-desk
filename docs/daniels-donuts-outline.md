# Daniel’s Donuts: customer-review desk

We can apply the same control pattern to Daniel’s Donuts. This would redo Agora as a Claude Agent SDK pipeline and reuse Agora’s prompts and coding patterns. Agora is Bart’s existing feedback-analysis product. It used a fixed Gemini pipeline for hierarchical themes, stance, sentiment and human-verifiable coding. It analysed 1,643 public airline reviews in 22 minutes for US$2.17. Stoa is its public-consultation sibling, with a nine-phase pipeline.

The shape is different from the NBL desk. NBL research is open-ended: agents can follow a storyline across source types. Review analysis is structured: agents work through set stages, preserve coding decisions, and produce comparable weekly measures.

## Proposed flow

1. Collect Google reviews first. Later add approved review sources and point-of-sale ratings.
2. Clean, de-identify where required, freeze the weekly data window, and preserve review IDs and source links.
3. Code hierarchical themes, stance and sentiment with evidence a human can inspect.
4. Ask agents to investigate patterns across sources. For example: a cluster of complaints may point to a store and time, then be checked against roster and sales data.
5. Produce a weekly report and email. Show the evidence, uncertainty, trend, held items and recommended owner.
6. Capture manager feedback. Turn confirmed failures and useful findings into the evaluation set.

We would retain the NBL desk gates: cutoff-safe inputs, one recheckable measure per checked finding, evidence links, data boundaries, coverage checks, charts tied to queries, sensitive holds and named sign-off. A separate judge can rank which patterns deserve management attention. This is a decision aid, not an automatic performance-management system.

## What LK needs to provide

LK would provide authorised Google review access or exports, later-source permissions, store mapping, point-of-sale ratings and sales data, roster and shift data where lawful, retention rules, weekly recipients, and named sign-off roles. We also need an agreed rule for personal information, staff claims and customer contact details. The first pilot should cover a small set of stores, compare coded results with human review, and test whether weekly reports change an operational decision.
