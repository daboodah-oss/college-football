# Claude spec — College Football: warning cleanup, source reconciliation, Playoff model v2

Repo: daboodah-oss/college-football (live page https://cf.daboodah.com/)
Author: Budzilla, 2026-11-11, at Jeff's direction ("Do them all", 2026-11-11).
Read the repo's AGENTS.md and docs/cfp-model.md first; the standards in
daboodah-oss/ai-build-standards apply as usual. Build on your own branch, do not
merge without Jeff's approval, and include before/after counts in your summary.

## Why

The page's Data Notes carry two permanent warnings:

1. "The latest automatic update could not refresh: team_2026, team_2025,
   team_2024" — fires when ANY team-season in a season is refused, even though
   on the 2026-11-08 run 2026 updated 114 of 138 teams fine.
2. "48 registry team seasons are not on the page" — 32 from 2024 + 12 from 2025
   (sealed seasons that can never self-heal) + 4 from 2026.

Root-cause analysis is done (logs/collect.txt of the 2026-11-08 run, 68 refusals
total). Do not redo it; the numbers below are from that log.

## Part 1 — Validator tolerances (update.py `compare`)

Most refusals are hairline disagreements between ESPN's summed box scores and
cfbstats' season totals. Widen three tolerances; every difference that passes
under a widened tolerance must STILL be printed in the stored `check` string
("except …") exactly as differences inside today's tolerances are — nothing is
hidden from the page.

- Yardage keys (rush_yds, pass_yds, total_yds): tolerance from
  max(5, 0.2% of cfbstats) to **max(5, 0.5% of cfbstats)** — the same 0.5%
  family the player `yds` check already uses.
- Third-down keys (third_att, third_conv): tolerance from 2 to **5**
  (extends Jeff's 2026-10-19 ruling, same reasoning: summed box-score
  third-down lines routinely drift a few attempts from season totals).
- Turnover keys (to_lost, to_gained): from exact to **±1**.
- Unchanged: games count exact, pf/pa exact, everything else exact.
- Negative test required: a synthetic case beyond each new tolerance must
  still be refused, and a pf mismatch must still be refused.

Expected effect, simulated against the 68 logged refusals: 38 clear. Missing
team-seasons drop from 48 to about 24. Report the actual after-counts.

## Part 2 — Per-game "total yards != rushing + passing" games: ROOT CAUSE PROVEN

Four 2026 teams have nothing stored because one game each fails
`check_team_game`'s total == rush + pass rule (Air Force 2026-10-10,
Hawai'i 2026-08-29, Sacramento State 2026-08-29, Stanford 2026-08-29), and
four more such games sit inside refused 2024 seasons (Arkansas, Coastal
Carolina, LSU, Toledo).

Proven for Hawai'i at Stanford, 2026-08-29 (ESPN event 401858201):

- ESPN's team fields: Hawai'i total 322, rush 46, pass 279; Stanford total 483,
  rush 158, pass 310. Neither total equals rush + pass.
- ESPN's own player lines sum exactly to the rush/pass fields
  (Hawai'i rushing 46, passing 279; Stanford rushing 158, passing 310).
- The official stat-crew box score (Hawai'i athletics, SIDEARM) gives Total
  Offense Yards **325 Hawai'i / 468 Stanford** — i.e. exactly rush + pass.
  Sportradar's independent feed also shows 468 / 325.
- Air Force at Northern Illinois, 2026-10-10 shows the same shape: player
  sums and team rush/pass fields agree (439 + 0); only `totalYards` (433) is off.

Conclusion: ESPN's `totalYards` summary field is intermittently wrong;
rushing/passing are right, and total offense under NCAA rules IS rush + pass.

Fix: in collect_tabs.py `box_row`, store `total_yds = rush_yds + pass_yds`
instead of trusting ESPN's `totalYards` field, and log a line naming the game
whenever ESPN's field disagreed with the computed total (keep the raw ESPN
value in the log line). Keep the validator's per-game equality rule — it
becomes true by construction and still guards the components. BEFORE applying
this to the four 2024 games, verify each shows the same shape (ESPN player
sums == team rush/pass fields); any game that does not, stays refused and is
named in your summary.

## Part 3 — Reconcile what's left against alternative sources

After Parts 1–2, roughly 18 refusals remain. These are large or score-level
disagreements (from the log: Army 2025 and Navy 2025 yardage off by 80–270;
Old Dominion 2024 rushing off by 116; Texas 2026 and Navy 2026 yardage ~2%;
Georgia Tech 2024 pf 376 vs 370; NC State 2024 pa 392 vs 386; UL Monroe 2025,
Central Michigan 2024, Middle Tennessee 2024 yardage 18–34). Do NOT widen
tolerances further to absorb them. Reconcile them, in this order of authority:

1. **Official school box scores** (SIDEARM / PrestoSports PDFs on school
   athletics sites) — the stat-crew document both aggregators derive from;
   gold standard per game. This is how the ND 2024 third-down exception and
   the Part 2 case were both settled. Use it to localize a season disagreement
   to its game(s): compare ESPN per-game rows against cfbstats' per-game
   splits where available, check the divergent game(s) against the official
   box score.
2. **NCAA official statistics** (stats.ncaa.org / ncaa.com stats pages) —
   season totals compiled from host stat crews; the right arbiter for
   "whose season total is right" when a box score can't be found. HTML, not
   an API — spot use only.
3. **CollegeFootballData.com API** (/games/teams per-game team stats,
   /stats/season aggregates; free key, 1,000 calls/month) — automatable and
   useful for LOCALIZING divergent games league-wide, but its box-score
   lineage is ESPN-adjacent, so it is a second opinion, not an independent
   arbiter against ESPN. Only if you judge it necessary: say so in your
   summary and stop — the API key is a secret and Jeff will set it up
   separately; do not block Parts 1, 2, 4, 5 on it.
4. Sportradar public pages — independent feed, spot corroboration only
   (it corroborated Part 2). Sports-Reference — manual spot check only;
   it blocks scrapers and offers no API; never automate against it.

Outcome per reconciled case: either a pinned SOURCE_EXCEPTIONS entry in
update.py citing the official document (team, season, stat, exact pair, why —
follow the existing Notre Dame entry's format), or the team-season stays
refused and named. No silent storing, no tolerance creep. Cases you cannot
resolve with the sources above: leave refused, list them in your summary
with what you checked.

## Part 4 — Banner wording (build_report.py notices)

Replace the all-or-nothing failure notice with counts, e.g.:
"3 of 408 team seasons could not be re-verified in the latest update and show
their last verified data." A season in which every stored team re-verified
produces no notice. Keep the missing-team-seasons notice and the Method-tab
list as they are (with the new, smaller count).

## Part 5 — "Report problems" workflow step

Known defect (reported to Jeff 2026-11-09): the Update workflow's
"Report problems" step has failed on every run since 2026-11-07 while
collect/build/push succeed — the step meant to report data problems is itself
broken, and the "Run failed" emails are currently meaningless. Diagnose from
the workflow run logs, fix it, and verify with a run whose report step
succeeds (or correctly reports a real refusal while Parts 1–3 are mid-flight).

## Part 6 — Playoff model: injury/context notes + as-of-date opponent strength (v2)

Two additions, both Jeff-approved 2026-11-11. Full numeric injury adjustments
are explicitly OUT (no reliable data source in the pipeline; breaks the
model's no-hand-tuning constraint in docs/cfp-model.md).

A. **Context notes.** Each weekly snapshot gains an optional `context` list:
short, sourced notes about major availability/context bearing on Top 25
teams that week — e.g. "Ohio State QB Julian Sayin has been out since the
Indiana game (Oct 17); Ohio State lost to USC and Oregon without him."
Rules: each note names team, fact, source, and date; notes are curated at
snapshot time from a cited public report (coach statement / credible beat
report), never rumor; they display in the Playoff tab's critique area
clearly labeled as context. Seed the Week 11 snapshot's context with the
Sayin note (source: Ryan Day's Oct 22 statement that Sayin is out
indefinitely) WITHOUT changing Week 11's frozen rankings or metrics — a
context append to a frozen snapshot is metadata, not a re-rank; note in
your summary that you did this and how update.py's cfp duplicate-guard
treated it (if the guard blocks it, add the narrowest metadata-only path
and negative-test that rankings still cannot be rewritten).

B. **As-of-date opponent strength.** The v1 model values every opponent at
its season-long average rating, so a team that collapses after a key injury
retroactively cheapens earlier results against it (the Sayin case: Indiana's
Oct 17 loss to a full-strength Ohio State is scored against Ohio State's
post-injury season average). Add a component that values each game against
the opponent's rating computed from games played **up to that game's date**
(expanding-window SRS, computed from the same stored rows; deterministic;
no new data sources). Precise integration is yours to propose in the build
summary — constraints: weights of the existing three components may be
rebalanced to make room, but the blend must stay documented in
docs/cfp-model.md and on the page's Method note; frozen snapshots are never
rewritten (Week 11 stays v1 and is labeled v1); v2 takes effect from the
next new snapshot (Week 12). For Jeff's review, include in your summary a
clearly-labeled "what v2 would have said about Week 11" comparison
(top 12 side by side, v1 vs v2) WITHOUT storing it as a snapshot.

## Acceptance

- tools/render_check.js passes completely against the built page (all
  sections, 0 script errors), and you state the live-vs-local result.
- Summary reports: refusals before/after by season, missing count before
  (48) and after, every SOURCE_EXCEPTION added with its citation, every
  team-season still refused with what was checked, the Part 5 diagnosis,
  and the Week 11 v1-vs-v2 comparison.
- Nothing in Parts 1–3 stores data whose disagreement is not either inside
  the stated tolerances (and printed on the page) or pinned to a cited
  official document.
