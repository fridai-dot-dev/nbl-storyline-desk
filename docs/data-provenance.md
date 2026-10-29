# Data provenance

Every finding in the demo traces back to one of the sources below. All of them are public. In production, LK would replace each one with its own feed (see the assumptions in the design, section 11).

The demo game is NBL27 Round 1: **Melbourne United 95–97 Adelaide 36ers**, Saturday 19 September 2026, John Cain Arena. Match UUID `36dbeb55-58ad-11f1-a69b-43a6b5595d3e`.

## Key times (UTC)

| Moment | UTC | Melbourne (AEST) | Source |
|---|---|---|---|
| Pre-game run cutoff | 06:30:00 | 4:30 pm | tip-off minus 3 hours |
| NBL YouTube live stream starts | 09:28:34 | 7:28 pm | stream metadata |
| Tip-off | 09:30:00 | 7:30 pm | match schedule |
| **Final whistle** (the post-game cutoff) | **11:26:37** | **9:26 pm** | play-by-play: the final period's `period / End` event |
| Official stats sign-off | 11:35:07 | 9:35 pm | play-by-play: `game_game_completed` |
| Briefing deadline (the 30-minute hard cap) | 11:56:37 | 9:56 pm | design |
| Adelaide press conference published | 12:23:56 | 10:23 pm | YouTube upload time |
| Melbourne press conference published | 12:44:33 | 10:44 pm | YouTube upload time |

## What each report could see

Each run is frozen at its cutoff, and every item is stamped with when it became available, not when it happened. This table shows what lands in time for each report on a real game night. The press-conference and article timings are estimates: on this game, Adelaide's press conference was published 57 minutes after the whistle and Melbourne's 78 minutes after.

| Source | Lands | Post-game (≤30 min) | Supplemental | Next pre-game |
|---|---|---|---|---|
| Live stats feed | live | ✓ | ✓ | ✓ |
| Broadcast commentary | live, *if LK transcribes it* | ✓ | ✓ | ✓ |
| YouTube live chat | live | ✓ | ✓ | ✓ |
| Press conferences | ~20–60 min after | ✗ | ✓ | ✓ |
| Post-game articles | 30 min to next morning | ✗ | some | ✓ |
| Highlights and press-conference video comments | hours after | ✗ | ✗ | ✓ |
| Comments on LK's own social posts | live, *production only* | ✓ | ✓ | ✓ |

### Social sources

- **Demo:** the only fan source is the YouTube live chat. It has 2,274 messages, many in Tagalog, with plenty of betting talk, so it isn't a clean read of fan opinion. Video comments on each team's recent games would feed the next pre-game brief, but this demo doesn't collect them yet.
- **Reddit:** self-serve API keys ended in November 2025, so apps now need Reddit's approval. Third-party reports say new requests close on 31 October 2026.
- **X:** reading posts is pay-per-use, at about US$0.005 per post. It isn't built.
- **Production:** fan signal would come from LK's own accounts through the platforms' APIs, plus a social listening tool.

## Sources

### Statistics: results, team and player box scores, play-by-play
- **Results and box scores:** the community `nblR` project's data releases (`github.com/JaseZiv/nblr_data`), refreshed daily in season.
  - Results go back to 1979.
  - Team and player box scores go back to 2015-16. That is the **data boundary**, which is why record claims say "since at least 2015-16".
- **Play-by-play for the demo game:** the NBL's own match API (`prod.rosetta.nbl.com.au/get/match/<uuid>/live/all`), which serves the league's Genius Sports / FIBA LiveStats feed. It's the same source the community scraper uses.
- **Checks:** the play-by-play quarter scores reconcile exactly with the box scores (MEL 23-25-22-25, ADL 25-24-26-22).
- **Clean-up:**
  - Match IDs mix numeric FIBA IDs (older seasons) with UUIDs, so they're read as text.
  - A handful of near-identical re-scraped team box rows in 2025-26 are deduplicated.
- **Never used:** the release's `pbp.rds`, which isn't readable in Python. Its `pbp.csv` is mislabelled and actually holds player box scores.

### Commentary
- **Source:** the NBL YouTube live stream of the game, "NBL27 Round 1 | Melbourne United vs Adelaide 36ers", `youtube.com/watch?v=jfZn7syBTUI`.
- **Text:** YouTube's automatic English captions, merged into chunks of about 30 seconds.
- **Timing:** stream start plus caption offset. This lines up with the play-by-play to within a second or two: commentary calling the finish lands at 11:26:39, against a whistle at 11:26:37.
- **Limits:** these are auto-captions, so names and numbers can be misheard. Any number taken from commentary is either quoted with its source (an *attributed* number) or rechecked against the stats.

### Press conferences
- **Adelaide:** Trevor Gleeson and Bryce Cotton (NBL YouTube, `1id823Gz8jg`).
- **Melbourne United:** the post-game press conference (Melbourne United YouTube, `v6dQVTM8zWs`).
- **Transcription:** done locally with Whisper (small model, CPU, memory-capped).
- **Timing:** time-stamped at **YouTube upload time**, when they became publicly available. That's why the supplemental run waits until 12:50 UTC. With the live access LK would have, it could run about 30 minutes after the whistle.

### Fans
- **Source:** the live-chat replay of the same NBL YouTube stream, 2,274 messages, each with its own UTC timestamp.
- **Privacy:** author names are dropped at collection and never stored. Quoting a fan outside LK is a sensitive category, held for sign-off.
- **Audience:** much of the chat is in Tagalog, which reflects the NBL's large international YouTube audience.
- **Not included:** Reddit's r/NBL threads. Reddit closed unauthenticated access in 2026, and the Apify route needs an account token.

### Media
- **Source:** 26 NBL.com articles published between 22 August and 18 September 2026 that mention either team. Candidates were found through the site's sitemap (robots.txt permits crawling), and each article's own `datePublished` was used.
- **Limits:** article dates are day-level only, so for a run on game day, same-day articles count as "after the cutoff".

## What the demo never uses

- Anything dated after a run's cutoff. Every tool enforces this, and the tests prove it.
- The live web during a run. It's off in the demo because web search can't be limited by date; in production it would be on.
- Synthetic data in the published site. The invented items under `tests/fixtures/corpus/` exist only for tests.
