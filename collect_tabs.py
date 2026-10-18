#!/usr/bin/env python3
"""Team registry, AP poll and league-wide team seasons for the Team tab.  Called from collect.py (no AI step).

Sources
  team registry .......... cfbstats.com team index per season (https://cfbstats.com/{season}/team/index.html),
                           joined by name to ESPN's college-football team list (ESPN team ids)
  AP Top 25 .............. ESPN rankings JSON (AP Top 25 entry: poll name, week, release date)
  team game rows ......... ESPN team schedule JSON (finals, scores) + ESPN game summary JSON (box score)
  season cross-checks .... cfbstats.com team pages: season team statistics

Every stored row is checked before it is written (update.py): total yards must equal rushing plus passing,
the score must match the schedule, turnovers must equal fumbles lost plus interceptions, and each season must
match cfbstats.com's season totals once cfbstats has posted the same games.  A completed season must match
before it is stored at all, and is then sealed: never collected again.  The cross-check is also what proves
each registry join: a wrong ESPN id cannot reproduce that cfbstats team's season totals.
"""
import datetime as dt, io, re, unicodedata

import pandas as pd

ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"


def num(d, k):
    return int(float(str(d[k]).replace(",", "")))


def norm(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"['’.]", "", s)
    s = re.sub(r"[,()\-/]", " ", s)
    s = re.sub(r"\bst\b$", "state", s.strip())
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------ registry
def cfb_team_ids(C, season):
    html = C.get(f"https://cfbstats.com/{season}/team/index.html").text
    out = {}
    for m in re.finditer(r'href="/?(?:https://cfbstats\.com)?/?(\d{4})/team/(\d+)/index\.html">([^<]+)</a>', html):
        if int(m.group(1)) == int(season): out[m.group(3).strip()] = int(m.group(2))
    return out


_ESPN_TEAMS = {}


def espn_teams(C, which):
    """ESPN team list: 'fbs' (groups=80) or 'all' (every college team ESPN lists).  [{id, location, ...}]"""
    if which not in _ESPN_TEAMS:
        url = f"{ESPN}/teams?limit=1000" + ("&groups=80" if which == "fbs" else "")
        j = C.get(url).json()
        teams = [t["team"] for s in j.get("sports", []) for l in s.get("leagues", []) for t in l.get("teams", [])]
        _ESPN_TEAMS[which] = [{"espn_id": str(t["id"]), "location": t.get("location") or "", "nickname": t.get("name") or "",
                               "display": t.get("displayName") or "", "short": t.get("shortDisplayName") or "",
                               "abbr": t.get("abbreviation") or ""} for t in teams]
    return _ESPN_TEAMS[which]


def join(C, cfb_name, aliases):
    """The ESPN team for a cfbstats team-index name, or (None, why).  Exact normalized names only, FBS list first."""
    want = [cfb_name] + ([aliases[cfb_name]] if cfb_name in aliases else [])
    for which in ("fbs", "all"):
        teams = espn_teams(C, which)
        for field in ("location", "short", "display"):
            for w in want:
                hits = [t for t in teams if norm(t[field]) == norm(w)]
                if len(hits) == 1: return hits[0], f"{'alias' if w != cfb_name else 'name'} = ESPN {field} ({which} list)"
                if len(hits) > 1: return None, f"'{w}' matches {len(hits)} ESPN teams by {field}"
    return None, "no ESPN team with that name"


