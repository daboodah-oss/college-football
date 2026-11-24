#!/usr/bin/env python3
"""Playoff snapshots for the Playoff tab.  Called from collect.py (no AI step).

Source: ESPN rankings JSON, the College Football Playoff poll (type "cfp", "Playoff Committee
Rankings").  The committee releases on Tuesday nights in November and December; the pipeline's
Wednesday full refresh lands the new release, and update.py stores a snapshot only when the
committee's Top 25 actually changed, so each release is kept exactly once and never rewritten.

"Our" Top 25 is cfp_model.compute: a documented blend (45% capped-margin SRS, 30% Colley Matrix,
25% resume points) over the stored team.json game rows only.  The snapshot freezes the committee
list, our list, the per-team lines and the agreement metrics for that week.

From Week 13 (2026) each snapshot also freezes a Wins Above Bubble Top 25 (cfp_model.wab), a third
ranking for comparison only: it is not in the blend and does not change our Top 25.  Earlier snapshots
stay exactly as stored (no backfill).

From the first snapshot stored after 2026-11-21 each snapshot also freezes the Bias tab's inputs: the SRS
Top 25 (`srs_top25`) and, on every line, `srs_rank` (the team's SRS rank among all FBS teams).  Lines then
cover the bias universe, committee Top 25 + SRS Top 25 + WAB Top 25 (plus our Top 25, as before).
"""
import datetime, os, sys
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cfp_model  # noqa: E402

ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/college-football"
CFP_GAP_DAYS = 8         # the committee releases weekly; 8+ days without a stored release while it is ranking = missed
CFP_LAST_DAY = (12, 10)  # (month, day): after the final ranking (selection day, early December) the feed stays empty


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


def make_snapshot(root, season, committee, week, date):
    """One week's snapshot from the stored rows and the committee's 25 ids (no network)."""
    model = cfp_model.compute(root, season)
    ours = model["top25"]
    wab = cfp_model.wab(root, season, model["through"])   # comparison column only; not in the blend
    srs25 = model["srs_top25"]                            # Bias tab baseline; not in the blend
    lines = {tid: dict(model["lines"][tid], wab=wab["values"][tid], wab_rank=wab["ranks"].get(tid))
             for tid in dict.fromkeys(committee + ours + wab["top25"] + srs25)}
    return {"season": season, "week": week, "date": date, "through": model["through"],
            "committee": committee, "ours": ours, "lines": lines,
            "metrics": agreement_metrics(committee, ours), "weights": model["weights"],
            "wab": wab["top25"], "wab_bubble": dict(wab["bubble"], sigma=wab["sigma"]),
            "wab_metrics": agreement_metrics(committee, wab["top25"]), "srs_top25": srs25, "model": model["model"]}


def cfp_poll(C, U):
    stored = U.load_or("cfp.json", {"weeks": []}).get("weeks", [])
    j = C.get(f"{ESPN}/rankings?season={C.SEASON}").json()
    r = next((x for x in j.get("rankings", []) if x.get("type") == "cfp" or "Playoff" in x.get("name", "")), None)
    if not r:
        # ESPN drops the committee poll from this feed once a new week starts (seen Sunday 2026-11-22 to the Tuesday
        # release): between releases that is normal, not a failure.  It is a failure only when no release has been
        # stored for CFP_GAP_DAYS or more while the committee is still ranking (through CFP_LAST_DAY), i.e. a weekly
        # release was missed.
        today = datetime.datetime.now(ZoneInfo("America/New_York")).date()
        last = datetime.date.fromisoformat(stored[-1]["date"]) if stored else None
        if last and (today - last).days >= CFP_GAP_DAYS and today <= datetime.date(C.SEASON, *CFP_LAST_DAY):
            raise ValueError(f"no College Football Playoff poll in ESPN rankings, and the latest stored release "
                             f"({stored[-1]['week']}, {stored[-1]['date']}) is {(today - last).days} days old")
        C.log("[cfp] no committee poll in ESPN's rankings feed right now (normal between releases); "
              + (f"latest stored {stored[-1]['week']} ({stored[-1]['date']}); no new snapshot" if stored else "none stored yet"))
        return
    if str(C.SEASON) not in (r.get("headline", "") + r.get("date", "")):
        raise ValueError(f"CFP poll is not for {C.SEASON}: {r.get('headline')}")
    ranks = sorted(r["ranks"], key=lambda x: x["current"])
    committee = [str(x["team"]["id"]) for x in ranks if 1 <= x["current"] <= 25]
    if len(committee) != 25: raise ValueError(f"CFP poll holds {len(committee)} ranked teams, not 25")
    if stored and stored[-1]["committee"] == committee:
        C.log(f"[cfp] committee Top 25 unchanged since {stored[-1]['week']} ({stored[-1]['date']}); no new snapshot")
        return
    week = (r.get("occurrence") or {}).get("displayValue", "") or f"Week {len(stored) + 1}"
    snap = make_snapshot(C.ROOT, C.SEASON, committee, week, r.get("date", "")[:10])
    U.cfp(snap)
    C.log(f"[cfp] {week} ({snap['date']}): snapshot stored; agreement {snap['metrics']['agreement']}%, "
          f"overlap {snap['metrics']['overlap25']}/25, Top 12 overlap {snap['metrics']['overlap12']}/12; "
          f"WAB Top 12 overlap {snap['wab_metrics']['overlap12']}/12, bubble {snap['wab_bubble']['rating']}")


def run(C, U):
    """One section: the Playoff snapshot.  Runs after the team sections, so our ranking uses this
    run's fresh game rows."""
    C.section("cfp_rankings")(lambda: cfp_poll(C, U))()
