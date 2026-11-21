#!/usr/bin/env python3
"""Re-collect chosen team-seasons with the CURRENT code in a scratch copy of the repo, and report which would now
store and which stay refused.  Network: ESPN + cfbstats (paced exactly as collect.py paces them).  The repo's own
data/ is never written: everything happens in OUT_DIR.

  python3 tools/trial_collect.py OUT_DIR                     # every team-season refused in the latest full run's log
  python3 tools/trial_collect.py OUT_DIR "Navy:2025" "Army:2025"

Prints one line per team-season (STORED with its check string, or REFUSED with the validator's reason) and the
counts by season.  Use it to measure a validator or collect change before it reaches the scheduled run."""
import contextlib, io, json, os, re, shutil, subprocess, sys

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2: sys.exit(__doc__)
out = os.path.abspath(sys.argv[1])
if out == SRC or out.startswith(SRC + os.sep): sys.exit("OUT_DIR must be outside the repo")
picks = [tuple(a.rsplit(":", 1)) for a in sys.argv[2:]]
if not picks:
    revs = subprocess.run(["git", "-C", SRC, "log", "--format=%h", "--", "logs/collect.txt"], capture_output=True, text=True).stdout.split()
    for r in revs:
        txt = subprocess.run(["git", "-C", SRC, "show", f"{r}:logs/collect.txt"], capture_output=True, text=True).stdout
        if re.search(r"\[team\] 2024: \d+ registry teams", txt): break
    picks = sorted(set(re.findall(r"\[team\] (.+?) (\d{4}) (?:REFUSED by validator|FAILED)", txt)), key=lambda p: (p[1], p[0]))
    print(f"team-seasons refused in run {r}: {len(picks)}")
if os.path.exists(out): shutil.rmtree(out)
shutil.copytree(SRC, out, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__", "_test*.html"))
sys.path.insert(0, out); os.chdir(out)
import collect as C, collect_tabs as T, update as U  # noqa: E402  (the COPY's modules)
reg = json.load(open(os.path.join(out, "data", "registry.json")))["seasons"]
res, thr = {}, {}
for name, season in picks:
    season = int(season)
    t = next((x for x in reg[str(season)]["teams"] if x["name"] == name), None)
    if not t: print(f"  {name} {season}: not in the {season} registry"); continue
    if season == C.SEASON and season not in thr: thr[season] = T.cfb_through(C, season)
    buf = io.StringIO()
    try:   # stored=None: every game's box score is read fresh with the current box_row
        with contextlib.redirect_stdout(buf): T.team_job(C, U, t, season, None, thr.get(season))
        chk = json.load(open(os.path.join(out, "data", "team.json")))["teams"][t["espn_id"]]["seasons"][str(season)].get("check", "")
        res[(name, season)] = ("STORED", chk)
    except SystemExit:
        res[(name, season)] = ("REFUSED", next((l for l in buf.getvalue().splitlines() if l.startswith("REFUSED")), "?"))
    except Exception as e:
        res[(name, season)] = ("FAILED", str(e))
    extra = [l for l in C.LOG if "totalYards" in l]
    for l in extra: print("   ", l)
    C.LOG.clear()
    print(f"  {res[(name, season)][0]:8} {name} {season}: {res[(name, season)][1]}")
by = {}
for (n, s), (st, _) in res.items(): by.setdefault(s, {}).setdefault(st, 0); by[s][st] += 1
print("\nby season:", {s: by[s] for s in sorted(by, reverse=True)})
