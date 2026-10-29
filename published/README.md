# Published snapshot

`store.db` is a copy of the completed demo store used to publish the static site. It includes the published runs and the retained failed runs that are intentionally excluded from the site.

`digests/` contains the cutoff-safe starting digest regenerated from the project code for each published run. These files show the material made available to the agents at the beginning of each run.

- `digests/pre_game/` uses the pre-game cutoff, 2026-09-19T06:30:00+00:00.
- `digests/post_game/` uses the final-whistle cutoff, 2026-09-19T11:26:37+00:00.
- `digests/supplemental/` uses the post-interview cutoff, 2026-09-19T12:50:00+00:00.
- `digests/follow_up/` uses the final-whistle cutoff and anchor finding 34.

## Simulated feedback round

`simulated-round.json` holds 11 reactions and team-usage marks and 2 directives from generic personas such as League CEO, Head of marketing and NBL Now producer. The design planned this round to show the collaboration loop on the board. It was added to `store.db` after the runs, with `python -m storydesk simulate --store published/store.db --file published/simulated-round.json`, so it didn't steer any run. Every row has `simulated = 1`, and the site labels each item "simulated".

## Known defects in this snapshot

- **The score line in `game.md`** reads "Melbourne United 95 – 97 97": the formatter printed the away score where the away team's name belonged. The agents saw that line. The quarter scores beside it were right. The formatter is fixed for future runs, and these files are kept as the runs saw them.
- **The stats evidence URLs** in `store.db` are the agents' guesses and don't resolve. The site links stats evidence to the real nblR release instead, from the table named in each item.
