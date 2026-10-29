# Prior-finding context

# Shipped findings from the latest pre-game run

## Finding 5
- Claim: No pre-game commentary or transcript material exists before the 2026-09-19T06:30:00+00:00 cutoff for Melbourne United vs Adelaide 36ers. Searches for "Cotton", "Anthony Melbourne United Adelaide", and "Gleeson Chance Ingles" with until=2026-09-19T06:30:00+00:00 all returned zero results.
- Kind: nothing_found
- Status: shipped
- Evidence:
  - commentary · mcp__desk__search_transcripts · ref queries: Cotton; Anthony Melbourne United Adelaide; Gleeson Chance Ingles; window until 2026-09-19T06:30:00+00:00; 0 results each

## Finding 7
- Claim: No fan reaction exists before the 2026-09-19T06:30:00+00:00 cutoff for Melbourne United v Adelaide 36ers, so no pre-game fan theme can be reported.
- Kind: nothing_found
- Status: shipped
- Evidence:
  - fans · search_fans://until=2026-09-19T06:30:00+00:00 · ref Queries: Cotton; Cole Anthony; Ingles; United; Sixers; opener; Travers. Window: corpus start to 2026-09-19T06:30:00+00:00. All returned 0 results.

## Finding 9
- Claim: Melbourne have won 16 of 20 regular-season home games against Adelaide in the dataset since at least 2015-16, but lost the most recent one 76-87 on 2026-02-07, and Adelaide won 3 of the last 4 meetings overall. Small sample, and rosters have turned over, so the history is context rather than a prediction. CONFIRMS the storyline if Adelaide win or lead at the half again at John Cain Arena, since that extends the recent flip. CONTRADICTS it if Melbourne win, which would fit the 16-of-20 home pattern and suggest the 2025-26 run was the exception.
- Kind: checked
- Status: shipped
- Evidence:
  - stats · https://github.com/nblr-data/releases/results.csv · ref home_team_name=Melbourne United; away_team_name=Adelaide 36ers; match_time_utc 2015-10-16 to 2026-02-07 (20 regular-season rows, 16 home wins); latest row 2026-02-07 MEL 76 ADL 87

## Finding 10
- Claim: Bryce Cotton averages 21.21 points in 39 games against Melbourne United in the dataset since 2015-16 (high 36), below his 25.3 ppg across 42 games for Adelaide in 2025-26. In his three games against Melbourne as an Adelaide player he scored 33, 22 and 17. Small sample, and the 21.21 mostly reflects Perth years. CONFIRMS the benchmark if Cotton scores around 21 or fewer, which would point to Melbourne's defence holding him down. CONTRADICTS it if he reaches 25 or more, in line with his season form, which would suggest the Melbourne history matters little.
- Kind: checked
- Status: shipped
- Parent finding: 8
- Evidence:
  - stats · https://github.com/nblr-data/releases/box_player.csv · ref family_name=Cotton; first_name=Bryce; opp_name=Melbourne United (39 rows); 2025-26 rows match_id=b239f201-4bef-11f0-a45e-438852f8f17e, b1defcc2-4bef-11f0-ada5-6bbf481c9dbd, b26f08e5-4bef-11f0-9b72-2b5bbafc199b

## Finding 11
- Claim: In 2025-26 Chris Goulding made 2.3 threes per game, 69 from 225 attempts (7.5 per game, 30.7%) over 30 games. That is the baseline for the Anthony-creates-easier-looks storyline. It is one season, so a single game will be noisy. CONFIRMS the storyline if Goulding makes 4 or more threes, or shoots clearly above 30.7% on at least 7 attempts. CONTRADICTS it if he makes 2 or fewer or his volume falls well below 7.5 attempts, which would suggest no easier looks.
- Kind: checked
- Status: shipped
- Parent finding: 8
- Evidence:
  - stats · https://github.com/nblr-data/releases/box_player.csv · ref family_name=Goulding; first_name=Chris; season=2025-2026 (30 rows; 69 three_pointers_made, 225 three_pointers_attempted)

# Feedback

No relevant feedback.

# Active directives

No active directives.
