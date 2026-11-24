#!/usr/bin/env python3
"""Re-judge one run's logged team refusals under the CURRENT update.tolerance (offline, no network).

  python3 tools/sim_refusals.py [GIT_REV]      # default: the latest full run in git history (all seasons collected)

Reads logs/collect.txt at that revision.  Season-total refusals ({'key': (ESPN, cfbstats)}) clear when every key is
inside update.tolerance; per-game "total yards != rushing + passing" refusals are counted separately (the
collect_tabs.box_row fix stores rush + pass, so those clear only if the season totals then match, which only a
real run can show).  Prints the before / after counts by season and every refusal that would remain."""
import ast, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import update  # noqa: E402


def log_at(rev):
    return subprocess.run(["git", "-C", ROOT, "show", f"{rev}:logs/collect.txt"], capture_output=True, text=True, check=True).stdout


def latest_full():
    revs = subprocess.run(["git", "-C", ROOT, "log", "--format=%h", "--", "logs/collect.txt"], capture_output=True, text=True).stdout.split()
    for r in revs:
        if re.search(r"\[team\] 2024: \d+ registry teams", log_at(r)): return r
    sys.exit("no full run found in git history")


rev = sys.argv[1] if len(sys.argv) > 1 else latest_full()
txt = log_at(rev)
SEASON_RE = re.compile(r"REFUSED: team-season (.+?) (\d{4}): ESPN box scores disagree with cfbstats season totals (\{.*\}) \(ESPN, cfbstats\)")
GAME_RE = re.compile(r"REFUSED: team (.+?) (\d{4}) (\d{4}-\d\d-\d\d): total yards (\d+) != rushing (\d+) \+ passing (\d+)")
before, clears, remain, games, other = {}, {}, [], [], []
for line in txt.splitlines():
    m = SEASON_RE.search(line)
    if m:
        team, season, bad = m.group(1), m.group(2), ast.literal_eval(m.group(3))
        before[season] = before.get(season, 0) + 1
        still = {k: (g, v) for k, (g, v) in bad.items() if abs(g - v) > update.tolerance(k, v)}
        if still: remain.append((season, team, still, bad))
        else: clears[season] = clears.get(season, 0) + 1
        continue
    m = GAME_RE.search(line)
    if m:
        team, season, date, tot, ru, pa = m.groups()
        before[season] = before.get(season, 0) + 1
        games.append((season, team, date, int(tot), int(ru), int(pa)))
        continue
    if "REFUSED:" in line: other.append(line.strip())
print(f"run {rev}: tolerances teams max(5, {update.TEAM_YARD_PCT:.1%}), third downs {update.THIRD_TOL}, turnovers {update.TO_TOL}")
for s in sorted(before, reverse=True):
    g = sum(1 for x in games if x[1] and x[0] == s)
    print(f"  {s}: {before[s]} refused before; {clears.get(s, 0)} clear on tolerance; {g} per-game total-yards (Part 2); "
          f"{before[s] - clears.get(s, 0) - g} still refused on season totals")
print(f"  all: {sum(before.values())} refused; {sum(clears.values())} clear; {len(games)} per-game; {len(remain)} remain")
print("\nstill refused on season totals (ESPN, cfbstats):")
for s, t, still, bad in sorted(remain, key=lambda x: (x[0], x[1])):
    print(f"  {t} {s}: {still}" + (f"   (inside tolerance now: {[k for k in bad if k not in still]})" if len(still) < len(bad) else ""))
print("\nper-game total yards != rush + pass (ESPN's totalYards field):")
for s, t, d, tot, ru, pa in sorted(games):
    print(f"  {t} {s} {d}: ESPN total {tot}, rush {ru} + pass {pa} = {ru + pa}")
for o in other: print("  other:", o)