def registry(C, U, season):
    d = U.load_or("registry.json", {"seasons": {}})["seasons"].get(str(season))
    if season < C.SEASON and d and not d.get("unmapped"):
        print(f"[registry] {season}: sealed ({len(d['teams'])} teams)"); return
    url = f"https://cfbstats.com/{season}/team/index.html"
    ids = cfb_team_ids(C, season)
    if len(ids) < 100: raise ValueError(f"cfbstats {season} team index lists only {len(ids)} teams")
    aliases = C.CFG.get("registry_aliases", {})
    teams, unmapped = [], []
    for name, cid in sorted(ids.items()):
        t, how = join(C, name, aliases)
        if t: teams.append({"cfb_id": cid, "cfb_name": name, "espn_id": t["espn_id"], "name": t["location"] or t["short"],
                            "nickname": t["nickname"], "abbr": t["abbr"], "how": how})
        else: unmapped.append({"cfb_id": cid, "cfb_name": name, "why": how})
    dup = {t["espn_id"] for t in teams if sum(1 for x in teams if x["espn_id"] == t["espn_id"]) > 1}
    for t in [t for t in teams if t["espn_id"] in dup]:  # one ESPN id joined twice: neither join is trusted
        teams.remove(t); unmapped.append({"cfb_id": t["cfb_id"], "cfb_name": t["cfb_name"], "why": f"ESPN id {t['espn_id']} also joined to another cfbstats team"})
    U.registry({"season": season, "source_url": url, "count": len(ids), "teams": teams, "unmapped": unmapped})
    C.log(f"[registry] {season}: {len(ids)} teams on the cfbstats index, {len(teams)} joined to ESPN ids"
          + (f"; UNMAPPED: {'; '.join(u['cfb_name'] + ' (' + u['why'] + ')' for u in unmapped)}" if unmapped else ""))
    if unmapped: raise ValueError(f"{len(unmapped)} cfbstats teams could not be joined to an ESPN team id")


# ------------------------------------------------------------------ ESPN
def espn_completed(C, team_id, season):
    """Completed games for a team and season (regular season + postseason), with scores, by Eastern date."""
    out = {}
    for st in (2, 3):
        j = C.get(f"{ESPN}/teams/{team_id}/schedule?season={season}&seasontype={st}").json()
        for ev in j.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            stype = (comp.get("status") or ev.get("status") or {}).get("type", {})
            if not stype.get("completed") or re.search(r"CANCEL|POSTPONE|FORFEIT", str(stype.get("name", "")), re.I): continue
            me = next((c for c in comp.get("competitors", []) if str(c.get("id")) == str(team_id)), None)
            op = next((c for c in comp.get("competitors", []) if str(c.get("id")) != str(team_id)), None)
            if not me or not op: continue
            sc = lambda c: int(float(c["score"].get("value", c["score"].get("displayValue")) if isinstance(c.get("score"), dict) else c.get("score")))
            date = dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(C.ET).date().isoformat()
            pf, pa = sc(me), sc(op)
            out[str(ev["id"])] = {"event": str(ev["id"]), "date": date,
                                  "opp": op.get("team", {}).get("location") or op.get("team", {}).get("displayName", ""),
                                  "opp_id": str(op.get("id")),
                                  "site": "N" if comp.get("neutralSite") else ("H" if me.get("homeAway") == "home" else "A"),
                                  "pf": pf, "pa": pa, "result": f"{'W' if pf > pa else 'L' if pf < pa else 'T'} {pf}-{pa}"}
    return sorted(out.values(), key=lambda g: g["date"])


def box_row(C, g, team_id):
    """Add box-score team stats to a schedule row.  (No per-game player arrays: this page has no school skill tabs.)"""
    j = C.get(f"{ESPN}/summary?event={g['event']}").json()
    bt = {str(t["team"]["id"]): {s["name"]: s.get("displayValue") for s in t.get("statistics", [])} for t in j["boxscore"]["teams"]}
    me = bt[str(team_id)]; op = next(v for k, v in bt.items() if k != str(team_id))
    tag = f"box {g['date']} {g['opp']}"
    for c in (j.get("header", {}).get("competitions") or [{}])[0].get("competitors", []):
        s = c.get("score")
        if s not in (None, ""):
            want = g["pf"] if str(c.get("id")) == str(team_id) else g["pa"]
            if int(float(s)) != want: raise ValueError(f"{tag}: summary score {s} != schedule score {want}")
    conv, att = (int(x) for x in str(me["thirdDownEff"]).split("-"))
    lost = num(me, "fumblesLost") + num(me, "interceptions")
    gained = num(op, "fumblesLost") + num(op, "interceptions")
    if "turnovers" in me and num(me, "turnovers") != lost: raise ValueError(f"{tag}: turnovers {me['turnovers']} != fumbles lost + interceptions {lost}")
    return dict(g, total_yds=num(me, "totalYards"), rush_yds=num(me, "rushingYards"), pass_yds=num(me, "netPassingYards"),
                to_lost=lost, to_gained=gained, third_conv=conv, third_att=att)


