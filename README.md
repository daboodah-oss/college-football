# College Football (cf.daboodah.com)

**START HERE.**  A standalone comparison page for every FBS team and the national-leader quarterbacks,
running backs and receivers, across the 2024, 2025 and 2026 seasons.  It runs itself: GitHub Actions
collects, validates and publishes on a schedule, with no AI or paid service in the loop.  Pipeline code
is Claude's lane (feature branches, merged after Jeff approves in chat); `data/`, `index.html` and
`logs/` are written only by the workflow ("college-football bot").  Never hand-edit `data/*.json`, never
overwrite `CNAME`, never type an ESPN id.  Conventions and lanes: [AGENTS.md](AGENTS.md).

Live page: https://cf.daboodah.com/ (GitHub Pages from `main`, repo root; `CNAME` holds the domain; the
Cloudflare DNS record is a DNS-only CNAME to `daboodah-oss.github.io`).

It generalizes the two school reports in `daboodah-oss/iu-report` and `daboodah-oss/nd-report` from one school to all of FBS.  The pipeline,
validation, design system and chart engine are theirs; see AGENTS.md for what differs.

## The two tabs

- **Team:** pick up to 6 team-seasons (any FBS team, 2024, 2025 or 2026; the same school can be added in
  two seasons) and compare them.  Opens on **Indiana 2026 vs Notre Dame 2026**.  The stat table is the
  reports' Team set, in order: Record, Points scored, Points allowed, Total yards, Rushing yards, Passing
  yards, Turnover margin, Third-down %, with the leader boxed (best value wins; fewer is better only for
  Points allowed; nothing boxed when everyone ties).  Every total runs through each team's own games
  played, with G printed, so seasons of different lengths compare on their seasons to date.  Per-game
  charts (Points scored, Points allowed, Total yds, Rush yds, Pass yds, TO margin, 3rd down %, Wins) as a
  running total or per game, a chip per team to toggle its line, game-by-game logs, and Method and
  sources.  The picker lists the current AP Top 25 in rank order when the search is empty, and annotates
  current-season rows with the AP rank.
- **Player:** QB / RB / WR.  Pick up to 4 player-seasons from that position's validated national pools,
  across all three seasons (the same player in two seasons is two picks).  Opens on the current
  season's yards leader and runner-up at that position, read from the data.  Table: QB passing yards,
  TD, passer rating, completion %, attempts; RB rushing yards, TD, yards per carry, yards per game,
  carries; WR receptions, receiving yards, TD, yards per catch, yards per game.  Charts per game or
  running total (QB also INT), plus gray **National Top 3** reference lines for the viewed stat and a
  chosen season (solid, dashed, dotted for #1, #2, #3; chips start off), game logs, Method and sources.

Line colours follow the order of picks: blue, orange, green solid, then amber, pink, violet dashed.  Past
three lines colour alone is not enough to tell every pair apart for colour-blind readers, so the line
style carries identity too (checked with the dataviz palette validator in both themes).  Gray is
reserved for the National Top 3.

The page follows the OS light/dark setting; the sun/moon button overrides it and remembers the choice
(localStorage `cf-theme`).

## config.json

The page config (it replaces the reports' `roster.json`):

- `seasons`: every season the page carries; `current_season`: the newest, the only one that refreshes.
- `default_teams`: the Team tab's selection on open, by registry team name (ESPN location name) and
  season, never an id.  The build fails if a default is not in the stored registry.
- `caps`: the most picks at once, `teams` 6 and `players` 4 (the reasoning is in the build summary of
  the launch branch and in AGENTS.md).
- `site`: masthead name, eyebrow, page and browser titles, description, URL, theme localStorage key,
  bot name.
- `registry_aliases`: cfbstats.com team-index name -> ESPN location name, for teams the two sources
  spell differently.

To add a season (2027): add it to `seasons`, set `current_season`, push through Claude's lane.  The
registry, team seasons and pools for 2027 are collected on the next run; 2026 then seals itself.

## The team registry (data/registry.json)

For each season, every team on cfbstats.com's team index (`https://cfbstats.com/{season}/team/index.html`)
joined to its ESPN team id: `{seasons: {season: {count, teams: [{cfb_id, cfb_name, espn_id, name,
nickname, abbr, how}], unmapped: [...], source_url}}}`.  The join is by exact normalized name, first
among ESPN's FBS teams for that season (ESPN core API group 80), then ESPN's full college list, with
`config.json` `registry_aliases` for spelling differences.  A join is **proven** only when that team's
season matches cfbstats.com's season totals (a wrong ESPN id cannot reproduce another team's totals);
`python3 tools/resolve_espn_ids.py proofs` lists every join and its proof.  A cfbstats team that cannot be
joined is stored in `unmapped`, named in the run log, and the section fails the run until it is fixed.

To fix an unmapped team: run `python3 tools/resolve_espn_ids.py candidates "NAME"` where ESPN is
reachable, add the cfbstats name and the ESPN location name to `registry_aliases`, and let the next run
prove the join.

## How it updates

`.github/workflows/update.yml` ("Update report") runs a full refresh every Sunday and Wednesday at 10:47
Eastern (cron is UTC, with two backups) and on demand from the Actions tab ("Run workflow", optional
`save_raw`).  During game windows (Thursday/Friday/Saturday, 4 PM–2 AM Eastern) it runs a quick check
every 20 minutes:

    schedule:
      - cron: "47 14 * * 0,3"
      - cron: "47 16 * * 0,3"
      - cron: "47 20 * * 0,3"
      - cron: "*/20 20-23 * * 4,5,6"
      - cron: "*/20 0-6 * * 5,6,0"

**Quick check (league-wide).**  The reports asked "has the home team just gone final?"; there is no
home team here.  The quick check reads ESPN's FBS scoreboard (`scoreboard?groups=80`) for today and
yesterday, Eastern: two requests.  It triggers the full update only if some game there is final for an
FBS team in the current registry and that event is neither stored in `data/team.json` for that team nor
in the last full run's list of finals it saw (`data/last_run.json` `finals_seen`).  Otherwise it writes
`.nochange` and exits in seconds; nothing is collected, built or committed.  A final the full run saw
but could not store (its box score not posted yet, a refused season) does not re-trigger every 20
minutes; the next new final or the next scheduled refresh retries it.

**Full run.**  `collect.py`, sections in order, each independent:

1. `registry_<season>`: cfbstats team index + ESPN team lists (sealed for a finished season once every
   team is joined).
2. `ap_poll`: ESPN rankings, AP Top 25 (poll name, week and release date are shown on the page).
3. `team_<season>`, newest first: for every registry team, ESPN's schedule (finals and scores) and the
   ESPN box score of each game not already stored (total, rushing and passing yards, turnovers lost and
   gained, third downs; no per-game player arrays), then cfbstats.com's season team totals as the
   cross-check.  A finished season is stored only once it matches, then sealed.  A current-season team
   with no new game is not re-asked; one whose latest game is newer than cfbstats' data-through date
   is stored with a "not cross-checked yet" note without asking cfbstats.
4. `natref_<season>_<tab>`: for QB, RB and WR, the cfbstats national leaderboard of each tracked stat
   (QB yards, TD, rating, completion %, attempts; RB yards, TD, yards/carry, yards/game, attempts; WR
   yards, receptions, TD, yards/catch, yards/game), the top 20 at the tab's positions (QB; RB; WR and
   TE) on each, and each listed player's game log from the link on his row.  A finished season's pool
   seals after its first complete store.

