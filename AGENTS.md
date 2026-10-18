# AGENTS.md — working conventions for college-football

This repo is a self-running pipeline for https://cf.daboodah.com/.  It must keep
working with no human or AI in the loop: GitHub Actions does everything on a
schedule, and the validation in `build_report.py` is the quality gate.  Follow
these rules so any helper (human, Claude, or otherwise) can safely contribute.

It generalizes the two school reports, `daboodah-oss/iu-report` and
`daboodah-oss/nd-report`, from one fixed school to every FBS team.  The
pipeline files, the validation rules, the design system and the chart engine
come from those repos (nd-report is the newer template).  A fix in shared code
(`update.py` checks, `lineChart()`, `render_check.js`, `check_manifest`) usually
ports between the three; port it deliberately, by diff.  What differs from the
reports is listed at the end of this file.

## Pipeline

1. `collect.py` runs the sections in order, each independent: the team registry
   per season (`registry_<season>`), the AP poll (`ap_poll`), every registry
   team's season (`team_<season>`), and the national player pools
   (`natref_<season>_<tab>`).  A failed section keeps its last verified data,
   is logged in `logs/collect.txt`, and is recorded in `data/last_run.json`.
2. `update.py` validates every row before it is stored.  It refuses bad data;
   nothing is stored then.
3. `build_report.py` (with `build_tabs.py`) re-checks every stored row and writes
   `index.html` from `template.html`.  **If any validation check fails, nothing
   is published**, and the workflow puts `data/` back as it was, so every data
   file the page can fetch has passed the build.
4. `.github/workflows/update.yml` ("Update report") commits `data/`,
   `index.html` and `logs/` to `main`, which GitHub Pages serves.

No AI or paid service is involved in the scheduled run.  Keep it that way.

## Seasons and sealing

`config.json` lists the seasons (2024, 2025, 2026).  The newest is the current
season, the only one that refreshes.  An earlier season is collected once and
sealed: a team season that matched cfbstats.com, a registry season with every
team joined, and a player pool stored with every game log read are never
collected again.  Adding 2027 means adding it to `config.json` `seasons` and
setting `current_season`; 2026 then seals itself on the next run once each team
season matches.

## Schedule

- Full refresh: Sunday and Wednesday, 10:47 AM Eastern (plus two backups).
- Game-window quick checks: every 20 minutes, Thu/Fri/Sat 4 PM–2 AM Eastern.
  A check reads ESPN's FBS scoreboard for today and yesterday (two requests)
  and exits in seconds unless some FBS game is final that is neither stored nor
  seen as final by the last full run (`data/last_run.json` `finals_seen`); then
  it runs the full pipeline.  It never runs the league collect when nothing is
  new, and sealed seasons are never collected by either path.

## Lanes and change control (Tier 2 repo)

- `main` is protected by the `main-protection` ruleset: no force pushes, branch
  deletions restricted, no pull-request requirement (the Actions bot commits
  straight to `main`).  Any merge to `main` deploys.
- **Pipeline (collect, update, build, workflow, config, template logic) is
  Claude's lane**, worked through Claude cloud sessions on a feature branch
  (`claude/...`), merged only after Jeff approves in chat.
- **Small display-only fixes** (copy, a colour, a CSS tweak) may be pushed to
  `main` by Budzilla at Jeff's request on this Tier 2 repo.  Anything that
  changes what is collected, validated or computed goes through Claude's lane.
- `data/`, `index.html`, `logs/` are written by "college-football bot" (the
  workflow) only.  Shared files (README.md, AGENTS.md): Claude owns them;
  Budzilla may fix wording at Jeff's request.
- Commit identities: Claude as `Claude <noreply@anthropic.com>`; Muse as
  `Budzilla <budzilla@noreply.github.com>`; the workflow as
  `college-football bot`.
- Anything that changes what the page shows its readers: Jeff's OK first, in
  BEFORE / AFTER form.

## Rules for contributors

1. **Pull before pushing.** The bot commits on schedule; push with
   `git pull --rebase` first to avoid collisions.
2. **Never hand-edit `data/*.json`.**  Data comes from `collect.py` through
   `update.py`.  To change what is collected, change `config.json` or the code.
