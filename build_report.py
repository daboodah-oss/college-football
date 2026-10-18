#!/usr/bin/env python3
"""Build the College Football page (cf.daboodah.com): any FBS teams and any national-leader
QBs, RBs and WRs, compared game by game across the seasons in config.json.

Reads data/*.json, validates every row, computes one model object, and writes
report.html (template.html with the model injected). No network access.

Usage:  python3 build_report.py [--root DIR] [--out report.html] [--standalone] [--as-of ISO]
Exit code is non-zero if any validation check fails; nothing is written then.
"""
import argparse, json, sys, datetime, hashlib, os
from html import escape
from zoneinfo import ZoneInfo

ERRORS = []


def check(cond, msg):
    if not cond:
        ERRORS.append(msg)


def build(root, as_of):
    import build_tabs
    cfg = json.load(open(os.path.join(root, "config.json")))
    seasons, cur = sorted(cfg["seasons"]), cfg["current_season"]
    tabs = build_tabs.build(root, cfg, check)
    T, PL = tabs["team"], tabs["player"]
    site = cfg["site"]

    # data freshness: what each part covers and when it was last successfully checked
    fp = os.path.join(root, "data", "freshness.json")
    fr = json.load(open(fp)) if os.path.exists(fp) else {}
    def d(iso): return datetime.date.fromisoformat(iso).strftime("%b %-d, %Y") if iso else "?"
    last_cur = max((e["last"] for e in T["index"].get(str(cur), [])), default=None)
    pools_cur = [PL[t]["pools"][str(cur)] for t in PL if PL[t]["pools"].get(str(cur), {}).get("status") == "ok"]
    fresh = {
        "team": {"what": f"{cur} team games through {d(last_cur)}; {', '.join(str(s) for s in seasons if s < cur)} complete and sealed",
                 "checked": fr.get(f"team_{cur}")},
        "ap": {"what": (f"{T['poll']['name']}" + (f", {T['poll']['week']}" if T['poll'].get('week') else "") + f", released {d(T['poll']['date'])}") if T["poll"] else "AP poll not collected yet",
               "checked": fr.get("ap_poll")},
        "player": {"what": f"{cur} national leaderboards through {d(max((p['data_through'] for p in pools_cur), default=None))}; earlier seasons final",
                   "checked": max((fr[k] for k in fr if k.startswith(f"natref_{cur}_")), default=None)},
    }
    now = datetime.datetime.fromisoformat(as_of)
    for v in fresh.values():
        v["stale"] = bool(v["checked"]) and (now - datetime.datetime.fromisoformat(v["checked"])).days >= 5

    notices = []
    lr_path = os.path.join(root, "data", "last_run.json")
    if os.path.exists(lr_path):
        lr = json.load(open(lr_path))
        if lr.get("failed"):
            notices.append("The latest automatic update could not refresh: " + ", ".join(lr["failed"]) + ". Those sections show the last verified data.")
    names = {"team": f"{cur} team data", "ap": "The AP poll", "player": f"{cur} national player pools"}
    for k, v in fresh.items():
        if v["stale"]: notices.append(f"{names[k]} has not refreshed in over 5 days (last checked {v['checked'][:10]}).")
    for t in PL:
        for s, p in PL[t]["pools"].items():
            if p["status"] != "ok": notices.append(p["message"])
    if T["missing"]:
        notices.append(f"{len(T['missing'])} registry team seasons are not on the page: their ESPN rows did not pass the cfbstats.com "
                       "cross-check (or have not been collected), so they cannot be picked.  The list is under Method on the Team tab.")
    sources = [{"label": f"cfbstats.com: {s} team index (registry)", "url": T["counts"][str(s)]["source_url"]} for s in seasons if str(s) in T["counts"]] + [
        {"label": "ESPN: team schedules and game box scores (site API)", "url": "https://www.espn.com/college-football/"},
        {"label": "ESPN: AP Top 25", "url": (T["poll"] or {}).get("source_url") or "https://www.espn.com/college-football/rankings"},
    ] + [{"label": f"cfbstats.com: {s} national {PL[t]['noun']} ({'passing' if t == 'qb' else 'rushing' if t == 'rb' else 'receiving'} leaders)",
          "url": PL[t]["pools"][str(s)]["stats"]["yds"]["source_url"]} for t in PL for s in seasons if PL[t]["pools"].get(str(s), {}).get("status") == "ok"]

    model = {
        "as_of": as_of,
        "site": {"name": site["name"], "eyebrow": site["eyebrow"], "title": site["title"].format(season=cur), "season": cur,
                 "seasons": seasons, "caps": cfg["caps"], "theme_key": site["theme_key"]},
        "data": tabs["data"], "team": T, "player": PL, "fresh": fresh, "notices": notices, "sources": sources,
    }
    return model, cfg