Then `build_report.py --standalone` writes `index.html`, and the workflow commits `data/`, `index.html`
and `logs/` (as "college-football bot").  If the build fails, nothing is published and `data/` is put
back.  The "Report problems" step then fails the run on purpose if any section failed, so GitHub emails
the owner; `data/last_run.json` says which section.

**cfbstats pacing.**  cfbstats.com refuses a fast crawl (403).  `collect.py` spaces its requests 1.5 s
apart, backs off 20 s and 60 s on a 403, reads each page once per run, and stops asking cfbstats for the
rest of the run after three refusals in a row; the affected sections fail, keep their stored data, and
retry next run.  Sealing keeps the steady state small: a scheduled refresh asks cfbstats only about
current-season teams with a new game cfbstats has posted, plus the current-season leaderboards and any
changed player lines.

## Validation (unchanged from the reports)

- Match or drop, never fabricate.
- Team rows: total yards = rushing + passing; the box-score score = the schedule score; turnovers =
  fumbles lost + interceptions; third-down conversions ≤ attempts; the result string agrees with the
  score.  Each season must match cfbstats.com once cfbstats has posted the same number of games: counts
  exactly; season yardage within max(5 yards, 0.2%) (a difference inside that is stored as a note shown
  on the page, anything larger is refused and nothing is stored).
