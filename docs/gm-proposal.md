# Proposal: an NBL storyline desk

**For:** GM – AI, LK Group · **From:** Bart Lind · **Status:** a working demo on real NBL27 data. The pilot plan below is the proposal.

## The problem

Game nights move fast. Producers, social, broadcast and leadership each need different angles within minutes of the final whistle. The best angles cross sources: a stat, the commentators' call, the fan reaction and the history behind them. Today that work is done by hand, each team separately, and under time pressure. It's also hard to keep messaging aligned, or to see what leadership wants pushed.

## What I built

An agent desk on the Claude Agent SDK. Before and after each game, a lead agent sends four specialists across stats, commentary, media and fan chat. They branch when something looks interesting. Code then checks what they found before anyone sees it:
- every number is rechecked by its own query
- records state where the data starts
- injury, officiating and fan-quote items are held until a named person signs off

Leadership gets a short briefing email. Producers get the same findings, ranked for their show, and can ask follow-up questions in plain language.

On Round 1 (Melbourne United 95–97 Adelaide 36ers) it produced:
- **Cole Anthony's 30 in 21:50,** the fewest minutes for a 30-point game in the box-score data since 2015-16.
- **The bench paradox,** answering a producer's question: Melbourne's bench outscored Adelaide's by 30 and still lost. That outcome has happened 18 times in 74 such games since 2015-16.
- **A fan's referee complaint tested against the play-by-play,** and not amplified.

A post-game briefing took about 3 minutes and cost about US$2 at API prices. A full game, with pre-game, post-game, supplemental and two follow-ups, comes to about US$8.

## Why build rather than buy

Stats Perform's OptaAI Studio and Genius Sports' tools do stat storytelling well, and Genius already supplies the NBL's data. What I haven't seen offered is:
- a storyline tested across stats, broadcast, press conferences and fans together
- LK's own collaboration layer around it: directives, sign-off by audience, and measurable use

I'd build that layer on top of Genius data rather than compete with it. The details are in [build vs buy](build-vs-buy.md).

## A pilot

| Weeks | Work |
|---|---|
| 1–2 | Connect the Genius live feed and broadcast transcription. Run pre-game and post-game for one round, privately. |
| 3–4 | Put the email in front of two or three real users, for example the NBL Now producer, social and the media manager. Record what they use and what they already had. |
| 5–6 | Tune on that feedback, add the producer board and Slack, and report usage, novelty, time to briefing and cost per game. |

**What I'd need:**
- access to the Genius feed and broadcast audio
- a named approver for sign-off
- two or three users willing to try it after games

**Success** means producers use at least one angle per game that they didn't already have, the briefing lands within 30 minutes of the whistle, and cost stays under about US$10 per game.

## Why this matters for the AI team

The pattern is reusable across LK: code-checked agent research, plus a human sign-off and collaboration layer. The [Daniel's Donuts outline](daniels-donuts-outline.md) applies the same engine to customer reviews. The demo, its tests, the reviews and the build history are all in this repo.
