# Build brief: make the site match the approved mockups

**Design approved by Bart:** 2026-10-28 (mockups), and scope confirmed on 2026-10-29 · **Builder:** Codex (gpt-5.6-terra) · **Integrator:** Claude Code (Opus 5.5). This brief carries everything from the design conversation you need. If something is missing, ask with `NEEDS_DECISION` instead of searching or guessing.

## Goal

The published site drifted from the approved mockups into three single-column lists. Rebuild the three pages so each one reads like its mockup, using only data the store already holds:
- the producer board (`site/index.html`)
- the leadership email (`site/outbox/post-game-email.html`)
- the finding page (`site/findings/<id>.html`)

Also add a `simulate` command. It loads a labelled, simulated feedback round (reactions, team usage and directives) into a store, which the design planned and never ran. Finally, fix the chart bug that pushes rotated axis labels off the canvas.

## Design

The approved look lives in `docs/design/mockups/`:

| Page | Mockup |
|---|---|
| Producer board | `producer-board-v2.html` |
| Email | `leadership-view.html`, **option A (email first)** only. Ignore option B. |
| Finding page | `finding-detail.html` |

The mockups are HTML fragments meant for a frame that defines `--bg-primary`, `--bg-secondary`, `--bg-tertiary`, `--border`, `--text-primary`, `--text-secondary`, `--accent` and `--warning`. Port their structure and visual language into `site.py`'s CSS, using the site's existing tokens (`--bg`, `--card`, `--text`, `--muted`, `--line`, `--accent`, `--held`). Add tokens you need, such as pill colours for ok, lead and hold, and define each one for dark mode as well.

Every value in the mockups is invented. Copy the layout and visual language, never the content. Everything shown must come from the store, or be an honest empty state.

Design spec: `docs/superpowers/specs/2026-10-28-nbl-storyline-desk-design.md`. Relevant sections:
- **5.6:** what each page shows
- **5.7:** the simulated feedback round, which must be "labelled as simulated"
- **5.9:** "every place they appear says so"

### Producer board: `index.html`

The page is in three parts, top to bottom:

1. **A slim intro above the board.**
   - The title, a one-line description, and the existing "Start here" links.
   - A link to the pre-game briefing (`pre-game.html`).
   - `test_landing.py` already checks this intro. Keep its links and labels.
2. **The board** (`class="board"`), styled as the mockup's frame.
3. **Below the board.**
   - The runs, as a compact table: run label, cutoff, duration, cost label and findings count. Use the human run labels.
   - The existing `<details>` "Searched, nothing found".
   - "How this was built".

The board's **top bar** shows:
- the score
- "Viewing as", a `<select id="role-switch">` whose first option is `value="all"`, followed by one option for each audience present on the board's angle cards

A few lines of inline JS filter the angle cards by `data-audience` and update the middle column's heading. Never use `?role=` links. With JS off, every card shows.

The board has three columns, `board-left`, `board-angles` and `board-right`, in that order. Under about 1050px they collapse to a single column.

**Left column (`board-left`)**
- **"From leadership"** is a feed of:
  - simulated reactions. These are feedback rows whose action is `back`, `comment` or `drop`. Show who (`role`), what they did ("Backed", "Commented" or "Dropped") and the text, and label each one "simulated".
  - every real sign-off, e.g. "Signed off for producers · Bart Lind (demo approver)", linking its finding.
- **"Active directives":** each active directive shows its text, its `owner_role`, "mandatory" when set, "expires <date>" when set, and a "simulated" label when `simulated` is set. When there are none, show "No directives yet".

**Middle column (`board-angles`)**
- The heading starts "Angles for".
- **The angles** are the findings shown as cards:
  - Include post-game, supplemental and follow-up findings that are `shipped`, plus `held` findings that have at least one sign-off.
  - Leave out pre-game findings; they stay in the pre-game briefing. Leave out `nothing_found` findings too.
  - Rank by `_judge_score` descending, with `id` as the tiebreak.
