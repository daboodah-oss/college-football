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
The summary sentences and the verdict follow fixed rules (thresholds below), so they are re-checkable.

Centering (Jeff's ruling, 2026-11-21): the verdict and the resume check compare each conference's average
gap with that week's ALL-25 average gap (mean gap vs SRS over the committee's 25; mean gap vs WAB over the
committee teams that have a WAB rank), not with zero.  The all-25 average is structurally positive: a
committee team's rank is at most 25, while its baseline rank can be 30 or 40, so the gaps of any Top 25
average above zero unless the two lists hold the same teams.  Tables, chart and trend keep the RAW gaps;
centering is applied in the verdict layer only."""
import statistics

SRS_T = 2.0      # a centered average gap vs SRS at least this far from zero is an efficiency gap worth explaining
WAB_T = 1.0      # a centered average gap vs WAB within +/- this is "explained by resume"; beyond it, same sign = not
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
    allw = [r["gap_wab"] for r in rows if r["gap_wab"] is not None]
    field = {"srs": sum(r["gap_srs"] for r in rows) / len(rows), "wab": (sum(allw) / len(allw)) if allw else None}
    for x in confs:   # centered on the week's all-25 averages (verdict layer only)
        x["_c_srs"] = x["_avg_srs"] - field["srs"]
        x["_c_wab"] = None if x["_avg_wab"] is None or field["wab"] is None else x["_avg_wab"] - field["wab"]
    summary, verdict = summarize(rows, confs, field)
    for x in confs:
        for k in ("_avg_srs", "_avg_wab", "_c_srs", "_c_wab"): x.pop(k)
    return {"rows": rows, "left": left, "confs": confs, "summary": summary, "verdict": verdict,
            "field": {"srs": r1(field["srs"]), "wab": r1(field["wab"]), "n_wab": len(allw)}}


def resume_check(x):
    """The resume check for one conference, on centered values, in words ('' with no WAB average)."""
    a, b = x["_c_srs"], x["_c_wab"]
    if b is None: return ""
    s = f"  Against Wins Above Bubble it averages {sg(x['_avg_wab'])}, {rel(b)}"
    if abs(a) > SRS_T and abs(b) <= WAB_T:
        return s + f": most of that efficiency gap is explained by {x['conf']}'s résumé, not its conference."
    if abs(a) > SRS_T and (b > 0) == (a > 0):
        return s + ", so the résumé does not explain the gap."
    return s + "."


def rel(c):
    """A centered value in words: '1.8 above the all-25 average', '6.1 below the all-25 average'."""
    return f"{abs(round(c, 1)):.1f} {'above' if round(c, 1) >= 0 else 'below'} the all-25 average"


def summarize(rows, confs, field):
    top, bot = confs[0], confs[-1]
    plural = lambda n: f"{n} ranked team{'s' if n != 1 else ''}"
    out = [f"This week the committee's 25 average {sg(field['srs'])} spots vs SRS"
           + (f" and {sg(field['wab'])} vs WAB" if field["wab"] is not None else "")
           + ".  Any Top 25 averages above zero (see Method), so each conference is judged against these all-25 averages, not against zero."]
    out.append(f"The committee is kindest to {top['conf']} relative to SRS: {sg(top['_avg_srs'])} spots across its "
               f"{plural(top['n'])}, {rel(top['_c_srs'])}.{resume_check(top)}")
    if bot is not top:
        out.append(f"It is hardest on {bot['conf']}: {sg(bot['_avg_srs'])} spots across its {plural(bot['n'])}, "
                   f"{rel(bot['_c_srs'])}.{resume_check(bot)}")
    hi, lo = rows[0], rows[-1]
    single = []
    if hi["gap_srs"] > 0:
        single.append(f"the committee's No. {hi['cfp']} {hi['name']} is SRS No. {hi['srs']} ({sg(hi['gap_srs'], 0)})")
    if lo["gap_srs"] < 0:
        single.append(f"its No. {lo['cfp']} {lo['name']} is SRS No. {lo['srs']} ({sg(lo['gap_srs'], 0)})")
    if single:
        out.append("Largest single-team gaps: " + "; ".join(single) + ".")
    ok = [x for x in confs if x["n"] >= MIN_N and x["_c_wab"] is not None]
    fav = [x for x in ok if x["_c_srs"] >= SRS_T and x["_c_wab"] >= WAB_T]
    agn = [x for x in ok if x["_c_srs"] <= -SRS_T and x["_c_wab"] <= -WAB_T]
    expl = [x for x in ok if abs(x["_c_srs"]) >= SRS_T and abs(x["_c_wab"]) <= WAB_T]
    q = lambda x: f"{x['conf']} ({sg(x['_c_srs'])} vs SRS, {sg(x['_c_wab'])} vs WAB, n={x['n']})"
    head = "Verdict, measured against the all-25 averages: "
    if fav or agn:
        parts = []
        if fav: parts.append("in favor of " + " and ".join(q(x) for x in fav))
        if agn: parts.append("against " + " and ".join(q(x) for x in agn))
        v = head + "bias indicated " + "; ".join(parts) + ".  The efficiency gap survives the résumé check."
        if expl: v += "  No bias indicated for " + " or ".join(q(x) for x in expl) + ": résumé explains it."
    elif expl:
        v = head + "no bias indicated.  " + "; ".join(q(x) for x in expl) + (": résumé explains the gap." if len(expl) == 1 else ": résumé explains the gaps.")
    else:
        v = head + "no clear bias in either direction this week."
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
