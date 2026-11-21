#!/usr/bin/env python3
"""Show what each model version says for a stored Playoff week, side by side, WITHOUT storing anything (offline).

  python3 tools/model_compare.py ["Week 11"] [N]        # default: the earliest stored week, top 12

Columns: the committee's list, our list as frozen in the snapshot, v1 and v2 recomputed now from the stored rows
with games through that snapshot's `through` date.  (v1 recomputed can differ from the frozen list when the model
code changed since, e.g. the 2026-11-21 SRS home-field fix; the frozen week is never rewritten.)"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import cfp_model as M  # noqa: E402

d = json.load(open(os.path.join(ROOT, "data", "cfp.json")))
want = next((a for a in sys.argv[1:] if not a.isdigit()), None)
n = int(next((a for a in sys.argv[1:] if a.isdigit()), 12))
w = next((x for x in d["weeks"] if x["week"] == want), d["weeks"][0]) if want else d["weeks"][0]
names = {k: v.get("name", k) for k, v in M.load_teams(ROOT).items()}
v1 = M.compute(ROOT, d["season"], w["through"], "v1"); v2 = M.compute(ROOT, d["season"], w["through"], "v2")
cols = [("Committee", w["committee"]), (f"Frozen ({w.get('model', 'v1')})", w["ours"]), ("v1 now", v1["top25"]), ("v2", v2["top25"])]
print(f"{w['week']} (released {w['date']}, games through {w['through']}); v2 weights {M.WEIGHTS['v2']}")
print("  #  " + "".join(f"{h:<20}" for h, _ in cols))
for i in range(n):
    print(f"{i + 1:3}  " + "".join(f"{names.get(lst[i], lst[i])[:19]:<20}" for _, lst in cols))
r1 = {t: i + 1 for i, t in enumerate(v1["top25"])}; r2 = {t: i + 1 for i, t in enumerate(v2["top25"])}
moves = sorted((t for t in set(r1) | set(r2) if r1.get(t) != r2.get(t)), key=lambda t: -abs(r1.get(t, 26) - r2.get(t, 26)))[:8]
print("\nlargest v1 -> v2 moves (now-recomputed v1): " + "; ".join(f"{names.get(t, t)} {r1.get(t, 'out')} -> {r2.get(t, 'out')}" for t in moves))
