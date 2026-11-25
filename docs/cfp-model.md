# The Playoff model: how "our" Top 25 is built

Added 2026-11-11 at Jeff's request: each week the committee releases its rankings, the page freezes a
snapshot (data/cfp.json) holding the committee's Top 25, our computed Top 25, the per-team lines and the
agreement metrics, and the Playoff tab argues with the committee from the numbers.  Jeff delegated the
algorithm ("come up with something on your own"), with three hard constraints: deterministic,
reproducible from the committed data alone (data/team.json game rows + the committee snapshot), and no
hand-tuned per-team adjustments.  Implementation: `cfp_model.py` (the math), `collect_cfp.py` (the
weekly snapshot through `update.py`), `build_cfp.py` (names + shape checks at build time).

## The systems assessed, and what was taken or left

- **Colley Matrix** (Wesley Colley; a BCS computer poll).  Wins and losses only; schedule strength
  falls out of solving a linear system over who beat whom.  Strength: it is a pure resume and cannot be
  gamed by margin.  Weakness: margin-blind — a 1-point win over a peer counts the same as a 40-point
  win, and it treats a loss to the No. 1 team exactly like a loss to the No. 40 team except through the
  schedule term.  **Taken**, as the resume backbone (30%).
- **Simple Rating System (SRS)**, Sports-Reference style.  Rating = average (margin + opponent
  rating), iterated.  Strength: simple, transparent, schedule-adjusted, uses how games were actually
  played.  Weakness: raw margin rewards running up the score and over-weights September blowouts of
  weak teams.  **Taken with two guards** (45%): margin capped at 28 points, home field fixed at 2.5.
- **Massey ratings.**  Least-squares fit of game margins (a close cousin of SRS) — sound, but in its
  published form it folds in more machinery (offense/defense splits, time weighting) than this page can
  explain in a paragraph.  Not taken separately; SRS covers the same ground more legibly.
