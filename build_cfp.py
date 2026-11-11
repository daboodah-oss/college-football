#!/usr/bin/env python3
"""Playoff tab model: the stored weekly snapshots from data/cfp.json, with team names resolved.
No network.  Called by build_report.py.  Snapshots are frozen history (each week's committee Top 25,
our computed Top 25, lines and agreement metrics, stored by collect_cfp.py through update.py); the
build only re-checks their shape and resolves ids to names, it never recomputes a past week."""
import json, os


def load(root, f, default):
    p = os.path.join(root, "data", f)
    return json.load(open(p)) if os.path.exists(p) else default


def build(root, cfg, check):
    d = load(root, "cfp.json", {"season": cfg["current_season"], "weeks": []})
    teams = load(root, "team.json", {"teams": {}}).get("teams", {})
    weeks = []
    for w in d.get("weeks", []):
        tag = f"cfp {w.get('week')} {w.get('date')}"
        comm, ours = w.get("committee", []), w.get("ours", [])
        check(len(comm) == 25 and len(set(comm)) == 25, f"{tag}: committee is not 25 distinct teams")
        check(len(ours) == 25 and len(set(ours)) == 25, f"{tag}: our Top 25 is not 25 distinct teams")
        names = {}
        for tid in set(comm) | set(ours):
            check(tid in teams, f"{tag}: team id {tid} is not a stored team")
            check(tid in (w.get("lines") or {}), f"{tag}: no stored line for team id {tid}")
            names[tid] = teams.get(tid, {}).get("name", tid)
        m = w.get("metrics") or {}
        for k in ("overlap25", "overlap12", "avg_delta", "exact", "agreement"):
            check(isinstance(m.get(k), (int, float)), f"{tag}: metric '{k}' missing")
        weeks.append({"week": w.get("week", ""), "date": w.get("date", ""), "through": w.get("through"),
                      "committee": comm, "ours": ours, "names": names,
                      "lines": w.get("lines", {}), "metrics": m, "weights": w.get("weights")})
    return {"season": d.get("season", cfg["current_season"]), "weeks": weeks}
