"""
actions_minutes.py -- the GitHub Actions time used by the HORIZON loop (docs/AUTOMATION.md, Section 10).

Reads, with the gh tool, every run of the workflow horizon.yml in rahul-k-mishra/horizon and the
timing of its job, saves the raw records in runs/<campaign>/actions_runs.json (committed with the log),
and prints from that file:
    - per run: its trigger, start, job duration in seconds, and the duration rounded up to whole minutes;
    - the median and the largest job duration, and the median rounded up to whole minutes;
    - the monthly total the cron would use if every tick took the median rounded-up minutes: 48 ticks a
      day for 30 days.
The repository is public, so GitHub charges none of this; the total matters only if the repository were
private (Section 10).  Plays nothing.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\actions_minutes.py --campaign dryrun > logs\\actions_minutes.log
EXPECTED OUTPUT (shape): one line per run, then
    runs: N; job seconds median S, largest L; median rounded up to whole minutes: M
    cron estimate: 1440 ticks a month x M minutes = T minutes a month (if the repository were private)
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
                         jobs=[dict(name=j["name"], started_at=j["started_at"], completed_at=j["completed_at"])
                               for j in js]))
    out = os.path.join(REPO, "runs", a.campaign, "actions_runs.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sorted(runs, key=lambda r: r["created_at"]), f, indent=1)
    with open(out, encoding="utf-8") as f:
        runs = json.load(f)
    secs = []
    for r in runs:
        done = [j for j in r["jobs"] if j["started_at"] and j["completed_at"]]
        if r["status"] != "completed" or not done:
            print(f"run {r['id']} {r['event']} {r['created_at']}: {r['status']}, not counted")
            continue
        s = sum(epoch(j["completed_at"]) - epoch(j["started_at"]) for j in done)
        secs.append(s)
        print(f"run {r['id']} {r['event']:<17} {r['created_at']} {r['conclusion']:<8} job {s:>4} s = {math.ceil(s / 60)} min rounded up")
    med = statistics.median(secs)
    m_up = math.ceil(med / 60)
    print(f"runs: {len(secs)}; job seconds median {med:g}, largest {max(secs)}; median rounded up to whole minutes: {m_up}")
    print(f"cron estimate: {48 * 30} ticks a month x {m_up} minutes = {48 * 30 * m_up} minutes a month "
          f"(if the repository were private; free for a public repository)")
    print(f"raw records: {os.path.relpath(out, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
