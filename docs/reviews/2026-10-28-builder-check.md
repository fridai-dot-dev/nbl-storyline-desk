# Builder check: the design, read cold before any build (2026-10-28)

A fresh reviewer read the design as the builder would, without access to the design conversation. It reported the places where it would have had to guess and a wrong guess would matter. Each question was then resolved, either in the design or by Bart.

| # | Question raised | Resolution |
|---|---|---|
| 1 | Do the agents work "as of full time" or "as of today"? Post-game coverage on the live web would make the backtest circular and the timing claims meaningless. | **Each run is frozen at its own cutoff.** Every tool takes `as_of`. The live web is off in the demo, and media comes from a corpus collected before the cutoff. |
| 2 | Who does the manual data steps (audio, Reddit, API keys), and how wide is the transcript library? | The transcript library covers the game's commentary, the two press conferences and pre-game media. Collection was later automated from public sources: YouTube captions and live chat, and NBL.com articles. |
| 3 | Can a finding carry a number that isn't in the stats database? | **Two kinds of number.** A *checked* number has its query rechecked by code. An *attributed* number appears only inside a quote with its source. |
| 4 | What does the public site show of sensitive findings and fan quotes? | Bart's decision: a public repo, with everything shown. Held items are marked held, and fan handles are never stored. |
| 5 | What is the per-run spend cap, and the budget for building? | Bart chose no Claude API spend: runs use his Claude login. `max_budget_usd` stays as a guard, and cost is reported at API prices. |
| 6 | Who scores how new an angle is and its audience fit, given "fixed code, no model judgement"? | **A separate judge:** one call per run with a fixed rubric, plus code-computed similarity, never the agents that wrote the findings. |
| 7 | Does a depth of "about 2" let specialists start their own sub-agents? | **Depth 1.** Only the lead starts specialists. Specialists propose new lines back to the lead. |
