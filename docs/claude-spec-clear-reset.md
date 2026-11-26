# Spec: a clear or a reset for every selection

Jeff's standing rule, stated 2026-11-26 after he could not find how to
drop a National Top 3 pill or a compare team on his phone: **every
filter or selection ships with a way to clear it or reset it, or it
does not ship.**  This job brings the existing controls up to the rule.
Template and checker only: no pipeline, no data, no wording changes
outside the hints named below.

## Diagnosis (verified by Budzilla in jsdom, 2026-11-26)

The removal paths exist but are nearly invisible:

- National Top 3 pills toggle correctly (tap on adds the gray line,
  tap again removes it; `aria-pressed` flips).  The signal is inverted
  and weak: `.pc[aria-pressed="false"]{opacity:.4}` dims the OFF pills,
  so a selected pill just looks normal and an unselected one looks
  disabled.  Nothing says tap again to remove.
- Team and player picks are removable only by a small muted × on each
  pick pill.  There is no clear-all anywhere, and since the picker
  became search-and-add there is no obvious place where selections are
  managed.

## Changes

1. **Selected means filled.**  Every toggle pill that carries
   `aria-pressed` (National Top 3 pills; the chart line chips in
   `#team-chips` and `#player-chips`) shows its selected state filled —
   `background:var(--ink);color:var(--bg)`, the same treatment as
   `.seg button[aria-pressed="true"]` — and its unselected state as the
   normal pill.  The dimming rule no longer applies to these pills.
   The name underline (`span.pu`, slot color and line style) stays
   visible in both states.  Non-toggle `.pc` elements (the pick pills)
   do not change.
2. **Clear all on the picks rows.**  When the selection is non-empty,
   the `#team-picks` and `#player-picks` rows end with a labeled
   "Clear all" button.  One tap empties the selection (and any
   line-off state tied to it) and redraws; the existing empty states
   ("No team picked yet." / the player equivalent) show.  The per-pick
   × stays exactly as it is.
3. **Clear for National Top 3.**  When any Top 3 pill is on, the
   National Top 3 block shows a labeled "Clear" button that turns all
   three off and redraws.  Tapping a pill still toggles it on its own.
4. **Say it in words.**  The National Top 3 block tells the reader,
   once, that tapping a selected name again removes it (extend the
   existing note line; do not add a new paragraph elsewhere).
5. **Record the rule.**  Add Jeff's rule to the repo `AGENTS.md` as a
   standing design rule, in his words: every filter or selection gets
   a clear or a reset.

## Checker additions (`tools/render_check.js`)

New checks only; every existing assertion keeps its meaning.

- Team tab: with picks present, "Clear all" is visible; clicking it
  leaves zero selected and the empty state showing.
- Player tab: same for player picks (place it where it cannot disturb
  later assertions in the run; restore any state later steps need).
- National Top 3: tapping a pill on marks it `aria-pressed="true"` and
  adds the gray line; "Clear" turns every Top 3 pill off and the gray
  lines are gone.

## Acceptance

- `python3 build_report.py --standalone --out _test.html` prints OK;
  delete `_test.html` after.
- Render checker: 5 consecutive passes against the local build and 5
  against the live page, 66/66 sections (plus the new checks),
  0 script errors, 0 failed checks.
- Handoff doc `docs/handoff-YYYY-MM-DD-clear-reset.md`: before/after
  behavior per control, the checker results, and confirmation that
  `data/` is untouched.
- US English spelling throughout (repo rule 12).  Build on a feature
  branch; do not merge.
