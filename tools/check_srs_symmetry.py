#!/usr/bin/env python3
"""Regression check for cfp_model.srs_ratings (offline, reads data/team.json only).

For every stored game, each season in config.json: solve SRS on that one game alone.  A single game
converges only when the winner's and loser's adjacency terms sum to exactly 0, and then the
winner-minus-loser rating gap equals the winner's term (capped margin minus its home edge).  The
2026-11-21 fix (docs/cfp-model.md) made the loser's term -(c - hw); the old -c - hw failed this.
Usage: python3 tools/check_srs_symmetry.py   (exit 0 = every game symmetric)"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import cfp_model as m

bad = n = 0
teams = m.load_teams(ROOT)
for season in json.load(open(os.path.join(ROOT, "config.json")))["seasons"]:
    for w, l, mg, home in m.collect_games(teams, season):
        c = min(mg, m.MARGIN_CAP)
        hw = m.HOME_FIELD if home == w else -m.HOME_FIELD if home == l else 0.0
        r = m.srs_ratings([w, l], [(w, l, mg, home)])
        n += 1
        if abs((r[w] - r[l]) - (c - hw)) > 1e-9 or abs(r[w] + r[l]) > 1e-9:
            bad += 1
            if bad <= 10: print(f"ASYMMETRIC {season} {w} beat {l} by {mg} (home {home}): gap {r[w]-r[l]:.3f}, want {c-hw:.3f}")
print(f"{'FAIL' if bad else 'OK'}: {n - bad}/{n} stored games have adjacency terms summing to 0")
sys.exit(1 if bad else 0)
