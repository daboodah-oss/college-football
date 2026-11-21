#!/usr/bin/env python3
"""Bias tab model: how far the committee's Top 25 sits from two pure-numbers baselines, per team and
rolled up by conference, for every stored Playoff snapshot that carries the bias fields.  No network.
Called by build_report.py after build_cfp.py.  Spec: docs/claude-spec-cfp-bias-analysis.md.

Both baselines come from this season's stored game results only (no preseason, no polls):
  SRS ... our margin rating (cfp_model.srs_ratings), the efficiency baseline; `srs_rank` frozen per line.
  WAB ... Wins Above Bubble (cfp_model.wab), the resume baseline; `wab_rank` frozen per line.
gap = baseline_rank - cfp_rank; positive = the committee ranks the team HIGHER than the baseline does.

The frozen snapshot is read as stored; nothing here is recomputed from game rows.  Conference comes from
the repo's conferences.json membership for the snapshot's season (the Conferences tab's source).
The summary sentences and the verdict follow fixed rules (thresholds below), so they are re-checkable."""
import statistics

SRS_T = 2.0      # an average gap vs SRS at least this far from zero is an efficiency gap worth explaining
WAB_T = 1.0      # an average gap vs WAB within +/- this is "explained by resume"; beyond it, same sign = not
MIN_N = 3        # the verdict only considers conferences with at least this many committee Top 25 teams


def r1(v):
    return None if v is None else round(v, 1) + 0.0   # + 0.0 turns -0.0 into 0.0


def sg(v, dp=1):
    """Signed number for the summary text: +2.3, -1.0, 0.0."""
    v = round(v, dp)
    return ("+" if v > 0 else "-" if v < 0 else "") + f"{abs(v):.{dp}f}"


def analyze(w, conf_of):
    comm, lines, names = w["committee"], w["lines"], w["names"]
    s25, wab25 = w["srs_top25"], w.get("wab") or []
    crank = {t: i + 1 for i, t in enumerate(comm)}
    conf = lambda t: conf_of.get(t, "Unknown")
    rows = []
    for t in comm:
        L = lines[t]; sr, wr = L.get("srs_rank"), L.get("wab_rank")
        rows.append({"id": t, "name": names[t], "conf": conf(t), "cfp": crank[t], "srs": sr,
                     "gap_srs": sr - crank[t], "wab": wr, "gap_wab": (wr - crank[t]) if wr else None})
    rows.sort(key=lambda r: (-r["gap_srs"], r["cfp"]))
    left = []
    for t in dict.fromkeys(s25 + wab25):
        if t in crank: continue
        by = [b for b, lst in (("SRS", s25), ("WAB", wab25)) if t in lst]
        L = lines[t]
        left.append({"id": t, "name": names[t], "conf": conf(t), "by": by,
                     "srs": L.get("srs_rank"), "wab": L.get("wab_rank")})
    left.sort(key=lambda x: (-len(x["by"]), x["srs"] if x["srs"] else 999, x["name"]))
    confs = []
    for c in dict.fromkeys(r["conf"] for r in rows):
        rs = [r for r in rows if r["conf"] == c]
        gs = [r["gap_srs"] for r in rs]; gw = [r["gap_wab"] for r in rs if r["gap_wab"] is not None]
        confs.append({"conf": c, "n": len(rs),
                      "avg_srs": r1(sum(gs) / len(gs)), "med_srs": r1(statistics.median(gs)),
                      "net_srs": len(rs) - sum(1 for t in s25 if conf(t) == c),
                      "avg_wab": r1(sum(gw) / len(gw)) if gw else None, "n_wab": len(gw),
                      "net_wab": (len(rs) - sum(1 for t in wab25 if conf(t) == c)) if wab25 else None,
                      "omissions": sum(1 for x in left if x["conf"] == c),
                      "_avg_srs": sum(gs) / len(gs), "_avg_wab": (sum(gw) / len(gw)) if gw else None})
    confs.sort(key=lambda x: (-x["_avg_srs"], x["conf"]))
    summary, verdict = summarize(rows, confs)
    for x in confs: x.pop("_avg_srs"); x.pop("_avg_wab")
    return {"rows": rows, "left": left, "confs": confs, "summary": summary, "verdict": verdict}


def resume_check(x, side):
    """The resume check for one conference, in words, or '' when it has no WAB average."""
    a, b = x["_avg_srs"], x["_avg_wab"]
    if b is None: return ""
    s = f"  Against Wins Above Bubble its average gap is {sg(b)}"
    if abs(a) > SRS_T and abs(b) <= WAB_T:
        return s + f": most of that efficiency gap is explained by {x['conf']}'s résumé, not its conference."
    if abs(a) > SRS_T and (b > 0) == (a > 0):
        return s + ", so the résumé does not explain the gap."
    return s + "."