def check_manifest(root, html):
    """Problems with the web app manifest the page links, or [].

    An installed app takes its name, colours and icons from the manifest, so a
    broken link or a missing icon is an app with default chrome.  Pages serves
    the repo root, so every path resolves against `root`.  theme_color must
    match the page's theme-color meta tag, and both colours must appear in the
    built page, so the manifest cannot drift from what the page paints."""
    import re, struct
    m = re.search(r'<link rel="manifest" href="([^"]+)">', html[:html.find("</head>")])
    if not m:
        return ["the page links no manifest"]
    path = os.path.join(root, m.group(1))
    try:
        man = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{m.group(1)}: {exc}"]
    out = []
    for k in ("name", "short_name", "id", "start_url", "scope", "display", "theme_color", "background_color", "icons"):
        if not man.get(k): out.append(f"{m.group(1)} has no {k}")
    if man.get("display") != "standalone": out.append("display must be standalone")
    meta = re.search(r'<meta name="theme-color" content="([^"]+)">', html)
    if meta and man.get("theme_color", "").lower() != meta.group(1).lower():
        out.append(f"theme_color {man.get('theme_color')} differs from the page's theme-color {meta.group(1)}")
    for k in ("theme_color", "background_color"):
        if man.get(k) and man[k].lower() not in html.lower():
            out.append(f"{k} {man[k]} does not appear in the page")
    have = set()
    for icon in man.get("icons") or []:
        ip = os.path.join(os.path.dirname(path), icon.get("src", ""))
        try:
            with open(ip, "rb") as f: head = f.read(24)
        except OSError:
            out.append(f"icon {icon.get('src')} is missing"); continue
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            out.append(f"icon {icon.get('src')} is not a PNG"); continue
        w, h = struct.unpack(">II", head[16:24])
        if icon.get("sizes") != f"{w}x{h}":
            out.append(f"icon {icon.get('src')} is {w}x{h} but declared {icon.get('sizes')}")
        have.add((icon.get("purpose", "any"), w))
    for need in (("any", 192), ("any", 512), ("maskable", 512)):
        if need not in have: out.append(f"no {need[1]}px icon with purpose {need[0]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--out", default="report.html")
    ap.add_argument("--standalone", action="store_true", help="wrap in a full HTML document (for GitHub Pages)")
    ap.add_argument("--as-of", default=datetime.datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="minutes"))
    a = ap.parse_args()
    sys.path.insert(0, a.root)
    model, cfg = build(a.root, a.as_of)
    if ERRORS:
        print("VALIDATION FAILED - report not written:", file=sys.stderr)
        for e in ERRORS: print("  -", e, file=sys.stderr)
        sys.exit(1)
    site = cfg["site"]
    tpl = open(os.path.join(a.root, "template.html")).read()
    blob = json.dumps(model, separators=(",", ":")).replace("</", "<\\/")
    browser_title = site["browser_title"].format(season=model["site"]["season"])
    html = tpl.replace("/*__MODEL__*/null", blob).replace("<title>College Football</title>", f"<title>{escape(browser_title)}</title>")
    for bad in ("TODO", "lorem", "PLACEHOLDER", "ghp_", "Bearer "):
        if bad in html: print(f"VALIDATION FAILED - found '{bad}' in output", file=sys.stderr); sys.exit(1)
    if a.standalone:
        T = model["team"]
        d0 = [next(e for e in T["index"][k.split("-")[1]] if e["k"] == k)["name"] for k in T["defaults"]]
        og_desc = escape(f"Pick any FBS teams ({', '.join(str(s) for s in model['site']['seasons'])}) and compare them game by game: record, points, "
                         f"yards, turnover margin and third downs.  Then compare national-leader quarterbacks, running backs and receivers.  "
                         f"Opens on {' vs '.join(d0)} {model['site']['season']}.")
        html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                '<link rel="icon" type="image/png" sizes="32x32" href="icons/favicon-32.png">'
                '<link rel="icon" type="image/png" sizes="192x192" href="icons/icon-192.png">'
                '<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">'
                '<link rel="manifest" href="manifest.webmanifest">'
                '<meta name="theme-color" content="#24303F">'
                '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
                f'<meta name="description" content="{escape(site["description"])}">'
                f'<meta property="og:title" content="{escape(browser_title)}">'
                f'<meta property="og:description" content="{og_desc}">'
                f'<meta property="og:image" content="{site["url"]}icons/og.png">'
                f'<meta property="og:url" content="{site["url"]}">'
                '<meta name="twitter:card" content="summary_large_image">'
                '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
                '</head><body>\n' + html + '\n</body></html>\n')
        problems = check_manifest(a.root, html)
        if problems:
            print("VALIDATION FAILED - web app manifest:", file=sys.stderr)
            for p in problems: print("  -", p, file=sys.stderr)
            sys.exit(1)
    tmp = a.out + ".tmp"
    open(tmp, "w").write(html)
    os.replace(tmp, a.out)
    T, PL = model["team"], model["player"]
    print(f"OK  teams: " + ", ".join(f"{s} {len(v)}" for s, v in T["index"].items()) + "  pools: " +
          ", ".join(f"{t} " + "/".join(str(len(p.get('players', []))) for p in PL[t]["pools"].values()) for t in PL))
    print(f"    defaults: teams {T['defaults']}, qb {PL['qb']['defaults']}")
    print(f"    sha256={hashlib.sha256(html.encode()).hexdigest()[:16]}  bytes={len(html)}")


if __name__ == "__main__":
    main()
