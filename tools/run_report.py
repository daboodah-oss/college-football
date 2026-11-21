#!/usr/bin/env python3
"""The Update workflow's "Report problems" step: summarize the run and fail it only for a real problem.

  python3 tools/run_report.py COLLECT_OUTCOME BUILD_OUTCOME      (outcomes as GitHub Actions reports them)

Writes a summary to $GITHUB_STEP_SUMMARY (or stdout) from data/last_run.json and exits 1, which makes GitHub email
the owner, only when:
  - the build failed (nothing was published), or
  - a collect section failed outright (an exception: a source down, a page that no longer parses), or
  - a team-season was refused by the validator that the previous run did not refuse (`new_refusals`).
Team-seasons that stay refused run after run are a known data condition, shown on the page's notices; they are
listed in the summary but do not fail the run.  (Before 2026-11-21 every one of them failed the collect step, so
every full run "failed" and the emails carried no signal: docs/claude-spec-warnings-model-v2.md Part 5.)"""
import json, os, sys

collect, build = (sys.argv[1:3] + ["", ""])[:2]
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = os.path.join(root, "data", "last_run.json")
lr = json.load(open(p)) if os.path.exists(p) else {}
skipped = os.path.exists(os.path.join(root, ".nochange"))
lines, problems = [f"## Update run: collect {collect or 'n/a'}, build {build or 'skipped'}"], []
if skipped: lines.append("Quick check: no new FBS final; nothing collected.")
if build == "failure": problems.append("the build failed validation: nothing was published (see logs/build.txt)")
if collect == "failure" and lr.get("failed"): problems.append("collect sections failed: " + ", ".join(lr["failed"]) + " (see logs/collect.txt)")
elif collect == "failure": problems.append("collect.py failed before writing data/last_run.json (see logs/collect.txt)")
for s, names in sorted((lr.get("new_refusals") or {}).items(), reverse=True):
    problems.append(f"{s}: newly refused by the validator: {', '.join(names)} (see logs/collect.txt)")
for s, names in sorted((lr.get("refused") or {}).items(), reverse=True):
    tot = (lr.get("registry_teams") or {}).get(s, "?")
    lines.append(f"- {s}: {len(names)} of {tot} team seasons refused by the validator" + (f": {', '.join(names)}" if names else ""))
lines += ["", "**Problems:** " + ("; ".join(problems) if problems else "none")]
out = os.environ.get("GITHUB_STEP_SUMMARY")
txt = "\n".join(lines) + "\n"
if out: open(out, "a").write(txt)
print(txt)
sys.exit(1 if problems else 0)
