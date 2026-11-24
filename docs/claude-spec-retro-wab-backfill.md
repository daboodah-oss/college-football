# Spec: one-time retrospective WAB + Bias inputs for Weeks 11 and 12

Repo: daboodah-oss/college-football. Build on your own branch, do not merge.
Run this job only after the Side by Side redesign branch has merged (both jobs
touch build_cfp.py and template.html).

## Jeff's ruling (2026-11-24) — read first

The standing rule is that a frozen snapshot is never recomputed. Jeff amended it
narrowly on 2026-11-24: **display-only comparison inputs (the WAB block and the
Bias tab's SRS inputs) may be computed retrospectively for a frozen week and
must be labeled as retrospective wherever they are shown. The committee list,
our Top 25, and the agreement metrics of a frozen week are never recomputed,
ever.** This job is the one application of that amendment: Weeks 11 and 12 of
2026, the two snapshots stored before WAB and the Bias inputs existed.

## What to compute and store

For each stored 2026 snapshot that lacks a `wab` block (today: Week 11,
through 2026-11-07, and Week 12, through 2026-11-17), compute from the stored
game rows through the snapshot's own `through` date, using the same functions
the live pipeline uses (`cfp_model.wab(root, season, through)` and the SRS
ordering inside `cfp_model.compute` — do not reimplement the math):

- `wab`: the WAB Top 25 (team ids), `wab_bubble` {rating, team12, team13},
  `wab_metrics` against the stored committee list (the same agreement_metrics
  code path collect_cfp uses).
- Per-line additions for every team in the snapshot's lines: `wab` (value)
  and `wab_rank` where the team is WAB-ranked, exactly as collect_cfp stores
  them for a live week.
- `srs_top25` and per-line `srs_rank`, exactly as collect_cfp stores them
  since the Bias build.
- A marker on the snapshot: `"retro": {"date": "<YYYY-MM-DD of the run>",
  "scope": "WAB and Bias inputs computed retrospectively from the stored game
  rows through this week's freeze date"}`.

Nothing else in the snapshot changes. The tool must prove it: committee, ours,
metrics, weights, model, date, through, and every pre-existing line field are
byte-identical before and after (compare parsed JSON field by field and print
the result).

## How it runs

A one-off tool, `tools/backfill_retro.py`, in the spirit of the other offline
tools: it reads data/cfp.json + data/team.json, computes, and rewrites only
data/cfp.json. It is NOT wired into collect.py, update.py's scheduled flow, or
the workflow, and it refuses to touch a snapshot that already has a `wab`
block. This is a deliberate one-time exception to "data comes only from
collect/update," approved by Jeff on 2026-11-24 and recorded here and in
AGENTS.md; the enriched snapshots must pass the existing validation as-is
(update.py's snapshot checks, build_cfp's checks, build_bias's checks) with no
check weakened. Run it once, in the session, and commit its output as part of
the branch.

Data-state note: the numbers depend on the stored rows at run time (rows for
those weeks have grown since the freezes — that is the point of the label).
Budzilla's preview on the 2026-11-24 data state, for orientation only:
Week 12 bubble 14.25 (Ole Miss 12th / Indiana 13th by SRS), WAB Top 12 exactly
the committee's twelve, Indiana WAB No. 7 (+1.41), Ohio State No. 17;
Week 11 bubble 13.26 (Indiana / Oregon), Utah WAB No. 1 (+1.93). Report the
numbers you actually get, with the data/last_run.json timestamp you computed
from; Budzilla re-runs the same calls to verify.

## Labeling (the honesty half of the ruling)

- Playoff tab: for a week carrying `retro`, the WAB agreement block gains a
  visible note: `WAB for this week was computed retrospectively on <date>,
  from the stored game rows through <through>. The committee list, our
  Top 25 and the agreement scores above are the frozen originals.` (The
  model agreement block needs no note — it is untouched.)
- Bias tab: for a retro week, the week note says its SRS and WAB inputs were
  computed retrospectively on <date>; the "Bias tracking began" line must now
  read from the data as Week 11, since Week 11 will carry the inputs.
- Method notes: the Playoff Method list and the Bias Method list each gain
  one sentence recording the one-time retrospective computation and Jeff's
  2026-11-24 amendment.
- build_cfp.py passes `retro` through to the page model (and validates its
  shape); build_bias.py needs no change unless its week handling assumes the
  first bias week is the first stored week — check and note it in the handoff.

## Docs

- AGENTS.md: the Playoff/Bias page-behavior note gains the amendment, dated:
  frozen committee/ours/metrics are never recomputed; WAB and Bias inputs for
  Weeks 11–12 (2026) were computed retrospectively once, on Jeff's ruling of
  2026-11-24, and are labeled wherever shown.
- README.md: one sentence to the same effect where the frozen snapshots are
  described.

## Verification (repo rule 4)

- `python3 build_report.py --standalone --out _test.html` prints OK;
  `node tools/render_check.js _test.html` passes. Extend the checker: a retro
  week shows the retrospective note on the Playoff tab and the Bias tab, and
  the Bias tab renders Week 11 as a populated bias week. Delete `_test.html`.
- The before/after field-equality proof from the tool, pasted into the
  handoff.
- Sanity: Week 12's WAB agreement line (overlap12) reads 12 of 12 if the
  as-run numbers match the preview; report whatever it actually reads.

## Handoff

`docs/handoff-<date>-retro-backfill.md` on the branch: the as-run numbers per
week (bubble, WAB Top 12 vs the committee's, Indiana and Ohio State WAB
ranks), the data timestamp they were computed from, the field-equality proof,
checker results, and anything Budzilla should re-verify after the merge.
