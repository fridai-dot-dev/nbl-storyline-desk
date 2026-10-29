Fix round for your final pre-publication review of this repo (branch `finish`). Claude has written the failing checks in `tests/test_final_review_fixes.py` and already fixed the score line in `src/storydesk/prepare.py`. Make the remaining checks pass. Never edit any test file; if you disagree with a check, stop and reply `NEEDS_DECISION: <why>`.

## What to fix

1. **Follow-up requests (your high finding), `src/storydesk/runner.py` `run_live`.** Mark a request answered only when the run's final status is `complete`. A timeout, `incomplete` or error leaves it pending. When a follow-up starts, reuse an existing unanswered request with the same anchor finding and the same stripped question, so a retry answers the original rather than adding a duplicate. A store helper in `src/storydesk/store.py` is fine.

2. **Interrupt at the deadline (your medium finding), `runner.py`.** Add a module constant `INTERRUPT_GRACE_S` (2.0 seconds is fine; tests monkeypatch it). In both `_query_with_deadline` and `enforce_deadline`, bound the interrupt with `asyncio.wait_for(..., INTERRUPT_GRACE_S)` and suppress its timeout or any `Exception` it raises, so the status stays `timeout` and finalisation still happens. Don't swallow `CancelledError` of the outer task. Keep the existing bounded drain after it.

3. **Evidence links, `src/storydesk/site.py` (the `evidence_html` in `_finding_page`, the only external evidence link).** Put the logic in one small helper:
   - **Stats evidence (`source_type == "stats"`):** ignore the agent's URL. The agents guessed these URLs, and every one in the published store is a 404, e.g. `github.com/nblr/...`, `github.com/nblr-data/...` and `api.nbl.com.au/...`. Link instead to the real source for the relation named anywhere in the item's `url` or `ref`, checking in this order:
     - `box_player` → `https://github.com/JaseZiv/nblr_data/releases/tag/pbp` (the nblR release named "pbp" holds the player box scores)
     - `box_team` → `.../releases/tag/box_team`
     - `results` → `.../releases/tag/match_results`
     - Anything else, including play-by-play (`pbp`, `playbyplay`, `action_id`) → `{_REPO_URL}/blob/main/docs/data-provenance.md`. The NBL match API returns 401 to a browser, so it can't be linked.
   - **Any other evidence:** render an `<a href>` only when the URL is `http:` or `https:` after removing ASCII control characters and whitespace and lower-casing (the way browsers parse it). Otherwise show the URL as inert, escaped text with no anchor, e.g. `mcp__desk__search_transcripts`.
   - **Always:** keep showing `source_type`, the `ref` and the quote as now.

4. **`prompts/contract.md`.** The stats sentence currently asks for "the nblr_data release CSV URL … and the NBL match API URL for `pbp`" without giving them, which is why agents guessed. Reword it: for statistics, put the relation (`results`, `box_team`, `box_player` or `pbp`) in `url` and the exact rows in `ref`; code links the evidence to the real data source. Change nothing else in the prompts.

## Out of scope

Don't touch:
- `site/`, `published/`, `docs/`, `README.md` or `.github/`. Claude rebuilds the site and edits the docs afterwards.
- any test file

Don't commit.

## Done when

This passes (use a basetemp inside the repo because the sandbox may block /tmp, and delete `.pytest_tmp` afterwards):

```
.venv/bin/python -m pytest -m "not live" -q -p no:cacheprovider --basetemp "$PWD/.pytest_tmp" \
  --deselect tests/test_final_review_fixes.py::test_committed_site_has_no_unsafe_or_broken_links \
  --deselect tests/test_final_review_fixes.py::test_committed_site_links_stats_evidence_to_real_sources
```

The two deselected checks run against the committed `site/` and pass only after Claude rebuilds it.

## Report

- Files changed, with one line each on what and why.
- The tail of the done command's output.
- Anything you noticed but left alone.
