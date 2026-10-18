# Claude Code cloud-session spec — College Football comparison page (cf.daboodah.com)

Paste everything below the line into a NEW Claude Code **cloud** session, with the repo
**daboodah-oss/college-football** picked at session start (Default cloud environment, GitHub App attached).
Do NOT start this in a Claude Project (chat project) — Projects cannot push.

---

## Standards header (read first, applies to the whole task)

- You are building in repo **daboodah-oss/college-football**. **This repo may not exist yet.**
  As of this spec being written (2026-10-18) it does **not** exist — Budzilla creates it and applies
  the Tier 2 `main-protection` ruleset (force pushes blocked, branch deletions restricted, no PR
  requirement because the Actions bot commits straight to `main`) before the session is normally
  started. **First action of the session: confirm the repo exists, that `main` is present, and that
  this session can push a branch to it. If the repo is missing or you cannot push, STOP and say so
  before building anything. Do NOT create the repo yourself, do not build a patch, a zip, or
  instructions for Jeff to upload by hand.**
- Work on your own feature branch and push it. **Do NOT merge to `main`, do NOT enable/deploy
  anything to production, and do not touch any other repo for writes.** Merging happens only after
  Jeff approves in chat. Note: cloud sessions auto-name their branches — report the actual branch
  name you pushed.
- **No manual steps for Jeff.** Everything below must be doable by you in the session plus GitHub
  Actions. If a step genuinely cannot be automated, build everything up to that step, commit the
  repo-side files for it, and list it as a single named remainder in your final report — do not make
  it a mid-build errand. (One known repo-side file: the `CNAME` file for `cf.daboodah.com` — commit
  it. The matching Cloudflare DNS record is *not* yours to create; if it is not already live when
  you finish, list it as the single remainder, exactly as the ND build did.)
- Follow the conventions in daboodah-oss/ai-build-standards (v5.3, including the “Installed web
  apps” manifest standard) and mirror the contributor conventions in the template repos' AGENTS.md,
  adapted as described below.
- **Jeff's decisions in the “Settled decisions” section are locked. Do not re-litigate, “improve,”
  or silently substitute them.** The only design questions open to you are the two in “Open
  questions for Claude” — and both must be answered explicitly in your final build summary.
- When you finish, report: branch name, what you built, the workflow run result on the branch if you
  triggered one, your answers to the two open questions, every acceptance check below with
  pass/fail against real collected data, and any remainders. Do not claim a check passed that you
  did not actually run.

## Task

