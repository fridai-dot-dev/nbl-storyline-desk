# Codex report: final-fix

Codex thread: `01a18588-ee21-7c22-98cc-dd6bcc71fbbe`

Implementation is blocked by a contradictory existing check.

Changed:

- [runner.py](../../../src/storydesk/runner.py): bounded interrupts, pending-request reuse, and complete-only answering.
- [store.py](../../../src/storydesk/store.py): added pending-request lookup/reuse.
- [site.py](../../../src/storydesk/site.py): canonical stats links and safe external-link rendering.
- [contract.md](../../../prompts/contract.md): corrected statistical evidence instructions.
- `prepare.py`: Claude’s existing score-line fix remains untouched.

Test tail:

```text
FAILED tests/test_round2_site.py::test_follow_up_run_records_and_answers_its_request
1 failed, 152 passed, 5 deselected in 490.27s (0:08:10)
```

That older test expects an incomplete follow-up with no required-source coverage to answer its request. The new regression checks and explicit requirement say incomplete runs must leave it pending. Both cannot pass without changing a test or adding a test-specific workaround.

`.pytest_tmp` was removed. Concurrent changes to `README.md`, `docs/`, `published/`, the database sidecars, and tests were left untouched.

NEEDS_DECISION: The obsolete `test_follow_up_run_records_and_answers_its_request` must be updated or excluded because it contradicts the newly required complete-only request-answering behavior.
