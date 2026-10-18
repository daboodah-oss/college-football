#!/usr/bin/env python3
"""Small, safe editors for the College Football page's data files.

Each command takes one JSON argument (or '-' to read JSON from stdin), checks it,
and merges it into data/*.json.  Nothing is stored unless every check passes.

  status                         summary of what is stored
  registry      {season block}   store one season's team registry (cfbstats team index joined to ESPN team ids)
  team-season   {season block}   store one team's box-score season (must match cfbstats totals when given)
  ap-poll       {poll}           store the latest AP Top 25 (poll name, week, release date, teams)
  natref        {tab, season, players, ...}   replace one season's national player pool for one tab
                                 (every game log must match the player's leaderboard line)

The seasons come from config.json: the newest is the current season, the only one that
refreshes; every earlier season is collected once and sealed.
"""
import json, os, sys, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda f: os.path.join(ROOT, "data", f)


def load(f): return json.load(open(P(f)))


def load_or(f, default):
    return json.load(open(P(f))) if os.path.exists(P(f)) else default


def config():
    return json.load(open(os.path.join(ROOT, "config.json")))


def current_season():
    return config()["current_season"]


def save(f, d):
    os.makedirs(os.path.dirname(P(f)), exist_ok=True)
    tmp = P(f) + ".tmp"
    json.dump(d, open(tmp, "w"), indent=1)
    os.replace(tmp, P(f))


def die(msg):
    print("REFUSED:", msg); sys.exit(2)


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="minutes")


def rating(r):
    return (8.4 * r["yds"] + 330 * r["td"] + 100 * r["cmp"] - 200 * r["int"]) / r["att"]


def need_ints(r, keys, tag):
    for k in keys:
        if not isinstance(r.get(k), int): die(f"{tag}: '{k}' must be an integer")
    if r["cmp"] > r["att"]: die(f"{tag}: completions exceed attempts")


def logs_file(season):
    return f"national_logs_{season}.json"


def status():
    cfg = config()
    reg = load_or("registry.json", {"seasons": {}})["seasons"]
    td = load_or("team.json", {"teams": {}, "ap": None})
    for s in cfg["seasons"]:
        r = reg.get(str(s)) or {}
        stored = [t for t in td["teams"].values() if str(s) in t.get("seasons", {})]
        matched = [t for t in stored if str(t["seasons"][str(s)].get("check", "")).startswith("cfbstats")]
        print(f"{s}: registry {len(r.get('teams', []))} mapped / {r.get('count', '?')} on cfbstats"
              + (f", unmapped {', '.join(u['cfb_name'] for u in r.get('unmapped', []))}" if r.get("unmapped") else "")
              + f"; team seasons stored {len(stored)} ({len(matched)} matched cfbstats)")
        nl = load_or(logs_file(s), {})
        print("   pools: " + ", ".join(f"{k} {len(v.get('players', {}))} (dropped {len(v.get('dropped', []))})" for k, v in sorted(nl.items())))
    ap = td.get("ap")
    if ap: print(f"AP poll: {ap['poll']} {ap.get('week', '')} {ap['date']}: " + ", ".join(f"{t['rank']} {t['name']}" for t in ap["top"][:5]) + " ...")


def arg():
    raw = sys.argv[2] if len(sys.argv) > 2 else "-"
    return json.loads(sys.stdin.read() if raw == "-" else raw)