# ------------------------------------------------------------------ cfbstats
def cfb_team_totals(C, season, cfb_id):
    """Season totals from a cfbstats team page: {games, pf, pa, rush_yds, pass_yds, total_yds, third_att, third_conv, to_lost, to_gained}."""
    url = f"https://cfbstats.com/{season}/team/{cfb_id}/index.html"
    html = C.get(url).text
    vals, group = {}, ""
    for t in pd.read_html(io.StringIO(html)):
        if t.shape[1] < 3: continue
        for _, r in t.iterrows():
            lab, a, b = (str(x).strip() for x in r.iloc[:3])
            if a.lower() in ("nan", lab.lower()) and b.lower() in ("nan", lab.lower()): group = lab; continue  # group header row
            if ":" in lab: group, lab = (x.strip() for x in lab.split(":", 1))
            vals[(group.lower(), lab.lower())] = (a, b)
    def parts(group, label, side):
        v = vals.get((group, label)) or next((v for (g, l), v in vals.items() if g.startswith(group) and l == label), None)
        if not v: raise ValueError(f"cfbstats {season} team {cfb_id}: no '{group}: {label}' row; rows seen: {sorted(vals)[:60]}")
        return [int(float(x.replace(",", ""))) for x in re.split(r"\s+-\s+", v[side])]
    g, pf = parts("scoring", "games - points", 0); _, pa = parts("scoring", "games - points", 1)
    rush = parts("rushing", "attempts - yards - td", 0)[1]
    pas = parts("passing", "yards", 0)[0]
    tot = parts("total offense", "plays - yards", 0)[1]
    t_att, t_conv = parts("3rd down conversions", "attempts - conversions", 0)
    int_thrown = parts("passing", "attempts - completions - interceptions - td", 0)[2]
    opp_int_thrown = parts("passing", "attempts - completions - interceptions - td", 1)[2]
    fum_lost = parts("fumbles", "number - lost", 0)[1]; opp_fum_lost = parts("fumbles", "number - lost", 1)[1]
    return {"through": C.through_date(html), "url": url,
            "totals": {"games": g, "pf": pf, "pa": pa, "rush_yds": rush, "pass_yds": pas, "total_yds": tot,
                       "third_att": t_att, "third_conv": t_conv, "to_lost": int_thrown + fum_lost, "to_gained": opp_int_thrown + opp_fum_lost}}


# ------------------------------------------------------------------ sections
def ap_poll(C, U):
    j = C.get(f"{ESPN}/rankings").json()
    r = next((x for x in j.get("rankings", []) if x.get("type") == "ap" or "AP" in x.get("name", "")), None)
    if not r: raise ValueError("no AP poll in ESPN rankings")
    if str(C.SEASON) not in (r.get("headline", "") + r.get("date", "")): raise ValueError(f"AP poll is not for {C.SEASON}: {r.get('headline')}")
    ranks = sorted(r["ranks"], key=lambda x: x["current"])
    top = [{"rank": x["current"], "team_id": str(x["team"]["id"]), "name": x["team"].get("location") or x["team"].get("name"),
            "nickname": x["team"].get("name", ""), "abbr": x["team"].get("abbreviation", ""), "record": x.get("recordSummary", ""),
            "first_place": x.get("firstPlaceVotes", 0)} for x in ranks if 1 <= x["current"] <= 25]
    U.ap_poll({"poll": r.get("name", "AP Top 25"), "week": (r.get("occurrence") or {}).get("displayValue", ""),
               "headline": r.get("headline", ""), "date": r.get("date", "")[:10], "season": C.SEASON, "top": top,
               "source_url": "https://www.espn.com/college-football/rankings"})


