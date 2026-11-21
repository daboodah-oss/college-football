# Claude spec — "CFP Bias Analysis" tab

Repo: daboodah-oss/college-football (live page https://cf.daboodah.com/)
Author: Budzilla, 2026-11-21. Proposed by Jeff (from a Grok chat draft) and
resolved by Jeff's ruling the same day: "I want the numbers to tell the
story, but provide honest summary and any indication of bias in any
direction." Jeff clarified the same day, in his own words: a SEPARATE TAB;
rankings "purely based on numbers this season — not preseason, not what
people thought they were ranked"; and "something straight up that tells
me: does it look like there's bias?" Build on your own branch, do not
merge without Jeff's approval.

Sequencing: this job runs AFTER the SRS home-field fix
(docs/claude-spec-srs-home-field-fix.md) has merged, and BEFORE the
warnings/model-v2 job. All three touch the Playoff snapshot code; one at a
time.

## What this is

A new TAB of its own ("Bias", alongside Team / Player / Conferences /
Playoff), with its own week picker listing the same CFP snapshot weeks
the Playoff tab uses. For the selected snapshot it measures how far the
committee's Top 25 sits from two baselines the pipeline already
computes, and rolls the gaps up by conference.

This is an ADDITION, not a change: the existing Playoff tab, the model
blend, and WAB keep their current behavior and presentation exactly.
The only existing-code touch is the snapshot step storing the extra
fields below.

Both baselines are PURE NUMBERS FROM THIS SEASON'S GAMES ONLY — computed
from the stored game results, with no preseason projections, no polls,
and no human input of any kind. That is the point of the tab, and the
intro copy says so. (There is deliberately no AP column: the AP poll is
another human ranking, and Jeff ruled polls out.)

- **Efficiency baseline: our SRS margin rating** (opponent-adjusted,
  predictive in character — the in-house analogue of SP+). SP+ itself is
  NOT an input: its play-by-play inputs are ESPN+ subscription data this
  page cannot store and re-check, which is the pipeline's standing rule
  and is already stated in the tab's Method note. The section says this
  plainly (see Method note below) rather than pretending SRS is SP+.
- **Résumé baseline: WAB** (stored on every snapshot from Week 13 on).

Gap definition, per team: `gap = baseline_rank − cfp_rank`. Positive means
the committee ranks the team HIGHER than the baseline does. Both gaps are
shown; neither is hidden when it points the "wrong" way.

Why two baselines: a committee gap against efficiency alone proves
nothing about favoritism, because the committee ranks résumés by design.
If a conference's gap vs SRS is large but its gap vs WAB is near zero,
the honest reading is that the committee is rewarding those teams'
résumés, not their conference. The summary block (below) is built around
exactly that check.

## Snapshot data (new snapshots only — no backfill)

Extend the cfp snapshot step (collect_cfp.py / update.py), same pattern
as the WAB fields:

- On every stored line for a team in the bias universe (below), store
  `srs_rank`: the team's rank by SRS among all FBS teams at snapshot
  time. (Lines already store the SRS value; the rank must be frozen at
  collect time, not derived later from the stored subset.)
- Bias universe per snapshot: committee Top 25 ∪ SRS Top 25 ∪ WAB
  Top 25. Lines must exist for every team in the universe (extend the
  existing line-collection union accordingly).
- update.py validates the new field in the same style as the WAB block
  (numeric `srs_rank` on universe lines). build_cfp.py re-checks and
  passes the lines through.
- Snapshots stored before this ships have no bias data: the tab shows
  one line, "Bias tracking began <first week with data>", exactly like
  the WAB start line, and no empty tables. The start week is read from
  the data, never hard-coded.

## The tab (for a snapshot with bias data)

Conference for each team comes from the repo's stored conference data
(conferences.json, the selected season's actual membership — the same
source the Conferences tab uses).

1. **Team table**, sorted by gap vs SRS descending (most
   committee-favored first, most committee-disfavored last):
   Team | Conf | CFP rank | SRS rank | Gap (SRS) | WAB rank | Gap (WAB).
   Teams in a baseline's Top 25 but unranked by the committee have no
   numeric gap: they appear after the ranked rows in a short
   "Left out by the committee" list, grouped by which baseline(s) had
   them Top 25, with their conference. Count them per conference in the
   summary table (column: Omissions).
2. **Conference summary table**, one row per conference with at least
   one committee Top 25 team, sorted by average gap vs SRS descending:
   Conf | Teams (n) | Avg gap vs SRS | Median gap vs SRS | Net spots
   vs SRS | Avg gap vs WAB | Net spots vs WAB | Omissions.
   Averages to one decimal. n is always printed — these are 5–8 team
   samples and must never look more precise than they are. (Omissions
   count baseline-Top-25 teams from that conference the committee left
   out entirely.)
3. **Bar chart**: average gap vs SRS by conference, horizontal bars in
   the page's existing chart style, zero line in the middle, positive
   bars one direction and negative the other, conference name and value
   labeled. Use the existing chart engine; do not add a chart library.
4. **Season trend table**: rows = conferences, columns = each stored
   week that has bias data, cells = that week's average gap vs SRS
   (one decimal, blank where a conference had no Top 25 team). This is
   the "systematic vs one loud week" evidence. Table, not a chart, in
   v1.
5. **Honest summary block** (2–4 sentences, generated deterministically
   from the week's numbers — same spirit as the data-generated
   disagreement reasons elsewhere on the tab). It must:
   - Name the conference with the largest positive average gap vs SRS
     AND the largest negative one, each with its n.
   - Run the résumé check for the largest positive conference: state
     its average gap vs WAB alongside, and if the WAB gap is within
     ±1.0 while the SRS gap exceeds ±2.0, say in plain words that most
     of the efficiency gap is explained by résumé, not conference.
     (Apply the same check, mirrored, to the largest negative
     conference.)
   - Name the largest single-team gap in each direction (team,
     committee rank, baseline rank, gap).
   - End with a straight verdict line that answers Jeff's question —
     does it look like there's bias? — under this fixed rule, applied
     per conference (n ≥ 3): bias is INDICATED in a conference's favor
     when its average gap vs SRS is at least +2.0 AND its average gap
     vs WAB is at least +1.0 in the same direction (the résumé check
     failed to explain it); mirrored for bias against a conference.
     When an efficiency gap is explained by résumé (gap vs WAB within
     ±1.0), the verdict says so plainly: no bias indicated, résumé
     explains it. When no conference meets the rule, the verdict is:
     no clear bias in either direction this week. The thresholds are
     printed in the Method note so the verdict is re-checkable, and
     the verdict never names a conference the rule didn't select.

## Method note (on the Bias tab)

A short note covering: the gap definition and sign; the two baselines
and why there are two; that both baselines are computed from this
season's stored game results only — no preseason projections, no
polls; that the efficiency baseline is our own SRS margin rating, an
SP+-style predictive rating, because SP+'s inputs are not public data
this page can store and re-check; that a gap against efficiency alone
is expected by design (the committee ranks résumés, efficiency ratings
forecast), which is why the verdict requires the gap to survive the
résumé check; the verdict thresholds from the summary block; that
conference averages rest on small samples (n shown everywhere); and
that bias tracking begins with the first snapshot stored after this
ships, with earlier weeks never recomputed.

## Acceptance

- tools/render_check.js passes completely, extended to cover: bias
  tab populates for a bias week (team table row count = committee
  25, conference rows present, summary block non-empty), and a pre-bias
  week shows the "Bias tracking began" line with no bias tables.
- Summary reports: the first bias snapshot's conference table and
  honest-summary text verbatim (including the verdict line), the
  largest single-team gaps in both directions that week, and explicit
  confirmation that earlier snapshots are byte-untouched, the model
  blend and WAB are unchanged, and the Playoff tab renders exactly as
  before.