# ================================================================ team registry
def registry(x):
    """Store one season's registry: {season, source_url, count, teams:[{cfb_id, cfb_name, espn_id, name, abbr, how}], unmapped:[...]}.
    Every cfbstats index team must appear exactly once, mapped or unmapped; no ESPN id may be used twice."""
    season = str(x.get("season") or die("registry: season required"))
    teams, unmapped = x.get("teams") or die("registry: no teams"), x.get("unmapped", [])
    if x.get("count") != len(teams) + len(unmapped): die(f"registry {season}: {len(teams)} mapped + {len(unmapped)} unmapped != {x.get('count')} on the index")
    ids = [t["cfb_id"] for t in teams] + [u["cfb_id"] for u in unmapped]
    if len(set(ids)) != len(ids): die(f"registry {season}: a cfbstats team id appears twice")
    espn = [t["espn_id"] for t in teams]
    if len(set(espn)) != len(espn): die(f"registry {season}: an ESPN team id is joined to two cfbstats teams")
    for t in teams:
        for k in ("cfb_id", "cfb_name", "espn_id", "name"):
            if not t.get(k): die(f"registry {season}: '{k}' missing for {t.get('cfb_name')}")
        if not isinstance(t["cfb_id"], int): die(f"registry {season}: cfbstats id must be an integer ({t['cfb_name']})")
    d = load_or("registry.json", {"seasons": {}})
    d["seasons"][season] = {k: x[k] for k in ("source_url", "count", "teams", "unmapped") if k in x}
    d["seasons"][season]["retrieved_at"] = now_iso()
    save("registry.json", d)
    print(f"STORED registry {season}: {len(teams)} of {x['count']} cfbstats teams joined to ESPN" + (f"; unmapped: {', '.join(u['cfb_name'] for u in unmapped)}" if unmapped else ""))


# ================================================================ team seasons
TEAM_KEYS = ["pf", "pa", "total_yds", "rush_yds", "pass_yds", "to_lost", "to_gained", "third_conv", "third_att"]
MAX_GAMES = 17  # sanity cap: no FBS season (12 regular + title game + full playoff run) is longer


def check_team_game(g, tag):
    need_ints(dict(g, cmp=0, att=0), TEAM_KEYS, tag)
    datetime.date.fromisoformat(g["date"])
    if not g.get("event") or not g.get("opp"): die(f"{tag}: event and opponent required")
    if g.get("site") not in ("H", "A", "N"): die(f"{tag}: bad site")
    if g["total_yds"] != g["rush_yds"] + g["pass_yds"]: die(f"{tag}: total yards {g['total_yds']} != rushing {g['rush_yds']} + passing {g['pass_yds']}")
    if not 0 <= g["third_conv"] <= g["third_att"]: die(f"{tag}: third-down conversions exceed attempts")
    if min(g["to_lost"], g["to_gained"], g["pf"], g["pa"]) < 0: die(f"{tag}: negative count")
    wl = "W" if g["pf"] > g["pa"] else "L" if g["pf"] < g["pa"] else "T"
    if g.get("result") != f"{wl} {g['pf']}-{g['pa']}": die(f"{tag}: result '{g.get('result')}' disagrees with the score")
    if "rush" in g or "rec" in g: die(f"{tag}: per-game player arrays are not stored in this repo")


YARD_KEYS = {"rush_yds", "pass_yds", "total_yds", "yds"}
LABEL = {"rush_yds": "rushing yards", "pass_yds": "passing yards", "total_yds": "total yards", "yds": "yards"}


def compare(got, want, tag):
    """Counts (games, points, turnovers, third downs, carries, catches, TD) must match exactly.  Season yardage may
    differ by a hair (a late stat correction on one side): up to max(5, 0.2%) for teams or max(3, 0.5%) for players.
    Any such difference is returned as a note that is shown on the page; anything larger is refused."""
    notes, bad = [], {}
    for k, v in want.items():
        g = got.get(k)
        if g == v: continue
        tol = max(5, round(0.002 * abs(v))) if k in ("rush_yds", "pass_yds", "total_yds") else max(3, round(0.005 * abs(v))) if k == "yds" else 0
        if k in YARD_KEYS and abs(g - v) <= tol: notes.append(f"{LABEL[k]} {g:,} in ESPN box scores vs {v:,} on cfbstats")
        else: bad[k] = (g, v)
    if bad: die(f"{tag}: ESPN box scores disagree with cfbstats season totals {bad} (ESPN, cfbstats)")
    return notes


def season_sums(games):
    return {"games": len(games), **{k: sum(g[k] for g in games) for k in TEAM_KEYS}}


