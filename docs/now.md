# Now: college-football

Updated 2026-11-11 08:20 ET by Budzilla.

## Current state
- Live at https://cf.daboodah.com/ with four tabs: Team, Player, Conferences, Playoff. The pipeline
  (Sun/Wed full refresh + Thu/Fri/Sat game-window quick checks) runs from main as before.
- Conferences tab (added 2026-11-11, Jeff's voice request): per-season non-conference standings and a
  full conference-vs-conference matrix, computed at build time from the stored team rows
  (build_conferences.py) with per-season membership from ESPN standings (conferences.json, repo root);
  the computed dataset is written to data/conferences.json on every build. 2026 through Nov 7: SEC owns
  the best non-conference mark (38-2); SEC leads the Big Ten 2-1 in their only three meetings.
- Playoff tab (added 2026-11-11, Jeff's voice request): weekly CFP critique. Snapshots in data/cfp.json
  are appended by the new cfp_rankings collect section only when the committee's Top 25 changes, so the
  Wednesday run lands each Tuesday release once. Our Top 25 is cfp_model.py's blend (45% capped-margin
  SRS, 30% Colley, 25% resume points; assessment in docs/cfp-model.md). Seeded with Week 11
  (Nov 10, 2026): agreement 84%, overlap 23/25, Top 12 overlap 9/12, our No. 1 Texas vs the committee's
  Georgia. The Nov 3 (Week 10) release could not be backfilled — ESPN's rankings endpoint serves only
  the current poll (its week parameter is ignored).

## Open threads
- The 56 refused team seasons (named in logs/collect.txt) remain as they were; their games still count
  on the Conferences tab from their opponents' stored rows.
- Links from iu.daboodah.com and nd.daboodah.com to cf.daboodah.com, and head-to-head tabs on the two
  reports reusing this page's comparison design, are still follow-ons, not yet built.
- The next CFP snapshot (Week 12) should land on its own with the Wednesday Nov 18 run after the
  Tuesday Nov 17 reveal; worth a glance at data/cfp.json then to confirm the append happened.

## Agreements
- Specs for Claude Code cloud sessions are committed in-repo first (docs/claude-spec-<project>.md); the
  prompt Jeff carries is one short paragraph pointing at the file — never a paste.
- The two 2026-11-11 tabs were built and pushed directly by Budzilla at Jeff's explicit request in the
  voice call, as one build with one render-check pass (54/54 sections, 0 script errors, light and dark).
