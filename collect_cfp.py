#!/usr/bin/env python3
"""Playoff snapshots for the Playoff tab.  Called from collect.py (no AI step).

Source: ESPN rankings JSON, the College Football Playoff poll (type "cfp", "Playoff Committee
Rankings").  The committee releases on Tuesday nights in November and December; the pipeline's
Wednesday full refresh lands the new release, and update.py stores a snapshot only when the
committee's Top 25 actually changed, so each release is kept exactly once and never rewritten.

"Our" Top 25 is cfp_model.compute: a documented blend (45% capped-margin SRS, 30% Colley Matrix,
25% resume points) over the stored team.json game rows only.  The snapshot freezes the committee
list, our list, the per-team lines and the agreement metrics for that week.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfp_model  # noqa: E402

ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"


def agreement_metrics(committee, ours):
    """The scorecard: Top 25 overlap, playoff-field (Top 12) overlap, exact positions, mean rank gap
    on the teams both lists share, and the headline Agreement % = the mean of the two overlaps."""
    crank = {t: i + 1 for i, t in enumerate(committee)}
    orank = {t: i + 1 for i, t in enumerate(ours)}
    common = set(crank) & set(orank)
    o25 = len(common)
    o12 = len(set(ours[:12]) & set(committee[:12]))
    exact = sum(1 for t in common if crank[t] == orank[t])
    avg = round(sum(abs(crank[t] - orank[t]) for t in common) / len(common), 2) if common else 0.0
    return {"overlap25": o25, "overlap12": o12, "avg_delta": avg, "exact": exact,
            "agreement": round(100 * (o25 / 25 + o12 / 12) / 2)}


def cfp_poll(C, U):
    stored = U.load_or("cfp.json", {"weeks": []}).get("weeks", [])
    j = C.get(f"{ESPN}/rankings?season={C.SEASON}").json()
    r = next((x for x in j.get("rankings", []) if x.get("type") == "cfp" or "Playoff" in x.get("name", "")), None)
    if not r: raise ValueError("no College Football Playoff poll in ESPN rankings")
    if str(C.SEASON) not in (r.get("headline", "") + r.get("date", "")):
        raise ValueError(f"CFP poll is not for {C.SEASON}: {r.get('headline')}")
    ranks = sorted(r["ranks"], key=lambda x: x["current"])
    committee = [str(x["team"]["id"]) for x in ranks if 1 <= x["current"] <= 25]
    if len(committee) != 25: raise ValueError(f"CFP poll holds {len(committee)} ranked teams, not 25")
    if stored and stored[-1]["committee"] == committee:
        C.log(f"[cfp] committee Top 25 unchanged since {stored[-1]['week']} ({stored[-1]['date']}); no new snapshot")
        return
    model = cfp_model.compute(C.ROOT, C.SEASON)
    ours = model["top25"]
    lines = {tid: model["lines"][tid] for tid in dict.fromkeys(committee + ours)}
    week = (r.get("occurrence") or {}).get("displayValue", "") or f"Week {len(stored) + 1}"
    snap = {"season": C.SEASON, "week": week, "date": r.get("date", "")[:10], "through": model["through"],
            "committee": committee, "ours": ours, "lines": lines,
            "metrics": agreement_metrics(committee, ours), "weights": model["weights"]}
    U.cfp(snap)
    C.log(f"[cfp] {week} ({snap['date']}): snapshot stored; agreement {snap['metrics']['agreement']}%, "
          f"overlap {snap['metrics']['overlap25']}/25, Top 12 overlap {snap['metrics']['overlap12']}/12")


def run(C, U):
    """One section: the Playoff snapshot.  Runs after the team sections, so our ranking uses this
    run's fresh game rows."""
    C.section("cfp_rankings")(lambda: cfp_poll(C, U))()
