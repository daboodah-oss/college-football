# Handoff: Wins Above Bubble (WAB) column, for Budzilla

Repo: daboodah-oss/college-football
Branch: `claude/awesome-noether-3njhfl` (commit `6471ac9` holds the code; not merged)
Spec: `docs/claude-spec-wab-column.md` (Jeff approved 2026-11-19)

## Summary

- WAB is built exactly as the spec says.  It is a third, comparison-only ranking on the Playoff tab.  It is not part of the blend and does not change our Top 25.
- Method, unchanged from the spec: SRS from `cfp_model.srs_ratings`; bubble = mean SRS of the 12th and 13th FBS teams; win chance = normal CDF of (bubble minus opponent SRS plus site adjustment) / 13.5; site adjustment is minus 2.5 if the ranked team was home, plus 2.5 if it was away, 0 if neutral; a win is worth 1 minus p, a loss minus p; ties skipped.
- Each new snapshot in `data/cfp.json` stores: `wab` (Top 25 ids), `wab` and `wab_rank` on every stored line, `wab_bubble` {rating, team12, team13, sigma}, and `wab_metrics`.  `wab_metrics` comes from the same `agreement_metrics` code as the model's metrics, so it also carries an agreement %.
- `update.py` validates the WAB fields.  The duplicate-week refusal still applies (tested).
- `build_cfp.py` re-checks the WAB fields at build time.
- Page: two WAB columns in the side-by-side table (rank and value), a WAB agreement line under the scorecard, and a Method note in plain words.  Weeks 11 and 12 show "WAB tracking began Week 13" with no empty columns.
- No backfill.  Weeks 11 and 12 in `data/cfp.json` are byte-untouched (checksum verified, `data/` identical to main).
- Blend unchanged: old and new `cfp_model.compute()` give identical output on the same data.
- Build prints OK.  `tools/render_check.js`: 0 script errors, 0 failed checks in light and dark, on real data and on a simulated Week 13 snapshot.

## One judgment call

The "fewer than 5 stored games" rule counts each team's OWN stored game rows.  Counting deduped games from opponents' rows gives Air Force, Stanford and Hawai'i 8 or 9 games each, so they would be ranked.  Counting their own rows leaves exactly the three teams the spec names unranked.

## Validation against your exploratory run (games through 2026-11-17)

| | Budzilla | Pipeline |
|---|---|---|
| Bubble | 15.98 (Ole Miss #12 / Utah #13) | 15.40 (Utah #12 / Indiana #13) |
| Top 5 | Georgia 2.12, Texas 1.92, UCLA 1.78, Miami 1.65, Alabama 1.51 | Georgia 2.25, Texas 2.10, UCLA 1.91, Utah 1.86, Miami 1.73 |
| Indiana | 7th (+1.33) | 7th (+1.38) |
| Ole Miss | 16th (+0.14) | 16th (+0.23) |
| Ohio State | 17th (+0.05) | 17th (+0.12) |
| Top 12 = committee's Week 12 twelve | yes | yes |

Same shape.  The small differences are most likely data vintage (stored rows were updated after your run).  Worth a look: Utah lands in the pipeline's top 5 and in your table it does not appear there.

## Simulated first snapshot (NOT the real Week 13)

This used a throwaway copy of the repo: the Week 12 committee list with #24 and #25 swapped (so it counts as a new release) and stored games through 2026-11-20.  The real Week 13 numbers arrive after the Tue 2026-11-24 reveal.

Bubble 15.67 (Oregon 12th / Utah 13th by SRS).

| # | Committee | WAB | Model |
|---|---|---|---|
| 1 | Georgia | Georgia +2.19 | Georgia |
| 2 | Utah | Texas +2.04 | Texas |
| 3 | Alabama | UCLA +1.88 | Miami |
| 4 | UCLA | Utah +1.76 | Alabama |
| 5 | Texas | Miami +1.68 | UCLA |
| 6 | Notre Dame | Alabama +1.56 | Utah |
| 7 | Miami | Indiana +1.34 | Notre Dame |
| 8 | Indiana | Notre Dame +1.25 | Tennessee |
| 9 | Tennessee | Tennessee +1.12 | Oregon |
| 10 | BYU | Wake Forest +0.77 | Ohio State |
| 11 | Wake Forest | BYU +0.59 | Indiana |
| 12 | Texas Tech | Texas Tech +0.52 | Ole Miss |

| | Top 25 overlap | Top 12 overlap | Avg rank gap | Exact | Agreement |
|---|---|---|---|---|---|
| Model | 23/25 | 9/12 | 3.61 | 1 | 84% |
| WAB | 22/25 | 12/12 | 2.18 | 4 | 94% |

## Action items for Budzilla

1. Review the branch diff: `cfp_model.py`, `collect_cfp.py`, `update.py`, `build_cfp.py`, `template.html`, `tools/render_check.js`, README.md, AGENTS.md.  Do not merge; Jeff approves merges in chat.
2. Re-run your exploratory WAB on the same through-date (2026-11-17) against the current `data/team.json` and say whether the bubble (15.40, Utah / Indiana) and the top 5 now agree with the pipeline.  If they still differ, name the first team whose SRS differs and by how much.
3. Confirm the 5-game rule reading above (own stored rows), or say if Jeff meant something else.
4. Prepare the BEFORE / AFTER for Jeff (AGENTS.md: page changes need his OK in that form).  BEFORE: Playoff tab with Committee and Model only.  AFTER: WAB columns, the WAB agreement line, the Method note, and the "WAB tracking began Week 13" line on Weeks 11 and 12.
5. Timing: for the Week 13 snapshot to include WAB, the branch must be merged before the Wednesday 2026-11-25 10:47 AM ET full refresh, which is the run that stores the Tue 2026-11-24 reveal.  If it merges later, Week 13 is frozen without WAB and the series starts Week 14 (no backfill).
6. Reminder from the spec: do not start the warnings-model-v2 job (`docs/claude-spec-warnings-model-v2.md`) while this branch is open.  Both touch the CFP snapshot code.
7. After the merge and the Week 13 run: check the live page with `tools/render_check.js`, and post the real Week 13 WAB top 12 next to the committee's, plus `wab_metrics` next to `metrics`, from `data/cfp.json`.
