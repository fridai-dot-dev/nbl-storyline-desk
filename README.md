# NBL Storyline Desk

An NBL media research layer built around a frozen `as_of` data boundary: specialists explore stats, commentary, media and fan material, while code rechecks numbers, holds sensitive findings and records the run ledger.

For a 60-second tour, build the static packet with `python -m storydesk site` and open `site/index.html`. The leadership route is email-first at `site/outbox/post-game-email.html`; individual findings expose their evidence and recheck query.

Model runs are deliberately opt-in: `python -m storydesk run post_game --game <uuid> --live`. The SDK route uses the local Claude login, not an API-key spend; it records API-price cost reported by the SDK. Published run results and the fuller README follow the deliberate live-run phase.
