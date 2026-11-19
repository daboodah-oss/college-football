# Spec — Wins Above Bubble (WAB) as a third Playoff-tab ranking

Repo: daboodah-oss/college-football · Page: https://cf.daboodah.com/ (Playoff tab)
Approved by Jeff 2026-11-19. Build on your own branch; do not merge.
This spec is independent of docs/claude-spec-warnings-model-v2.md (a separate,
larger job). The two sessions must not run at the same time — both touch the
CFP snapshot code. This one is smaller and time-sensitive (see "No backfill").

## Why

On 2026-11-19 Budzilla computed a pure Wins Above Bubble ranking for the
Week 12 snapshot (2026-11-17) from the stored data, outside the pipeline.
Result: WAB's top 12 was exactly the committee's top 12 (same twelve teams),
while the blended model's top 12 matched only 9 of 12 (the model swapped in
Ohio State, Ole Miss, Oregon for Wake Forest, BYU, Texas Tech). Jeff wants
WAB tracked as a standing third ranking every week, next to Committee and
Model, to test whether the committee behaves more like a résumé metric than
a power rating. WAB is NOT added to the blend and does not change the
model's rankings — it is a comparison column, like the committee's own.

## The method (implement exactly; do not tune)

WAB here mirrors the NCAA basketball definition, adapted to a 12-team
playoff, using this repo's own SRS as the rating base:

1. Ratings: SRS exactly as cfp_model.srs_ratings computes it (margin capped
   at ±28, home field 2.5, iterated to convergence), over the deduped games
   in data/team.json through the snapshot's through-date, including the
   combined FCS opponent node (FCS_ID) and its rating.
2. Bubble team: the cut line sits between the 12th- and 13th-highest FBS
   teams by SRS. Bubble rating = the mean of those two teams' SRS values.
3. Win probability that the bubble team beats a given opponent at a given
   site: normal CDF of (bubble_rating − opponent_SRS + site_adj) / 13.5,
   where site_adj is from the bubble team's perspective in the actual
   game's venue: −2.5 if the ranked team was home (bubble would be the
   visitor), +2.5 if the ranked team was away, 0 at a neutral site.
   Opponents with no FBS entry use the FCS node's SRS.
4. Game value: win = 1 − p; loss = −p. Ties skipped (consistent with the
   existing pipeline). WAB = the sum over all of the team's games through
   the snapshot date.
5. Rank all FBS teams by WAB descending; ties break on raw SRS, then name.
   Teams with fewer than 5 stored games are unranked (today that is
   Air Force, Stanford, Hawai'i — the known missing team-seasons).
6. σ = 13.5 and the 12/13 bubble definition are part of the method. Do not
   adjust them to fit the committee better; the point is an honest test.

## Snapshot + page changes

- Each NEW snapshot in data/cfp.json gains: the WAB top 25 (team ids, same
  shape as "committee" / "ours"), each line's WAB value and WAB rank where
  lines are stored, the bubble rating and the two bubble-adjacent team
  names, and wab_metrics {overlap25, overlap12, avg_delta, exact} computed
  with the SAME definitions as the existing model metrics (reuse the
  existing metric code path so the numbers are comparable).
- Playoff tab: show WAB as a third ranking alongside Committee and Model,
  with its own agreement line, and extend the Method note with a plain-words
  explanation: WAB counts only wins and losses — for each game, how many
  more (or fewer) wins you earned than a team sitting exactly on the
  playoff cut line would be expected to earn against your schedule.
- update.py: WAB is computed inside the same snapshot step as the model;
  refusing to append a duplicate week still applies.

## No backfill

Weeks 11 and 12 snapshots stay frozen exactly as they are — their precise
input data can no longer be reproduced, and frozen snapshots are never
rewritten. The WAB series starts with the next snapshot (Week 13, reveal
Tue 2026-11-24). The tab should make the start week plain (e.g. "WAB
tracking began Week 13") rather than implying missing data.

## Validation target (sanity check only)

Budzilla's exploratory run on data through 2026-11-17 (computed outside the
pipeline; your pipeline numbers may differ slightly from data vintage):
bubble ≈ 15.98 (Ole Miss #12 / Utah #13 by SRS); WAB top 5: Georgia +2.12,
Texas +1.92, UCLA +1.78, Miami +1.65, Alabama +1.51; Indiana 7th (+1.33);
Ohio State 17th (+0.05); Ole Miss 16th (+0.14); WAB top 12 = the committee's
Week 12 twelve exactly. If your implementation's shape differs materially
from this on comparable data, stop and say so in the summary.

## Acceptance

- tools/render_check.js passes completely against the built page.
- Build summary reports: the first WAB snapshot's top 12 next to the
  committee's, the WAB metrics next to the model metrics for that week,
  and explicit confirmation that the Week 11/12 snapshots are byte-untouched
  and the model blend is unchanged.
