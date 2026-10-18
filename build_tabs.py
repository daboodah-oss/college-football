#!/usr/bin/env python3
"""Models for the Team and Player tabs.  No network.  Called by build_report.py.

Every stored row in data/team.json and data/national_logs_<season>.json is re-checked here (it was checked
when it was stored).  The page itself carries only a light index (the registry, the pools' leaderboard lines,
the default selections' rows); it fetches the rest of the same validated files from its own origin when a
reader picks a team or player.  The workflow commits data files only when this build passes, so every file
the page can fetch has passed these checks.
"""
import hashlib, json, os

SHORT = {"Record": "Record", "Points scored": "Pts for", "Points allowed": "Pts against", "Total yards": "Total yds",
         "Rushing yards": "Rush yds", "Passing yards": "Pass yds", "Turnover margin": "TO +/-", "Third-down %": "3rd down %"}
# The school reports' Team-tab stat set, in order (their build_tabs.TEAM_STATS): key, label, decimals, higher is better
TEAM_STATS = [("wins", "Record", 0, True), ("pf", "Points scored", 0, True), ("pa", "Points allowed", 0, False),
              ("total_yds", "Total yards", 0, True), ("rush_yds", "Rushing yards", 0, True), ("pass_yds", "Passing yards", 0, True),
              ("to_margin", "Turnover margin", 0, True), ("third_pct", "Third-down %", 1, True)]
TEAM_CHART = [("pf", "Points scored"), ("pa", "Points allowed"), ("total_yds", "Total yds"), ("rush_yds", "Rush yds"),
              ("pass_yds", "Pass yds"), ("to_margin", "TO margin"), ("third_pct", "3rd down %"), ("wins", "Wins")]
# Player tab: the reports' compare sets (build_tabs.SKILL / build_tabs.NATREF).  table: key, label, short, decimals
PLAYER = {
    "qb": {"label": "Quarterbacks", "noun": "quarterbacks", "keys": ["att", "cmp", "yds", "td", "int"],
           "table": [("yds", "Passing yards", "Pass yds", 0), ("td", "Passing TD", "Pass TD", 0), ("rating", "Passer rating", "Rating", 1),
                     ("pct", "Completion %", "Comp %", 1), ("att", "Pass attempts", "Att", 0)],
           "chart": [("yds", "Pass yards"), ("td", "Pass TD"), ("int", "INT"), ("rating", "Rating"), ("pct", "Comp %"), ("att", "Attempts")]},
    "rb": {"label": "Running backs", "noun": "running backs", "keys": ["att", "yds", "td"],
           "table": [("yds", "Rushing yards", "Rush yds", 0), ("td", "Rushing TD", "Rush TD", 0), ("ypc", "Yards per carry", "Yds/carry", 2),
                     ("ypg", "Yards per game", "Yds/game", 1), ("att", "Carries", "Car", 0)],
           "chart": [("yds", "Rush yds"), ("td", "Rush TD"), ("ypc", "YPC"), ("ypg", "Yds/game"), ("att", "Carries")]},
    "wr": {"label": "Receivers", "noun": "receivers", "keys": ["rec", "yds", "td"],
           "table": [("rec", "Receptions", "Rec", 0), ("yds", "Receiving yards", "Rec yds", 0), ("td", "Receiving TD", "Rec TD", 0),
                     ("ypr", "Yards per catch", "Yds/catch", 2), ("ypg", "Yards per game", "Yds/game", 1)],
           "chart": [("yds", "Rec yds"), ("rec", "Receptions"), ("td", "Rec TD"), ("ypr", "Yds/catch"), ("ypg", "Yds/game")]},
}
GAME_KEYS = ("event", "date", "opp", "opp_id", "site", "pf", "pa", "result", "total_yds", "rush_yds", "pass_yds",
             "to_lost", "to_gained", "third_conv", "third_att")


def load(root, f, default):
    p = os.path.join(root, "data", f)
    return json.load(open(p)) if os.path.exists(p) else default


def ver(root, f):
    """Cache-busting stamp for a data file the page fetches (first 12 hex of its sha256)."""
    p = os.path.join(root, "data", f)
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:12] if os.path.exists(p) else None


