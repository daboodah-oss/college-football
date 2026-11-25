# Handoff 2026-11-25: Playoff Side by Side redesign

Spec: `docs/claude-spec-side-by-side.md`, including the 2026-11-25 amendment (WAB swap view on narrow
screens, three lists on wide).  Branch `ccr-fb9ca8d7-x96vm1`, not merged.  Display only: nothing in
`collect*`, `update.py`, `cfp_model.py` or `data/` changed.

## What changed, per file

- `build_cfp.py`: each week gains `"conf": {team_id: conference}` for the same union `names` covers,
  read from repo-root `conferences.json` `members[<snapshot season>]`.  `check()` fails the build if a
  union team has no membership for the season.  Nothing else in the model changed.
- `template.html`:
  - CSS: conference pill tokens `--cp-*` in the light root, the `prefers-color-scheme` dark block and
    `:root[data-theme="dark"]` (spec colors; tint 12% and border 50% are `color-mix` of the text
    color; IND uses `--muted` / `--surface-2` / `--rule`).  New `.sbs*` styles: rows share one height
    so the Δ and slim columns ride with their list; under 560px the record wraps to a second line.
  - Shell: eyebrow "Two Top 25s, drawn against each other"; `#cfp-side` drops `tscroll`; caption no
    longer has the swipe hint.  Click / keyboard / hover listeners on `#cfp-side` are registered once
    in `renderCfpShell()`; the outside-dismiss `pointerdown` listener is registered once at load.
  - `updateCfp()`: the table is gone; it resets the pop-up, measures the section and calls
    `sbsRender()`.  New helpers, all function declarations (TDZ-safe): `cpill`, `sbsRanks`, `sbsOrder`,
    `sbsDir`, `sbsDelta`, `sbsSigned`, `sbsView`, `sbsRender`, `sbsCaption`, `sbsDraw`, `sbsLayout`,
    `sbsHot`, `sbsOpen`, `sbsClose`, `sbsPlace`, `sbsPopHtml`.
  - Presentation by the section's own width (`getBoundingClientRect`, threshold 920px; 0 in jsdom, so
    narrow): narrow = CFP + one list on the right (+ slim column and swap button on a WAB week);
    wide on a WAB week = CFP, Ours + Δ, WAB + Δ, each trace two segments.  `drawAll()` (tab open,
    debounced resize, theme change) now calls `sbsLayout()` on the Playoff tab: it re-renders only
    when the presentation flips, otherwise recomputes path geometry.
- `tools/render_check.js`: the side-table assertions (row count, 5 / 7 td columns, first-row name) are
  replaced by the spec's list checks, run on the latest week and, when that is a WAB week, again on
  the earliest week without WAB.
- `README.md`, `AGENTS.md`: Playoff descriptions updated.

## Checker results (repo rule 4)

- `python3 build_report.py --standalone --out _test.html`: `OK`.
- `node tools/render_check.js _test.html`: 66/66 sections populated across light and dark, 0 script
  errors, 0 failed checks; TDZ scan clean.  `_test.html` deleted.
- Week 13 (the latest stored, a WAB week): 29 CFP / 29 Ours entries, 29 lines, 29 Δ cells; every
  entry has a pill; the caption names the 3 WAB-only teams; 29 slim-column cells; the swap makes the
  right header "WAB" and opens on Utah (WAB No. 1), swapping back reopens on Georgia; the Georgia
  pop-up shows "What our model sees" and the Wins Above Bubble line; a body `pointerdown` dismisses it.
- Week 11 (no WAB): 27 / 27 / 27 / 27, no slim column, no swap, pop-up opens and dismisses.

## Sanity read in Chromium (390px and 1200px)

- Week 12: 27 entries per side (LSU and Auburn NR at the bottom of the CFP list; Arizona and Houston
  NR at the bottom of ours), 27 lines.  Ole Miss green (CFP 25, ours 11, Δ +14); Georgia and Indiana
  blue.  Ole Miss's pop-up: "Schedule strength: 2nd nationally", "Top-25 wins: 4".
- **Spec discrepancy, Texas:** the spec's sanity list says Texas's Week 12 line is red, but the stored
  ranks are CFP 5, ours 2.  The spec's color rule (green when CFP rank > our rank), its Δ rule
  (5 − 2 = +3, positive green) and the caption all make that green, the same direction as Ole Miss.
  The build follows the rule; Texas is green.  If red was intended, the rule itself would have to flip.
- Week 13 at 1200px renders the three-list view (58 path segments); at 390px the swap view.

## What changed since the spec was written

The spec expected no WAB week in stored data until after today's run.  Today's bot commit
(`cb5d2d7`, 2026-11-25) stored Week 13 with WAB, so the WAB pop-up line and the swap were exercised
on real stored data, both by the checker and in Chromium.  Nothing was fabricated.  The pop-up WAB
line stays data-guarded (shown only when the line carries `wab_rank`).

## For Budzilla to re-verify after the merge (live page)

1. Week 12: Ole Miss green, Texas green (see above), Georgia and Indiana blue; Ole Miss pop-up shows
   the 2nd schedule and 4 Top-25 wins.
2. Week 13 on a desktop (section 920px or wider): three lists, two-segment traces, hover highlights
   the whole trace, Δ columns after Ours and after WAB, pop-up WAB line carries "Δ vs CFP".  This is
   the wide presentation's first exercise outside a scratch browser.
3. Week 13 on a phone: slim WAB column, swap and swap back, pop-up "What WAB sees" in the WAB view.
4. Both themes: pill colors and line colors.
5. Run `node tools/render_check.js` against the live page.

## Small calls made inside the spec

- A team NR in both the CFP and the right-hand list (possible only in the WAB swap view) reads
  "in neither of these Top 25s" in the pop-up sub-line.
- On WAB weeks the sub-line's Δ is labeled with its list ("Δ vs Ours", "Δ vs WAB"), since three ranks
  are shown; weeks without WAB keep the plain "Δ".
- The slim column shows a Top 25 position or NR (matching the lists), not the FBS-wide WAB rank;
  the FBS-wide rank and value are in the pop-up.
- A Δ > 0 team with no losses closes with "The committee has no losses to weigh, so the gap is in how
  it values the rest of the résumé" instead of naming a worst loss.
- The scorecard's pre-WAB note still ends "so it has no WAB column" (the spec leaves that block
  unchanged).
