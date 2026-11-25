#!/usr/bin/env python3
"""Playoff tab model: the stored weekly snapshots from data/cfp.json, with team names resolved.
No network.  Called by build_report.py.  Snapshots are frozen history (each week's committee Top 25,
our computed Top 25, lines and agreement metrics, stored by collect_cfp.py through update.py); the
build only re-checks their shape and resolves ids to names, it never recomputes a past week."""
import datetime, json, os


def load(root, f, default):
    p = os.path.join(root, "data", f)
    return json.load(open(p)) if os.path.exists(p) else default


def context_notes(root, season, weeks, teams, check):
    """cfp_context.json (repo root): curated, sourced, display-only notes per committee week.  Returns
    {week label: [note, ...]} for stored weeks; a note for a week not stored yet waits (printed, not shown)."""
    p = os.path.join(root, "cfp_context.json")
    if not os.path.exists(p): return {}
    by_name = {}
    for tid, t in teams.items(): by_name.setdefault(t.get("name"), []).append(tid)
    have = {w.get("week"): w for w in weeks}
    out = {}
    for i, n in enumerate(json.load(open(p)).get("notes", [])):
        tag = f"cfp_context.json note {i + 1}"
        for k in ("season", "week", "team", "fact", "source", "source_url", "date"):
            check(n.get(k) not in (None, ""), f"{tag}: '{k}' is required")
        if n.get("season") != season: continue
        check(len(by_name.get(n.get("team"), [])) == 1, f"{tag}: team '{n.get('team')}' does not name exactly one stored team")
        check(str(n.get("source_url", "")).startswith("https://"), f"{tag}: source_url must be an https link")
        try: datetime.date.fromisoformat(str(n.get("date")))
        except ValueError: check(False, f"{tag}: date '{n.get('date')}' is not YYYY-MM-DD")
        w = have.get(n.get("week"))
        if not w: print(f"    {tag}: {n.get('week')} is not stored yet; the note waits"); continue
        check(str(n.get("date")) <= str(w.get("date")), f"{tag}: dated {n.get('date')}, after the {n.get('week')} release ({w.get('date')})")
        tid = (by_name.get(n.get("team")) or [None])[0]
        out.setdefault(n["week"], []).append({"team": tid, "name": n["team"], "fact": n["fact"], "source": n["source"],
                                              "source_url": n["source_url"], "date": n["date"]})
    return out


def build(root, cfg, check):
    d = load(root, "cfp.json", {"season": cfg["current_season"], "weeks": []})
    teams = load(root, "team.json", {"teams": {}}).get("teams", {})
    ctx = context_notes(root, d.get("season", cfg["current_season"]), d.get("weeks", []), teams, check)
    cp = os.path.join(root, "conferences.json")   # per-season membership (the Conferences tab's source), for the pills
    members = (json.load(open(cp)).get("members", {}) if os.path.exists(cp) else {}).get(str(d.get("season", cfg["current_season"])), {})
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
        names, conf = {}, {}
        for tid in set(comm) | set(ours) | set(wab or []) | set(s25 or []):
            check(tid in teams, f"{tag}: team id {tid} is not a stored team")
            check(tid in (w.get("lines") or {}), f"{tag}: no stored line for team id {tid}")
            check(tid in members, f"{tag}: team id {tid} has no {d.get('season')} conference membership in conferences.json")
            names[tid] = teams.get(tid, {}).get("name", tid)
            conf[tid] = members.get(tid, "")
        m = w.get("metrics") or {}
        for k in ("overlap25", "overlap12", "avg_delta", "exact", "agreement"):
            check(isinstance(m.get(k), (int, float)), f"{tag}: metric '{k}' missing")
        weeks.append({"week": w.get("week", ""), "date": w.get("date", ""), "through": w.get("through"),
                      "committee": comm, "ours": ours, "names": names, "conf": conf,
                      "lines": w.get("lines", {}), "metrics": m, "weights": w.get("weights"),
                      "wab": wab, "wab_bubble": w.get("wab_bubble"), "wab_metrics": w.get("wab_metrics"), "srs_top25": s25,
                      "model": w.get("model", "v1"), "context": ctx.get(w.get("week"), [])})
    return {"season": d.get("season", cfg["current_season"]), "weeks": weeks}
