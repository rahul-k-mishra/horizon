"""
actions_minutes.py -- the GitHub Actions time used by the HORIZON loop (docs/AUTOMATION.md, Section 10).

Reads, with the gh tool, every run of the workflow horizon.yml in rahul-k-mishra/horizon and the
timing of its job and steps, saves the raw records in runs/<campaign>/actions_runs.json (committed with
the log), and prints from that file:
    - per run: its trigger, start, conclusion, job seconds, the seconds of the step "Tick" and of the
      step "Start the next tick" (the sleep before the successor), and the job rounded up to whole minutes;
    - a tick: the median seconds of the step "Tick" over all runs;
    - a run that did not wait (its step "Start the next tick" under 30 s, or absent: a tick alone): the
      median job seconds, rounded up to whole minutes;
    - a month with nothing to do (manifest complete or loop halted): the cron's 48 runs a day for 30
      days, each costing that rounded-up figure;
    - a month of a campaign in flight: the rounded-up job minutes of the runs that waited for a
      successor, divided by the wall-clock minutes from the first such run's start to the last one's
      end, times the 43,200 minutes of 30 days.
Runs cancelled while pending (a newer run replaced them in the concurrency group) used no runner time
and are listed as not counted.  The repository is public, so GitHub charges none of this; the totals
matter only if the repository were private (Section 10).  Plays nothing.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\actions_minutes.py --campaign dryrun > logs\\actions_minutes.log
"""
from __future__ import annotations

import argparse
import calendar
import json
import math
import os
import statistics
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def epoch(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", default="dryrun")
    ap.add_argument("--repository", default="rahul-k-mishra/horizon")
    a = ap.parse_args(argv)
    runs = []
    data = gh(f"/repos/{a.repository}/actions/workflows/horizon.yml/runs?per_page=100")
    if data["total_count"] > 100:
        raise SystemExit("more than 100 runs: add paging before using this script")
    for r in data["workflow_runs"]:
        js = gh(f"/repos/{a.repository}/actions/runs/{r['id']}/jobs")["jobs"]
        runs.append(dict(id=r["id"], event=r["event"], status=r["status"], conclusion=r["conclusion"],
                         created_at=r["created_at"],
                         jobs=[dict(name=j["name"], started_at=j["started_at"], completed_at=j["completed_at"],
                                    steps=[dict(name=t["name"], started_at=t.get("started_at"),
                                                completed_at=t.get("completed_at"), conclusion=t.get("conclusion"))
                                           for t in j.get("steps", [])])
                               for j in js]))
    out = os.path.join(REPO, "runs", a.campaign, "actions_runs.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sorted(runs, key=lambda r: r["created_at"]), f, indent=1)
    with open(out, encoding="utf-8") as f:
        runs = json.load(f)

    def step(j, name):
        t = [x for x in j["steps"] if x["name"] == name and x["started_at"] and x["completed_at"]]
        return epoch(t[0]["completed_at"]) - epoch(t[0]["started_at"]) if t else None

    ticks, idle, waiting = [], [], []
    for r in runs:
        done = [j for j in r["jobs"] if j["started_at"] and j["completed_at"]]
        if r["status"] != "completed" or not done:
            print(f"run {r['id']} {r['event']:<17} {r['created_at']} {r['conclusion']}: no job ran, not counted")
            continue
        j = done[0]
        s = epoch(j["completed_at"]) - epoch(j["started_at"])
        tk, wt = step(j, "Tick"), step(j, "Start the next tick")
        if tk is not None:
            ticks.append(tk)
        (waiting if wt is not None and wt >= 30 else idle).append((s, j))
        print(f"run {r['id']} {r['event']:<17} {r['created_at']} {r['conclusion']:<8} job {s:>5} s, tick {tk} s, "
              f"wait-and-start {wt} s = {math.ceil(s / 60)} min rounded up")
    print(f"runs counted: {len(idle) + len(waiting)} ({len(waiting)} that waited for a successor, {len(idle)} that did not)")
    if ticks:
        print(f"the step Tick: median {statistics.median(ticks):g} s, largest {max(ticks)} s, over {len(ticks)} runs")
    if idle:
        med = statistics.median(s for s, _ in idle)
        up = math.ceil(med / 60)
        print(f"a run that did not wait (a tick alone): median job {med:g} s; rounded up to whole minutes: {up}")
        print(f"a month with nothing to do: {48 * 30} cron runs x {up} min = {48 * 30 * up} minutes")
    if waiting:
        billed = sum(math.ceil(s / 60) for s, _ in waiting)
        t0 = min(epoch(j["started_at"]) for _, j in waiting)
        t1 = max(epoch(j["completed_at"]) for _, j in waiting)
        wall = (t1 - t0) / 60
        print(f"runs that waited for a successor: {billed} minutes rounded up over {wall:.1f} wall-clock minutes "
              f"({billed / wall:.3f} billed minutes per minute)")
        print(f"a month of a campaign in flight: {billed / wall:.3f} x 43200 = {billed / wall * 43200:.0f} minutes")
    print("the repository is public: GitHub charges none of these minutes")
    print(f"raw records: {os.path.relpath(out, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
