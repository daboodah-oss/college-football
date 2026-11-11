#!/usr/bin/env python3
"""Conference head-to-head model for the Conferences tab.  No network.  Called by build_report.py.

Computed on every build from data/team.json (the same stored, cross-checked game rows the Team tab uses)
and conferences.json at the repo root (per-season FBS conference membership by ESPN team id, from ESPN's
standings API; membership is a season fact, so realignment is per-season).  The result is embedded in the
page model and also written to data/conferences.json by build_report.py, so the dataset is a committed,
inspectable file that the next build regenerates identically from the same inputs.

Counting rules: a completed FBS-vs-FBS game is stored as a row in BOTH teams' lists under the same event
id, so games are deduped by event id and counted once.  A game whose opponent has no stored row is a game
against an FCS opponent (the page stores FBS teams only); those count in the "FCS" bucket only.  Only
interconference games count: a pair entry exists only between two different conferences (or a conference
and FCS).  Ties count in neither wins nor losses (the pair's game count still rises).
"""
import json, os

FCS = "FCS"


def load(root, f, default):
    p = os.path.join(root, "data", f)
    return json.load(open(p)) if os.path.exists(p) else default


def season_block(teams, members, order, check, season):
    """One season's conference table from the stored game rows."""
    # membership covers every registry team, including a team whose own season rows were refused by the
    # cross-check and so are not stored: a stored row against such a team is still a real interconference
    # game with a known score, and counts (deduped by event like any other).  Only an opponent with no
    # membership at all is an FCS opponent.
    conf_of = dict(members)
    seen = {}          # event -> (winner_conf or None, conf_a, conf_b) for FBS-vs-FBS games
    vs_fcs = {}        # conf -> [wins, losses, ties]
    for tid, t in teams.items():
        c1 = conf_of.get(tid)
        if not c1: continue
        for g in t.get("seasons", {}).get(str(season), {}).get("games", []):
            ev = g.get("event")
            if not ev or g.get("result", "")[:1] not in "WLT": continue
            op = str(g.get("opp_id", ""))
            if op in conf_of:
                if ev in seen: continue
                c2 = conf_of[op]
                if c2 == c1: seen[ev] = None; continue
                seen[ev] = (c1 if g["pf"] > g["pa"] else c2 if g["pf"] < g["pa"] else None, c1, c2)
            elif op not in teams:
                r = vs_fcs.setdefault(c1, [0, 0, 0])
                r[0 if g["pf"] > g["pa"] else 2 if g["pf"] == g["pa"] else 1] += 1
    pair = {}          # "A|B" (A before B in `order`, FCS last) -> [A wins, B wins, ties, games]
    rank = {c: i for i, c in enumerate(order + [FCS])}
    for v in seen.values():
        if not v: continue
        w, c1, c2 = v
        a, b = (c1, c2) if rank[c1] < rank[c2] else (c2, c1)
        p = pair.setdefault(f"{a}|{b}", [0, 0, 0, 0])
        p[3] += 1
        if w is None: p[2] += 1
        elif w == a: p[0] += 1
        else: p[1] += 1
    for c, (w, l, t) in vs_fcs.items():
        a, b = (c, FCS) if rank[c] < rank[FCS] else (FCS, c)
        p = pair.setdefault(f"{a}|{b}", [0, 0, 0, 0])
        p[0 if a == c else 1] += w; p[1 if a == c else 0] += l; p[2] += t; p[3] += w + l + t
    confs = [c for c in order if any(m == c for m in conf_of.values())]
    nonconf = {}
    for c in confs + [FCS]:
        w = l = t = 0
        for k, (aw, bw, ti, gm) in pair.items():
            a, b = k.split("|")
            if a == c: w, l, t = w + aw, l + bw, t + ti
            elif b == c: w, l, t = w + bw, l + aw, t + ti
        if w or l or t: nonconf[c] = [w, l, t]
    thru = max((g["date"] for t in teams.values() for g in t.get("seasons", {}).get(str(season), {}).get("games", [])), default=None)
    return {"conferences": confs, "pair": pair, "nonconf": nonconf,
            "vs_fcs": {c: v for c, v in vs_fcs.items()}, "through": thru}


def build(root, cfg, check):
    src = os.path.join(root, "conferences.json")
    check(os.path.exists(src), "conferences.json (conference membership) is missing")
    if not os.path.exists(src): return {"seasons": {}}
    memb = json.load(open(src))
    order = memb.get("order", [])
    teams = load(root, "team.json", {"teams": {}}).get("teams", {})
    out = {"order": order, "seasons": {}}
    for s in sorted(cfg["seasons"]):
        members = (memb.get("members") or {}).get(str(s))
        check(members is not None, f"conferences.json: no membership for season {s} (add it before the season)")
        if members is None: continue
        reg = load(root, "registry.json", {"seasons": {}})["seasons"].get(str(s), {})
        missing = [t["name"] for t in reg.get("teams", []) if t["espn_id"] not in members]
        check(not missing, f"conferences.json {s}: no conference for {', '.join(missing[:5])}")
        blk = season_block(teams, members, order, check, s)
        tot = sum(v[3] for v in blk["pair"].values())
        check(tot > 0, f"conferences {s}: no interconference games computed")
        out["seasons"][str(s)] = blk
    return out