- **Elo-style ratings** (and Sagarin's ELO half).  Game-by-game: order matters, streaks compound, a
  September loss fades exactly as much as the formula says regardless of who it was to.  That is a
  *predictive* property, and it makes the rating path-dependent — two identical resumes played in a
  different order score differently, which is wrong for a resume ranking.  **Rejected** as a component;
  its iteration-to-convergence idea is already inside SRS.
- **Anderson & Hester, Wolfe, Billingsley** (the other BCS computers).  Anderson & Hester is
  conference-aware resume math (respectable, but its conference adjustments are exactly the kind of
  opaque hand-tuning the constraints forbid).  Wolfe is a maximum-likelihood wins-only model in the
  same family as Colley, harder to explain and no better behaved on this data.  Billingsley weights
  recent games more (a defensible choice, but it is a judgment knob, and turning it changes history —
  snapshots here must be explainable as "the resume to date", so no recency weight).  **All rejected**,
  Colley covers the wins-only family.
- **SP+ / FPI** (modern predictive systems).  Play-by-play efficiency, opponent-adjusted, genuinely
  excellent at forecasting who wins next week.  Two disqualifiers: forecasting is not the committee's
  question (who has *earned* a spot is), and their inputs are not stable public data this pipeline can
  store and re-check.  **Rejected as inputs**; noted as the design reference for what we are *not* doing.

## The blend (cfp_model.compute, run at snapshot time on the stored rows)

Every FBS team (plus one combined FCS opponent node) is scored three ways; each score becomes a 0–100
percentile among FBS teams; the final score is the weighted sum; ties break on raw SRS, then name.

1. **SRS, 45%.**  Iterated to convergence (delta < 1e-9, mean-centered): rating = mean over games of
   (margin capped at ±28, minus 2.5 if the team was home, plus 2.5 if the opponent was home) +
   opponent rating.
2. **Colley, 30%.**  Solve (2I + L) r = b over all games, FCS included as one node.
3. **Resume points, 25%.**  Per game played: +1.0 per win over a team with a winning record, +0.5 more
   per win over an SRS Top 25 team, −0.75 per loss to a team at .500 or worse, +0.1 per win over the
   FCS node.  Per game, so playing extra games is not itself a reward.

Stored per team in each snapshot: record, strength-of-schedule rank (by mean opponent SRS), best win
and worst loss (by opponent SRS) with their records, quality wins, Top-25 wins, and the three component
scores' final blend.  The Playoff tab's disagreement lines are generated from those fields only.

**Correction, 2026-11-21 (SRS home field).**  Until this date `srs_ratings` stored the loser's
adjacency term as `-c - hw` instead of `-(c - hw)`, so the two terms of a non-neutral game summed to
-2hw instead of 0: home field counted twice against the home team (an extra 5 points across the pair).
The formula above was always the intent; the code now matches it, and `tools/check_srs_symmetry.py`
checks every stored game.  The fix applies from the first snapshot stored after it landed.  Weeks
frozen before it keep the ratings they were stored with; snapshots are never recomputed.  Wins Above
Bubble uses `srs_ratings` for its ratings and bubble, so it inherits the fix with no change to `wab()`.
On games through 2026-11-17 ratings moved by up to 3.6 points (North Carolina 11.95 -> 8.35, Georgia
26.29 -> 24.40) and the WAB bubble from 15.40 (Utah / Indiana) to 14.36 (Ole Miss / Indiana).

**Bias tab inputs (from the first snapshot stored after 2026-11-21).**  `compute` also returns the SRS
Top 25 and puts each team's SRS rank among all FBS teams (`srs_rank`, ordered by rating then name, the
same order as WAB's bubble) on its line.  Neither enters the blend; our Top 25, the scores and WAB are
unchanged.  The Bias tab (`build_bias.py`, spec `docs/claude-spec-cfp-bias-analysis.md`) reads them from
the frozen snapshot.

## Model v2 (from the first snapshot stored after 2026-11-21)

Jeff-approved 2026-11-11 (`docs/claude-spec-warnings-model-v2.md` Part 6B).  v1 values every opponent at
its season-long rating, so a team that collapses later (the case that prompted this: Ohio State without QB
Julian Sayin after Oct 17) retroactively cheapens results earned against it at full strength.

- **Dated, 20%.**  Per team, the mean over its games of (capped margin, home-adjusted, exactly as SRS) +
  the opponent's rating *as of that game's date*: SRS computed from only the games played strictly before
  that day (an expanding window over the same stored rows; deterministic; no new data).  Early in the
  season an opponent has few prior games, so while it has fewer than 4 its as-of rating is blended with
  its season rating (weight n/4).  No preseason or poll input exists to stand in for it, by design.
- **Weights v2:** SRS 25, Dated 20, Colley 30, Resume 25.  The 20 comes out of SRS, so margin-based
  evidence keeps its 45 and wins-and-losses and resume keep their 30 and 25: the blend's balance is
  unchanged, only how opponents are valued shifts.
- **Versioning.**  `cfp_model.MODEL` is what collect_cfp stores; each snapshot records `model` and its
  `weights`, and v2 lines carry `dated`.  Snapshots stored through 2026-11-21 (Weeks 11 and 12) have no
  `model` key, are labeled v1 on the page, and are never recomputed.  `compute(..., model="v1")`
  reproduces v1 exactly (checked against the pre-v2 code).  `tools/model_compare.py` shows committee /
  frozen / v1 / v2 for any stored week without storing anything.
- **Effect, honestly.**  On Week 11's games (through 2026-11-07) Ohio State rates 19.95 as of Oct 17
  against 15.40 for its season, so Indiana's Oct 17 loss is now valued 4.5 points higher; Indiana's Dated
  score is 14.10 against an SRS of 13.61.  The Top 12 moves little (Tennessee and Oregon swap 10th and
  11th); v2 corrects the valuation without reshuffling the list.
- Unchanged: the SRS baseline and `srs_rank` of the Bias tab, WAB, the margin cap and home field.
- Numeric injury adjustments are out of scope (no reliable source in the pipeline; they would break the
  no-hand-tuning rule).  Context instead appears as notes (below).

## Context notes (cfp_context.json)

Curated, sourced, display-only notes per committee week, shown in the Playoff tab's critique area under
"Context this week (not part of any ranking)".  Each names the team (exactly as stored), the fact, the
source, a link and the source's date, from a cited public report (a coach's statement or a credible beat
report), never rumor.  They live in `cfp_context.json` at the repo root, not in `data/cfp.json`: adding a
note to a past week does not touch its frozen snapshot (update.py's cfp guard would refuse any re-store of
an earlier week anyway: it refuses a date before the latest stored week and a committee list equal to the
latest).  `build_cfp.py` validates every note; a note for a week not yet stored waits.

## Agreement metrics (collect_cfp.agreement_metrics)

- **Agreement %** (the headline) = mean of the Top 25 overlap share and the Top 12 overlap share.
- Also stored: Top 25 overlap, Top 12 (playoff field) overlap, exact-position matches, and the mean
  absolute rank difference over the teams on both lists.

## Snapshot discipline

ESPN's rankings endpoint is re-read on each pipeline run; a snapshot is appended only when the
committee's 25 differ from the stored latest (update.py refuses a duplicate), so the Wednesday run
after each Tuesday reveal adds exactly one week and no run can rewrite history.  The Nov 3, 2026 release
(Week 10) could not be backfilled: ESPN's endpoint serves only the current poll (its week parameter is
ignored), so the file starts with Week 11 (Nov 10, 2026).
