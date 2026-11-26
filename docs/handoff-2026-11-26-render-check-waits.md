# Handoff 2026-11-26: render_check.js waits for async renders

Spec: `docs/claude-spec-render-check-waits.md`.  Branch `ccr-fb9ca8d7-x96vm1` (restarted from main
`9d3b2eb` after the Side by Side merge), not merged.  Tooling only: `tools/render_check.js`.  No page,
pipeline or data changes.

## What changed

- New `waitFor(fn, what, timeoutMs = 5000, found)` next to `sleep`: polls `fn` every 50 ms; on timeout
  it records `FAIL  waited 5000 ms for <what>; found <state>` and returns, so the run never hangs or
  crashes.  `found` is an optional fourth argument that describes the state at timeout (selection
  length, row count, cap message).
- Two predicates per theme: `teamAt(n)` / `playerAt(pos, n)` are true when `CF_CHECK.state()` holds n
  picks **and** the head-to-head table has n rows, which is the end state the next assertion reads.
- **No assertion changed.**  I extracted every `ok(...)` call from main's checker and from this one and
  compared them: all 80 are byte-identical.  The only new `ok` is the timeout record inside `waitFor`.

## Every sleep replaced

| Step | Was | Now waits for |
|---|---|---|
| Team: add the third team | `sleep(150)` | 3 selected and 3 table rows |
| Team: cross-season pick | `sleep(150)` | 4 selected and 4 rows |
| Team: each cap-fill add | `sleep(120)` | selection + 1 and rows + 1 |
| Team: × remove | `sleep(30)` | cap − 1 selected and rows |
| Player: National Top 3 chip on | `sleep(200)` | more chart paths than before the tap |
| Player: cross-season pick | `sleep(200)` | 3 selected and 3 rows |
| Player: each cap-fill add | `sleep(150)` | selection + 1 and rows + 1 |
| Player: × remove | `sleep(30)` | cap − 1 selected and rows |

The National Top 3 chip isn't on the spec's list, but it is the same pattern: the tap runs
`drawPlayerAsync()`, which fetches that season's game logs before drawing.  So it follows the spec's
rule ("every click that triggers an async fetch/render").

Kept as fixed sleeps, because those steps are synchronous in the page (`removeTeam`, `removePlayer` and
the over-cap branch of `addTeam` / `addPlayer` return before any `await`): theme toggle, tab switches,
the position switcher, the over-cap click (`sleep(60)`), the National Top 3 chip off (`sleep(50)`),
week and season pickers, the Side by Side swap and pop-up clicks, and `type()`'s 20 ms.  The × removes
are synchronous too; they wait anyway, as the spec asks, and pass on the first poll.

## Results

5 consecutive runs against each target, run on 2026-11-26:

| Target | Runs | Sections | Script errors | Failed checks |
|---|---|---|---|---|
| Local build (`build_report.py --standalone --out _test.html`, prints OK) | 5/5 pass | 66/66 each | 0 | 0 |
| Live page `https://cf.daboodah.com/` (418,454 bytes) | 5/5 pass | 66/66 each | 0 | 0 |

The TDZ scan was clean on every run.  Each run took 11 to 13 seconds.

**Why the old checker didn't fail here, and the proof the fix works anyway.**  Main's unchanged checker
also passed 5/5 against the live page from this container: its data fetches return fast enough that
150 ms was always enough here.  To reproduce Budzilla's slower link, I ran scratch copies of both
checkers (deleted afterwards, never committed) against the local build with 300 ms added to every data
fetch:

- Old checker: failed 3 of 3 runs, 4 checks each: `3-team selection` and `QB cross-season pick renders`
  in both themes.  These are the first fetch of `team.json` and of an earlier season's pool file,
  the same failures Budzilla reported.
- New checker: passed 3 of 3, 0 failed checks.

## For Budzilla after the merge

Run `node tools/render_check.js https://cf.daboodah.com/` 5 times from your environment, the one where
the race showed up.  Expected: 5/5 pass.  If a `waited 5000 ms for …` line ever appears, it names the
step and the state it found; that would mean a fetch took over 5 seconds, not that the clock is off.
