# Product requirements: Daniel's Donuts Review Desk

A design for a weekly review desk, taken as far as working configuration. Two companions show it: the [sample weekly email](../../site/daniels-donuts/weekly.html), rendered from [illustrative data](sample-week.json), and the [`reviewdesk` module](../../src/reviewdesk/), which builds the real Claude Agent SDK options for every role and is checked by offline tests. Every store number and figure in the examples is invented.

## Framing

The Review Desk reads every customer review each week and links it to the sales, staffing, stock and promotion data, a link that usually takes several teams in a room. It tells store, region and network leaders what's changing and why it might be, early, with the evidence attached, and gives them one place to discuss it.

It is a simplified Agora. Agora is my feedback-analysis product: hierarchical themes, sentiment and coding a person can check against the quote. The Review Desk keeps that coding and adds the part reviews alone can't give: the operational data that might explain them, and the reverse direction, where the numbers move first.

The shape differs from the NBL Storyline Desk. NBL research is open-ended, so its lead hands work to subagents. Review analysis is staged and has to be comparable week to week, so code runs each role as its own session in a fixed order, and several of the controls below are session settings.

## Users and recipients

Everyone on the list is internal.

| Who | What they get | What they do with it |
|---|---|---|
| GM | The whole email, Monday 7 am | Sees what's changing across the whole network, and sets stances |
| Operations | The whole email | Picks up roster, stock and waste threads |
| Area managers | The whole email, and named-staff detail for their region | Follows up stores, escalations and praise |
| Marketing | The whole email, and the risk check on next week's promotions | Adjusts or holds promotions |
| Product | The whole email | Range, freshness and new-item threads |
| Store managers | Their own store's section | Acts on what changed at their store |
| Food-safety lead | Food-safety mentions the day they're coded | Reviews and responds before anything public happens |

## Data sources by tier

Google reviews come first. The other sources join in the roadmap's second phase.

### Customer voice

| Source | What it adds | Access route |
|---|---|---|
| Google Business Profile API | As the owner, LK can pull every review for every location, with its rating, date and any reply, not just the handful a public search shows | Owner access to LK's Business Profile account |
| Uber Eats, DoorDash, Menulog | Delivery ratings and complaints ("arrived squashed", "cold", "missing items") | Merchant portal exports, or partner APIs where the contracts allow |
| Instagram, TikTok, Facebook | Comments and messages on Daniel's Donuts' own accounts | The platforms' APIs, for DD's own accounts only |
| Complaints inbox | Complaints sent by email or web form | Mailbox or helpdesk export |
| QR surveys | Short surveys on a counter card, for stores with too few reviews | The survey tool's export |

### Operations

| Source | What it adds | Access route |
|---|---|---|
| POS by hour and channel | Average sale, items per sale, item mix, walk-in against delivery | Nightly POS export or reporting API |
| Rosters and labour hours | Who was on, and how many staff hours each hour had | Rostering system export |
| Stock-outs and end-of-day waste | What sold out when, and what was thrown away | Store waste logs or the inventory system |
| Store format | Standalone, food court or petrol-station kiosk | A store register LK keeps |
| Manager changes | Start dates of new managers | The same store register |

### Commercial

| Source | What it adds | Access route |
|---|---|---|
| Promotions calendar and redemptions | What ran where and when, and what it sold | Marketing's calendar and POS promotion codes |
| Membership deals | Member offers and their uptake | Loyalty platform export |
| Campaign sends and spend | Emails, SMS and paid social, by audience and date | Email platform and ad account exports |

### Context

| Source | What it adds | Access route |
|---|---|---|
| Weather | Heat melts glaze; rain cuts foot traffic | Bureau of Meteorology observations near each store |
| School and public holidays | Changes in who visits and when | Published Victorian calendars |
| Local events, including Melbourne United home games | Crowds near a store on the day, and a cross-portfolio link inside LK | Event listings, and LK's own fixture list |
| Competitor openings | A new store nearby | A list area managers keep |

## Specialists

Code runs a lead, five specialists and a judge, each as its own Agent SDK session.

| Role | What it does |
|---|---|
| Lead | Picks the week's threads, asks the specialists for the data that could explain them, and assembles the email. Its session stays open for meeting mode |
| Customer voice | Codes the week's reviews by theme, sentiment and evidence quote. Code then counts themes for this week, the last month and the last 3 months, by store, region and against the whole network: a simplified Agora |
| Operations | Links themes and number changes to POS, rosters, stock and waste, running its stats in Python inside a sandbox |
| Product | Range, freshness, missing items and how new items are received |
| Marketing | How promotions and member deals show up in reviews and sales, plus a risk check on next week's promotions: which stores and hours they will load, and whether rosters and stock are set for them |
| Context | Weather, holidays, events and competitor openings next to the stores and days they touch |
| Judge | Ranks the stories, with food safety first, and polices causal language |

