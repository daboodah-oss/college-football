# Spec: Side by Side rationale as a bottom sheet on narrow screens

Jeff's report, 2026-11-26 (screenshot: Arizona's rationale open over the
lists): on the phone the rationale pop-up floats over the lists and hides
the highlighted trace he tapped to see — "It would be nice to be able to
see the highlight path for a team, but the popup blocks it completely for
several."  Jeff chose the fix from three options Budzilla put to him:
**dock it as a bottom sheet.**  Template and checker only; no data, no
pipeline, no wording changes.

## Change (narrow presentation only, ≤920px — the swap view)

1. `.sbs-pop` becomes a bottom sheet: `position:fixed`, anchored
   `left:8px; right:8px; bottom:max(8px, env(safe-area-inset-bottom))`,
   `width:auto`, `max-height:55vh`, `overflow-y:auto`, z-index above the
   sticky bars.  Its content, × button, and typography are unchanged.
2. `sbsPlace()` must not fight the sheet: in the narrow presentation it
   sets no inline `left`/`top` on the pop-up (clear any set by a prior
   wide placement).  Wide presentation (≥921px) placement behavior is
   unchanged.
3. On open in the narrow presentation, scroll the tapped entry to about
   38% of the viewport height (`window.scrollBy` from its bounding
   rect), so the entry and its trace sit in the visible band above the
   sheet.  Respect `prefers-reduced-motion` (no smooth scroll there).
4. Everything else about the pop-up is unchanged: tapping another team
   swaps the contents, × closes, an outside tap closes, the highlight
   (`sbsHot`) behaves as now, and the wide view keeps the floating card
   under the tapped entry exactly as today.

## Checker (`tools/render_check.js`)

- Every existing assertion keeps its meaning (jsdom already exercises
  the narrow presentation, so the existing pop-up checks now run
  against the sheet).
- One new check: in the narrow presentation, an open pop-up is
  sheet-anchored (assert the mechanism you implement — computed
  `position:fixed`, or a class/data marker the sheet mode sets).

## Docs

- Update the AGENTS.md page-behavior notes for the Side by Side pop-up
  so they describe both placements (floating card wide, bottom sheet
  narrow).

## Acceptance

- `python3 build_report.py --standalone --out _test.html` prints OK;
  delete `_test.html` after.
- Render checker: 5 consecutive passes against the local build and 5
  against the live page, 66/66 sections (plus the new check),
  0 script errors, 0 failed checks.
- Handoff doc `docs/handoff-YYYY-MM-DD-sbs-bottom-sheet.md`: what
  changed, the checker results, and confirmation that `data/` is
  untouched.
- US English spelling throughout (repo rule 12).  Build on a feature
  branch; do not merge.