3. **Never type an ESPN id.**  The registry joins cfbstats.com team names to
   ESPN ids by name.  When a team cannot be joined, add its cfbstats name to
   `config.json` `registry_aliases` (cfbstats name -> ESPN location name;
   `tools/resolve_espn_ids.py candidates NAME` lists the ESPN teams to choose
   from, in Actions), and let the next run prove it: a join counts only once
   that team's season matches cfbstats.com's season totals.
4. **Run the build and the render check locally before pushing** template or
   build changes: `python3 build_report.py --standalone --out /tmp/test.html`
   must print `OK`, and `node tools/render_check.js /tmp/test.html` (run from
   the repo root so the page can read `data/`) must pass (0 script errors,
   every section populated, TDZ scan clean).  A build that has not been
   executed is not done (see Lessons).
5. **Update this file and README.md when behavior changes.**
6. **Do not remove or let any step overwrite the `CNAME` file.**  It holds the
   custom domain (`cf.daboodah.com`).  The workflow only stages `data/`,
   `index.html` and `logs/`; keep it that way.
7. **Keep page output deterministic.**  No live API calls from the page (it
   reads only its own committed `data/*.json`), no AI-generated text in the
   scheduled build.
8. **No secrets in files.**  The scheduled workflow uses its own temporary
   `GITHUB_TOKEN`.  See the Secrets section of README.md.
9. The output check in `build_report.py` rejects `TODO`, `lorem`,
   `PLACEHOLDER`, and anything looking like a credential.  Don't add those.
