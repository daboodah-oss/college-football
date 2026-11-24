#!/usr/bin/env python3
"""Offline negative tests for update.py's team-season comparison and the Playoff snapshot guards.  Exit 0 = all pass.

  python3 tools/test_validator.py

Each widened tolerance (docs/claude-spec-warnings-model-v2.md Part 1) is tested at its edge: the value just inside
must pass and be printed as a note; the value just outside must be refused; counts that stay exact (games, points)
must be refused at a difference of 1.  Also: an empty ESPN box score is refused, and a v2 snapshot without its
Dated component is refused."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import update as U  # noqa: E402

fails = []
def refused(fn):
    try: fn(); return False
    except SystemExit: return True
def case(what, cond):
    print(("PASS  " if cond else "FAIL  ") + what)
    if not cond: fails.append(what)

base = {"games": 12, "pf": 400, "pa": 300, "rush_yds": 2000, "pass_yds": 3000, "total_yds": 5000,
        "third_att": 170, "third_conv": 70, "to_lost": 15, "to_gained": 18}
def cmp(k, delta):
    got = dict(base); got[k] = base[k] + delta
    return lambda: U.compare(got, dict(base), "test")
# yardage: max(5, 0.5%): 2000 -> 10, 3000 -> 15, 5000 -> 25
for k, tol in (("rush_yds", 10), ("pass_yds", 15), ("total_yds", 25)):
    case(f"{k} off by {tol} (0.5%) passes with a note", not refused(cmp(k, tol)) and U.compare({**base, k: base[k] + tol}, dict(base), "t"))
    case(f"{k} off by {tol + 1} is refused", refused(cmp(k, tol + 1)))
small = dict(base, rush_yds=600)
case("small yardage: 5 passes (the floor)", not refused(lambda: U.compare(dict(small, rush_yds=605), dict(small), "t")))
case("small yardage: 6 is refused", refused(lambda: U.compare(dict(small, rush_yds=606), dict(small), "t")))
for k in ("third_att", "third_conv"):
    case(f"{k} off by 5 passes with a note", not refused(cmp(k, 5)) and U.compare({**base, k: base[k] - 5}, dict(base), "t"))
    case(f"{k} off by 6 is refused", refused(cmp(k, 6)))
for k in ("to_lost", "to_gained"):
    case(f"{k} off by 1 passes with a note", U.compare({**base, k: base[k] + 1}, dict(base), "t") != [])
    case(f"{k} off by 2 is refused", refused(cmp(k, 2)))
for k in ("pf", "pa", "games"):
    case(f"{k} off by 1 is refused (exact)", refused(cmp(k, 1)))
g = {"event": "1", "opp": "X", "date": "2025-12-13", "site": "N", "pf": 17, "pa": 16, "result": "W 17-16",
     "total_yds": 0, "rush_yds": 0, "pass_yds": 0, "third_att": 0, "third_conv": 0, "to_lost": 0, "to_gained": 0}
case("an empty ESPN box score is refused", refused(lambda: U.check_team_game(dict(g), "test")))
case("a normal game passes", not refused(lambda: U.check_team_game(dict(g, total_yds=300, rush_yds=200, pass_yds=100, third_att=12, third_conv=5), "test")))
case("total != rush + pass is still refused", refused(lambda: U.check_team_game(dict(g, total_yds=301, rush_yds=200, pass_yds=100, third_att=12), "test")))
# Playoff poll missing from ESPN's feed: normal between releases, a failure only after CFP_GAP_DAYS in season
import datetime as _dt, collect_cfp as CF  # noqa: E402
class _C:
    SEASON = 2026
    def __init__(s): s.logs = []
    def log(s, m): s.logs.append(m)
    def get(s, url):
        class R:
            def json(self): return {"rankings": [{"type": "ap", "name": "AP Top 25", "ranks": []}]}
        return R()
class _U:
    def __init__(s, last): s.last = last
    def load_or(s, f, d): return {"weeks": [{"week": "Week 12", "date": s.last, "committee": []}]} if s.last else {"weeks": []}
_today = _dt.datetime.now(CF.ZoneInfo("America/New_York")).date()
def _poll(days_ago, season=2026):
    c = _C(); c.SEASON = season
    try: CF.cfp_poll(c, _U((_today - _dt.timedelta(days=days_ago)).isoformat() if days_ago is not None else None)); return "ok"
    except ValueError: return "fail"
in_season = _today <= _dt.date(_today.year, *CF.CFP_LAST_DAY)
case("no CFP poll, nothing stored yet: not a failure", _poll(None) == "ok")
case("no CFP poll, latest release 7 days old: not a failure", _poll(7, _today.year) == "ok")
case("no CFP poll, latest release 8 days old: " + ("a failure (in season)" if in_season else "not a failure (after the final ranking)"),
     _poll(8, _today.year) == ("fail" if in_season else "ok"))
case("no CFP poll, 30 days old in a past season: not a failure", _poll(30, _today.year - 1) == "ok")
print(f"\n{'FAIL' if fails else 'OK'}: {len(fails)} failed")
sys.exit(1 if fails else 0)
