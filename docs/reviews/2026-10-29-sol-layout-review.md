# The site rebuilt to match the mockups (2026-10-29)

**Why:** Bart compared the live site with the dashboard from the design session and found it "pretty distant". All three pages had drifted into single-column lists:
- the producer board
- the leadership email
- the finding page

The round-1 brief pointed at `docs/design/mockups/`, but no check enforced the layout. The simulated feedback round the design planned (section 5.7, "labelled as simulated") was never run. As a result, the board had no reactions, directives or team usage to show.

**Decisions Bart made:**
- Rebuild all three pages.
- Fill the board's collaboration panels with a small simulated round. Each item is labelled "simulated" and was added after the runs.
- After Sol's fix round, have Claude fix the remaining defects directly rather than run a second Codex round.

**How it went:**
1. **Checks first.** Claude wrote 22 failing structural checks in `tests/test_mockup_layout.py`, along with a [build brief](../handoffs/2026-10-29-mockup-layout.md).
2. **Build.** Terra built against them ([readiness](codex-prompts/layout-readiness.md) → [report](codex-reports/layout-readiness.md); [build](codex-prompts/layout-build.md) → [report](codex-reports/layout-build.md)).
3. **Review.** Claude compared screenshots with the mockups at 1400px and 390px, in light and dark. Sol reviewed the diff.
4. **Fix round.** Sol fixed its own findings and Claude's 16 visual findings ([prompt](codex-prompts/layout-fix.md), [visual findings](codex-prompts/layout-visual-findings.md), [report](codex-reports/layout-fix.md)).
5. **Remaining defects.** Claude fixed what the fix round left, against new failing checks.

## Sol's review

**Verdict:** needs attention, with 1 high and 2 medium findings. All three were fixed in the fix round.

| Severity | Finding | Outcome |
|---|---|---|
| High | The email interpolated the run's `num_agents` without escaping, so a malformed store could inject markup. | Coerced to an integer and escaped. A check plants markup in the field and scans every page. |
| Medium | `simulate` initialised the store before validating its file, so bad input could still create or migrate a database. | The whole file is validated first, with finding IDs checked through a read-only connection. Then the round is replaced in one transaction. A missing store is an error and is never created. |
| Medium | Very long chart labels grew the margins without bound and could invert the plot. | Margins are capped so the plot keeps its minimum height. |

## Left after the fix round, fixed by Claude

Each fix below has a failing check in the last section of `tests/test_mockup_layout.py`:
- **Chart labels:** the fix round shortened every axis label to seven characters on every chart, so finding 25 read "Anthony…". Labels are now shortened only when the canvas can't hold them, with the room worked out from each chart's size. Full-size charts keep labels like "Anthony 30 pts (21:50)". The first rotated label also touched the bottom edge; label room now uses a wider glyph estimate and padding.
- **Values on board charts:** they overlapped on the small charts. These charts now label only the highlighted value, as the mockup does.
- **Email held rows:** they squeezed the headline, badge, sign-off note and buttons into one row, which overflowed the email. The headline now sits on its own line, with the rest on a line under it.
- **Board card descriptions:** these could open with "User follow-up to finding 34." Meta lead-ins are skipped, and the same rule applies to headline fallbacks.
- **Sideways scrolling on phones:** a probe of all 32 pages at 390px found the board's runs table and the email's longest held badge wider than the screen. The table now scrolls in its own box, and held badges wrap. The probe now finds no overflow.

## Parked

- `directives.simulated` defaults to 1, so on a legacy store any existing directives would be marked simulated when the column is added. No published or real store has directives from any other source.
- `check_chart` now accepts a label shortened with "…" when the label starts with the shortened text. Only the tests call it; no gate does, so agent charts aren't checked by the looser rule.
