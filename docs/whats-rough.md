# What's rough and what I assumed

This is a rapid build. The prompts are not yet engineered or versioned, and I
would spend about 2–3 hours refining them before showing this to non-AI
stakeholders, followed by up to 10 more test runs.

The Cole Anthony example shows a statistical limitation: fewest minutes for a 30-point game mostly selects players whose minutes were capped. A better measure is quickest to 30: time on court when a player reached 30. That needs play-by-play, which this round does not yet load.

The remaining quality risks include agents choosing chart forms themselves (the
three donut, scatter and line charts were added by code after the runs, as a
temporary fix so the charts could be seen before the hand-in date; the real fix
is for agents to pick the chart form as they write each finding),
multi-step stats searches, and richer fan sourcing. Each needs a concrete data and evaluation
pass before it becomes a production claim.

Three charts (a donut, a scatter and a line) were added after the runs. Code builds them from the stats database; no agent produced them.
