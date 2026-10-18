#!/usr/bin/env python3
"""Collect fresh data for the College Football page without any AI step.

Runs inside GitHub Actions (or any machine with open internet). Each section is
independent: a failure keeps that section's stored data, is logged, and makes
the script exit 1 at the end (so GitHub emails the owner), but every section
that did succeed is still saved and the page is still rebuilt.

Sections, in order (seasons from config.json; only the current season refreshes,
earlier seasons are collected once and then sealed):
  registry_<season> .. cfbstats.com team index for the season, joined to ESPN team ids (collect_tabs.py)
  ap_poll ............ ESPN rankings JSON, AP Top 25 (poll name, week, release date)
  team_<season> ...... every registry team's ESPN schedule + box scores, cross-checked against
                       its cfbstats.com season team totals (collect_tabs.py)
  natref_<season>_<tab>  cfbstats.com national passing / rushing / receiving leaders, top 20 per
                       tracked stat, each player's linked game log (collect_natref.py)

QUICK=1 (the 20-minute game-window checks): read ESPN's FBS scoreboard for today and
yesterday (Eastern) and exit at once, writing .nochange, unless some FBS game has gone
final that the stored data has not seen.  Two requests; a full run otherwise.
"""
import datetime as dt, json, os, re, sys, time, traceback
from zoneinfo import ZoneInfo
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update as U  # noqa: E402  (the same validated editors every store goes through)

ROOT = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")
CFG = U.config()
SEASONS = sorted(CFG["seasons"])
SEASON = CFG["current_season"]
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
UA = {"User-Agent": "Mozilla/5.0 (compatible; college-football/1.0; +https://github.com/daboodah-oss/college-football)"}
# cfbstats leaderboard abbreviations -> full team names (leaderboards abbreviate; the team index does not)
TEAM_FIX = {"Oregon St": "Oregon State", "Miss St": "Mississippi State", "Coast Car": "Coastal Carolina",
            "SJSU": "San Jose State", "Va Tech": "Virginia Tech", "Miami (Fl)": "Miami (FL)",
            "Sam Hou St": "Sam Houston", "Wk Forest": "Wake Forest", "Okla St": "Oklahoma State",
            "N Texas": "North Texas", "Ariz St": "Arizona State", "Mich St": "Michigan State",
            "Ga Tech": "Georgia Tech", "Ga South": "Georgia Southern", "S Carolina": "South Carolina",
            "N Carolina": "North Carolina", "N'western": "Northwestern",
            "WKU": "Western Kentucky", "CSU": "Colorado State", "BC": "Boston College"}
LOG, FAILED, NOTES = [], [], {"finals_seen": set()}


def log(msg):
    print(msg); LOG.append(msg)


class _Raw:  # offline testing: OFFLINE_RAW=<dir of saved pages>
    def __init__(s, t): s.status_code, s.text = int(t.split("\n", 1)[0]), t.split("\n", 1)[1]
    def json(s): return json.loads(s.text)
    def raise_for_status(s):
        if s.status_code >= 400: raise ValueError(f"HTTP {s.status_code}")


_S = requests.Session()
_LAST = {}


def get(url, **kw):
    if os.environ.get("OFFLINE_RAW"):
        f = os.path.join(os.environ["OFFLINE_RAW"], re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + ".txt")
        return _Raw(open(f).read())
    host = url.split("/")[2]
    if "cfbstats" in host:  # be polite to cfbstats: at most ~3 requests a second
        wait = 0.35 - (time.time() - _LAST.get(host, 0))
        if wait > 0: time.sleep(wait)
    for attempt in range(3):  # a transient network error or 5xx gets two retries; a 4xx is final
        try:
            r = _S.get(url, headers=UA, timeout=30, **kw)
            _LAST[host] = time.time()
            if r.status_code < 500 and r.status_code != 429: break
        except requests.RequestException:
            if attempt == 2: raise
        time.sleep(2 * (attempt + 1))
    if os.environ.get("SAVE_RAW"):  # debugging aid: keep exactly what each source returned
        d = os.path.join(ROOT, "raw"); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, re.sub(r"[^A-Za-z0-9]+", "_", url)[-120:] + ".txt"), "w").write(f"{r.status_code}\n{r.text}")
    r.raise_for_status()
    return r