def team_seasons(C, U, season):
    reg = U.load_or("registry.json", {"seasons": {}})["seasons"].get(str(season))
    if not reg: raise ValueError(f"no {season} registry stored; team seasons cannot be collected")
    d = U.load_or("team.json", {"teams": {}, "ap": None})
    failed, done, sealed = [], 0, 0
    for t in reg["teams"]:
        stored = d["teams"].get(t["espn_id"], {}).get("seasons", {}).get(str(season))
        if stored and stored.get("complete") and str(stored.get("check", "")).startswith("cfbstats"):
            sealed += 1; continue  # a finished season that matched cfbstats never changes
        try: team_job(C, U, d, t, season, stored); done += 1
        except SystemExit: failed.append(f"{t['name']} (refused, see above)"); C.log(f"[team] {t['name']} {season} REFUSED by validator")
        except Exception as e: failed.append(f"{t['name']} ({e})"); C.log(f"[team] {t['name']} {season} FAILED: {e}")
        d = U.load_or("team.json", {"teams": {}, "ap": None})
    C.log(f"[team] {season}: {len(reg['teams'])} registry teams; {sealed} sealed, {done} collected, {len(failed)} not stored")
    if failed: raise ValueError(f"{season} team seasons not stored: " + "; ".join(failed))


def team_job(C, U, d, t, season, stored):
    tid, name, cfb = t["espn_id"], t["name"], t["cfb_id"]
    have = {g["event"]: g for g in (stored or {}).get("games", [])}
    sched = espn_completed(C, tid, season)
    if season == C.SEASON: C.NOTES["finals_seen"].update(g["event"] for g in sched)
    rows = [have.get(g["event"]) or box_row(C, g, tid) for g in sched]
    if not rows: print(f"[team] {name} {season}: no completed games yet"); return
    cf, note = None, "not cross-checked: no cfbstats page found for this team"
    try:
        tt = cfb_team_totals(C, season, cfb)
        if tt["totals"]["games"] == len(rows): cf = tt
        else: note = f"not cross-checked yet: cfbstats has {tt['totals']['games']} games through {tt['through']}, ESPN {len(rows)}"
    except Exception as e:
        note = f"not cross-checked: cfbstats season totals unreadable ({e})"
    if season < C.SEASON and not cf:  # a finished season is stored only once it matches; otherwise it is a named failure
        raise ValueError(f"completed season cannot be cross-checked: {note}")
    U.team_season({"team_id": tid, "name": name, "season": season, "games": rows, "cfbstats": cf, "check_note": note,
                   "cfbstats_url": f"https://cfbstats.com/{season}/team/{cfb}/index.html", "complete": season < C.SEASON})
    print(f"[team] {name} {season}: {len(rows)} games; " + (f"matches cfbstats through {cf['through']}" if cf else note))
    chk = U.load("team.json")["teams"][tid]["seasons"][str(season)].get("check", "")
    if "known cfbstats error" in chk:  # a pinned update.SOURCE_EXCEPTIONS entry applied: name it in the run log
        C.log(f"[team] {name} {season}: EXCEPTION applied: " + chk.split(", except ", 1)[-1])


def run(C, U):
    """Run the team sections in order.  Each is independent; a failure keeps that section's stored data."""
    for s in C.SEASONS:
        C.section(f"registry_{s}")(lambda s=s: registry(C, U, s))()
    C.section("ap_poll")(lambda: ap_poll(C, U))()
    for s in sorted(C.SEASONS, reverse=True):
        C.section(f"team_{s}")(lambda s=s: team_seasons(C, U, s))()
