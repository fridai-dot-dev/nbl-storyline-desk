# Fix-round report: mockup layout (Sol)

Done. No commit; tests were untouched; `.pytest_tmp` was deleted.

Done command tail:

```text
................................... [100%]
184 passed, 7 deselected in 653.07s (0:10:53)
```

Files changed:

- [site.py](../../../src/storydesk/site.py) — completed V1–V16, escaped run metadata, and tightened board/email/finding layouts.
- [charts.py](../../../src/storydesk/charts.py) — added configurable dimensions, bounded margins, ellipsized labels, and dark-mode styling.
- [cli.py](../../../src/storydesk/cli.py) — validates simulated rounds and finding IDs read-only before initialization or transactional replacement.
- [store.py](../../../src/storydesk/store.py) — added the simulated-directive migration and API field.

Calls beyond the design:

- Axis display labels truncate after seven characters plus `…` to preserve the 100px plot area.
- Card SVG titles use the concise finding headline; full finding-page charts retain the claim.
- “Suggested follow-ups” remains as an accessibility label, not a redundant visible heading.

Left alone:

- `site/` and `published/` remain untouched for Claude’s integration step.
- The pytest-asyncio loop-scope deprecation warning remains; configuration is outside scope.
