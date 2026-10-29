# Assumptions register

The approved [design](superpowers/specs/2026-10-28-nbl-storyline-desk-design.md) is the source for A1–A9. The demo evidence is described in [data provenance](data-provenance.md).

1. **A1.** LK has statistics at least as detailed as nblR. The demo has results from 1979 and team/player box scores from 2015-16.
2. **A2.** LK can access broadcast audio, shows and press conferences, and can obtain transcripts during games.
3. **A3.** LK owns or has permission to use its social engagement data.
4. **A4.** Email is the first channel. Slack or voice notes may replace it after user testing.
5. **A5.** LK has a mainstream cloud, email provider and operating stack that can host the service.
6. **A6.** Genius Sports output is available as a live input. The demo uses nblR releases and the NBL match API as stand-ins.
7. **A7.** Users include the CEO, NBL GM, LK directors, marketing lead, producers, head of social, live social and stats team, and ESPN broadcast team.
8. **A8.** The demo’s persona feedback is simulated. It is not user research.
9. **A9.** Bart’s Claude subscription was for the demo only. A production service uses LK-owned API credentials, Bedrock or Vertex.
10. **Data boundary.** Team and player comparisons start at 2015-16. A record claim must say “since at least 2015-16”. Results history reaches 1979, but that does not make box-score claims historical to 1979.
11. **Data timing.** A run only sees material at or before its `as_of` cutoff. Media dates are day-level, so same-day articles are treated as after the cutoff. This is conservative.
12. **Data quality.** The demo removes near-duplicate 2025-26 team rows and reads mixed numeric/UUID match IDs as text. Auto-captions can mishear names or numbers. `pbp.rds` is not used.
13. **Social coverage.** The demo has 2,274 anonymised YouTube live-chat messages. It has no Reddit data because unauthenticated access was closed and the Apify route needs a token. A chat sample is not a population survey.
14. **Privacy.** Fan handles are removed. A fan quote, injury, conflict, officiating or legal finding remains held until the relevant audience signs off.

## What LK needs to provide

- A licensed Genius live feed and historical data access.
- Broadcast audio, show recordings, press conferences, or live transcription with timestamps.
- Owned social data and approved retention and privacy rules.
- An email channel now, and Slack access if LK chooses that channel later.
- Named sign-off roles for internal, producer and partner audiences.

## What a pilot validates

One club’s games or one round should test data latency and completeness, the whistle-to-briefing workflow, what each audience actually uses, sensitive-content approval speed, and whether findings are new and useful. It should also compare cost, quality and support against existing tools. The pilot must produce real user feedback, not simulated feedback.
