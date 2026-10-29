Small fix in `src/storydesk/site.py` `headline_for`. On the live site, a judge-written headline reads "fewest minutes for 30 on record", but its claim says "since at least 2015-16". The demo promises that record claims state where the data starts, and headlines currently skip that rule.

Rule: when a stored headline uses a record word and the finding's claim carries the data boundary, but the headline doesn't, append the claim's boundary phrase in parentheses: `"<headline> (since at least 2015-16)"`. Reuse `_RECORD_WORD` and `_BOUNDARY` from `src/storydesk/gates.py`, and take the exact phrase from the claim's match rather than hard-coding it. Leave every other headline unchanged, along with the claim-based fallback path.

Done when this passes:

    .venv/bin/python -m pytest tests/test_final_review_fixes.py -q -p no:cacheprovider --basetemp "$PWD/.pytest_tmp" -k "headline and not committed"

Delete `.pytest_tmp` afterwards.

Constraints:
- Never edit any test.
- Touch only `src/storydesk/site.py`, plus `gates.py` if an import alias is needed.
- Don't commit.
- If a check looks wrong, reply `NEEDS_DECISION: <why>`.

Report the files changed and the test output tail.
