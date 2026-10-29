Repo: /home/bart/projects/LK Group Demo, on branch `finish`. Draft six docs under `docs/`. Claude, the integrator, will review them, and Bart is applying for the AI Engineer role at LK Group. Read first:
- `docs/superpowers/specs/2026-10-28-nbl-storyline-desk-design.md` (the approved design)
- `docs/build-log.md`
- `docs/data-provenance.md`
- `lessons.md`
- `published/README.md`
- the code in `src/storydesk/` and the prompts in `prompts/`

Use real numbers from `published/store.db` (SQLite: the `runs` and `findings` tables), and quote real findings by their headline.

Style: plain, specific, short sentences, no hype, no em dashes, no marketing language. Use "we" for the proposed LK team. Every claim must be traceable to the code, the store or the design. Mark assumptions as assumptions. Don't edit anything outside `docs/`, and don't commit.

## Documents

1. **`docs/architecture.md`** (readers: engineers on a 3–4 person team). Cover:
   - the components and how data flows between them, with a Mermaid diagram
   - the Agent SDK topology: an Opus lead with four Sonnet specialists, depth 1, explicit MCP tools for each specialist, hooks, caps, and the wall-clock deadline enforced in code
   - the stdio MCP tool server and the `as_of` guarantee: the four safe relations, the SQL allowlist, corpus windows
   - the store schema
   - the gates: recheck, one checked number per finding, chart rule, sensitive hold, data boundary, coverage and top-up
   - the judge pass: scores, headlines, exec summary, suggested follow-ups
   - the four run types plus smoke
   - the site
   - how to run it: `fetch`, `build-db`, `run … --live`, `rejudge`, `site`
   - how to extend it: a new source, a new run type
   - the known limits

2. **`docs/cost.md`** (readers: leadership).
   - Measured cost per run type, at API prices from `runs.cost_usd`, and duration.
   - A per-game estimate: pre-game, post-game, supplemental and two follow-ups.
   - A per-regular-season estimate for 165 games.
   - The levers: effort per role, a Sonnet lead, caching, fewer follow-ups, sharing digests.
   - Subscription versus API key.
   - What's not costed: engineering time, data feeds, hosting.
   - Questions to ask a vendor such as Stats Perform (OptaAI) for comparison, since their pricing isn't public.

3. **`docs/assumptions.md`** (readers: everyone). A numbered register:
   - A1–A9 from the design, section 11
   - the data assumptions from the provenance doc
   - what LK would need to provide: the Genius live feed, broadcast audio or live transcription, owned social data, email or Slack, and sign-off roles
   - what a pilot would validate

4. **`docs/prd.md`** (readers: internal stakeholders such as the NBL GM, CEO, marketing and media).
   - **Problem and why now:** fast, connected storylines under tight game-day timelines, with OptaAI-style tools as prior art; we lead with cross-source links and the collaboration layer.
   - **Users and jobs:** leadership, producers, social, broadcast, partners.
   - **Scope:** the run types, the email, the board, the finding pages, follow-ups.
   - **Requirements:** speed, accuracy, sign-off, auditability.
   - **Success metrics:** usage rate, novelty, audience fit, time from the whistle to the briefing, cost per game.
   - **Risks and mitigations.**
   - **Rollout:** a pilot with one club's or one round's games, then the season.
   - **Open questions.**

5. **`docs/team-pitch.md`** (readers: the engineering team). How we'd build and run this together:
   - the working method: decide, prove with failing checks, build in small reviewed rounds, run real data early
   - the architecture choices and why
   - what the live runs taught us
   - a prioritised backlog: producer board, live feeds, wider media corpus, OpenTelemetry/LangSmith tracing, Slack, graphics, a feedback-to-eval loop
   - how a new engineer gets going

6. **`docs/daniels-donuts-outline.md`**, one page: the same engine pattern applied to customer reviews for Daniel's Donuts, another LK business.
   - It redoes Agora as a Claude Agent SDK pipeline, reusing its prompts and patterns. Agora is Bart's existing feedback-analysis product: a fixed Gemini pipeline producing hierarchical themes, stance, sentiment and human-verifiable coding. It analysed 1,643 public airline reviews in 22 minutes for US$2.17. Stoa is its public-consultation sibling with a 9-phase pipeline.
   - It's a structured pipeline with agents at set stages, where the NBL desk does open-ended research.
   - Sources: Google reviews to start, later others and point-of-sale ratings.
   - Agents investigate across sources, for example a cluster of complaints traced to a store and time, then to the roster and sales data.
   - Weekly reports and email.
   - The same gates and sign-off.
   - What LK would need to provide.

Done when all six files exist, each is under about 1,200 words (the Daniel's Donuts outline is one page), they use real numbers, and none has broken relative links. End with a list of the files and their word counts.