10. **Leaderboards and ranked lists are always sorted by rank ascending,
    unranked last** (the picker's AP list and its search results included).
11. **Be polite to cfbstats.com.**  It answers 403 to a fast crawl.
    `collect.py` spaces cfbstats requests 1.5 s apart, backs off on a 403, reads
    each page once per run, and stops asking after three refusals in a row.
    Do not lower `CFB_GAP` or add cfbstats requests to the quick check.

## File map

- `config.json` — seasons, current season, the Team tab default (by name +
  season), the picker caps, page/bot identity, registry name aliases
- `collect.py` — section runner, HTTP (pacing, retries, cfbstats backoff), the
  league-wide QUICK check
- `collect_tabs.py` — team registry, AP poll, league-wide team seasons (ESPN
  schedule + box scores, cfbstats season cross-check)
- `collect_natref.py` — national QB / RB / WR pools per season (cfbstats boards
  plus each listed player's linked game log)
- `update.py` — row validation before storage, `SOURCE_EXCEPTIONS`
- `build_tabs.py` — Team and Player models; re-checks every stored row
- `build_report.py` — validation + model + render + `check_manifest` (no network)
- `template.html` — page; the model is injected at `/*__MODEL__*/null`
- `data/` — `registry.json`, `team.json`, `national_logs_<season>.json`,
  `freshness.json`, `last_run.json`
- `icons/` — PWA icons and the link-preview card, drawn by `tools/make_icons.py`
- `assets/fonts/` — Barlow Condensed and Public Sans (OFL), used only by
  `tools/make_icons.py` to set the link-preview card's text; the page loads
  Google Fonts, as the reports do
- `manifest.webmanifest` — web app manifest; checked by
  `build_report.py --standalone`
- `tools/render_check.js` — executes the built page in jsdom (light and dark);
  fails on any script error, empty section, broken picker, wrong leader box, or
  a TDZ-order helper
- `tools/resolve_espn_ids.py` — registry joins: `proofs` (offline) shows every
  join and whether cfbstats proved it; `candidates NAME` (network) lists ESPN
  teams for an alias
- `tools/gh_status.py` — recent workflow runs and repo files, no credential needed
- `logs/` — per-run logs, force-added to git

## Page behavior notes

- Two tabs, Team and Player; the tab shows in the URL hash (`#team`,
  `#player`; section links `#team-h2h` and so on).  Charts draw only for the
  visible tab and redraw when a tab opens.
- Every pick carries its season: a team pick is team + season, a player pick
  is player + season.  Pills, chips, table rows and game-log headings show the
  full "Name 2026"; chart end labels use the short form "IND ’26" (the ND
  report's `Carr ’25` / `Carr ’26` pattern).
- Team tab opens on `config.json` `default_teams` (Indiana 2026 vs Notre Dame
  2026).  The picker: season toggle + search; with an empty search on the
  current season it lists the AP Top 25 in rank order.  AP ranks annotate
  current-season rows only.  Cap: `caps.teams`.
- Player tab: QB / RB / WR switcher; each position keeps its own picks.  Opens
  on the current season's passing (rushing, receiving) yards leader and
  runner-up, derived from the stored pool at build time.  Cap: `caps.players`.
- Unequal game counts: every table total runs through that selection's own
  games played, with G printed; charts line selections up by game number.
  Leader boxes: best value wins (fewer is better only for Points allowed); no
  box when every compared entry ties.
- Line slots in pick order: `--s1`..`--s3` solid, `--s4`..`--s6` dashed (and
  hollow markers), so colour plus line style separate every pair in both
  themes.  A removed pick frees its slot; the survivors keep their colours.
  National Top 3 lines are gray (`--field`), solid / dashed / dotted for #1 / #2
  / #3, chips off until tapped, chosen per stat and per season (a season toggle
  inside the group).
- Chips and pills show the name (+ season) only, underlined in the line's colour
  and style (`.un` / `.pu`); ON is full opacity, OFF is dimmed; all off shows a
  friendly empty state.  Tables keep their line swatches; table numbers are in
  ink, not the series colour.
- Chart tooltips are sticky: a tap or click in a chart pins the pop-up; a tap
  outside any chart dismisses it (one shared tip element and a guide registry
  in `lineChart()`; pointerleave does not hide it).
- Data loading: the built page embeds the registry index, the pools'
  leaderboard lines, and the default picks' rows.  The rows of anything else
  come from `data/team.json` and `data/national_logs_<season>.json` on the same
  origin, fetched once (cache-busted with each file's hash) when the reader
  first focuses a search box.
- Theme: follows `prefers-color-scheme` unless the reader picks the header
  sun/moon toggle, which sets `data-theme` on `:root` and persists in
  localStorage (`cf-theme`).  Charts redraw on `data-theme` changes.

## Validation rules (the reports' discipline, unchanged)

- Match or drop, never fabricate.  A player whose game log does not equal his
  leaderboard line is dropped and named; a team season that disagrees with
  cfbstats beyond the yardage tolerance is refused and named.
- The one rating tolerance: a published passer rating may differ from the
  NCAA formula by up to 0.15, on that single comparison only (QB game logs).
  The `update.compare` yardage tolerances for ESPN-vs-cfbstats season totals
  (teams max(5, 0.2%), players max(3, 0.5%)) are kept exactly; counts must
  match exactly.  Do not widen any check.
- `SOURCE_EXCEPTIONS` in `update.py`: one team, one season, one stat, pinned to
  the exact recorded ESPN / cfbstats pair, applied only when both values match
  it, named in the run log.  The one entry is nd-report's documented Notre Dame
  2024 `third_att` (185 vs 184, the 2024-09-07 Northern Illinois box score).
  Add an entry only with the same kind of per-game evidence from an official box
  score.  It is not a general tolerance.

## Differences from the school reports

No home team, no `roster.json`, no QB backfill, no Heisman cohort or odds, no
next-game panel, no school RB/WR tabs.  `config.json` replaces `roster.json`.
`data/team.json` has every FBS team (keyed by ESPN id) with no per-game player
arrays, and the AP block holds the full Top 25.  `data/registry.json` and
`data/national_logs_<season>.json` (one pool file per season) are new.  The
quick check is league-wide (ESPN FBS scoreboard).  cfbstats requests are paced
(rule 11).  The page fetches data files at runtime instead of embedding
everything.  Neutral slate branding (#24303F), icons drawn from a football mark.

## Lessons learned the hard way (inherited from the IU and ND repos)

- A byte-identical push once shipped a blank IU page for about 2.5 days: a
  `const` helper was used before its definition (TDZ ReferenceError) and killed
  the page script.  The build passed; only executing the page shows it.  Run
  `tools/render_check.js` on every template change and against the live page
  after every merge.
- Never estimate a missing national line.  Match or drop, and name the drop.
- cfbstats.com blocks a fast crawl with 403s (first league-wide run,
  2026-10-18: about 80 pages in, every request refused).  Pace it.
- Docs that go stale cause near misses; update them with the change.