# Known source errors: one team, one season, one stat, pinned to the exact disagreeing pair.  Each entry lets
# that single comparison pass ONLY when ESPN's sum and cfbstats' total are exactly the recorded values; any other
# value (including a later correction on either side) falls back to the normal exact check.  Like the 0.15 ESPN
# passer-rating tolerance, this is one comparison only; every other field and season is checked as before.
SOURCE_EXCEPTIONS = {
    ("87", "2024", "third_att"): {  # carried over from daboodah-oss/nd-report, where it was diagnosed (tools/diag_third_downs.py there)
        "espn": 185, "cfbstats": 184,
        "why": "cfbstats lists Notre Dame 3-of-9 on third down vs Northern Illinois (2024-09-07); the official "
               "stat-crew box score (niuhuskies.com boxscore 24108: '3rd. Down Conv.' UND 3 of 10), ESPN's box score "
               "(3-10) and ESPN's play-by-play (10 snaps) all give 10 attempts, so ESPN's 185 is stored"},
}


def apply_exceptions(tid, season, got, want, tag):
    """Swap in ESPN's value for a pinned known-source-error comparison.  Returns the notes to log and show."""
    notes = []
    for (t, s, k), e in SOURCE_EXCEPTIONS.items():
        if (t, s) != (str(tid), str(season)) or k not in want: continue
        if got.get(k) == e["espn"] and want[k] == e["cfbstats"]:
            want[k] = got[k]
            notes.append(f"{k} {e['espn']} stored from ESPN, cfbstats {e['cfbstats']} (known cfbstats error: {e['why']})")
            print(f"EXCEPTION applied ({tag}): {notes[-1]}")
        else:
            print(f"EXCEPTION not applied ({tag}): {k} ESPN {got.get(k)} / cfbstats {want[k]} is not the recorded pair "
                  f"{e['espn']} / {e['cfbstats']}; normal exact check")
    return notes


def team_season(x):
    """Store one team's season of box-score rows: {team_id, name, season, games, cfbstats|None, complete, check_note}.
    If cfbstats season totals are given they must match the sums (see compare), or nothing is stored.
    A completed season must come with cfbstats totals for the same number of games: it is sealed once stored."""
    tid, season, games = str(x["team_id"]), str(x["season"]), x.get("games") or die("team-season: no games")
    tag = f"team-season {x.get('name')} {season}"
    if len(games) > MAX_GAMES: die(f"{tag}: {len(games)} games is more than any FBS season")
    for g in games: check_team_game(g, f"team {x.get('name')} {season} {g.get('date')}")
    dates = [g["date"] for g in games]
    if dates != sorted(dates) or len(set(g["event"] for g in games)) != len(games): die(f"{tag}: games out of order or duplicated")
    cf = x.get("cfbstats")
    if x.get("complete") and not cf: die(f"{tag}: a completed season must match cfbstats season totals before it is stored")
    if cf:
        if cf["totals"]["games"] != len(games): die(f"{tag}: {len(games)} ESPN games vs {cf['totals']['games']} on cfbstats")
        got = season_sums(games)
        want = dict(cf["totals"])
        exc = apply_exceptions(tid, season, got, want, tag)
        diffs = exc + compare(got, want, tag)
    d = load_or("team.json", {"teams": {}, "ap": None})
    t = d["teams"].setdefault(tid, {"name": x.get("name"), "seasons": {}})
    t["name"] = x.get("name") or t.get("name")
    t["seasons"][season] = {"games": games, "complete": bool(x.get("complete")), "retrieved_at": now_iso(),
                            "check": (f"cfbstats season totals matched through {cf['through']}" + (f", except {'; '.join(diffs)}" if diffs else "")) if cf else x.get("check_note", "not cross-checked"),
                            "cfbstats_url": cf.get("url") if cf else x.get("cfbstats_url")}
    d["teams"] = dict(sorted(d["teams"].items(), key=lambda kv: int(kv[0])))
    save("team.json", d); print(f"STORED team {x.get('name')} {season}: {len(games)} games")


