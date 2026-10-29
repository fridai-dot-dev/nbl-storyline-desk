## Claude's visual check against the mockups

These come from rendering the published store with the simulated round applied, at 1400px and 390px, in light and dark. The structure matches the mockups. The density doesn't yet, so fix these:

**Board (`index.html`)**
- V1. Angle cards print the whole claim, up to 10 lines. Show only the claim's first sentence, clamped to 2 lines with CSS. The full claim stays on the finding page.
- V2. The card chart is the 680×340 SVG scaled down to about 240px, so its text renders at about 4px and can't be read. Render a compact chart for cards: add optional `width`/`height` keyword arguments to `render_bar_chart`/`render_line_chart`, keeping the current defaults, and draw the card chart at about 320×190. Its text then shows at its real size, as on the mockup. Widen the chart slot to about 320px.
- V3. The evidence summary prints raw refs (match ids, row lists). Summarise by source type with counts instead, e.g. "Evidence: 3 stats checks · 1 commentary quote · 2 media items". Show no ids.
- V4. The left column repeats "Signed off for producers / Bart Lind (demo approver)" as seven cards, and none of them says which finding. Group sign-offs by approver and audience into one feed item, e.g. "Bart Lind (demo approver) signed off 7 held items for producers", followed by a compact list of the headlines as links.
- V5. The board is squeezed into `main`'s 960px. Widen the index page to about 1200px, so the columns get the mockup's 210 / 1fr / 230 proportions.
- V6. Make "Using it" the filled primary button, as on the mockup. Drop the plain "shipped" pill from board cards; keep the kind, run and held/sign-off pills. When a card has a simulated `back` reaction, add a lead pill like the mockup's "backed by CEO": "backed by League CEO · simulated".
- V7. Right column: an answered request lists every answer headline as a run-on paragraph of links. Show "answered by the follow-up run" and then the answer links as a short list, one per line.
- V8. Under 1050px, show the angles column first. Use CSS `order` so the left column follows it and the right column comes last. On a phone, the 12 feed items currently push the angles down by about two screens.
- V9. Dark mode: muted bars are barely visible against the card. Give muted bars a lighter fill in dark mode, and keep the highlight distinct.

**Email (`outbox/post-game-email.html`)**
- V10. "What happened" prints a bold "What happened." lead-in that repeats the heading. Remove it. The `<strong>What happened.</strong>` that `test_round4_polish.py` checks for comes from the Editor's notes markdown, so leave that path alone.
- V11. The 11 held rows are each a large amber block. Make each one a single compact line, as in the mockup's held card: headline link, badge, and a small "signed off for producers" note, with the two small buttons at the right. Use an amber left border, not a full amber fill.
- V12. The addendum prints whole claims, as walls of text. Show the headline link plus the claim's first sentence only.
- V13. The subject says "1 angles". Make it singular when there is one.

**Finding page (`findings/<id>.html`)**
- V14. The chart card's title is the entire claim in bold, five lines on finding 25. Put the claim as a normal lead paragraph under the header. Give the chart card a short title: the y label, or the headline.
- V15. The sidebar headings ("What people said", "Follow the lead", "Original sources") are full-size h2s, and the follow-up questions are large and bold. Use the board's small uppercase section-label style for the sidebar headings, and card-title size (about .95rem) for questions. Drop the redundant "Suggested follow-ups" sub-heading inside "Follow the lead".
- V16. The header's action buttons wrap onto three rows. Keep them on one row beside the title, and let them wrap under the title only when narrow.
