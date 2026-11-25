# Spec: render_check.js — wait for async renders instead of fixed sleeps

Repo: daboodah-oss/college-football.  Tooling only: `tools/render_check.js`.
No page, pipeline, or data changes.  Small job; one branch, handoff doc as usual.

## Problem (measured 2026-11-25 by Budzilla, live page, jsdom)

The checker clicks a picker result to add a team, sleeps a fixed 150 ms, then
asserts the table rows and chart paths.  Adding a team is async: the page
fetches that team's data, then renders.  Instrumented re-runs of the exact
"3-team selection" steps (5 trials) reached the expected state (3 selected,
3 rows, 3 paths) in 50 ms in 3 trials and **250 ms in 2 trials** — so the
150 ms read lands too early about 40% of the time and the check fails on a
healthy page.  The click itself never failed (button connected, selection
always reached 3, zero page errors).

The same fixed-sleep pattern follows every async add/remove in the file
(cross-season pick 150 ms, cap-fill loop 120 ms, the Player tab's add/cap/×
steps), which is why the failure set rotates between runs ("3-team
selection", "cross-season selection", "QB cap holds at 4", "QB × removes a
player", "picker finds …", "all team chips off"): once one step reads early,
later steps inherit a shifted state and fail downstream.  The page is not
broken; the checker's clock is.

## Fix

- Add a small `waitFor(fn, what, timeoutMs = 5000)` helper: poll `fn` every
  50 ms until it returns true or the timeout passes; on timeout, record a
  failed check naming `what` and the state found, and continue (never hang,
  never crash the run).
- After every click that triggers an async fetch/render — team add,
  cross-season add, each cap-fill add, player add, player × remove, team ×
  remove — wait for the observable end state the following assertion checks
  (selection length via `CF_CHECK.state()`, and/or the row count) instead of
  the fixed sleep.  Keep a short settle sleep where the current code has one
  for non-async UI (theme toggle, tab switches) — those are synchronous.
- **No assertion is weakened**: every existing `ok(...)` condition stays
  exactly as written.  Only *when* the DOM is read changes.

## Acceptance

- `node tools/render_check.js` against a local build (`build_report.py
  --standalone`) and against the live page, 5 consecutive runs each: every
  interactive check passes 5/5, sections still 66/66, 0 script errors.
- The handoff doc reports the 5× results for both targets and lists every
  sleep replaced.
