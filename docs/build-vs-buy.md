# Build vs buy

**Short answer:** buy the data and the graphics, and build the desk. Genius Sports already supplies the NBL's official data, and vendors such as Stats Perform sell stat storytelling and graphics tools. What LK would build is the layer on top: cross-source storylines, sign-off, and collaboration among LK's own people.

## What's on the market (public material, October 2026)

| Offering | What it does | Fit for the NBL |
|---|---|---|
| **Genius Sports** | The NBL's official data partner since 2015 (FIBA LiveStats). It also has an AI-technology partnership with FIBA running to 2035 | The data source we'd build on, not a competitor |
| **Stats Perform: OptaAI Studio** | Opta Search (trends and records across games and seasons), Opta Live, and Opta Graphics (branded, sponsorable graphics). Basketball-ready | Strong on stat search and graphics. Runs on Opta data, and whether Opta covers the NBL is unconfirmed |
| **Stats Perform: storylines service** | A data-insights team supplying facts and storylines for coverage | A service, not a tool LK controls |
| **Lega Basket Serie A: LUCA** | An AI agent that turns game statistics into stories | Close in spirit, built by a league for itself |

## Where the desk is different

1. **It tests storylines across sources.** For example: a commentator's call, checked in the play-by-play, set against history, then compared with fan reaction. On Round 1, a fan's "10-point referee gift" claim was tested against fourth-quarter free throws and not amplified. The public material for the tools above describes stat search and graphics, not this.
2. **It has a collaboration layer.** Leadership directives, sign-off by audience (internal, producers, partners), an email for leadership and a board for producers, and follow-up questions from any finding. This is LK's workflow, and no vendor ships it.
3. **It's owned and inspectable.** Every finding stores the query or source behind it, and the history of every change is in git. Prompts are plain files that a small team can change in a day.
4. **Cost is measured, not quoted.** A post-game run costs about US$2 at API prices, and a full game about US$8 (see [cost](cost.md)). Vendor pricing isn't public, so a fair comparison needs the questions below.

## Quality: what we can prove, and what's still to prove

- **Proven by checks:**
  - every shipped checked number re-runs and matches
  - record claims carry the data boundary
  - sensitive items are held
  - nothing after a run's cutoff is visible

  133 offline checks and 3 live checks pass.
- **Still to prove, with people:**
  - a blind rating of the new angles by basketball fans
  - a backtest against what media published after the game
  - real producers using it for a few rounds

  These are the first things a pilot would measure.

## Support and continuous improvement: the deciding factor

A vendor tool improves on the vendor's roadmap. This desk improves on LK's:
- prompts and agent definitions are files
- a scorecard re-runs a fixed game to compare changes
- each producer's "already had it" or "not for us" click feeds what counts as new or useful

The build history shows how quickly that loop works. Every defect the live runs exposed became a failing check and a fix within the same session ([build log](build-log.md)).

## When to buy instead

- **Live in-game graphics at broadcast scale:** a mature vendor product is the faster path.
- **Official data distribution to betting and media partners:** that already sits with Genius.

## Questions to ask a vendor before deciding

1. Does your storyline or search product cover the NBL, using Genius or FIBA LiveStats data?
2. Can it combine broadcast audio, press conferences and social reaction with the stats?
3. Can we add our own sign-off and directive workflow, and our own audiences?
4. What's the per-game or per-season price, and what's included?
5. Can we export the evidence behind each storyline?
