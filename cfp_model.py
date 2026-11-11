#!/usr/bin/env python3
"""Budzilla's own Top 25 model for the Playoff tab: a documented blend of three published ideas,
computed only from the stored game rows in data/team.json (plus one combined FCS opponent node).
No network, no per-team adjustments, fully deterministic.  The assessment behind the blend is in
docs/cfp-model.md; the short version also shows on the page.

Components (each turned into a 0-100 percentile among FBS teams before blending):
  SRS ..... margin-based rating, Sports-Reference style: rating = average over a team's games of
            (margin capped at +/-28, home field worth 2.5 points) + opponent rating, iterated to
            convergence.  Rewards how a team plays, schedule-adjusted.  Weight 45.
  Colley .. the Colley Matrix: wins and losses only, schedule-adjusted by solving Colley's linear
            system.  Margin-blind on purpose, so it cannot be gamed by running up the score; it is
            the pure resume of who beat whom.  Weight 30.
  Resume .. explicit resume points: +1.0 per win over a team with a winning record, +0.5 more per
            win over an SRS Top 25 team, -0.75 per loss to a team at .500 or worse (a "bad loss"),
            with wins over FCS opponents worth a flat +0.1.  Ranked by points per game so a team is
            not rewarded merely for playing more games.  Weight 25.

Final score = .45 * SRS percentile + .30 * Colley percentile + .25 * Resume percentile; ties break on
the raw SRS rating, then team name, so the order is stable run to run.
"""
import json, os

MARGIN_CAP = 28.0
HOME_FIELD = 2.5
W_SRS, W_COLLEY, W_RESUME = 0.45, 0.30, 0.25
FCS_ID = "__FCS__"


def load_teams(root):
    p = os.path.join(root, "data", "team.json")
    return json.load(open(p)).get("teams", {}) if os.path.exists(p) else {}


def collect_games(teams, season):
    """Deduped completed games for one season: [(winner_id, loser_id, margin, home_id or None)].
    A game against an opponent with no FBS membership in team.json's registry sense (no stored team
    entry) is a game against the combined FCS node.  Ties are skipped (no FBS ties in the data era
    that matter here, and neither SRS nor Colley needs them)."""
    seen, games = set(), []
    ids = set(teams)
    for tid, t in teams.items():
        for g in t.get("seasons", {}).get(str(season), {}).get("games", []):
            ev = g.get("event")
            if not ev or ev in seen or g.get("pf") == g.get("pa"): continue
            seen.add(ev)
            op = str(g.get("opp_id", ""))
            op = op if op in ids else FCS_ID
            w, l = (tid, op) if g["pf"] > g["pa"] else (op, tid)
            home = tid if g.get("site") == "H" else op if g.get("site") == "A" else None
            games.append((w, l, abs(g["pf"] - g["pa"]), home))
    return games


def srs_ratings(nodes, games):
    """Iterated simple rating: r_i = mean over games of (signed capped margin, home-adjusted) + r_opp."""
    adj = {n: [] for n in nodes}
    for w, l, m, home in games:
        c = min(m, MARGIN_CAP)
        hw = HOME_FIELD if home == w else -HOME_FIELD if home == l else 0.0
        adj[w].append((l, c - hw))    # winner's margin, minus its home edge if it was home
        adj[l].append((w, -c - hw))   # loser's view: negative margin, home edge flips sign the same way
    r = {n: 0.0 for n in nodes}
    for _ in range(10000):
        delta = 0.0
        for n in nodes:
            if not adj[n]: continue
            v = sum(mv + r[o] for o, mv in adj[n]) / len(adj[n])
            delta = max(delta, abs(v - r[n])); r[n] = v
        mean = sum(r.values()) / len(r)
        for n in r: r[n] -= mean
        if delta < 1e-9: break
    return r


def colley_ratings(nodes, games):
    """Colley Matrix ratings: solve (2I + L) r = b, L the game-count Laplacian, b = 1 + (wins-losses)/2."""
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    import numpy as np
    A = np.zeros((n, n)); b = np.ones(n)
    wins = {x: 0 for x in nodes}; losses = {x: 0 for x in nodes}
    for w, l, _m, _h in games:
        wins[w] += 1; losses[l] += 1
        A[idx[w]][idx[l]] -= 1; A[idx[l]][idx[w]] -= 1
    for x in nodes:
        i = idx[x]
        A[i][i] = 2 + wins[x] + losses[x]
        b[i] = 1 + (wins[x] - losses[x]) / 2.0
    sol = np.linalg.solve(A, b)
    return {x: float(sol[idx[x]]) for x in nodes}


