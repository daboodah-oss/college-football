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
        wab = w.get("wab")
        if wab is not None:
            check(len(wab) == 25 and len(set(wab)) == 25, f"{tag}: WAB Top 25 is not 25 distinct teams")
            wm = w.get("wab_metrics") or {}
            for k in ("overlap25", "overlap12", "avg_delta", "exact", "agreement"):
                check(isinstance(wm.get(k), (int, float)), f"{tag}: WAB metric '{k}' missing")
            check(isinstance((w.get("wab_bubble") or {}).get("rating"), (int, float)), f"{tag}: WAB bubble rating missing")
        s25 = w.get("srs_top25")   # Bias tab inputs (snapshots stored after 2026-11-21)
        if s25 is not None:
            check(len(s25) == 25 and len(set(s25)) == 25, f"{tag}: SRS Top 25 is not 25 distinct teams")
            check(wab is not None, f"{tag}: a bias snapshot has no WAB block")
            for tid in set(comm) | set(s25) | set(wab or []):
                r = ((w.get("lines") or {}).get(tid) or {}).get("srs_rank")
                check(isinstance(r, int) and r >= 1, f"{tag}: line for team id {tid} lacks a numeric srs_rank")
            check([((w.get("lines") or {}).get(t) or {}).get("srs_rank") for t in s25] == list(range(1, 26)), f"{tag}: SRS Top 25 ranks are not 1-25 in order")
        names = {}
        for tid in set(comm) | set(ours) | set(wab or []) | set(s25 or []):
            check(tid in teams, f"{tag}: team id {tid} is not a stored team")
            check(tid in (w.get("lines") or {}), f"{tag}: no stored line for team id {tid}")
            names[tid] = teams.get(tid, {}).get("name", tid)
        m = w.get("metrics") or {}
        for k in ("overlap25", "overlap12", "avg_delta", "exact", "agreement"):
            check(isinstance(m.get(k), (int, float)), f"{tag}: metric '{k}' missing")
        weeks.append({"week": w.get("week", ""), "date": w.get("date", ""), "through": w.get("through"),
                      "committee": comm, "ours": ours, "names": names,
                      "lines": w.get("lines", {}), "metrics": m, "weights": w.get("weights"),
                      "wab": wab, "wab_bubble": w.get("wab_bubble"), "wab_metrics": w.get("wab_metrics"), "srs_top25": s25})
    return {"season": d.get("season", cfg["current_season"]), "weeks": weeks}
