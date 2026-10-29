# NBL Storyline Desk: design

**Status:** approved by Bart, 2026-10-28. Sanity-check done, with results in section 12 · **Date:** 2026-10-28 · **Owner:** Bart Lind

**Working title.** Mockups are in `docs/design/mockups/` (`leadership-view.html`, `producer-board-v2.html`, `finding-detail.html`). Their values are invented: only game results are real, and none of their numbers carry into the build.

---

## 1. Intent

**The real goal.** This demo was built for the AI Engineer role in LK Group's AI team, which reports to the GM – AI. Within about 60 seconds the repo has to show the design and shipping of a Claude Agent SDK system with engineering judgement. The window was 2–3 days from 27 Oct, which left about one build day.

Lessons from an earlier portfolio piece apply here. The engineering has to be visible from the surface, there has to be a guided path through it, and a real person from the audience should test it.

**The product.** An agent-powered layer that informs and connects the people who make NBL media, before and after every game. It works out:
- what story the stats, commentary, media and fans are telling
- where they agree and where they disagree
- what LK might elevate, put in context, monitor, play down or challenge

It puts that in front of leadership and producers fast enough to use, in a form they can react to in minutes. Their direction then shapes the next run.

**Why the NBL, and why build rather than buy.** From the plausibility check on 28 Oct:
- **The league controls production.** It commissions its own broadcast production (Jam TV replaced IMG; current status to verify), and NBL26 set digital-engagement records by the league's own figures. One tool can reach most of what goes out.
- **The problem is real.** Stats Perform's OptaAI Studio (Opta Search, Live and Graphics; basketball-ready), its storylines service, and Lega Basket Serie A's LUCA agent all already sell stat storytelling.
- **There's a gap.** In public material, none of them test a storyline across sources by linking stats with commentary, pressers and fan talk. None of them has an internal collaboration layer either: directives, sign-off and alignment. **Those two lead the pitch, and the stats engine is the foundation.**
- **Genius Sports would be the real input.** The NBL's official data comes from Genius Sports (FIBA LiveStats since 2015, with a FIBA–Genius AI deal to 2035), so a real rollout would take Genius output. nblR stands in for it here.
- **Opta may not cover the NBL.** If it doesn't, that strengthens the build case (to verify).
- **The build-vs-buy case** rests on cost, quality, fit, and above all ease of support and continuous improvement. Learn from OptaAI wherever possible, for example by giving every finding a visual.

## 2. Who reads what

| Reader | What they get |
|---|---|
| GM – AI | README with a 60-second path, a one-page proposal and a short video |
| Engineers (a team of 3–4) | Architecture doc, code and a team pitch doc |
| Internal stakeholders (CEO, NBL GM, marketing, media) | Proposal or PRD, build vs buy, cost |
| Users inside the demo | Pre-game briefing, post-game leadership email, supplemental addendum, producer board, finding detail page |

## 3. Goals, non-goals, anti-goals

**Goals**
1. **One engine, four kinds of run** (section 5.1) on one real NBL27 game: pre-game, post-game, supplemental and follow-up. Code rechecks every number in their output.
2. **Speed.** The post-game briefing goes out within 30 minutes of the final whistle. That is a hard cap.
3. **A visible Agent SDK system.**
   - A lead agent with specialist sub-agents that branch across source types.
   - Concurrency and spend are capped.
   - Every finding records how it was reached.
4. **Follow-up research from any finding.** A user asks in plain language and the answer appears as new findings linked under it.
5. **The collaboration loop.**
   1. A pre-game briefing.
   2. Leadership steers.
   3. The post-game briefing.
   4. Reactions and directives.
   5. A supplemental addendum.
   6. The producer board.
   7. A packet for each show.
6. **Cost per run at API prices,** projected to a season of 165 games.
7. **A small improvement loop.** Re-run a fixed game, score it against the checks and log the cost.
8. **Docs that make the build-vs-buy case.**

