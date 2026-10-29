# Sol's final pre-publication review (2026-10-29)

**Scope:** everything since round 1 (`a58d645..HEAD`). The review covered site rendering and escaping, the runner's deadline and finalisation paths, public claims checked against `published/store.db` and the code, and leaks of private material.

**Verdict:** needs attention, with 1 high, 3 medium and 1 low finding. All five were fixed. Claude wrote the failing checks in `tests/test_final_review_fixes.py`, Sol made them pass in one fix round ([prompt](codex-prompts/final-fix.md), [report](codex-reports/final-fix.md)), and Claude re-ran the full suite: 155 offline and 3 live checks pass (160 offline after the headline fix below).

| Severity | Finding | Outcome |
|---|---|---|
| High | A failed follow-up was still marked answered, because `answer_request` ran in `finally` on timeout, error and incomplete runs. A retry added a duplicate request. | Only a complete run answers a request. A retry reuses the pending request. |
| Medium | Evidence URLs weren't checked for scheme, so a `javascript:` URL would run when clicked. Two published links were tool names. | Only `http`/`https` URLs become links, checked the way a browser parses them. Anything else renders as inert text. |
| Medium | At the deadline, the runner awaited `client.interrupt()` without a bound. The SDK can wait 60 s, then raise, which would turn a timeout into an error. | The interrupt has a 2 s grace, and its failures are suppressed, so the run stays a timeout and still finalises. |
| Medium | The starting digest's score line printed the away score twice: "Melbourne United 95 – 97 97". | Fixed in the formatter. The published digests are kept as the runs saw them, with a note in [published/README.md](../../published/README.md). |
| Low | The docs gave stale check counts. The README said the judge scored novelty, when code does. | Counts updated and no longer repeated across docs. The README now says code scores novelty and the judge scores audience fit and direction. |

## Found while fixing

A link check of the rebuilt site found something the review hadn't. Every stats source link was a URL the agents had guessed, such as `github.com/nblr/nblr_data/...` and `api.nbl.com.au/...`, and none of them resolved. The contract had asked for "the actual data source" without giving the URL.

The site now links stats evidence to the real nblR release, chosen by the table named in the evidence. Play-by-play links to [data provenance](../data-provenance.md), because the NBL match API refuses browser requests. The contract now asks agents for the table name, not a URL. A check fails if any committed page carries a guessed URL.

Checking the live site after the first publish found one more. A judge-written headline said "fewest minutes for 30 on record", while its claim said "since at least 2015-16". The boundary rule checked claims but not headlines. A headline with record words now carries its claim's boundary, so it reads "...on record (since at least 2015-16)".

## Parked

- The judge prompt still asks for a novelty score, and code discards it. That's harmless, but it's wasted tokens.
- Stats evidence URLs are fixed at render time, not at ingestion, so `store.db` still holds the guesses. A follow-up's starting digest can still carry an anchor's guessed URL.
