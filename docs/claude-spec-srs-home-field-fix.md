# Claude spec — Fix the SRS home-field double-count in cfp_model.srs_ratings

Repo: daboodah-oss/college-football (live page https://cf.daboodah.com/)
Author: Budzilla, 2026-11-21. Jeff's ruling (2026-11-21, "A"): fix this as its
own small job, after the WAB branch merge (merge commit b700d327, done).
Build on your own branch, do not merge without Jeff's approval.

## The bug

In `cfp_model.py`, `srs_ratings` builds each game into two adjacency terms:

```python
hw = HOME_FIELD if home == w else -HOME_FIELD if home == l else 0.0
adj[w].append((l, c - hw))    # winner's margin, minus its home edge if it was home
adj[l].append((w, -c - hw))   # loser's view
```

The winner's term is standard: capped margin c, minus 2.5 when the winner was
home, plus 2.5 when the winner was away. The loser's term is not the negative
of it. The symmetric form is `-(c - hw)`; the code has `-c - hw`, so the pair
sums to −2hw instead of 0. In plain terms: the home team's rating is docked an
extra 5 points per game across the two equations — home field is effectively
double-counted against the home team, in every SRS rating the pipeline has
produced. SRS is 45% of the model blend, sets the resume component's Top-25
set, and (since the WAB merge) is also the rating base for Wins Above Bubble.

## The fix

One line: the loser's term becomes `-(c - hw)`. Update the inline comment to
say the two terms are negatives of each other. Nothing else in `srs_ratings`
changes: margin cap ±28, home field 2.5, iteration and mean-centering as they
are.

Add a short note to `docs/cfp-model.md` recording the correction, its date,
and that it applies from the first snapshot stored after the fix lands.
Update README/AGENTS only if their text describes the formula in a way this
change makes wrong.

## Constraints

- Frozen snapshots are never recomputed or rewritten. Weeks stored before
  this fix keep the ratings they were frozen with; that is correct behavior,
  not an inconsistency to repair.
- Blend weights (45/30/25), Colley, and the resume rules do not change.
- WAB needs no code change: it calls `srs_ratings` and inherits the fix.
  Confirm that in your summary rather than touching `wab()`.
- No other file changes beyond the doc note above.

## Validation target (Budzilla's independent run, games through 2026-11-17)

With the symmetric form on that data: ratings shift by up to ~3.6 points
(largest: North Carolina 11.95 → 8.35; #1 Georgia 26.29 → 24.40); the WAB
bubble moves 15.40 → 14.36 (Ole Miss #12 / Indiana #13 by SRS); WAB top 5
becomes Utah +2.26, Georgia +2.04, Texas +1.99, UCLA +1.88, Miami +1.66
(Indiana still 7th). Your numbers on the same through-date should match
these closely; if they differ materially, stop and say so.

Also add or run a regression check that, for every stored game, the two
adjacency terms now sum to exactly 0.

## Timing

Best case: merged before the Wed 2026-11-25 10:47 AM ET full refresh, so the
Week 13 snapshot — the first WAB snapshot — is computed with the corrected
SRS for both the model and WAB. If it lands after that run, Week 13 stands
as computed and the correction applies from Week 14. Either way is accepted;
do not hold the branch open past Jeff's merge approval to chase the timing.

## Acceptance

- tools/render_check.js passes completely against the built page.
- Summary reports: the one-line diff; before/after SRS Top 13 and WAB bubble
  on a stated through-date against the validation target above; explicit
  confirmation that no stored snapshot in data/cfp.json changed and that
  `wab()` needed no changes.
