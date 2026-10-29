# Independent verification

The desk's numbers come from the NBL's own feed: the nblR box-score releases and the NBL match API, which serves Genius Sports / FIBA LiveStats data. Code rechecks every checked number against that feed, but a recheck can't catch an error in the feed itself. So the headline facts were also compared by hand with an independent publisher's box score.

**Source:** ESPN's box score for the game, [espn.com/nbl/boxscore/_/gameId/401875251](https://www.espn.com/nbl/boxscore/_/gameId/401875251), Adelaide 36ers at Melbourne United, 19 September 2026. Checked on 29 October 2026.

| Fact used by the desk | Desk (NBL feed) | ESPN | Match |
|---|---|---|---|
| Final score | Melbourne 95, Adelaide 97 | 95–97 | Yes |
| Quarter scores | MEL 23-25-22-25, ADL 25-24-26-22 | same | Yes |
| Cole Anthony | 30 pts in 21:50, 10/21 FG, 3/7 3P, 7/9 FT | 30 pts, 22 min, 10-21, 3-7, 7-9 | Yes (ESPN rounds minutes) |
| Bryce Cotton | 29 pts in 37:03, 9/19 FG, 4/9 3P, 7/7 FT | 29 pts, 37 min, 9-19, 4-9, 7-7 | Yes |
| Chris Goulding | 7 pts, 2/9 FG, 1/6 3P | 7 pts, 2-9, 1-6 | Yes |
| Team three-pointers | ADL 13/30, MEL 7/23 | 13-30, 7-23 | Yes |
| Two-pointers (derived) | ADL 19/36 (38 pts), MEL 29/48 (58 pts) | from FG 32-66 and 36-71, less threes | Yes |

**The record claim** (Cole Anthony's 30 in 21:50 being the fewest minutes for a 30-point game) is checked against the box-score data only. It covers box rows with minutes recorded, since 2015-16: 370 such games up to that night. The fewest minutes before it was 23:02, Jo Lual-Acuil Jr, January 2024. Three weeks later, David Johnson scored 32 in 17:39 (9 October 2026), which the run correctly couldn't see from its 19 September cutoff.

**Not yet done:**
- the human acceptance checks from the design: a blind fan rating of the new angles, and a backtest against coverage published after the game
- a read test of the README by someone who hires engineers