# ------------------------------------------------------------------ Team
def team_totals(games):
    """Season totals through every stored game (the page computes the same numbers; render_check compares them)."""
    t = {"games": len(games), "wins": 0, "losses": 0, "ties": 0, "pf": 0, "pa": 0, "total_yds": 0, "rush_yds": 0, "pass_yds": 0,
         "to_margin": 0, "third_conv": 0, "third_att": 0}
    for g in games:
        t["wins"] += g["pf"] > g["pa"]; t["losses"] += g["pf"] < g["pa"]; t["ties"] += g["pf"] == g["pa"]
        for k in ("pf", "pa", "total_yds", "rush_yds", "pass_yds", "third_conv", "third_att"): t[k] += g[k]
        t["to_margin"] += g["to_gained"] - g["to_lost"]
    t["third_pct"] = 100 * t["third_conv"] / t["third_att"] if t["third_att"] else None
    t["record"] = f"{t['wins']}-{t['losses']}" + (f"-{t['ties']}" if t["ties"] else "")
    return t


def team_tab(root, cfg, check):
    seasons, cur = sorted(cfg["seasons"]), cfg["current_season"]
    reg = load(root, "registry.json", {"seasons": {}})["seasons"]
    td = load(root, "team.json", {"teams": {}, "ap": None})
    teams, ap = td.get("teams", {}), td.get("ap")
    ap_rank = {}
    poll = None
    if ap:
        ranks = [t["rank"] for t in ap["top"]]
        check(ranks == sorted(ranks) and ranks and ranks[0] == 1, "AP poll: ranks out of order")
        poll = {"name": ap["poll"], "week": ap.get("week", ""), "date": ap["date"], "source_url": ap.get("source_url"),
                "top": [{"rank": t["rank"], "team_id": t["team_id"], "name": t["name"], "record": t.get("record", "")} for t in ap["top"]]}
        ap_rank = {t["team_id"]: t["rank"] for t in ap["top"]}
    index, missing, counts = {}, [], {}
    for s in seasons:
        r = reg.get(str(s))
        check(r is not None, f"registry: season {s} not stored")
        if not r: continue
        ids = [t["espn_id"] for t in r["teams"]]
        check(len(ids) == len(set(ids)), f"registry {s}: an ESPN id appears twice")
        check(r["count"] == len(r["teams"]) + len(r.get("unmapped", [])), f"registry {s}: counts do not add up")
        counts[str(s)] = {"index": r["count"], "mapped": len(r["teams"]), "unmapped": [u["cfb_name"] for u in r.get("unmapped", [])], "source_url": r["source_url"]}
        rows = []
        for t in r["teams"]:
            blk = teams.get(t["espn_id"], {}).get("seasons", {}).get(str(s))
            if not blk or not blk.get("games"):
                missing.append(f"{t['name']} {s}"); continue
            G = blk["games"]; tag = f"team {t['name']} {s}"
            for g in G:
                check(all(isinstance(g.get(k), int) for k in ("pf", "pa", "total_yds", "rush_yds", "pass_yds", "to_lost", "to_gained", "third_conv", "third_att")), f"{tag} {g.get('date')}: stat missing or not an integer")
                check(g["total_yds"] == g["rush_yds"] + g["pass_yds"], f"{tag} {g['date']}: total yards != rushing + passing")
                check(0 <= g["third_conv"] <= g["third_att"], f"{tag} {g['date']}: third-down conversions exceed attempts")
                wl = "W" if g["pf"] > g["pa"] else "L" if g["pf"] < g["pa"] else "T"
                check(g["result"] == f"{wl} {g['pf']}-{g['pa']}", f"{tag} {g['date']}: result disagrees with the score")
                check("rush" not in g and "rec" not in g, f"{tag} {g['date']}: per-game player arrays must not be stored")
            check([g["date"] for g in G] == sorted(g["date"] for g in G), f"{tag}: games out of order")
            check(len({g["event"] for g in G}) == len(G), f"{tag}: duplicate game")
            if s < cur:
                check(blk.get("complete") and str(blk.get("check", "")).startswith("cfbstats"), f"{tag}: a completed season is stored without a cfbstats match")
            tot = team_totals(G)
            e = {"k": f"{t['espn_id']}-{s}", "id": t["espn_id"], "season": s, "name": t["name"], "nick": t.get("nickname", ""),
                 "abbr": t.get("abbr", ""), "games": len(G), "record": tot["record"], "last": G[-1]["date"],
                 "check": blk.get("check", ""), "url": blk.get("cfbstats_url"), "matched": str(blk.get("check", "")).startswith("cfbstats")}
            if s == cur and t["espn_id"] in ap_rank: e["ap"] = ap_rank[t["espn_id"]]
            rows.append(e)
        index[str(s)] = sorted(rows, key=lambda e: e["name"])
    # default selection (config.json), by registry name and season
    defaults, seed, expect = [], {}, {}
    for want in cfg["default_teams"]:
        e = next((x for x in index.get(str(want["season"]), []) if x["name"] == want["name"]), None)
        check(e is not None, f"config.json default team {want['name']} {want['season']} is not in the stored registry")
        if not e: continue
        G = teams[e["id"]]["seasons"][str(e["season"])]["games"]
        defaults.append(e["k"]); seed[e["k"]] = [{k: g[k] for k in GAME_KEYS} for g in G]; expect[e["k"]] = team_totals(G)
    check(len(defaults) <= cfg["caps"]["teams"], "config.json: more default teams than the team cap")
    unmatched_cur = [f"{e['name']}" for e in index.get(str(cur), []) if not e["matched"]]
    return {"index": index, "counts": counts, "missing": missing, "poll": poll, "defaults": defaults, "seed": seed, "expect": expect,
            "unmatched_current": unmatched_cur,
            "stats": [{"key": k, "label": l, "short": SHORT.get(l, l), "dp": d, "hb": hb} for k, l, d, hb in TEAM_STATS],
            "chart": [{"key": k, "label": l} for k, l in TEAM_CHART]}