Build **cf.daboodah.com**: Jeff's standalone college-football comparison page — the “fun page.”
It generalizes the two school reports (IU Report, https://iu.daboodah.com/, repo
**daboodah-oss/iu-report**; ND Report, https://nd.daboodah.com/, repo **daboodah-oss/nd-report**)
from one fixed school to all of FBS:

- A **Team tab**: pick teams and compare them — stat table + per-game charts. This is the reports'
  Team tab generalized from a fixed set (home team + AP Top 5) to every FBS team.
- A **Player tab**: pick players and compare them — position-scoped (**QB / RB / WR**), standard
  comparison charts. This is the reports' compare-chart experience generalized from fixed school
  players + a national pool to the national pool itself.

This is a **generalization task, not a redesign and not a new invention**: architecture, pipeline
discipline, validation, design system, and page mechanics come from the two reports, adapted only
where this spec says. Where the reports differ, **nd-report is the newer template** — prefer its
versions of shared tooling (notably `tools/render_check.js`).

## Settled decisions (Jeff, 2026-10-17 — locked, verbatim in substance)

- **Domain: cf.daboodah.com** (chosen over football.daboodah.com).
- **Repo: daboodah-oss/college-football** (chosen over daboodah-oss/cf), Tier 2 branch protection.
- **Seasons at launch: 2024 + 2025 + 2026.** The 2024 and 2025 seasons are finished and **static** —
  collected once, sealed, never recollected; **only 2026 refreshes** on schedule.
- **Team tab: multi-team comparisons — more than 2 teams.** (The exact maximum is Open Question 1.)
  **The stat set mirrors the IU/ND Team tabs exactly** — no additions, no cuts (stat list below).
- **Player tab: QB / RB / WR only at launch.** Position-scoped picker over the **validated natref
  pools** (union of roughly the top 20 per tracked stat, per position, per season; **match-or-drop**
  validation; **0.15 tolerance on the passer-rating comparison only**).
- **Default on open: Indiana vs Notre Dame (2026) preselected** on the Team tab — the page opens
  populated, charts drawn.
- **Refresh: same schedule as the IU/ND reports** — full refresh Sun/Wed 10:47 AM ET plus
  20-minute checks in the Thu/Fri/Sat game windows (exact crons below).
- **Season is part of every selection.** A team pick is *team + season* and a player pick is
  *player + season* (a player's pool entry belongs to one season), so cross-season comparisons —
  Indiana 2026 vs Notre Dame 2024, a 2025 QB vs a 2026 QB — work exactly like same-season ones.
  Legends, pills, and table headers must always carry the season when it is needed to tell two
  selections apart (the ND report's `Carr ’25` / `Carr ’26` shorts are the template pattern).
- Linking to this page from the IU and ND reports is a **follow-on in those repos, after this page
  is live — not part of this build** (see Out of scope).

## Template sources — the live repos, as verified 2026-10-18

Clone/read **daboodah-oss/iu-report at its current `main`** and **daboodah-oss/nd-report at its
current `main`**. (iu-report was renamed from `iu-qb-report` and its domain from qb.daboodah.com to
iu.daboodah.com on 2026-10-17; the ND spec's references to the old names are stale — the repos
themselves are the truth.) The two trees are near-identical; verified inventory:

- Pipeline: `collect.py`, `collect_tabs.py`, `collect_natref.py`, `build_report.py`, `build_tabs.py`,
  `update.py` (validated data editors / quality gate), `requirements.txt`
  (`requests`, `pandas`, `lxml`, `html5lib`, `beautifulsoup4`)
- Page: `template.html` → built `index.html` (via `build_report.py --standalone`)
- Data (committed, in-repo): `data/games.json`, `data/skill.json`, `data/skill_national.json`,
  `data/team.json`, `data/national.json`, `data/national_logs.json`, `data/cohort.json`,
  `data/heisman.json`, `data/freshness.json`, `data/last_run.json`; `roster.json` at root
- Logs: `logs/collect.txt`, `logs/build.txt` (`data/last_run.json` records per-section failures)
- Workflow: `.github/workflows/update.yml` (“Update report”)
- Site: `CNAME`, `manifest.webmanifest`, `icons/` (favicon-32, 192, 512, maskable-512, apple-touch,
  og.png), a root logo PNG (`iu-logo.png` / `nd-logo.png`), `tools/make_icons.py`
- Docs: `README.md`, `AGENTS.md`
- **nd-report extras (port these):** `tools/render_check.js` (the jsdom render check, with a TDZ
  scan — see Render-verify), `logs/render_check.txt`, `tools/resolve_espn_ids.py`,
  `tools/gh_status.py`, and the `SOURCE_EXCEPTIONS` mechanism in `update.py` (see Validation).
  nd-report also carries self-hosted font files under `assets/fonts/` but its template still loads
  Google Fonts like iu-report's — mirror the template behaviour, do not cargo-cult the unused
  files.

What carries over **unchanged in spirit**: per-section independent collection (a failed section
keeps its last verified data, is logged, and is recorded in `data/last_run.json`); `update.py`
refusing bad data before anything is stored; `build_report.py` recomputing everything from stored
rows and publishing nothing if validation fails; the workflow gating on `.nochange`; no AI or paid
service anywhere in the scheduled run.

What does **not** carry over: anything school-specific. There is no home team, no `roster.json`
QB list, no Heisman cohort, no BetMGM odds, no school skill tabs. Replace `roster.json` with a
small page config (name it `config.json` unless you have a better-documented idea): the season
list `[2024, 2025, 2026]`, the current season (2026), the default Team-tab selection
(Indiana 2026, Notre Dame 2026), bot/page identity strings, and whatever the branding proposal
needs. Document it in README.md and AGENTS.md the way the reports document roster.json.

## League-wide team data — how the current pipeline really works, and the generalization

Read `collect_tabs.py` (`team_seasons`, `team_job`, `espn_completed`, `box_row`, `cfb_team_ids`,
`cfb_team_totals`) and `update.py` (`team_season`, `check_team_game`, `compare`, `season_sums`)
before designing this. The current shape, verified from the live repos:

- `data/team.json` is `{teams: {espn_id: {name, seasons: {season: {games[], complete,
  retrieved_at, check, cfbstats_url}}}}, ap: {...}}`. Each game row carries: `event, date, opp,
  opp_id, site, pf, pa, result, total_yds, rush_yds, pass_yds, to_lost, to_gained, third_conv,
  third_att` — plus, **for the home team only**, per-game `rush`/`rec` player arrays (collected
  with `with_players=(tid == home)`).
- Game rows are **ESPN-first**: ESPN team schedule JSON for finals/scores + ESPN game-summary
  (box score) JSON for the stat line. **cfbstats is the cross-check, not the source of the rows:**
  season totals from the team's cfbstats page (`cfb_team_totals`) must reconcile with the summed
  ESPN rows once cfbstats has posted the same number of games (`update.compare`: counts exact;
  season yardage within max(5, 0.2%) for teams — a difference inside tolerance is stored as a note
  shown on the page, anything larger is **refused and nothing is stored**).
- The cfbstats team id for a team is resolved by name from the season's cfbstats team index
  (`https://cfbstats.com/{season}/team/index.html`, see `cfb_team_ids`), with the reports'
  `TEAM_FIX` name-normalization table for the mismatches.
- Today the store holds only **5 distinct teams**: the home team (all three seasons) + the current
  AP Top 5 (current season only) — `data/team.json` is ~88 KB in iu-report, ~90 KB in nd-report.
  A finished season that matched cfbstats is **sealed**: `team_job` returns immediately and it is
  never recollected.

Generalize it to **every FBS team × 2024, 2025, 2026**:

1. **Build a team registry** (committed data or config, documented in the README): every team on
   the cfbstats team index for each season — verified counts at spec time: **134 teams (2024),
   136 (2025), 138 (2026)**; do not hard-code 136, enumerate per season and report the actual
   counts. Each registry entry joins the **cfbstats id** (from the index) to the **ESPN team id**
   (the `team.json` key space; e.g. Indiana = ESPN `84` / cfbstats `306`, Notre Dame = ESPN `87`).
   Prove the join per team — a wrong join shows up as a failed cfbstats cross-check, which is the
   proof mechanism, so a team whose seasons cannot be cross-checked is a named failure in the run
   log, never a silently accepted mapping. List any team you could not map in your final report.
2. Collect each team-season exactly the way `team_job` does (ESPN schedule + box-score rows,
   cfbstats season-total cross-check, `update.py` validation before anything is stored), with one
   change: **`with_players` off for every team** — no per-game `rush`/`rec` player arrays in this
   repo's team store (in the reports those arrays exist only for the home team and feed its skill
   tabs, which this page does not have). Size math from the live data: a team-season without the
   player arrays is ~2 KB per 7 games (~4 KB for a full season), so the full league-wide store
   should land around **1.5–2 MB** across the three seasons. Report the actual size.
3. **2024 and 2025 collect once and seal** under the same rule as the reports (complete +
   cfbstats-matched → never recollected). Only 2026 team-seasons refresh. The AP poll block stays
   in the store exactly as the reports keep it (current poll, week + release date labelled) — on
   this page it annotates the picker (below); it is not a fixed set of comparison entries.

## Player pools — generalize `collect_natref.py` per season

Verified current shape (`collect_natref.py`, `data/national_logs.json` in both reports):

- Per position tab — QB (cfbstats category `02`, page `passing`, positions `[QB]`), RB (category
  `01`, `rushing`, `[RB]`), WR (category `03`, `receiving`, `[WR, TE]`) — for **each tracked stat**,
  take the cfbstats national leaderboard, filter to the tab's positions, and take the **top 20**
  (`POOL_N = 20`); the union across that tab's stats is the pool. Tracked stats — QB: `yds, td,
  rating, pct, att`; RB: `yds, td, ypc, ypg, att`; WR: `yds, rec, td, ypr, ypg`. Each stat also
  records its **top 3** (`TOP_N = 3`) and the full rank `order`.
- Each player's game log is fetched **via the link on his leaderboard row — never by name
  matching** — and stored **only if** the log's game count equals the leaderboard `G` and its
  totals equal the leaderboard line (QB logs: **every game's passer rating must also match the
  NCAA formula**). Anything else is **dropped and named** (`dropped` list + run log). A stored log
  is reused until that player's leaderboard line changes.
- Current store: a **single season only** (2026), keyed `{qb, rb, wr}` with a `season` field per
  tab — 49 QBs / 52 RBs / 55 WRs and ~219 KB in iu-report (~216 KB in nd-report).
  `build_tabs.natref()` **refuses (renders “pending”) any tab whose stored season is not the
  current season** — that gate is the main structural thing you must change.
- The reports **exclude the home team** from the pool (`team != "Indiana"` / Notre Dame). This
  page has no home team: **exclude nobody.**

Generalize to **one pool per season (2024, 2025, 2026) per position**, with the same stats,
`POOL_N`, validation, and drop discipline. Storage shape is your call — per-season files
(e.g. `data/national_logs_2024.json`) or a season key above the existing structure — but:
the build must validate **every** season's pool the way `build_tabs.natref()` validates the
current one (game count and totals against each player's leaderboard `line`, dates ordered and
unique, every `top`/`order` id resolving to a stored player), and **2024/2025 pools seal after
their first successful collect** exactly like finished team seasons. Expected scale: roughly
150 players per position across the three seasons, ~650 KB of pool data total. Report actuals.

## The Team tab

- **Picker:** search/select over the registry — every FBS team, every season (2024/2025/2026).
  Selecting a team adds it **with a season** (defaulting to 2026); the same school may be added
  twice in different seasons. Annotate picker rows with the current AP rank where one exists
  (from the stored poll). Selections are removable pills, labelled *Team + season* (season always
  shown — it is part of the pick). **Maximum simultaneous selections: your answer to Open
  Question 1** — enforce it in the picker with a friendly message at the cap.
- **Default on open: Indiana 2026 vs Notre Dame 2026 preselected**, table and charts drawn.
- **Stat table (head-to-head):** exactly the reports' Team-tab stat set — from
  `build_tabs.TEAM_STATS`, in order: **Record, Points scored, Points allowed, Total yards,
  Rushing yards, Passing yards, Turnover margin, Third-down %** — season totals through each
  selection's games, with the per-stat **leader highlighted** under the same rule as the reports
  (best value wins, “higher is better” except Points allowed; no highlight when every compared
  entry ties). **Tables keep their line swatches** (see Design system). Note the reports compare
  at *equal game counts* (totals through the first N games); with arbitrary team+season picks,
  state in the Method section how unequal game counts are handled — mirror the reports
  (totals through each selection's own games played, game counts printed in the table header)
  unless you argue otherwise in your summary; do not silently mix the two rules.
- **Per-game charts:** the reports' Team chart set — **Points scored, Points allowed, Total yds,
  Rush yds, Pass yds, TO margin, 3rd down %, Wins** — per-game lines with the cumulative /
  per-game treatment the reports' compare charts use, toggle chips for every selected
  team-season, sticky tooltips (below).
- **Game logs:** each selected team-season's game-by-game rows (date, opponent, site, result,
  and the stored stat line), as the reports render team game rows.
- A **Method and sources** section, like the reports'.

## The Player tab

- **Position scope first: QB / RB / WR** (a position switcher, defaulting to QB). The picker
  searches **only that position's validated pools**, across all three seasons; a pick is
  *player + season* (the same player may appear in two seasons as two distinct picks — label
  them with the season, ND `Carr ’25` / `Carr ’26` pattern). Picker rows show name, team, and
  season. **Maximum simultaneous selections: your answer to Open Question 1.**
- **Default on open (QB):** preselect the 2026 pool's passing-yards leader and runner-up
  (derived from the collected data — do not hard-code names) so the tab opens populated; name
  them in your summary.
- **Comparison table + charts:** the reports' compare experience for that position — the stat
  sets from `build_tabs.SKILL` / `build_tabs.NATREF`: QB — passing yards, TD, passer rating,
  completion %, attempts (chart draws `yds, td, int, rating, pct, att`); RB — rushing yards,
  TD, yards/carry, yards/game (+ carries); WR — receptions, receiving yards, TD, yards/catch,
  yards/game. Per-game and cumulative lines with the reports' stat switching, toggle chips, and
  sticky tooltips.
- **National Top 3:** keep the reports' third compare element — for the currently viewed stat,
  the top 3 of that stat's pool for the relevant season, as toggleable reference lines (gray
  solid/dashed/dotted for #1/#2/#3, chips start off), dynamic per stat.
- **Game logs** for each selected player (from the stored, validated logs only — a player whose
  log was dropped is not pickable, and dropped players are named in the run log as in the
  reports).

## Validation — copy the reports' discipline verbatim

- **Match-or-drop, never fabricate.** Sources: ESPN (team schedules, box scores, AP poll),
  cfbstats (team season totals for cross-checks, national leaderboards + linked game logs).
- The ONE rating tolerance: a published passer rating can round 0.1 off the NCAA formula —
  **tolerance 0.15 on that single comparison only**, everywhere it occurs in the templates
  (the ESPN gamelog check in `collect.py` and the QB check in `collect_natref.py`). **Do not
  widen any other check.** The `update.compare` yardage tolerances (teams max(5, 0.2%), players
  max(3, 0.5%)) are existing template behaviour for ESPN-vs-cfbstats season totals — keep them
  exactly; do not extend them to counts, which must match exactly.
- **Known-source-error exceptions:** nd-report's `update.py` carries a `SOURCE_EXCEPTIONS`
  mechanism — an entry pinned to one team / season / stat key with the **exact** recorded
  ESPN-vs-cfbstats pair; it applies only when both values match the record exactly, and it is
  named in the run log when applied. Port the mechanism. Add an entry only for a discrepancy you
  can document the same way (a published source error), and name every entry you add in your
  summary. It is not a general tolerance.
- A failed section keeps its last verified data, is logged in `logs/collect.txt`, and is recorded
  in `data/last_run.json`; the workflow's “Report problems” step deliberately fails the run if
  any section failed, as in the templates.

## Workflow — “Update report” (`update.yml`), same schedule as the reports

Copy either template's workflow; the two are identical except the bot identity
(`iu-qb-report bot` / `nd-report bot` → **`college-football bot`**). The schedule, verbatim from
the live files (full refresh Sun/Wed 10:47 AM ET with two UTC backups; 20-minute game-window
checks Thu/Fri/Sat 4 PM–2 AM ET; `workflow_dispatch` with the `save_raw` input):

```yaml
schedule:
  - cron: "47 14 * * 0,3"
  - cron: "47 16 * * 0,3"
  - cron: "47 20 * * 0,3"
  - cron: "*/20 20-23 * * 4,5,6"
  - cron: "*/20 0-6 * * 5,6,0"
```

Collect → gate on `.nochange` → `build_report.py --standalone` → commit `data` + `index.html`
(and `logs`) to `main` → “Report problems” fails the run if collect or build failed — all as in
the templates. GitHub Pages serves `main`, root, via the `CNAME` file (`cf.daboodah.com`).

**One mechanism you must redesign: the game-window QUICK check.** In the templates, QUICK mode
answers “has *the home team* just gone final?” (`collect.py`: stored 2026 game count vs ESPN
finals) and writes `.nochange` otherwise. There is no home team here. Replace it with a league-
wide check that is still **cheap — a handful of requests, exits in seconds** (e.g. ESPN's
scoreboard for the current week, or an equivalent single source of “finals since the stored
data-through date”) and that triggers the full update when **any** FBS final is newer than what
is stored. It must never run the full league collect on a 20-minute tick when nothing is new.
State your trigger design in your summary. Full refreshes (Sun/Wed) always collect 2026 in full;
sealed 2024/2025 data is never recollected by either path.

## Design system — mirror the reports

- **Barlow Condensed** display type (Public Sans body), sections with eyebrow + big uppercase
  titles, full-width tab titles `clamp(30px, 6.5vw, 54px)`; **sticky tab bar** (Team / Player)
  with `scroll-margin-top` on every anchored section so titles never hide under the bar.
- **Dark/light theme toggle**: follows OS, header override remembered in localStorage (use a
  page-specific key, e.g. `cf-theme` — the reports' key is `qb-theme`).
- **Chips/pills are name-only**: player/team name (+ season), with a **tight underline in the
  line's colour and style** via the templates' `.un` / `.pu` treatment — no swatch inside pills.
  ON = full opacity, OFF = dimmed; tap toggles the line; **friendly empty state** when everything
  is off. **Tables keep their line swatches** — Jeff's explicit standing call; only legends,
  chips, tooltips, and game-log headings use underlines.
- **Sticky chart tooltips**: tap/click in a chart pins the pop-up; tap outside any chart
  dismisses it (one shared tip element + guide registry in `lineChart()`; `pointerleave` does
  NOT hide). Copy the shipped template behaviour exactly.
- **Every leaderboard / ranked list sorted by rank ascending, unranked last** — standing rule,
  always.
- Line assignment: follow the templates' palette-slot logic (distinct hues, solid then
  dashed/dotted as selections multiply, gray reserved for National Top 3 reference lines on the
  Player tab). Every colour/style combination you use must stay legible and distinguishable in
  **both** light and dark themes — this feeds Open Question 1.
- Collapsible chip categories with the templates' disclosure treatment, as shipped.

## Web app manifest (ai-build-standards v5.3)

Replicate the templates' manifest + build validation (`check_manifest` in `build_report.py`):
`manifest.webmanifest` linked from the built page, `display: standalone`, `id`/`start_url`/
`scope` `/`, icons 192 / 512 / maskable-512 whose declared sizes match the actual PNGs, and a
`theme_color` that **matches the page's theme-color meta tag and actually appears in the built
page** (the validator enforces all of this — do not weaken it). Name, short name, description,
theme colour, and the icon mark all come from your **Open Question 2** branding proposal.
Icons: adapt `tools/make_icons.py` — generate the set from a simple neutral mark drawn in code
(do not scrape or hotlink any school's logo).

## Open questions for Claude (Jeff's instruction — answer BOTH in your build summary)

1. **Comparison caps.** Propose the **maximum number of teams** comparable at once on the Team
   tab and the **maximum number of players** at once on the Player tab, with reasoning that
   explicitly weighs: chart readability (how many lines stay followable), how many **distinct
   line colours × styles** the design system can honestly offer in both themes, **data size /
   built-page weight** (see the size warning below), and **mobile UX** (table column count,
   pill wrapping, tap targets). Build the caps you propose into the pickers. Jeff approves or
   adjusts them at the merge gate — a well-argued number, not a guess, is the deliverable.
2. **Neutral branding.** Propose the page's identity: masthead name (working title “College
   Football”), browser-title pattern, manifest `name` / `short_name` / description, and a
   **neutral colour scheme — not IU crimson (`#990000`), not ND navy/gold
   (`#0C2340` / `#AE9142`)** — with the primary/theme colour and the line palette worked out for
   **both light and dark themes**, plus the code-drawn icon mark. Build with your proposal and
   flag it as an explicit approval item in your summary; Jeff approves or redirects it at the
   merge gate (branding is display-only and cheap to change after).

**Size warning (feeds Question 1):** the templates embed the entire model as a JSON blob in
`template.html` → `index.html` (~286 KB built for a whole school report). This page's full data
is an order of magnitude larger (~2 MB+ of team + pool JSON). State in your summary what the
built page weighs and how the pickers get their data (embedded model vs fetching the committed
`data/*.json` from the same Pages origin at runtime are both acceptable); a multi-megabyte
first load with no reasoning will not pass review.

## Docs

Write fresh (adapting the templates' structure, not their school text): `README.md` (live URL
https://cf.daboodah.com/, tab descriptions, config/team-registry how-to, refresh schedule,
data-file inventory) and `AGENTS.md` (contributor conventions and lanes: pipeline = Claude's lane
via cloud sessions on feature branches, merged only after Jeff approves in chat; small display-
only fixes may be pushed to `main` by Budzilla at Jeff's request on this Tier 2 repo; never
hand-edit `data/*.json`; never overwrite the `CNAME` file; run the build + render check before
pushing template/build changes). Grep out every school-specific string before pushing (Indiana,
Hoosier, Notre Dame, Fighting Irish, Cignetti, Freeman, `990000`, `0C2340`, `iu.daboodah`,
`nd.daboodah`) **except** legitimate data mentions: team names in the registry/data, and the
locked default selection (Indiana vs Notre Dame) in config, docs, and Method text.

## Render-verify (mandatory — the reports' hardest lesson)

A byte-identical push once shipped a blank IU page for ~2.5 days (a `const` helper used before
its definition — TDZ ReferenceError — killed the page script). Therefore:

1. **Port `tools/render_check.js` from nd-report** and adapt its checks to this page: execute the
   built `index.html` in jsdom, in light and dark theme, and confirm **every section populates
   with zero script errors**; both tabs open; the Team tab renders the **default Indiana vs
   Notre Dame (2026)** comparison on first load; pickers add/remove selections and the table +
   charts re-render; chips toggle; a chart tap pins the tooltip and a tap outside dismisses it;
   the manifest link is present. Keep its **TDZ scan** (first-call vs definition order for every
   `const`/`let` helper in the page script).
2. Report the section count and error count in your final report (the ND live page's benchmark
   was 56/56 sections, 0 errors). Budzilla will re-run the same check against the live page after
   merge — your in-session check does not replace it, and a build that has not been executed is
   not “done.”

## Out of scope (explicitly do NOT build)

- **Head-to-head tabs on the IU/ND reports**, and the **links from iu.daboodah.com /
  nd.daboodah.com to cf.daboodah.com** — follow-on work in those repos, after this page is live.
  Do not write to those repos at all.
- Positions beyond **QB/RB/WR**; team stats beyond the reports' Team set; any new stat category.
- **Heisman cohort, BetMGM odds**, school scorecards, next-game panels — school-report features.
- Creating the repo, its branch-protection ruleset, GitHub Pages enablement settings, or the
  Cloudflare DNS record (repo-side `CNAME` file only; see Standards header).

## Acceptance checklist (report each, pass/fail, from real collected data)

- [ ] Repo existed at session start and the branch pushed (branch named); `main` untouched; if the repo was missing, you stopped and said so instead of building
- [ ] Team registry covers every cfbstats-index team for 2024/2025/2026 (actual counts reported; expected ≈134/136/138); every ESPN↔cfbstats join proven by its cross-check or the team named as unmapped/failed
- [ ] League-wide `team.json`: every team-season stored with NO per-game player arrays; 2024/2025 complete + cfbstats-matched and sealed; file size reported
- [ ] Player pools for **all three seasons** × QB/RB/WR: pool sizes reported (2026 sanity range ≈49 QB / 52 RB / 55 WR); every stored log matches its leaderboard line; every dropped player named in the run log / `dropped` lists
- [ ] Team tab: opens on Indiana 2026 vs Notre Dame 2026; stat table shows the 8 mirrored stats with correct leader highlighting and swatches; per-game charts + game logs render for multi-team, multi-season selections (demonstrate at least one 3+ team and one cross-season selection in-session)
- [ ] Player tab: position-scoped pickers (QB/RB/WR) over the pools; default QB preselection populated (players named); compare table/charts, National Top 3 references, and game logs all render; cross-season player picks work
- [ ] Picker caps enforced (Open Question 1 numbers), with the friendly at-cap message working
- [ ] Workflow carries the exact template crons, the redesigned league-wide QUICK trigger (design stated), and the `.nochange` gate; a branch workflow run result reported
- [ ] Manifest validates via the build's `check_manifest`; theme toggle works; leaderboards in rank order, unranked last
- [ ] Built page executes in jsdom (ported render check): all sections populated, 0 script errors, TDZ scan clean; built-page weight reported
- [ ] Open Questions 1 and 2 answered in the summary with reasoning (caps + branding, incl. light/dark palette)
- [ ] No school-specific strings outside legitimate data/config/default mentions (grep list in Docs)
- [ ] Final report includes any `SOURCE_EXCEPTIONS` added (with the documented source error) and any remainders (no Jeff errands)

---
End of spec.