The judge allows three labels and no others. "coincides with" means two things happened together. "consistent with" means the baseline and context were checked and fit, but other explanations remain. "tested" means a comparison against matched stores or a planned trial was run. A finding that says "caused" goes back.

## Threads

The desk follows six kinds of thread. The [sample email](../../site/daniels-donuts/weekly.html) shows one of each.

1. **A theme spike, traced and explained.** Complaints about stale donuts jump after 8 pm at three south-east Melbourne stores, starting with Store 12 · south-east Melbourne. The desk traces them to the hour, then to late-evening stock since closing time moved later.
2. **Praise worth spreading.** Reviews praising a new manager's counter rise. The suggestion is a training note for other stores, never a ranking of staff.
3. **A promotion with side effects.** A lunch deal sells, and wait-time complaints rise at food-court stores in the same hours.
4. **Data first, the reverse direction.** Items per sale fall at kiosks with no change in reviews, and stock records show a range selling out before noon.
5. **Food safety, escalated at once.** An allergen, illness or foreign-object mention goes to the area manager and the food-safety lead the day it is coded, not on Monday.
6. **Quiet stores.** A store with too few reviews to report on: are there fewer customers, or just fewer reviews?

## Gates

Privacy, accuracy and quality control are built in from the first run.

- **Recheck every number.** Code recomputes each number in the email from the source tables before it goes out. A mismatch drops the story.
- **A minimum sample per store.** A store needs at least 10 reviews in the window before the desk reports its theme shares. Below that it says so.
- **Named staff are sensitive.** Staff names go only to the area manager. The story itself goes to the list without them, under a sensitive tag, and never feeds performance management automatically. Staff names are also stripped from anything drafted for outside.
- **A stance and a comment on every story.** Anyone on the list can mark a story push it, use it if it comes up, or steer away, with a comment. Drafted replies and promotions need a recorded push or use-if-raised stance first.
- **Causal language.** Every explanation carries one of the judge's three labels.

## The weekly email

The email goes at 7 am on Monday to the GM, operations, area managers, marketing and product. Each store manager gets their own store's section. The order is:

1. a short lead
2. what changed across the network, with a theme-mix donut
3. the threads the desk followed, each as a story box with a premise, the number, its causal label, a chart where it earns one, and a suggestion
4. sensitive stories, food safety first
5. a section for each store manager
6. questions for Thursday's ops meeting

Each story has stance links. In the demo they are `mailto:` links to `review-desk@example.com`, mirroring the NBL desk. In production a reply would arrive through an inbound-email webhook (for example n8n or Power Automate), record the stance, and trigger a follow-up run.

## Meeting mode

During the weekly ops meeting, the desk resumes the week's lead session with `resume`, so a question asked in the room is answered from the same evidence, with nothing re-read. When the room has two explanations for one change, the desk forks the session with `fork_session`, so each explanation is checked from the same starting point and the two answers sit side by side. Forking branches the conversation history, not the files.

## SDK features

The NBL desk already shows subagents, an in-process MCP server, logging hooks, `interrupt()` against a deadline, a mix of models and effort levels, `max_budget_usd`, `setting_sources=[]`, `strict_mcp_config` and disallowed tools. The review desk adds six more.

