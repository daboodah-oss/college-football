# Handoff 2026-11-24: warnings cleanup, source reconciliation, Playoff model v2

Repo daboodah-oss/college-football, branch `claude/modest-pasteur-qsttu7`.  Jeff approved the merge in chat on
2026-11-24.  Spec: `docs/claude-spec-warnings-model-v2.md`.  The branch contains main; `data/` is unchanged.

## What it does

1. **Validator tolerances** (`update.tolerance`).  Team season yardage max(5, 0.5%), third downs 5, turnovers 1.
   Games and points stay exact.  Every difference inside a tolerance is still printed in the stored note on the
   page.  `tools/test_validator.py` tests every edge.
2. **Total yards fix** (`collect_tabs.box_row`).  ESPN's `totalYards` field is sometimes wrong; total is now stored
   as rushing + passing, only when ESPN's own player lines prove the components, and each corrected game is logged.
3. **Source reconciliation.**  Two pinned `SOURCE_EXCEPTIONS`: Georgia Tech 2024 points (376 vs 370) and NC State
   2024 points allowed (392 vs 386).  cfbstats' own schedule tables sum to ESPN's values; its season lines miss 6
   points of GT's 30-29 win on 2024-11-21.  Army and Navy 2025 stay refused: ESPN's box score for the 2025-12-13
   Army-Navy game has no team stats.  13 rushing-yard cases stay refused; each is narrowed to one or two candidate
   games in `docs/part3-reconciliation.md`.
4. **Banner wording.**  Per-season counts instead of the all-or-nothing notice.
5. **"Report problems" workflow step.**  It was not broken: it failed every run on purpose because any single refused
   team failed its whole season section, and refused 2024/2025 seasons never heal, so the emails carried no signal.
   Now refusals are recorded in `data/last_run.json` and the run fails (email) only for a failed build, a section that
   broke, or a team newly refused since the last run (`tools/run_report.py`).  Also: ESPN drops the Playoff poll from
   its feed between releases (Sunday until the Tuesday reveal); that no longer fails the run unless no release has
   been stored for 8+ days before Dec 10.
6. **Playoff model v2** from the next snapshot (Week 13): SRS 25%, Dated 20% (each game valued against the
   opponent's rating as of that game's date), Colley 30%, Resume 25%.  Weeks 11-12 stay v1 and are labelled v1.
   Curated, sourced, display-only context notes live in `cfp_context.json` (Week 11: Ohio State QB Julian Sayin,
   out since Oct 17; Ryan Day's announcement was Oct 20).  They never move a ranking and never touch `data/cfp.json`.

## Expected effect (measured by re-collecting all 70 refused team-seasons with the new code)

| Season | Refused before | After | Missing from page before → after |
|---|---|---|---|
| 2026 | 26 | 0 | 4 → 0 |
| 2025 | 12 | 5 | 12 → 5 |
| 2024 | 32 | 10 | 32 → 10 |
| All | 70 | 15 | 48 → 15 |

The 2024/2025 numbers land on the first FULL run after the merge (Sunday or Wednesday 10:47 AM ET); quick checks
only touch 2026.

## What readers will see (BEFORE / AFTER)

- Banner BEFORE: "The latest automatic update could not refresh: team_2026, team_2025, team_2024, cfp_rankings.
  Those sections show the last verified data."  AFTER: "N of M 2026 team seasons could not be re-verified in the
  latest update and show their last verified data: ..." (only when that is true), and the missing-team-seasons
  notice with the smaller count (about 15).
- Playoff tab: "model v1" / "model v2" in the lede; a "Context this week (not part of any ranking)" block on Week 11;
  the Method note describes v2.
- From Week 13: the first real Bias tab week and the first v2 snapshot.

## Who does what

**Budzilla (Muse)**
1. Merge `claude/modest-pasteur-qsttu7` into `main` (Jeff approved 2026-11-24), ideally before Wed 2026-11-25
   10:47 AM ET so Week 13 is stored as v2.
2. After the next workflow run: check the run is green and its summary lists refusals; run
   `node tools/render_check.js https://cf.daboodah.com/` against the live page; confirm the banner shows counts.
3. After the Wednesday run: confirm Week 13 is stored, labelled "model v2", and the Bias tab shows its first week.
4. When convenient: open the official box scores listed in `docs/part3-reconciliation.md` and report the official
   team rushing yards per candidate game, so Claude can pin exceptions where the evidence supports one.  Do not edit
   `update.py` or `data/` directly (Claude's lane).

**Keela, and Sports (GrokBot)**: nothing to do.  For reference when discussing the page:
- Our Playoff Top 25 changes method from Week 13 (v2).  On Week 11's games v2 barely moved the list (Tennessee and
  Oregon swap 10th and 11th); its point is valuing opponents as they were when played (the Ohio State / Sayin case:
  Indiana's Oct 17 loss now counts against a 19.95-rated Ohio State instead of its 15.40 season rating).
- Injury context appears as sourced notes only; no ranking is adjusted for injuries.
- New context notes go in `cfp_context.json` (team, fact, source, link, date), from a coach's statement or a credible
  beat report, never rumor.
- The Bias tab's first real week is Week 13; its verdict compares each conference with that week's all-25 average.
