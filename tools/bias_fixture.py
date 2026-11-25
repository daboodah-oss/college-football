#!/usr/bin/env python3
"""Build a throwaway copy of this repo whose data/cfp.json ends in one real bias snapshot, so the Bias tab's
populated view can be built and render-checked before the pipeline has stored a bias week.  Offline.

  python3 tools/bias_fixture.py OUT_DIR            # then, from OUT_DIR:
  python3 build_report.py --standalone --out index.html && node tools/render_check.js index.html

It copies the repo (no .git) to OUT_DIR, removes the latest stored snapshot from the COPY's cfp.json, and
stores in its place a snapshot for that same committee Top 25 labeled "<week> (bias preview)", made by
collect_cfp.make_snapshot on the stored game rows and passed through the copy's update.cfp validation.
The repo's own data/ is never written."""
import json, os, shutil, sys

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else sys.exit("usage: bias_fixture.py OUT_DIR")
if out == SRC or out.startswith(SRC + os.sep) and os.path.basename(out) in ("data",): sys.exit("refusing to write over the repo")
if os.path.exists(out): shutil.rmtree(out)
shutil.copytree(SRC, out, ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"))
sys.path.insert(0, out)
import update, collect_cfp  # noqa: E402  (the COPY's modules: update.ROOT is out)
assert os.path.dirname(update.__file__) == out
p = os.path.join(out, "data", "cfp.json")
d = json.load(open(p))
last = d["weeks"].pop()
json.dump(d, open(p, "w"), indent=1)
snap = collect_cfp.make_snapshot(out, d["season"], last["committee"], f"{last['week']} (bias preview)", last["date"])
update.cfp(snap)
print(f"fixture at {out}: {last['week']} replaced by a bias snapshot (games through {snap['through']})")