def summarize(rows, confs):
    top, bot = confs[0], confs[-1]
    out = [f"The committee is kindest to {top['conf']} relative to SRS: an average gap of {sg(top['_avg_srs'])} spots "
           f"across its {top['n']} ranked team{'s' if top['n'] != 1 else ''}.{resume_check(top, 'pos')}"]
    if bot is not top:
        if bot["_avg_srs"] < 0:
            out.append(f"It is hardest on {bot['conf']}: {sg(bot['_avg_srs'])} spots across {bot['n']} "
                       f"team{'s' if bot['n'] != 1 else ''}.{resume_check(bot, 'neg')}")
        else:
            out.append(f"No conference sits below its SRS ranks on average; the lowest is {bot['conf']} at {sg(bot['_avg_srs'])} "
                       f"across {bot['n']} team{'s' if bot['n'] != 1 else ''}.")
    hi, lo = rows[0], rows[-1]
    single = []
    if hi["gap_srs"] > 0:
        single.append(f"the committee's No. {hi['cfp']} {hi['name']} is SRS No. {hi['srs']} ({sg(hi['gap_srs'], 0)})")
    if lo["gap_srs"] < 0:
        single.append(f"its No. {lo['cfp']} {lo['name']} is SRS No. {lo['srs']} ({sg(lo['gap_srs'], 0)})")
    if single:
        out.append("Largest single-team gaps: " + "; ".join(single) + ".")
    fav = [x for x in confs if x["n"] >= MIN_N and x["_avg_wab"] is not None and x["_avg_srs"] >= SRS_T and x["_avg_wab"] >= WAB_T]
    agn = [x for x in confs if x["n"] >= MIN_N and x["_avg_wab"] is not None and x["_avg_srs"] <= -SRS_T and x["_avg_wab"] <= -WAB_T]
    expl = [x for x in confs if x["n"] >= MIN_N and x["_avg_wab"] is not None and abs(x["_avg_srs"]) >= SRS_T and abs(x["_avg_wab"]) <= WAB_T]
    q = lambda x: f"{x['conf']} ({sg(x['_avg_srs'])} vs SRS, {sg(x['_avg_wab'])} vs WAB, n={x['n']})"
    if fav or agn:
        parts = []
        if fav: parts.append("in favor of " + " and ".join(q(x) for x in fav))
        if agn: parts.append("against " + " and ".join(q(x) for x in agn))
        v = "Verdict: bias indicated " + "; ".join(parts) + ".  The efficiency gap survives the résumé check."
        if expl: v += "  No bias indicated for " + " or ".join(q(x) for x in expl) + ": résumé explains it."
    elif expl:
        v = "Verdict: no bias indicated.  " + "; ".join(q(x) for x in expl) + (": résumé explains the gap." if len(expl) == 1 else ": résumé explains the gaps.")
    else:
        v = "Verdict: no clear bias in either direction this week."
    return out, v


def build(cfp_model, membership, check):
    """cfp_model is build_cfp.build's output; membership is conferences.json `members` ({season: {id: conf}})."""
    season = str(cfp_model.get("season"))
    conf_of = membership.get(season, {})
    weeks = []
    for w in cfp_model.get("weeks", []):
        if w.get("srs_top25"):
            for t in dict.fromkeys(w["committee"] + w["srs_top25"] + (w.get("wab") or [])):
                check(t in conf_of, f"bias {w['week']}: team id {t} has no {season} conference in conferences.json")
        weeks.append({"week": w["week"], "date": w["date"], "through": w.get("through"),
                      **(analyze(w, conf_of) if w.get("srs_top25") else {"rows": None})})
    trend_weeks = [w["week"] for w in weeks if w["rows"] is not None]
    trend = {}
    for w in weeks:
        if w["rows"] is None: continue
        for x in w["confs"]: trend.setdefault(x["conf"], {})[w["week"]] = x["avg_srs"]
    first = next((w["week"] for w in weeks if w["rows"] is not None), None)
    last = lambda c: trend[c].get(trend_weeks[-1])
    order = sorted(trend, key=lambda c: (last(c) is None, -(last(c) or 0), c))   # latest week's order, absent last
    return {"season": cfp_model.get("season"), "weeks": weeks, "first": first,
            "trend": {"weeks": trend_weeks, "rows": [{"conf": c, "cells": [trend[c].get(k) for k in trend_weeks]} for c in order]},
            "thresholds": {"srs": SRS_T, "wab": WAB_T, "min_n": MIN_N}}
