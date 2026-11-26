# Handoff: a clear or a reset for every selection (2026-11-26)

Spec: `docs/claude-spec-clear-reset.md`.  Branch: `ccr-f4b99fc4-90drt5`.
Status: built and checked, **not merged**, waiting for Jeff's review.

Files changed: `template.html`, `tools/render_check.js`, `AGENTS.md`,
`README.md`, and this handoff.  Nothing in `data/`, `index.html`, `logs/` or
the pipeline was touched (`git diff origin/main -- data/` is empty).

## Before / after, per control

| Control | Before | After |
|---|---|---|
| National Top 3 pills | OFF pills dimmed to 40% opacity, ON pills looked like plain pills.  Nothing said a second tap removes a name. | ON is filled (ink background, page-color text, the same look as a selected `.seg` button).  OFF is the normal pill, not dimmed.  The gray underline (solid / dashed / dotted) shows in both states. |
| National Top 3 group | No way to turn all three off at once. | A labeled **Clear** button sits after the pills while any Top 3 pill is on (hidden when all are off).  One tap turns all three off and the gray lines go.  A single pill still toggles on its own. |
| National Top 3 note | "...Tap a name to draw his line; each is lined up by his own games played." | "...Tap a name to draw his line, and tap a selected name again to remove it; each is lined up by his own games played."  (Existing note line extended, no new paragraph.) |
| Chart line chips (`#team-chips`, `#player-chips`) | ON normal, OFF dimmed. | ON filled, OFF normal pill; the slot-colored underline (solid or dashed) shows in both. |
| Team picks row (`#team-picks`) | Only a small muted × on each pick. | Same ×, plus a labeled **Clear all** button at the end of the row while at least one team is picked.  One tap empties the selection and its line-off state; "No team picked yet." shows in the table, chart and logs. |
| Player picks row (`#player-picks`) | Only the ×. | Same ×, plus **Clear all** (current position only; the other positions keep their picks).  "No player picked yet." shows. |
| Pick pills (`.pc.nrpick`) | No change. | No change (they carry no `aria-pressed`). |

Implementation notes:

- CSS: `.pc[aria-pressed="false"]{opacity:.4}` is replaced by
  `.pc[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}`.
  New `.clearbtn` (outlined pill, 36px min height for touch).
- `clearTeams()` and `clearPlayers()` sit next to `removeTeam()` /
  `removePlayer()` and follow the same path (reset state, clear the cap
  message, re-run search, update).
- The Top 3 Clear button is rendered by `topRefresh()` and its visibility is
  updated in place on each pill tap, so the pills themselves are never
  re-rendered by a tap (the existing checker taps the same element twice).

## AGENTS.md

- New rule 13, in Jeff's words: every filter or selection ships with a way to
  clear it or reset it, or it does not ship; a new control lands with its
  Clear / Reset and a render-check assertion.  (Rule 12, US English, keeps
  its number because the spec cites it.)
- Page behavior notes: the "ON is full opacity, OFF is dimmed" line now
  describes the filled ON state; Clear all and the Top 3 Clear are described.
- README.md: the Player tab line and the render-check coverage list mention
  the new controls.

## Checker additions (`tools/render_check.js`)

New assertions only; no existing assertion changed.  Per theme:

- Team: "Clear all" visible with 5 picks; after one tap, 0 selected, no
  line-off state, "No team picked yet." in the table and chart, and the
  button gone.  Placed at the end of the Team block (nothing later reads the
  team picks).
- Per position (QB, RB, WR):
  - National Top 3 Clear is hidden while all pills are off; tapping every
    pill marks each `aria-pressed="true"`, draws the gray lines and shows
    Clear; Clear turns every pill off (`aria-pressed="false"`, state empty),
    the chart path count returns to its pre-Top 3 value, and Clear hides.
  - The note says a second tap removes a name.
  - "Clear all" visible with 3 picks; after one tap, 0 selected, no
    line-off state, "No player picked yet.", button gone.  Placed last in
    each position's block.

That is 20 new assertion lines per theme (40 total); the run now has 296
PASS lines.

## Acceptance results

- `python3 build_report.py --standalone --out _test.html`: `OK` (teams 2024
  124, 2025 131, 2026 138; sha256=361f002b76be9d0e); `_test.html` deleted.
- Local build, new checker, 5 consecutive runs: each **66/66 sections, 0
  script errors, 0 failed checks**, 296 PASS, exit 0.
- Live page (https://cf.daboodah.com/), 5 consecutive runs with the main
  branch checker: each **66/66, 0 script errors, 0 failed checks**, exit 0.
  The live page is still the pre-change build, so this is the baseline.
- Live page with the new checker, 1 run: 66/66, 0 script errors, 20 failed
  checks, exactly the new feature checks (team Clear all visible; per
  position Clear all visible, Top 3 Clear present, the note line; both
  themes).  The dependent follow-up checks are skipped by their guard.
  This is expected until the merge deploys the template.
- **After merge:** run `node tools/render_check.js https://cf.daboodah.com/`
  5 times; each must report 66/66, 0 script errors, 0 failed checks.  This
  is the one acceptance item that cannot be met before the merge.
- Not done: screenshots of the filled pills in light and dark.  The headless
  browser step was blocked in this session, so the look was checked only
  through the CSS and the jsdom assertions.  Worth a glance on the phone
  after merge.

## `data/` untouched

`git diff origin/main -- data/ index.html logs/` is empty on this branch.