# ------------------------------------------------------------------ Player
def player_tab(root, cfg, check):
    seasons, cur = sorted(cfg["seasons"]), cfg["current_season"]
    out = {}
    for tab, spec in PLAYER.items():
        pools = {}
        for s in seasons:
            t = load(root, f"national_logs_{s}.json", {}).get(tab)
            if not t:
                pools[str(s)] = {"status": "pending", "message": f"{s} national {spec['noun']} have not been collected yet; the next full refresh adds them."}
                continue
            check(t.get("season") == s, f"natref {s} {tab}: file holds season {t.get('season')}")
            players = []
            for pid, p in t["players"].items():
                tag = f"natref {s} {tab} {p['name']}"
                g = p["games"]
                check(len(g) == p["line"]["g"], f"{tag}: {len(g)} games vs leaderboard G {p['line']['g']}")
                check(all(sum(x[k] for x in g) == p["line"][k] for k in spec["keys"]), f"{tag}: game log no longer matches the leaderboard line")
                dates = [x["date"] for x in g]
                check(dates == sorted(dates) and len(set(dates)) == len(dates), f"{tag}: games out of order or duplicated")
                players.append({"k": f"{s}:{pid}", "pid": pid, "season": s, "name": p["name"], "team": p["team"], "pos": p.get("pos", ""),
                                "line": p["line"], "url": p.get("url")})
            stats = {}
            for key, st in t["stats"].items():
                check(all(p in t["players"] for p in st["top"] + st["order"]), f"natref {s} {tab} {key}: list names a player with no stored game log")
                stats[key] = {"top": [f"{s}:{p}" for p in st["top"]], "top_dropped": st.get("top_dropped", []), "source_url": st["source_url"],
                              "leader": f"{s}:{st['order'][0]}" if st["order"] else None}
            pools[str(s)] = {"status": "ok", "data_through": t["data_through"], "positions": t.get("positions", []), "stats": stats,
                             "players": sorted(players, key=lambda p: (p["name"], p["team"])), "dropped": t.get("dropped", [])}
        # default on open: the current season's leader and runner-up in the first tracked stat (yards), from the data
        defaults, seed = [], {}
        P = pools.get(str(cur), {})
        if P.get("status") == "ok":
            d = load(root, f"national_logs_{cur}.json", {})[tab]
            order = d["stats"]["yds"]["order"]
            defaults = [f"{cur}:{p}" for p in order[:2]]
            for k in defaults: seed[k] = d["players"][k.split(":", 1)[1]]["games"]
        out[tab] = {"label": spec["label"], "noun": spec["noun"], "keys": spec["keys"], "pools": pools, "defaults": defaults, "seed": seed,
                    "table": [{"key": k, "label": l, "short": sh, "dp": dp} for k, l, sh, dp in spec["table"]],
                    "chart": [{"key": k, "label": l} for k, l in spec["chart"]]}
    return out


def build(root, cfg, check):
    seasons = sorted(cfg["seasons"])
    check(cfg["current_season"] == seasons[-1], "config.json: current_season must be the newest season")
    check(all(isinstance(cfg["caps"][k], int) and cfg["caps"][k] >= 2 for k in ("teams", "players")), "config.json: caps must be integers of at least 2")
    data = {"team": f"data/team.json?v={ver(root, 'team.json')}",
            "logs": {str(s): f"data/national_logs_{s}.json?v={ver(root, f'national_logs_{s}.json')}" for s in seasons}}
    return {"data": data, "team": team_tab(root, cfg, check), "player": player_tab(root, cfg, check)}
