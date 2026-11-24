#!/usr/bin/env python3
"""Narrow a refused team-season's ESPN-vs-cfbstats disagreement down to candidate games (network: ESPN + cfbstats,
paced like collect.py; nothing is written).  For Part 3 reconciliations (docs/claude-spec-warnings-model-v2.md).

  python3 tools/localize_refusal.py "Navy" 2025 [rushing passing scoring]

cfbstats publishes no per-game team yardage, only splits (home / road, wins / losses, conference, FBS / FCS, month).
This sums ESPN's per-game box-score rows into the same splits and prints, per split, ESPN vs cfbstats.  A game can
hold the difference only if every split it belongs to disagrees by the same amount; those games are printed as the
candidates to check against the official stat-crew box score.  It also prints cfbstats' own schedule table, whose
game scores can disagree with cfbstats' season scoring total (the Georgia Tech 2024 case)."""
import io, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import pandas as pd  # noqa: E402
import collect as C, collect_tabs as T  # noqa: E402

name, season = sys.argv[1], int(sys.argv[2])
cats = sys.argv[3:] or ["rushing", "passing"]
reg = json.load(open(os.path.join(ROOT, "data", "registry.json")))["seasons"][str(season)]["teams"]
t = next(x for x in reg if x["name"] == name)
conf = json.load(open(os.path.join(ROOT, "conferences.json")))["members"][str(season)]
fbs = set(conf)
rows = [T.box_row(C, g, t["espn_id"]) for g in T.espn_completed(C, t["espn_id"], season)]
month = lambda d: {8: "in August/September", 9: "in August/September", 10: "in October", 11: "in November"}.get(int(d[5:7]), "in December/January")
def splits(g):
    s = ["All Games", "at Home" if g["site"] == "H" else "on Road/Neutral Site", "in Wins" if g["pf"] > g["pa"] else "in Losses", month(g["date"])]
    op = str(g.get("opp_id", ""))
    s.append("vs. FBS (I-A)" if op in fbs else "vs. FCS (I-AA)")
    if op in fbs: s.append("vs. Conference" if conf.get(op) == conf.get(t["espn_id"]) and conf.get(op) != "Independent" else "vs. Non-Conference")
    else: s.append("vs. Non-Conference")
    return s
KEY = {"rushing": ("rush_yds", "rushing/offense/split.html", "Yards"), "passing": ("pass_yds", "passing/offense/split.html", "Yards"),
       "scoring": ("pf", "scoring/offense/split.html", "Pts")}
print(f"{name} {season}: {len(rows)} ESPN games")
for g in rows: print(f"  {g['date']} {g['site']} {g['opp'][:22]:<22} {g['result']:<10} rush {g['rush_yds']:>4} pass {g['pass_yds']:>4} total {g['total_yds']:>4}")
for cat in cats:
    k, path, col = KEY[cat]
    try:
        tab = pd.read_html(io.StringIO(C.get(f"https://cfbstats.com/{season}/team/{t['cfb_id']}/{path}").text))[0]
    except Exception as e:
        print(f"\n{cat}: cfbstats split page unreadable ({e})"); continue
    cf = {r["Split"]: int(str(r.get(col, r.iloc[3])).replace(",", "")) for _, r in tab.iterrows() if str(r["Split"]) != "nan"}
    es = {}
    for g in rows:
        for s in splits(g): es[s] = es.get(s, 0) + g[k]
    print(f"\n{cat} ({k}): split, ESPN, cfbstats, ESPN - cfbstats")
    diff = {}
    for s in cf:
        if s in es: diff[s] = es[s] - cf[s]; print(f"  {s:<24} {es[s]:>6} {cf[s]:>6} {diff[s]:>+6}")
    tot = diff.get("All Games", 0)
    cand = [g for g in rows if tot and all(diff.get(s, tot) == tot for s in splits(g))]
    print(f"  candidates holding the whole {tot:+d}: " + ("; ".join(f"{g['date']} {g['opp']}" for g in cand) if cand else "none single (spread over several games)"))
