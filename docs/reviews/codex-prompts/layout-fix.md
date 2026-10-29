Fix round for the mockup-layout build (brief: `docs/handoffs/2026-10-29-mockup-layout.md`). You're taking over the builder's thread. Claude has added failing checks at the end of `tests/test_mockup_layout.py` (section "fix round"). Make them pass and fix everything below. Never edit anything under `tests/`; if you disagree with a check, stop and reply `NEEDS_DECISION: <why>`. Scope stays the brief's four files: `site.py`, `charts.py`, `store.py`, `cli.py`. Don't commit.

## Sol's review findings (all three)

1. **High: `src/storydesk/site.py` ~804.** `post["num_agents"]` is interpolated unescaped. Coerce to int where possible and escape whatever is rendered, on every page that shows run metadata (`test_run_metadata_is_escaped_on_every_page`).
2. **Medium: `cli.py` `simulate`.** Validate the whole file before touching any store: JSON shape and allowed actions first, then finding ids through a read-only connection (a store path that doesn't exist is an error, and must not be created). Only then init/migrate and replace in one transaction (`test_invalid_simulated_round_creates_and_changes_nothing`). Keep `directives.simulated DEFAULT 1` as is.
3. **Medium: `charts.py`.** Margins grow without bound and can invert the plot. Truncate long display labels with "…" inside `_display_label` (so `check_chart` still finds each label) and cap the reserved margins so the plot keeps at least 100px of height (`test_extreme_labels_never_invert_the_plot`).

## Claude's visual check against the mockups

Read [`layout-visual-findings.md`](layout-visual-findings.md) and fix V1–V16. `test_board_cards_stay_short_like_the_mockup` and `test_email_has_no_repeated_lead_in_and_counts_angles_in_words` cover V1–V4, V6, V10 and V13; the rest are checked by Claude's screenshots, so follow the mockups. For V2, add optional `width`/`height` keyword arguments to the chart renderers (the defaults stay 680×340) and draw card charts at about 320×190.

## Done when

The brief's done command exits 0 (whole offline suite, the same four deselects; delete `.pytest_tmp` afterwards).

## Report

Files changed with one line each, the done command's tail, and anything you noticed but left alone.
