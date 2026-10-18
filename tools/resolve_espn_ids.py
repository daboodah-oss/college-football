#!/usr/bin/env python3
"""Show, and prove, how each cfbstats.com team joins to an ESPN team id in data/registry.json.

    python3 tools/resolve_espn_ids.py proofs [--season 2026]       no network: every join and its proof
    python3 tools/resolve_espn_ids.py candidates NAME [--season S]  network: ESPN teams that could be NAME

The registry (collect_tabs.registry) joins by exact normalized name, first among ESPN's FBS teams for
that season, and never by an id typed by hand.  A join is proven when that team's stored season matched
cfbstats.com's season totals (data/team.json `check` starts with "cfbstats"): a wrong ESPN id cannot
reproduce another team's totals.  `proofs` lists every join as proven, pending (current season, cfbstats
not caught up), or unproven, plus every unmapped cfbstats team.  `candidates` prints the ESPN teams whose
names come close to an unmapped cfbstats name, so the right entry can be added to config.json
`registry_aliases` (cfbstats name -> ESPN location name); the next run then has to prove it.
`candidates` needs network (run it in GitHub Actions, like collect.py).
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def proofs(season):
    reg = json.load(open(os.path.join(ROOT, "data", "registry.json")))["seasons"]
    td = json.load(open(os.path.join(ROOT, "data", "team.json")))["teams"]
    for s in sorted(reg):
        if season and s != str(season): continue
        r = reg[s]; tally = {"proven": 0, "pending": 0, "unproven": 0}
        print(f"== {s}: {r['count']} cfbstats teams, {len(r['teams'])} joined")
        for t in r["teams"]:
            blk = td.get(t["espn_id"], {}).get("seasons", {}).get(s)
            chk = str((blk or {}).get("check", ""))
            st = "proven" if chk.startswith("cfbstats") else "pending" if blk else "unproven"
            tally[st] += 1
            if st != "proven": print(f"  {st:<9} {t['cfb_name']} (cfbstats {t['cfb_id']}) -> ESPN {t['espn_id']} {t['name']}: {chk or 'no stored season'}")
        for u in r.get("unmapped", []): print(f"  UNMAPPED  {u['cfb_name']} (cfbstats {u['cfb_id']}): {u['why']}")
        print(f"  {tally}")


def candidates(name, season):
    import collect as C, collect_tabs as T
    fbs = T.espn_fbs_ids(C, season) or set()
    want = T.norm(name).split()
    for t in T.espn_teams(C, "all"):
        hay = " ".join(T.norm(t[f]) for f in ("location", "short", "display", "abbr"))
        if any(w in hay.split() for w in want if len(w) > 2) or T.norm(t["abbr"]) == T.norm(name):
            print(f"  ESPN {t['espn_id']:>6}  {'FBS ' if t['espn_id'] in fbs else '    '}{t['location']!r:<28} short {t['short']!r:<22} {t['display']!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["proofs", "candidates"]); ap.add_argument("name", nargs="?")
    ap.add_argument("--season", type=int)
    a = ap.parse_args()
    if a.cmd == "proofs": proofs(a.season)
    else: candidates(a.name or sys.exit("candidates needs a name"), a.season or json.load(open(os.path.join(ROOT, "config.json")))["current_season"])