- Players: a game log is stored only if it has exactly the leaderboard G games and sums exactly to the
  leaderboard line; QB game logs must also match the NCAA passer-rating formula within 0.15 per game (a
  published rating can round 0.1 off; this one comparison only).  Anything else is dropped and named
  (run log and the pool's `dropped` list, shown under Method).
- `SOURCE_EXCEPTIONS` (`update.py`): a single team / season / stat pinned to the exact recorded ESPN and
  cfbstats values, applied only when both match exactly, named in the run log.  One entry, carried over
  from nd-report with its evidence: Notre Dame 2024 third-down attempts, ESPN 185 vs cfbstats 184
  (cfbstats has 3-of-9 vs Northern Illinois on 2024-09-07; the official stat-crew box score, ESPN's box
  score and ESPN's play-by-play all give 10).
- The build re-checks every stored row, every pool (game count and totals against each player's line,
  dates ordered and unique, every Top 3 / order id resolving), every registry season, and the manifest.

## Data files

| File | What | Written by |
|---|---|---|
| `data/registry.json` | cfbstats team index joined to ESPN ids, per season | `registry_<season>` |
| `data/team.json` | `{teams: {espn_id: {name, seasons: {season: {games[], complete, check, cfbstats_url, retrieved_at}}}}, ap: {...}}` | `team_<season>`, `ap_poll` |
| `data/national_logs_<season>.json` | `{qb, rb, wr}`: each `{season, data_through, positions, stats: {key: {order, top, top_dropped, source_url}}, players: {id: {name, team, pos, line, url, games}}, dropped}` | `natref_<season>_<tab>` |
| `data/freshness.json` | when each section last collected successfully | `collect.py` |
| `data/last_run.json` | the last run's failed sections, log and `finals_seen` | `collect.py` |

All public sports statistics.  No personal or contact data is ever stored.  Data files are UTF-8, no BOM,
LF, byte-exact (`.gitattributes` turns off line-ending conversion for `data/` and `config.json`).

## How the page gets its data

The built `index.html` embeds a light model: the registry index (name, season, games, record, AP rank,
cross-check note per team-season), the pools' leaderboard lines, Top 3 ids, and the rows of the default
picks, so the page opens populated with no extra request.  When a reader first focuses a search box, the
page fetches `data/team.json` or the season's `data/national_logs_<season>.json` from its own origin
(cache-busted with each file's hash, served gzipped by GitHub Pages) and computes per-game and running
totals from those rows, exactly as the build does (`tools/render_check.js` compares the page's totals
with the build's).

## Render check

`tools/render_check.js` executes the built page in jsdom (light and dark theme) and fails on any script
error or empty section; it checks the default comparison, the page-vs-build totals, every leader box, a
3-team and a cross-season pick, the caps and their message, chips, the empty state, the sticky tooltip,
rank order in the picker, each Player position with its defaults, National Top 3 and a cross-season pick,
and scans the page script for const/let helpers called before their definition (the TDZ bug that once
blanked the IU page for 2.5 days).  Run it after any template change, and against the live page after a
merge:

    npm install --no-save jsdom@24.1.0
    node tools/render_check.js index.html
    node tools/render_check.js https://cf.daboodah.com/

## Installed app

`manifest.webmanifest` gives the installed app its name ("College Football", short "College FB"), its
colours (`theme_color` #24303F, the neutral slate brand and the page's theme-color; `background_color`
#111216, the dark theme's `--bg`, the theme Jeff runs) and its icons in `icons/` (192, 512, maskable 512,
the 180 apple-touch icon and the link-preview card).  `id` is "/" because the page owns its origin.
`build_report.py --standalone` refuses to publish if the manifest link, a member, or an icon does not
resolve, or if `theme_color` drifts from the page's theme-color tag.  All icons are drawn by
`tools/make_icons.py` from a plain football mark (no school logo); rerun it if the mark changes.  No
service worker: Chrome installs from the menu without one, and the page has no install button.

## Secrets

No secret is stored in this repository, in GitHub Actions secrets, or in any file on disk.

| Credential | Where it lives | What it accesses | Scope | Owner | Expires | Renewal reminder | What breaks if it lapses |
|---|---|---|---|---|---|---|---|
| GitHub's per-run `GITHUB_TOKEN` ("Update report" runs) | Minted by GitHub Actions per run; never stored | `daboodah-oss/college-football` only | `contents: write` (set in `update.yml`) | GitHub (repo setting) | End of each run | None needed | Nothing to renew; with read-only Actions permissions the bot could not commit and the page would stop updating |
| Pushes from Claude cloud sessions | The Claude GitHub App installation (claude.ai connector), not a token in the repo | `daboodah-oss/college-football` feature branches | Contents write via the app; `main` protected by the Tier 2 ruleset | Jeff Bandera (`daboodah-oss`) | While the app stays installed | None | Cloud sessions cannot push code changes; scheduled runs are unaffected |

Start a run on demand from the GitHub app or website (Actions tab, "Update report", "Run workflow").
`python tools/gh_status.py` shows recent runs without any credential (the repo is public).

## Capability matrix (this project)

| Agent | Repo read | Push to own lane | Run build locally | Reach external systems | Run unattended |
|---|---|---|---|---|---|
| GitHub Actions ("Update report") | Yes (checkout) | Commits `data/`, `index.html`, `logs/` to the branch it runs on | Yes | ESPN site + core APIs, cfbstats.com | Yes, the crons above |
| Claude Code, cloud session | Yes (Claude GitHub App) | Yes, `claude/...` branches (the launch branch) | Yes, build and render check | GitHub only: ESPN and cfbstats are blocked by the session's network policy, so collection is demonstrated in Actions runs on the branch | No |
| Budzilla (Muse) | Not demonstrated on this repo | Display-only fixes to `main` at Jeff's request (AGENTS.md) | Not demonstrated | Not demonstrated | Not demonstrated |