- **Each angle card** is `<article class="angle …" data-finding="<id>" data-audience="<space-separated audiences>">` (escape attributes) and contains:
  - the headline, linking `findings/<id>.html`
  - pills: kind (e.g. "stats checked" for `checked`), the run label, and the held/sign-off state
  - a one-line description: the claim
  - an evidence box. When the finding has a valid chart, the chart sits on the left (scaled to about 240px wide) and a compact evidence summary sits on the right: source types and refs, with no raw URLs.
  - team-usage chips from feedback whose action is `using it`, `already had it` or `not for us`, formatted as "<role>: using it". With none, show the mockup's "no one using yet".
  - the buttons Using it, Already had it, Not for us and Ask a follow-up
- **The held strip:** after the cards, a compact strip (`class="held-strip"`) lists held findings that have no sign-off. Each entry is one line: the headline link plus "held · <category> · waiting for sign-off". The strip has no charts and no buttons. It plays the role of the mockup's "kept internal" row.

**Right column (`board-right`)**
- **"Ask the next run":** a `<textarea>` with a placeholder, and a one-line note that a local run starts a follow-up (`python -m storydesk run follow_up …`) while the static site doesn't write back. Below that, list each follow-up request: the question, who asked, and its state. An answered request links the answer finding(s) from the answering run.
- **"This run":** the post-game run's duration and cost label.

The board ends with a one-line footer explaining that the buttons show the simulated round's state and don't write back.

### Email: `outbox/post-game-email.html`

Mockup A puts a narrow column, about 640px, on the page background, inside a card styled as an email.

**Header block**
- From: NBL Storyline Desk
- To: League leadership
- Subject: "<score>: what moved, and N angles for your call", as plain text
- **Sent:** use the cutoff wording ("N min from a cutoff frozen at the final whistle"). Never use "after full time"; `test_publish_safety.py` forbids it.

Then the score as a large heading, with the run meta under it.

**Sections.** Each heading stays an `<h2>`, styled as the mockup's small uppercase labels, because the existing tests split on `<h2`.
- **What happened:** the exec summary, plus the final score and quarter scores.
- **What moved since pre-game:** a compact `<table>`, one row per moved item:
  - the "Pre-game said" headline, as plain text and not linked, because each finding is linked only once in the email
  - the post-game headline, linked
  - a kind pill
- **During the game (in-game pulse):** compact rows.
- **Angles for the next 48 hours:** compact cards. Each has:
  - the headline link and a kind pill
  - the claim
  - a "For: <audiences joined by ', '>" line
  - the buttons Back it, Comment, Make it a directive and Drop
- **Held for sign-off:** one `<div class="held-row">` per held item, holding:
  - its single link
  - the existing `_status_badge`
  - its sign-off lines
  - the buttons "Approve for <remaining audience>" and "Keep internal"
  - no `card` articles
- **Your directives:** the same data as the board, or "No directives yet".
- **Addendum: what's new since the briefing:** compact rows.
- **Suggested follow-ups:** keep the existing `_leadership_followups_html`, at most 3.
- **Give direction:** "Reply to this email in plain language. It goes to the next run and to the producers."

**Footer.** Last of all comes a footer holding:
- a link `href="../index.html"` whose text includes "board", e.g. "Open the full board →"
- the run meta: agents, minutes and cost label
- "Feedback shown here is simulated."
- the Editor's notes `<details>`

### Finding page: `findings/<id>.html`

**Header**
- the breadcrumb: Board › score › Finding N
- the `<h1>` headline, unchanged; `headline_for` keeps the data boundary
- pills: kind, held/sign-off state, "For: …" audiences, and usage chips
- on the right, the buttons Using it, Already had it, Not for us and Comment, then `<button disabled>Make a graphic · later</button>`. Grey it out with colour. Never use opacity on text (`test_round4_polish.py`).
- the run cost line, small and under the header

**Two columns.** `detail-main` is wide and `detail-side` is about 300px. They collapse to a single column under about 900px.