**Non-goals (covered in the docs only)**
- Live in-game features, video analysis (SAM3), clipping, and making graphics in the OptaAI/Genius style. Graphics are a future direction. The pre-game run *serves* the live social and stats team, but nothing runs during the game.
- Real email sending and replies. A local outbox stands in.
- Social scraping at scale, X and Instagram.
- LangChain orchestration. LangSmith is optional.
- Login, auth and hosting for many users.
- The full loop that turns feedback into prompt changes.
- The Daniel's Donuts build, which gets a one-page outline only. It redoes Agora/Stoa as an Agent SDK pipeline and reuses their prompts. It also shows a different shape: a structured pipeline with agents at set stages, against the NBL's open-ended research.

**Anti-goals** (failures even if it runs)
- Any wrong number in a packet.
- Output that is obvious, too niche to use, or far removed from directives and suggestions (Bart's "disappointing run").
- A post-game briefing that lands after the 30-minute cap.
- Sensitive content reaching producers or partners without sign-off.
- Engineering that can't be seen from the surface, so it reads as a wrapper.
- An agent tree nobody can explain or put a cost on.
- Claiming the demo ran in a way it didn't.

## 4. Constraints

- **Time:** about one build day. If the day runs short, ship the Must list in section 9.
- **No Claude API spend (Bart's decision).**
  - Runs happen locally on Bart's own Claude login. The sanity-check confirmed this: Anthropic's help centre says the Agent SDK and `claude -p` "still draw from your subscription limits". Anthropic announced changes to that and then paused them in June 2026, so the README says it could change.
  - Fallback: headless Claude Code (`claude -p`) running the same agent definitions and tools on his subscription.
  - **Pro plan limits** (a five-hour window and a weekly limit) allow about **3 full runs**, spread across usage windows: pre-game, post-game and one follow-up. More runs happen only if limits allow.
  - The demo route uses **Opus 5.5 for the lead and Sonnet 5.5 for the specialists** (Bart's decision). Opus everywhere stays the documented production default on API keys.
  - The repo ships with API-key auth for anyone else, as the docs require for products. The README says exactly how the published run was produced.
  - `max_budget_usd` stays set (about $5) as a guard on each run's cost at API prices. A usage ledger records the reported `total_cost_usd` of every run for the cost page.
- **Speed.** The post-game run gets data up to the final whistle and has about 25 minutes of wall-clock time, so the briefing goes out by full time plus 30 minutes. Specialists run in parallel and effort is limited to fit. In production, stats would arrive live from Genius and commentary would be transcribed during the game. In the demo both are preloaded.
- **Each run is frozen at its own time.** The game is weeks old, so every tool takes an `as_of` cutoff and returns nothing dated after it.

  | Run | Cutoff |
  |---|---|
  | Pre-game | Its start time, about 3 hours before tip-off (Claude's call) |
  | Post-game | The final whistle |
  | Supplemental | When the post-game press conferences are finished |
  | Follow-up | The cutoff of the run it extends |

  The media agent searches only what existed before the cutoff, not the live web, because web search can't be limited by date. In production "now" *is* the cutoff, so the same tool would call live search. Freezing keeps the backtest (H2) fair and makes the timing claims true.
- **Inputs:**
  - Apify scrapers handle r/NBL threads (comments with timestamps), YouTube comments (with dates) and NBL.com and club news, all within the free $5 of monthly credit.
    - Test the Reddit scraper on one thread first.
    - NBL.com article dates are day-level only, so for the post-game run treat same-day articles as "after".
    - Scraping without logging in is a grey area under Reddit's and YouTube's terms, and the README notes it.
  - Bart supplies the full-game stream or audio and the links to the post-game press conferences and the latest NBL Now episode before the game.
  - Fallback for fans: a hand-copied r/NBL sample of 30–50 comments. That means the game thread's comments, plus the first 20 or so from the post-game thread sorted by Old, and a YouTube Data API key.
- **Stats data (checked 28 Oct):**
  - nblR is a thin loader over GitHub release files in `JaseZiv/nblr_data`, refreshed daily during the season.
  - NBL27 had 43 of 165 games in by 26 Oct, and the history goes back to 2015-16.
  - Python downloads the CSV files directly, so no R code runs.
  - **History comes from the CSVs:** results, team box scores and player box scores.
    - `box_team.csv` has quarter-by-quarter scores (`p1_score`–`p4_score`, `ot_score`) for every season, so claims like "most fourth-quarter points since 2015-16" need no play-by-play.
  - **Play-by-play comes per game from the NBL match API** (`prod.rosetta.nbl.com.au/get/match/<uuid>/live/all`; Bart approved this source). It's small JSON from the NBL's own Genius-backed feed, and the same source the community scraper uses. It's needed for the chosen game and a few comparison games.
  - `pbp.rds` can't be read by `pyreadr`. The pure-Python reader is too heavy for this machine, which has 7.7 GB of WSL memory and crashed during the sanity-check, so **never parse the full `pbp.rds` here.**
  - `pbp.csv` is mislabelled: it actually holds player box scores.
  - Older history can come from the spatialjam PDFs if it's ever needed.
- **Being honest about the data:** record claims state where the data starts, for example "most since at least 2015-16".
- **Commentary:** transcribe the final minutes and other key moments, not the whole game, with timestamps.
- **Privacy:** fan handles are hidden. Quoting a fan outside LK needs sign-off.
- **The repo is public and the site shows everything in full** (Bart's decision). Held findings appear with their held status, and fan handles stay hidden.
- **The GM never has to run anything.** What he's meant to see opens in a browser.

## 5. The design

### 5.1 One engine, four kinds of run

Code sets the rails and agents explore.
- **Code decides** when a run happens, what it starts with, and what may leave the system: checks, sign-off and packets.
- **Agents decide** where to look and how far to go.

Each run type is a configuration: a starting set, a brief, an output template and a time limit. Runs differ only in those four things.

| Run | When | Starting set (loaded by code) | Brief | Produces |
|---|---|---|---|---|
| **Pre-game** | About 3 hours before tip-off | Recent form, matchup history, milestones and records within reach, pre-game chatter (the latest NBL Now episode, previews), active directives | Find the storylines to watch, and what would confirm or contradict them | Storylines to watch for show producers and the live social and stats team. Also a leadership briefing they can steer from; their steer feeds the post-game brief |
| **Post-game** | From the final whistle; briefing out by full time + 30 minutes | The box score and play-by-play, commentary from the final minutes and key moments, the in-game fan thread, leadership's pre-game steer, the pre-game storylines | What happened, what moved against pre-game, what to do about it | The leadership briefing (email first) |
| **Supplemental** | Once the press conferences are finished | Press conference transcripts and a fresh pass over social comments | What's new since the briefing | An addendum to the briefing |
| **Follow-up** | On demand, from any finding | The anchor finding with its evidence, plus the user's question | Answer the question | New findings linked under the anchor |

**How agents go beyond the starting set:**
- **Going beyond it.** Any past game or season, SQL across all seasons, transcript search, fan search and media search, all as of the cutoff.
- **Branching.** A finding can open a new line of research, and the lead decides which lines are worth the spend.
- **Tracking.** Agents can create tracking tables in the store that carry over to later runs.

**Example chains to support:**
- Talk-show tension leads to the press conference transcripts and minutes played.
- A commentator's "four threes in a row" leads to the play-by-play, then the record books, then fan reaction.
- A fan's pushback ("United gave it away") leads to a check of turnovers.

**Follow-up questions the demo runs** (Bart's), each anchored on a post-game finding such as "most fourth-quarter points against United since at least 2015-16":
1. "What about league-wide stats on fourth-quarter points given up? Where does this rank among other collapses?"
2. "Build from this and look at the rivalry between the two teams, with this comeback as the anchor."
3. "It felt like rebounds, threes or better ball movement drove the swing. Can you test that, and find other games where either team did the same or the opposite with a matching result? Is it a new focus for them, or have they been doing it for a while?"

### 5.2 Agents

- **Lead agent.** It plans the run from the brief, starting set and directives, sends work to specialists, merges their findings, decides on branches and ranks the results.
- **Specialists.** Each one has its own prompt, tools, model and effort level:
  - **stats:** history, comparisons, anomalies, league-wide ranks, trends over time
  - **commentary:** moments, excitement, commentators who disagree
  - **media:** pre-game shows, press conferences, articles; searches the media corpus
  - **fans:** comment samples, mood, claims worth checking
- **Explicit tool access.** Each specialist names the MCP server and its tools in its own definition (`mcpServers`, plus `tools: mcp__desk__*`). Nothing relies on sub-agents inheriting tools, because of an open Claude Code bug, claude-code#30280. A day-one smoke test checks it (D13).
- **The starting set is prepared once.** Code turns it into compact digest files before agents start, so parallel specialists don't each reload the same documents. Reloads were a known cost and usage drain in claude-code#104543.
- **Agent definitions live in files** (`prompts/` and agent definition files). The SDK entry point and the Claude Code fallback load the same ones, and they make up the "library of reusable prompt templates" the JD asks for.
- **Two layers only.** Only the lead starts specialists (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1`).
  - A specialist follows a lead within its own loop.
  - When it finds a new line in another source, it proposes that line back to the lead, and the lead decides whether to spend on it.
- **Caps:**
  - concurrency with `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (about 5)
  - cost with `max_budget_usd` (about $5 at API prices)
  - a wall-clock limit per run type, about 25 minutes for post-game. The SDK has no session or per-sub-agent deadline, so **our code enforces it**: a timeout around the run, then `ClaudeSDKClient.interrupt()`. Each specialist also has `maxTurns`.

  A run that hits its cost cap ends without a packet, so the lead's prompt carries the same budget and time limit so it can pace itself.
- **SDK version:** pin `claude-agent-sdk` at 0.2.127 or later, the release the caps need. Watch the casing: `AgentDefinition` fields are camelCase, while `ClaudeAgentOptions` fields are snake_case.
- **Models:**
  - Demo route (Bart's Pro plan): Opus 5.5 for the lead and Sonnet 5.5 for the specialists.
  - Production default: Opus 5.5 throughout, with effort set per role.
  - Effort is the first lever for the time cap. The scorecard can compare the two mixes on quality and cost.
- **Cost reporting:** `total_cost_usd` and `model_usage` from each run's result give cost at API prices per run and per model.

### 5.3 Tools: a standalone MCP server shared by both routes

- **The tools run as their own stdio MCP server,** so the SDK entry point and the Claude Code fallback use exactly the same tools.
- **Every tool takes the run's `as_of`** and returns nothing dated after it.
- **Every tool call is logged** with the agent, the call, its arguments and the result reference.
  - The agent comes from the hook input's `agent_id` and `agent_type`, which the SDK provides inside sub-agents.
  - The server also logs every call it receives, so the trail still works on the `claude -p` route.

| Tool | What it does |
|---|---|
| `stats_sql` | Read-only SQL over DuckDB across all seasons, with row and time limits |
| `get_game` | The full record for any match |
| `search_transcripts` | Returns a quote, timestamp and source URL. The demo library is this game's commentary segments, the two post-game press conferences and the latest NBL Now episode before the game; in production it would cover every game and show |
| `search_fans` | Returns comment text, score, time and source, with handles stripped |
| `search_media` | Searches the media corpus as of the cutoff |
| `write_finding` / `read_findings` | A finding can't be written without at least one piece of evidence and, unless it's a starting point, a parent finding |
| `create_tracking_table` / `update_tracking_table` | Agent-made tables that carry over |

The SDK's built-in WebSearch and WebFetch are **off** in the demo (see the cutoffs in section 4). They'd be on in production.

### 5.4 The store (SQLite or DuckDB)

- **runs:** game, run type, cutoff, start and end, wall-clock duration, cost at API prices, model usage, number of agents, and the route (SDK or Claude Code).
- **findings:**
  - which run it came from, its parent finding (this is the trail; for a follow-up, the parent is the anchor), and the agent that wrote it
  - the claim text, the numeric claim and the query that produced it, and its check status
  - audience tags and scores: how new it is, audience fit, link to a directive
  - the directive that prompted it (or "unprompted"), its sensitivity category and sign-off status
- **evidence:** finding, source type, URL, timestamp or row IDs, quote, stance (supports or pushes back).
- **requests:** follow-up questions, with the anchor finding, who asked, the question text and the run that answered it.
- **directives:** owner's role, text, mandatory or suggested, expiry date, status.
- **feedback:** finding, role, action (back, comment, drop, using it, already had it, not for us, ask a follow-up), text, time, and a `simulated` flag.
- **Agent-made tracking tables,** kept in their own namespace.

### 5.5 Checks on output

Items 1–4, 6 and 7 are fixed code. Item 5, ranking, uses a separate judge.

1. **Recheck, and two kinds of number.**
   - A **checked number** comes from the stats store or is computed by code from our own samples. It stores its query. Code re-runs the query and compares the result, and a mismatch drops the claim.
   - An **attributed number** comes from someone else, such as an article's figure or a commentator saying "four threes in a row". It can only appear inside a quote with its source.
   - If an attributed number can be checked against the stats store, it must be, and it becomes a checked number.
2. **Chart rule.** Every chart:
   - is drawn from the same query that rechecks the claim
   - uses the claim as its title
   - labels every bar or point
   - highlights this game
   - starts bars at zero, and shows rates over time as lines
3. **Coverage minimums.** After the run, code checks that each source type in the starting set produced findings or an explicit "nothing found". If one didn't and time allows, a top-up run targets the gap.
4. **Sensitive content.** Findings in these categories are held until a named approver signs off, separately for internal staff, producers and outside partners:
   - conflict between players and coaches
   - injury or health
   - officiating
   - anything legal
   - quoting a fan
5. **Ranking.** Findings are ranked on:
   - how new they are, measured against coverage published before the cutoff, plus "already had it" clicks
   - audience fit
   - their link to a directive or suggestion

   The scores come from a **separate judge**: one model call per run with a fixed rubric, not the agents that wrote the findings. Code adds the signals it can compute, such as text similarity to the pre-cutoff coverage. The rubric stays fixed across scorecard comparisons. Unprompted finds are capped at a minority of the packet.
6. **Data boundaries.** Record claims carry where the data starts.
7. **Time.** Every run records its wall-clock duration. A post-game run over its limit is a failure, even if its output is good.

### 5.6 What people see (static HTML built from the store)

- **Pre-game briefing.** For producers and the live social and stats team: storylines to watch and milestones within reach. For leadership: the same, with a way to steer the post-game run, using Back it, Comment, Make it a directive and a reply in plain language.
- **Post-game leadership email, sent first** (mockup `leadership-view.html`, option A). It contains:
  - what happened
  - what moved since pre-game
  - the in-game pulse
  - angles with Back it, Comment, Make it a directive and Drop
  - directives with a "still happy with this?" prompt
  - reply in plain language to give direction
  - the run's cost and how long the briefing took after full time

  It is rendered to `outbox/` and not sent.
- **Supplemental addendum,** "What's new since the briefing": press conference moments and fresh fan reaction, each linked to the finding it changes.
- **Producer board** (`producer-board-v2.html`). One shared board, filtered by role, with:
  - leadership reactions, showing who said what and when
  - angles ranked per show, each with why it fits, a chart, sources and which teams are using it
  - the buttons Using it, Already had it, Not for us and Ask a follow-up
  - the producer's own notes matched against the angles
  - tracked topics
  - when the packet builds
- **Finding detail** (`finding-detail.html`). It has:
  - the full chart, with a range switch and a table or CSV view
  - "How we know", showing the recheck stamp, with the query hidden behind "Show the query"
  - the trail of steps, each linked to the original moment
  - quotes that support the finding and quotes that push back
  - leads to follow
  - the original sources
  - a greyed-out "Make a graphic · later"
  - **"Ask about this"**, a plain-language follow-up box. Answers appear as new findings under this one, each with its own chart, evidence and trail. Locally it starts a follow-up run. The static site shows Bart's three demo questions already answered.
- **Published on GitHub Pages** so the GM can click through a real run without installing anything. Buttons show the state left by the simulated feedback round; they don't write anything back.

### 5.7 The collaboration loop in the demo

1. Pre-game run, then the pre-game briefing.
2. Leadership's steer (simulated personas, **labelled as simulated**) goes into the post-game brief.
3. Post-game run, with the briefing out by full time plus 30 minutes.
4. Simulated reactions and directives.
5. Supplemental run, then the addendum.
6. The producer board.
7. Follow-up runs on Bart's three questions.
8. A packet for each show.

### 5.8 Improvement loop (a small version in the build)

- A scorecard command re-runs a fixed game's post-game run and prints:
  - the recheck pass rate
  - coverage
  - the scores for how new the angles are, audience fit and direction
  - how many sensitive items were held
  - wall-clock time and cost at API prices
- Any prompt or model change is compared on the scorecard before it's kept.
- The docs describe the full loop: feedback becomes test cases, test cases drive prompt changes, and every change is checked against past games.

### 5.9 What execs see

- Usage per team, from Using it.
- How new the angles are, from Already had it.
- Audience fit, from Not for us.
- Time from the final whistle to the briefing.
- Cost per run and per season at API prices.

In the demo, the usage, novelty and fit numbers come from the simulated round, and every place they appear says so.

## 6. Decisions Bart has made

- **What gets built**
  - The NBL is the build. Daniel's Donuts gets a one-page outline.
  - Four run types: pre-game, post-game (briefing within 30 minutes of the final whistle, as a hard cap), supplemental once interviews land, and follow-ups from any finding.
  - Follow-up research from a finding is a headline feature, and the demo answers his three questions.
- **The pitch**
  - It leads with cross-source links and the collaboration layer. The stats engine is the foundation, and the docs name Genius output as the real input.
  - The build-vs-buy case rests on cost, quality, support and continuous improvement, and learns from OptaAI.
- **What people see**
  - Leadership gets email first, producers get the board, and findings open into the detail page.
  - The query is hidden by default.
- **Earlier answers**
  - The deepen answers are accepted: 1a–1f, 2a–2f, 3a–3f and 4a–4e. One correction: agents branch beyond the starting set, and code controls what goes out.
  - What makes a run disappointing: it's obvious or shallow, too niche to use, or far removed from directives.
  - Creating graphics is a future direction.
- **Running it**
  - No Claude API spend: runs use his Claude login, or Claude Code as the fallback.
  - Apify for data sourcing where it works.
  - The repo is public, and the site shows everything in full.

## 7. Claude's calls (please check)

1. **The game (Bart's pick): the NBL27 Round 1 opener, Melbourne United 95–97 Adelaide 36ers, 19 Sep 2026, John Cain Arena.**
   - Match UUID `36dbeb55-58ad-11f1-a69b-43a6b5595d3e`; attendance 9,278.
   - Tip-off 09:30 UTC (7:30 pm AEST).
   - **The final whistle is 11:26:37 UTC (9:26 pm AEST):** the final period's `period / End` event. The Q4 clock hit 0:00 at 11:26:24.
   - The "game completed" event at 11:35:07 is the official stats sign-off, about nine minutes later. Claude's call: the post-game cutoff and the 30-minute cap both run from the whistle, not the sign-off. The scores are final at the buzzer, though minor stat corrections can follow.
   - The NBL match API returns 916 play-by-play events. Their quarter scores reconcile with `box_team.csv`: MEL 23-25-22-25 = 95, ADL 25-24-26-22 = 97. `score_1` is the home team.
   - **Cutoffs:**
     - pre-game: 06:30 UTC
     - post-game data: 11:26:37 UTC (the whistle), with the briefing out by 11:56:37 UTC
     - supplemental: once the press conferences finish
2. **The pre-game run starts about 3 hours before tip-off.**
3. **The supplemental run is an addendum,** not a repeat of the briefing.
4. **Commentary** covers only the final minutes and other key moments.
5. **Stack:** Python, DuckDB for stats, SQLite or DuckDB for the store, a stdio MCP server for tools, and static HTML pages.
6. **Cost** always comes from the reported `total_cost_usd`. The first run checks that it's populated on a subscription login.
7. **Directives and suggestions** are read by the lead from the store, not by a separate specialist.
8. **GitHub Pages** for the click-through.
9. **Two layers of agents.** Specialists propose new lines to the lead instead of starting their own sub-agents.
10. **Numbers come in two kinds,** checked and attributed.
11. **A separate judge** scores ranking.
12. **Gates are developed against a saved store** (section 8).

## 8. Done: the checks

**Automated (the build loop works until these pass):**
- **D1** The chosen game's play-by-play loads from the NBL match API. Its scoring by quarter matches `box_team.csv` (`p1_score`–`p4_score`), and the box score matches that game's page on NBL.com.
- **D2** Every checked number in a shipped packet re-runs and matches: 100%. Every attributed number sits inside a quote with a source.
- **D3** Each source type in a run's starting set has at least one finding or an explicit "nothing found".
- **D4** Every rendered chart passes the chart rule. A test checks the title, labels and highlight.
- **D5** Every finding in a sensitive category is held. None appears in a producer or partner view without a sign-off record.
- **D6** Every finding has at least one piece of evidence with a URL plus a timestamp or row ID. Every finding that isn't a starting point has a parent, and every follow-up finding's chain leads back to its anchor.
- **D7** Every run logs its cost at API prices, wall-clock duration, model usage and route. Each stays under `max_budget_usd`.
- **D8** The static site builds from the store, and every link in every page works.
- **D9** The scorecard command runs on the fixed game and prints every field.
- **D10** The post-game run finishes within its wall-clock limit (about 25 minutes), so the briefing exists by full time plus 30 minutes.
- **D11** Each of the three demo follow-ups produces at least one checked finding under its anchor that answers the question asked.
- **D13** Smoke test, before any full run: every specialist calls one MCP tool and the call is logged with its `agent_id`. This guards against claude-code#30280.
- **D12** The SDK entry point's configuration is tested without a model call. A test checks the agent definitions, MCP server config, caps, hooks and the handling of a recorded result. The README states which route produced the published runs.

**How the checks run without wasting runs:**
- One real run happens early, as soon as the lead, specialists and tools exist. Its store is saved as a fixture.
- D1, D2, D4, D5, D6, D8 and D12 run against fixtures at no model cost. D13 is a single cheap run.
- **On Pro, budget for about 3 full runs:** pre-game, post-game and one follow-up. Everything else waits until usage limits allow.
- **No heavy data job runs without a memory cap.** WSL has 7.7 GB, and a crash takes the session with it.
- D3, D7, D9, D10 and D11 need real runs, and are checked on a small number of deliberate ones.
- Real runs need an explicit flag and write to the usage ledger.
- No unattended loop starts a real run, because each one spends Bart's subscription usage.

**Human acceptance (after the build):**
- **H1** Ten sampled claims are checked by hand against NBL.com.
- **H2** Backtest the post-game packet against what was published after its cutoff, which the run couldn't see. "Found the story" means a published headline angle appears among the packet's angles, with the same subject and the same claim. Report how many overlap and how many angles are new.
- **H3** A basketball fan who isn't Bart rates the new angles blind, asking only "would you post this?".
- **H4** Someone who hires engineers does the 60-second read test on the README and the LinkedIn message.

## 9. Scope and cut line

**Must** (a credible demo on its own)
- One game, plus all seasons back to 2015-16, loaded into DuckDB.
- A lead agent and 3–4 specialists, with caps, sharing one MCP tool server.
- The pre-game and post-game runs, with the post-game run inside its time limit.
- One of the three follow-ups, answered.
- At least two source types beyond stats. Commentary is preferred; otherwise press conferences or NBL Now plus fans.
- Findings with evidence and parent links.
- The recheck, the chart rule, the sensitive hold, and `as_of` on every tool.
- The judge, as one call per run.
- The pre-game briefing, the leadership email and the finding detail pages, rendered as static HTML.
- The usage ledger, saved-store fixtures and D12.
- A README with the 60-second path, including how the run was produced.

**Should**
- The supplemental run and its addendum.
- The other two follow-ups.
- The simulated feedback round.
- The producer board.
- The scorecard.
- The backtest (H2).
- GitHub Pages.
- The commentary segment, if Must used a fallback.
- The wider media corpus: NBL.com and club news for the season.

**Could**
- Matching producers' notes, and the role switcher.
- A Daniel's Donuts outline longer than one page.

## 10. Deliverables

- **Repo layout:** `README.md`, `src/`, `prompts/`, `data/` (raw files, gitignored), `site/` (rendered pages), `outbox/`, `docs/`, `lessons.md`.
- **Docs written after the build,** so they quote real run numbers and real findings:
  - `gm-proposal.md` (one page)
  - `prd.md`
  - `architecture.md`
  - `build-vs-buy.md`
  - `cost.md`
  - `assumptions.md` (numbered)
  - `team-pitch.md`
  - `daniels-donuts-outline.md`
- **`lessons.md`,** started when the repo is set up, with these entries:
  - agents roam, and code gates what goes out
  - don't cut items from Bart's core workflow on Claude's own judgement
  - timing requirements come from the job, not from the data
  - cap memory before any heavy data job on this machine
- **A video** of about 3 minutes showing the process and a run.
- **The LinkedIn message,** drafted last and given a humanizer pass.

## 11. Assumptions (starting register)

- **A1** LK holds stats at least as detailed as nblR's.
- **A2** LK has full access to broadcast audio, show and press conference recordings, and their transcripts, including live transcription during games.
- **A3** LK owns its social engagement data.
- **A4** Email is the channel for now; Slack or voice notes could replace it in a real rollout.
- **A5** LK runs a mainstream stack, email provider and cloud.
- **A6** Genius Sports output is available as an input, live.
- **A7** The roles are the CEO, the NBL GM, LK directors, the marketing lead, show producers, the head of social, the live social and stats team, and the ESPN broadcast team. No real names are used.
- **A8** Persona feedback stands in for real users.
- **A9** Running on a personal Claude login is a convenience for the demo only. Production would use API keys, or Bedrock or Vertex.

## 12. Sanity-check results (2026-10-28)

Full table: [sanity-check findings](../../reviews/2026-10-28-sanity-check-findings.md). Everything below is already reflected in sections 4, 5 and 8.

| # | Assumption | Verdict | What changed |
|---|---|---|---|
| A1 | The SDK runs on Bart's Claude login | Confirmed. Cost reporting is checked on the first run | README notes Anthropic paused its announced changes |
| A2 | The `claude -p` fallback shares agents and tools | Confirmed | None |
| A3 | One MCP server serves both routes, with calls attributable | Divergent (claude-code#30280) | Explicit MCP access per specialist; smoke test D13; agent identity from hook input |
| A4 | SDK features and caps | Confirmed | Pin version 0.2.127 or later; watch the casing |
| A5 | Parallel specialists finish within about 25 minutes | Confirmed with change; timing uncertain | Our code enforces the deadline with `interrupt()`; `maxTurns`; starting set prepared once |
| A6 | `pbp.rds` reads with `pyreadr` | Divergent | History from `box_team.csv` quarter scores; play-by-play per game from the NBL match API; never parse the full file here |
| A7 | Apify for fans and news | Confirmed with caveats | Free credit; test the Reddit scraper; day-level media cutoffs |
| A8 | Stream and transcription | Uncertain | Bart supplies the stream; test a 20-minute transcription early with a small model |
| A9 | Pro allows 8–12 runs a day | Divergent | About 3 full runs; Opus lead and Sonnet 5.5 specialists on the demo route |
| A10 | Tracing | OTel confirmed | Docs only |

Not technical, so still open for the docs: whether Opta covers the NBL, and Jam TV's current production role.

## 13. Left to the builder

- Prompt wording.
- Exact table schemas and tool signatures.
- The chart library, as long as it follows the chart rule.
- The static site generator.
- How the trail is drawn.
- Which Whisper variant to use.

## 14. Next steps

1. ~~Run the sanity-check on section 12 and fold the verdicts into this document.~~ Done.
2. ~~Bart approves the document and picks the game.~~ Done 2026-10-28: the Round 1 opener.
3. Prove: turn section 8 into failing checks.
4. Build through `/codex-build`. Bart's standing rule is no implementation plan.

`git init`, `.gitignore` (including `.superpowers/`) and `lessons.md` are created at repo setup.