| Feature | What the desk uses it for | Where | Docs |
|---|---|---|---|
| Structured outputs (`output_format` with a JSON schema) | Customer voice returns theme coding that must validate against `THEME_CODING_SCHEMA`. Code, not the model, counts the shares. The agent returns the result through a `StructuredOutput` tool that Claude Code adds, so that tool is pre-approved for the role's `dontAsk` mode. A session that can't produce valid output ends with `error_max_structured_output_retries`, and the week's coding is retried, never guessed | `agents.py` (customer voice), `schema.py` | https://code.claude.com/docs/en/agent-sdk/structured-outputs |
| Message Batches | Bulk coding of a backlog, or a full re-code after the theme list changes, at half the standard price. The module builds the request list only, with each review sent without its author's name | `batches.py` | https://platform.claude.com/docs/en/build-with-claude/batch-processing |
| Sandbox | Operations runs its stats in Python through Bash inside the sandbox. If the sandbox can't start, the session refuses to run (`failIfUnavailable`). Commands can't retry outside it. No host is allow-listed, and `strictAllowlist` makes the sandbox proxy refuse every other host in every permission mode, so the network is off. The SDK passes these keys through `--settings`, which can set any user-scope key. Writes go to the temp directory, not the agent folder. The sandbox covers shell commands only, so WebFetch and WebSearch are disallowed as well | `agents.py` (operations) | https://code.claude.com/docs/en/agent-sdk/python, https://code.claude.com/docs/en/sandboxing and https://code.claude.com/docs/en/settings |
| Approval callback (`can_use_tool`) | `post_review_reply` and `draft_promo` are refused unless a recorded stance approves that action for that story. When one does, staff names are stripped through `updated_input`. In Python the callback needs a streaming prompt and a no-op `PreToolUse` hook to keep the stream open | `approvals.py` | https://code.claude.com/docs/en/agent-sdk/user-input |
| Sessions (`resume`, `fork_session`) | Meeting mode resumes the week's session; competing explanations fork it | `agents.py` (`meeting_options`, `fork_options`) | https://code.claude.com/docs/en/agent-sdk/sessions |
| Skills | `theme-coding` and `promo-effect` as SKILL.md packages: a small library of reusable prompt templates and workflows that every role shares | `agent/.claude/skills/` | https://code.claude.com/docs/en/agent-sdk/skills and https://code.claude.com/docs/en/agent-sdk/claude-code-features |
| Behaviour in a live run | Two settings are checked against the docs and the bundled CLI but haven't been run live. First, `failIfUnavailable`, `strictAllowlist` and `filesystem` aren't in the Python SDK's `SandboxSettings` type, though they are in the bundled CLI. Second, it is unverified whether customer voice's explicit `tools` list leaves the `StructuredOutput` tool in place | the offline tests | unverified |

**Why `setting_sources=["project"]` here, when the NBL desk uses `setting_sources=[]`.** Skills load only through filesystem setting sources, so the NBL desk's empty list would load none. The review desk loads `"project"` and never `"user"`. Its `cwd` is pinned to `src/reviewdesk/agent/`, a folder that holds nothing but `.claude/skills/`. So the settings and skills that load are the repo's own, version-controlled and reviewed, never the operator's personal ones. The explicit value matters: setting `skills` without `setting_sources` makes the SDK default to `["user", "project"]`. Skill discovery walks from `cwd` up to the repo root, so a test walks that path and fails if any other skill, `CLAUDE.md`, agent or command appears. Each role's `skills` list is explicit, and `"Skill"` is in its `tools` list. Skills are a context filter, not a sandbox: unlisted skill files stay readable on disk, so none holds anything secret.

## Roadmap

1. **A 5-store pilot**, Google reviews and POS only, compared with a human analyst's read of the same weeks. It asks: did the desk find what the analyst found, what did it add, and did any story change a decision?
2. **All stores and sources**, with delivery platforms, social, the complaints inbox and surveys, plus a pack for the weekly ops meeting.
3. **Drafted actions**, each behind a stance: whole campaigns, staff training modules, roster suggestions, waste and labour cost analysis, and review replies.
4. **Strategy**: menu changes, pricing tests and new-site scoring, and checking whether the actions taken moved the numbers.

## What LK provides

- Owner access to the Business Profile account, and merchant access to the delivery platforms and DD's social accounts.
- Nightly exports from POS, rostering, waste and stock, the promotions calendar, the loyalty platform and campaign tools.
- A store register: number, region, format and manager start dates.
- The recipient list, the roles that can set stances, and a named food-safety contact.
- Privacy rules for customer and staff data, including retention.
- An analyst's time for the pilot comparison.

## Risks

- **Privacy.** Reviews carry customers' names and sometimes details of their visit. Reviewer names stay out of model requests, data is kept for an agreed period, and only DD's own social accounts are read.
- **Staff.** Named praise can feel like surveillance, and named complaints can feel like a case being built. Staff names go only to the area manager. The list sees the story without them, under a sensitive tag, and it never feeds performance management automatically.
- **Causation.** Reviews and sales move for many reasons at once. The desk links and suggests, and its labels say how far each link has been checked. A suggestion comes with the trial that would test it.
- **Reviews as instructions.** Review text is untrusted input. A review can't reach a write tool, because drafted replies and promotions need an approval record.

## The offer

I'm happy to use this to walk you through how I build, in an interview or a working session.
