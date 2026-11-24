# Part 3 reconciliation: team-seasons still refused (2026-11-21)

Spec: `docs/claude-spec-warnings-model-v2.md` Part 3.  Measured with `tools/trial_collect.py` (every team-season
refused in the 2026-11-18 full run, re-collected with Parts 1 and 2 applied) and localized with
`tools/localize_refusal.py` (ESPN's per-game rows summed into cfbstats' split tables: home / road, wins / losses,
conference, FBS / FCS, month).

## Settled

| Team-season | Stat | ESPN | cfbstats | Finding | Outcome |
|---|---|---|---|---|---|
| Georgia Tech 2024 | pf | 376 | 370 | cfbstats' own schedule table sums to 376 (incl. W 30-29 vs NC State, 2024-11-21); its season line says 370 | `SOURCE_EXCEPTIONS` entry, ESPN stored |
| NC State 2024 | pa | 392 | 386 | cfbstats' own schedule table sums to 392 points allowed (incl. L 29-30 at Georgia Tech); season line 386: the same 6 missing points | `SOURCE_EXCEPTIONS` entry, ESPN stored |
| Army 2025, Navy 2025 | rushing, passing, total, turnovers | | | The whole difference sits in the Army-Navy game, 2025-12-13: ESPN's box score for it carries no team statistics (0 rushing, 0 passing, 0 total) | Stay refused: missing source data cannot be pinned away; the validator now names the empty box score |

The official stat-crew box score for the Georgia Tech game (gopack.com, boxscore 23347) renders client-side and
could not be read from the build environment; the final score 30-29 is not in dispute anywhere (AP, both schools).

## Still refused: one official box score each would settle them

Every case below is a rushing-yards difference.  Open the official stat-crew box score (the school's athletics site,
SIDEARM / PrestoSports "Box Score", team statistics "Rushing" line) for each candidate game, compare it with ESPN's
team rushing yards for that game (printed by `python3 tools/localize_refusal.py "<team>" <season>`), and:

- if the official box matches ESPN and the season gap is cfbstats', add a `SOURCE_EXCEPTIONS` entry pinned to the
  exact pair, citing the box score (the Notre Dame entry's format);
- if the official box matches cfbstats, ESPN's row is wrong: the season stays refused (named), since data is never
  hand-edited;
- anything else: stays refused.

| Team-season | ESPN − cfbstats (rushing) | Candidate game(s), from the splits |
|---|---|---|
| Old Dominion 2024 | +116 (also total +116) | 2024-11-16 James Madison, 2024-11-23 Marshall (home, losses, November) |
| Central Michigan 2024 | +34 (also total +34) | spread: +26 in home November losses, +8 in a road October loss |
| UL Monroe 2025 | −28 (also total −28) | 2025-11-01 Old Dominion, 2025-11-15 South Alabama |
| Toledo 2024 | +20 | 2024-11-20 Ohio |
| Middle Tennessee 2024 | +18 | 2024-11-09 Liberty, 2024-11-23 New Mexico State |
| West Virginia 2024 | +18 | 2024-11-30 Texas Tech |
| UTSA 2024 | +17 | 2024-09-07 Texas State, 2024-09-14 Texas |
| NC State 2025 | +14 | 2025-12-19 Memphis |
| East Carolina 2025 | −12 | 2025-11-01 Temple, 2025-11-29 Florida Atlantic |
| Louisiana Tech 2024 | +10 | 2024-09-14 NC State |
| Arizona 2024 | −9 | 2024-11-15 Houston |
| Northwestern 2024 | +8 | spread over several games |
| San José State 2024 | −7 | 2024-11-29 Stanford |

NCAA statistics (stats.ncaa.org) and CollegeFootballData.com were not used: the first is spot-use HTML and the
second needs an API key (a secret Jeff would set up separately); neither was needed to settle the cases above, and
CFBD's ESPN-adjacent lineage would not arbitrate ESPN anyway.