**`detail-main`**
- **The chart card:** the chart's title is the claim, followed by the chart. Under it sits a "How we know · rechecked by code" strip, with the query in a `<details>` titled "Show the query". The SQL stays hidden by default; that's a design decision.
- **"How the agents got here":** a vertical timeline. Each step has:
  - a source-type tag (STATS, COMMENTARY, FANS…)
  - a one-line title
  - a small "Open" link to the related page or source, where there is one

  The steps come from three places, in order:
  1. the parent chain, oldest first, each linked to its page
  2. this finding's own evidence, one step per item: source type, ref, and quote if present, linked through `_evidence_source_html`
  3. children, each linked

  Never print "No linked finding yet". A finding always has at least its evidence steps.

**`detail-side`**, in this order:
1. **"What people said":** the quotes from non-stats evidence, with the handle stripped through `_HANDLE` as now. Each quote shows its source-type tag, its ref and its link. When no item has a quote, give a short empty state. Never print "Evidence recorded without a quote".
2. **"Follow the lead":** one card per suggested follow-up. Each card has:
   - a type pill, plus a "Projection" pill when the type is `on_pace`
   - the question and the why
   - the command, inside a `<details><summary>Run it locally</summary>…</details>`

   The existing command format must stay, since `test_round3_followups.py` matches it. Then the follow-up requests anchored on this finding, with links to their answers.
3. **"Original sources":** one row per distinct source URL after `_evidence_source_html` mapping. Each row has the source type, a short ref, and "open ↗". Inert, non-web references show as text.

### Charts: `src/storydesk/charts.py`

Rotated x labels are anchored at `height - 30` instead of just under the axis, so long labels run off the left and bottom edges. Today only "(21:50)" shows on finding 25.

The fix:
- Anchor rotated labels 10–24px below `baseline`.
- Widen the left margin, or reserve room, so that the estimate `len(label) * 6.5 * 0.7071` fits on the canvas from the anchor, both left and down.

Non-rotated labels may keep their current placement. Charts must scale down inside cards: `max-width:100%; height:auto` in the page CSS. Chart text must stay readable in dark mode.

### Simulated round: `store.py` and `cli.py`

**Store**
- Add `simulated INTEGER NOT NULL DEFAULT 1` to `directives`, through `_add_column_if_missing`.
- `Store.add_directive(owner_role, text, mandatory=False, expires=None, simulated=True)`.

**CLI.** Add `python -m storydesk simulate --store <db> --file <json>`. The JSON looks like this:

```json
{"feedback": [{"finding_id": 25, "role": "League CEO", "action": "back", "text": "..."}],
 "directives": [{"owner_role": "...", "text": "...", "mandatory": false, "expires": "2026-10-05"}]}
```

- **Allowed feedback actions** are the design's: `back`, `comment`, `drop`, `using it`, `already had it`, `not for us` and `ask a follow-up`.
- **Validate everything first.** Every `finding_id` must exist and every action must be allowed. If anything is invalid, exit non-zero, or raise, with nothing written.
- **Then, in one transaction:**
  1. delete every `feedback` row where `simulated = 1` and every `directives` row where `simulated = 1`
  2. insert the file's rows with `simulated = 1`

  Running it twice gives the same store. Real rows (`simulated = 0`) are never touched.

## Done when

```
.venv/bin/python -m pytest -m "not live" -q -p no:cacheprovider --basetemp "$PWD/.pytest_tmp" \
  --deselect tests/test_mockup_layout.py::test_published_snapshot_carries_the_labelled_simulated_round \
  --deselect tests/test_final_review_fixes.py::test_committed_site_has_no_unsafe_or_broken_links \
  --deselect tests/test_final_review_fixes.py::test_committed_site_links_stats_evidence_to_real_sources \
  --deselect tests/test_final_review_fixes.py::test_committed_record_page_headline_states_the_data_boundary
```

This must exit 0. Delete `.pytest_tmp` afterwards. It runs the whole offline suite, which takes about 7 minutes.