def mark_fresh(name):
    """Record when a section last collected successfully (shown on the page as 'last checked')."""
    p = os.path.join(ROOT, "data", "freshness.json")
    d = json.load(open(p)) if os.path.exists(p) else {}
    d[name] = dt.datetime.now(ET).isoformat(timespec="minutes")
    json.dump(d, open(p, "w"), indent=1)


def section(name):
    def wrap(fn):
        def run(*a, **k):
            try:
                out = fn(*a, **k)
                mark_fresh(name)
                return out
            except SystemExit as e:  # update.py refused the data
                FAILED.append(name); log(f"[{name}] REFUSED by validator (exit {e.code})")
            except Exception as e:
                FAILED.append(name); log(f"[{name}] FAILED: {e}"); traceback.print_exc()
        return run
    return wrap


def through_date(html):
    m = re.search(r"through\s+(\d{2})/(\d{2})/(\d{4})", html, re.I) or re.search(r"through\s+(\d{2})/(\d{2})/(\d{2})\b", html, re.I)
    if not m: return None
    y = int(m.group(3)); y = y + 2000 if y < 100 else y
    return dt.date(y, int(m.group(1)), int(m.group(2))).isoformat()


def ival(x):
    return int(str(x).replace(",", "").strip())


# ---------------------------------------------------------------- game-window quick check (league-wide)
def quick_check():
    """True if any FBS game ESPN marks final today or yesterday (Eastern) is not yet handled: not stored in
    data/team.json for that team's current season, and not seen as final by the last full run."""
    reg = {t["espn_id"] for t in U.load_or("registry.json", {"seasons": {}})["seasons"].get(str(SEASON), {}).get("teams", [])}
    if not reg: log("quick check: no current-season registry stored yet"); return True
    td = U.load_or("team.json", {"teams": {}})["teams"]
    have = {(tid, g["event"]) for tid, t in td.items() for g in t["seasons"].get(str(SEASON), {}).get("games", [])}
    seen = set(U.load_or("last_run.json", {}).get("finals_seen", []))
    today = dt.datetime.now(ET).date()
    for d in (today, today - dt.timedelta(days=1)):
        j = get(f"{ESPN}/scoreboard?groups=80&limit=500&dates={d:%Y%m%d}").json()
        for ev in j.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            if not (comp.get("status") or ev.get("status") or {}).get("type", {}).get("completed"): continue
            for c in comp.get("competitors", []):
                tid = str(c.get("id"))
                if tid in reg and (tid, str(ev["id"])) not in have and str(ev["id"]) not in seen:
                    log(f"quick check: new final {d} {ev.get('name', ev['id'])}")
                    return True
    return False


def main():
    if os.environ.get("QUICK"):
        if not quick_check():
            print("quick check: no new FBS final"); open(os.path.join(ROOT, ".nochange"), "w").write("1")
            sys.exit(0)
    import collect_tabs   # team registry, AP poll, league-wide team seasons
    import collect_natref  # national QB / RB / WR pools, one per season
    me = sys.modules[__name__]
    collect_tabs.run(me, U)
    collect_natref.run(me, U)
    log("FAILED sections: " + (", ".join(FAILED) if FAILED else "none"))
    prev = U.load_or("last_run.json", {})
    seen = sorted(NOTES["finals_seen"]) or prev.get("finals_seen", [])
    open(os.path.join(ROOT, "data", "last_run.json"), "w").write(
        json.dumps({"at": dt.datetime.now(ET).isoformat(timespec="minutes"), "failed": FAILED, "log": LOG, "finals_seen": seen}, indent=1))
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