def ap_poll(p):
    for k in ("poll", "date", "top"):
        if not p.get(k): die(f"ap-poll: '{k}' required")
    datetime.date.fromisoformat(p["date"][:10])
    ranks = [t["rank"] for t in p["top"]]
    if ranks != sorted(ranks) or ranks[0] != 1 or len(p["top"]) < 5 or ranks[-1] > 25: die("ap-poll: need ranks 1..25 in order")
    for t in p["top"]:
        if not t.get("team_id") or not t.get("name"): die("ap-poll: team id and name required")
    if len({t["team_id"] for t in p["top"]}) != len(p["top"]): die("ap-poll: a team is listed twice")
    d = load_or("team.json", {"teams": {}, "ap": None})
    d["ap"] = dict(p, retrieved_at=now_iso()); save("team.json", d)
    print("STORED", p["poll"], p["date"][:10], ", ".join(f"{t['rank']} {t['name']}" for t in p["top"][:5]), "...")


# ================================================================ national player pools (Player tab)
NATREF_KEYS = {"qb": ["att", "cmp", "yds", "td", "int"], "rb": ["att", "yds", "td"], "wr": ["rec", "yds", "td"]}
RATING_TOL = 0.15  # a published passer rating can round 0.1 off the NCAA formula; this one comparison only


def natref_check(tab, name, line, games, die=die):
    """A national player's game log must have exactly his leaderboard G games and sum exactly to his leaderboard
    line; for QBs every game's listed passer rating must match the NCAA formula (within 0.15).  Refuses otherwise."""
    keys = NATREF_KEYS.get(tab) or die(f"natref: unknown tab {tab}")
    tag = f"natref {tab} {name}"
    if not games: die(f"{tag}: no games")
    for g in games:
        need_ints(dict(g, cmp=g.get("cmp", 0), att=g.get("att", g.get("cmp", 0))), keys, f"{tag} {g.get('date')}")
        datetime.date.fromisoformat(g["date"])
        if min(g[k] for k in keys if k != "yds") < 0: die(f"{tag} {g['date']}: negative count")
        if tab == "qb" and g["att"]:
            if g.get("src_rating") is None or abs(rating(g) - g["src_rating"]) > RATING_TOL:
                die(f"{tag} {g['date']}: listed rating {g.get('src_rating')} != NCAA formula {rating(g):.2f}")
    dates = [g["date"] for g in games]
    if dates != sorted(dates) or len(set(dates)) != len(dates): die(f"{tag}: games out of order or duplicated")
    if len(games) != line.get("g"): die(f"{tag}: {len(games)} games in the log vs G {line.get('g')} on the leaderboard")
    got = {k: sum(g[k] for g in games) for k in keys}
    want = {k: line.get(k) for k in keys}
    if got != want: die(f"{tag}: game log totals {got} != leaderboard line {want}")


def natref(x):
    """Replace one season's pool for one tab: {tab, season, data_through, positions, stats, players, dropped}."""
    tab, season = x.get("tab"), x.get("season")
    if tab not in NATREF_KEYS: die("natref: tab must be qb, rb or wr")
    if season not in config()["seasons"]: die(f"natref: season {season} is not in config.json")
    datetime.date.fromisoformat(x.get("data_through") or die("natref: data_through required"))
    players = x.get("players") or die("natref: no players")
    for pid, p in players.items():
        natref_check(tab, p.get("name"), p.get("line") or {}, p.get("games"))
    for key, s in (x.get("stats") or die("natref: no stats")).items():
        if len(s.get("top", [])) > 3: die(f"natref {tab} {key}: more than three in the Top 3")
        for pid in s.get("order", []) + s.get("top", []):
            if pid not in players: die(f"natref {tab} {key}: {pid} has no stored game log")
    f = logs_file(season)
    d = load_or(f, {})
    d[tab] = {k: x[k] for k in ("season", "data_through", "positions", "stats", "players", "dropped") if k in x}
    d[tab]["retrieved_at"] = now_iso()
    save(f, d); print(f"STORED natref {season} {tab}: {len(players)} players through {x['data_through']}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    fn = {"status": None, "registry": registry, "team-season": team_season, "ap-poll": ap_poll, "natref": natref}.get(cmd)
    if cmd == "status": status()
    elif fn: fn(arg())
    else: print(__doc__); sys.exit(1)