The new checks are in `tests/test_mockup_layout.py`. All the existing checks must keep passing. The deselected checks read the committed `site/` and `published/`, so they pass only after Claude writes the simulated round and rebuilds the site.

## Scope

- **May change:** `src/storydesk/site.py`, `src/storydesk/charts.py`, `src/storydesk/store.py`, `src/storydesk/cli.py`.
- **Must not change:**
  - anything under `tests/`
  - `site/`, `published/`, `docs/`, `README.md`, `prompts/` and `.github/`
  - the runner, the gates, the judge, and any agent behaviour

  Claude writes the simulated round's content, rebuilds the site and updates the docs afterwards.
- **Fixed interfaces:**
  - `build_site(store, stats_db, out_dir, *, game_id)`
  - `headline_for`
  - `_evidence_source_html`'s behaviour
  - the store's existing method signatures. The only change is the new `simulated` keyword on `add_directive`.
  - the `follow_up` command text shown on finding pages
  - page paths

## Facts — don't re-derive

- **Constraints from existing tests:**
  - **The index:**
    - It must never contain the run-type keys `pre_game` or `post_game`, so no `data-run="post_game"`. Use labels.
    - Before the "Searched, nothing found" `<details>`, it must not link any `nothing_found` finding.
    - It must contain the labels "Pre-game", "Post-game" and "Follow-up", and the links `href="outbox/post-game-email.html"`, the repo URL and "build-log".
  - **Links:**
    - Every `href` must be `http(s)`, `../`, `*.html`, `#` or `dir/`. `_unsafe_hrefs` in `test_final_review_fixes.py` rejects anything else.
    - Every internal link must resolve (`test_d08_site.py`).
  - **Untrusted text:** any text from the store, including feedback text, directive text, roles and audiences, must be escaped everywhere it appears, attributes included (`test_publish_safety.py`).
  - **The email:**
    - Each finding is linked at most once before "Suggested follow-ups".
    - `held[^<]{0,60}officiating` must match.
    - The full claim of a shipped angle appears.
    - "simulated" appears.
    - The text after "What happened" and up to the next `<h2` holds the exec summary.
  - **Sign-offs:** "Signed off for producers" and the approver's name show on the finding page and in the email. A held badge names its remaining audiences.
  - **Colour and contrast:** `--muted` keeps WCAG AA contrast, and no text class uses `opacity` (`test_round4_polish.py`).
- **The published store** (`published/store.db`) has:
  - 42 findings, 16 with charts, and 61 evidence items with quotes
  - `stance` empty everywhere, so there's no supports/pushes-back split. One "What people said" list is right.
  - 0 directives and 0 feedback rows. Claude adds the simulated round after your build.
  - 7 sign-offs and 1 answered follow-up request
  - audiences drawn from producers, broadcast, social, leadership and partners
  - finding 25 has no parent and no children, which is why its page needs the evidence-step trail
- **Data that isn't in the store,** so leave it out and don't invent it:
  - the mockup's "Your notes for Monday" panel (a "Could" in the design)
  - "Why your show:" (no stored field; use the claim)
  - packet build times
  - timestamps on simulated reactions
- **Tooling:**
  - `grep` in this shell is ugrep. Use Python for long regexes.
  - WSL has about 7.7 GB of RAM. Never parse `data/raw/pbp.rds`.

## How to work

- The design is approved. Don't brainstorm and don't write a plan: build against the checks.
- Follow the repo's conventions:
  - the f-string HTML building and `escape()` patterns already in `site.py`
  - small helpers rather than one giant function
  - read `lessons.md`
- If a choice comes up that the design doesn't make and a wrong guess would matter, or a check looks wrong, stop and end your final message with `NEEDS_DECISION: <question>`. Never edit the checks.
- After 4 attempts at the done command without progress, stop and report.
- Don't commit.

## Your final message

- The done command's output (last lines).
- Files changed, one line each.
- Calls you made that the design didn't, one line each.
- Anything you noticed but left alone (out of scope).
- `NEEDS_DECISION: <question>` as the last line, if you stopped for one.