def percentile(values):
    """Each value's percentile (0-100) among the given {node: value}: 100 * (rank from bottom) / (n-1),
    ties sharing the average rank."""
    items = sorted(values.items(), key=lambda kv: kv[1])
    out, i = {}, 0
    n = len(items)
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]: j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1): out[items[k][0]] = 100.0 * avg / (n - 1) if n > 1 else 100.0
        i = j + 1
    return out


def compute(root, season):
    """Our Top 25 plus every ranked team's display line, from the stored rows alone.
    Returns {"top25": [team_id, ...], "lines": {team_id: {...}}, "through": last game date}."""
    teams = load_teams(root)
    games = collect_games(teams, season)
    nodes = sorted({x for g in games for x in g[:2]})
    fbs = [n for n in nodes if n != FCS_ID]
    srs = srs_ratings(nodes, games)
    col = colley_ratings(nodes, games)
    rec = {n: [0, 0] for n in nodes}
    for w, l, _m, _h in games: rec[w][0] += 1; rec[l][1] += 1
    winning = {n for n in nodes if rec[n][0] > rec[n][1]}
    srs_top25 = set(sorted(fbs, key=lambda n: -srs[n])[:25])
    resume = {}
    for n in nodes:
        pts = 0.0; qw = t25w = 0; bad = 0
        for w, l, _m, _h in games:
            if w == n:
                if l == FCS_ID: pts += 0.1
                else:
                    if l in winning: pts += 1.0; qw += 1
                    if l in srs_top25: pts += 0.5; t25w += 1
            elif l == n and w != FCS_ID and rec[w][0] <= rec[w][1]:
                pts -= 0.75; bad += 1
        gp = rec[n][0] + rec[n][1]
        resume[n] = pts / gp if gp else 0.0
    ps, pc, pr = percentile({n: srs[n] for n in fbs}), percentile({n: col[n] for n in fbs}), percentile({n: resume[n] for n in fbs})
    score = {n: W_SRS * ps[n] + W_COLLEY * pc[n] + W_RESUME * pr[n] for n in fbs}
    order = sorted(fbs, key=lambda n: (-score[n], -srs[n], teams.get(n, {}).get("name", n)))
    opp_srs = {n: [] for n in nodes}
    best_win, worst_loss = {}, {}
    for w, l, _m, _h in games:
        opp_srs[w].append(srs[l]); opp_srs[l].append(srs[w])
        if l != FCS_ID and (w not in best_win or srs[l] > srs[best_win[w]]): best_win[w] = l
        if w != FCS_ID and (l not in worst_loss or srs[w] < srs[worst_loss[l]]): worst_loss[l] = w
    sos_val = {n: (sum(opp_srs[n]) / len(opp_srs[n]) if opp_srs[n] else 0.0) for n in fbs}
    sos_rank = {n: i + 1 for i, n in enumerate(sorted(fbs, key=lambda n: -sos_val[n]))}
    names = {tid: t.get("name", tid) for tid, t in teams.items()}
    lines = {}
    for n in fbs:
        qw = sum(1 for w, l, _m, _h in games if w == n and l in winning)
        t25 = sum(1 for w, l, _m, _h in games if w == n and l in srs_top25)
        lines[n] = {"record": f"{rec[n][0]}-{rec[n][1]}", "sos_rank": sos_rank[n],
                    "best_win": ({"id": best_win[n], "name": names.get(best_win[n], best_win[n]),
                                  "record": f"{rec[best_win[n]][0]}-{rec[best_win[n]][1]}"} if n in best_win else None),
                    "worst_loss": ({"id": worst_loss[n], "name": names.get(worst_loss[n], worst_loss[n]),
                                    "record": f"{rec[worst_loss[n]][0]}-{rec[worst_loss[n]][1]}"} if n in worst_loss else None),
                    "quality_wins": qw, "top25_wins": t25,
                    "score": round(score[n], 2), "srs": round(srs[n], 2)}
    through = max((g["date"] for t in teams.values() for g in t.get("seasons", {}).get(str(season), {}).get("games", [])), default=None)
    return {"top25": order[:25], "lines": lines, "through": through,
            "weights": {"srs": W_SRS, "colley": W_COLLEY, "resume": W_RESUME},
            "margin_cap": MARGIN_CAP, "home_field": HOME_FIELD}
