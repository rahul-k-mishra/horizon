"""
dryrun_report.py -- the numbers of docs/DRYRUN.md, read from committed files only (jobs/manifest.json,
runs/dryrun/, logs/automation.log and the git history).  Plays nothing and calls no service.

It prints:
    - per chunk: status, attempts, failures, and every session with its Kaggle kernel version, run
      nonce, outcome and end time;
    - per row: unit, schema check, and the host, run nonce and times of each session that built it;
    - the forced-checkpoint chunk dry-02: its two kernel versions, the commits that wrote and removed
      its checkpoint, and the checkpoint's files with their sizes and where each was kept (git or the
      release);
    - graph-a against an uninterrupted enumeration of the same dummy graph (states seen, goal depth),
      and graph-b's cap;
    - every FAILURE line of logs/automation.log;
    - the loop's commits: how many, and whether every message is one line;
    - the elapsed time from the first dispatch to the collection that left every chunk done, and from
      the first dispatch that reached Kaggle.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\dryrun_report.py > logs\\dryrun_report.log
"""
from __future__ import annotations

import calendar
import json
import os
import subprocess
import sys
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from common import load_manifest, read_json  # noqa: E402
from schema import validate_agent_row, validate_search_row  # noqa: E402


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout


def epoch(s):
    return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))


def hms(sec):
    sec = int(sec)
    return f"{sec // 3600} h {sec % 3600 // 60:02d} min {sec % 60:02d} s"


def reference(M, edges, goal):
    seen, q, depth = {0}, deque([0]), {0: 0}
    while q:
        n = q.popleft()
        for a, b in edges:
            x = (a * n + b) % M
            if x not in seen:
                seen.add(x)
                depth[x] = depth[n] + 1
                q.append(x)
    return len(seen), depth.get(goal)


def main():
    m = load_manifest(REPO)
    print(f"dry-run report -- campaign {m['campaign']}, code tag {m['code_tag']}, state commit {git('rev-parse', '--short', 'HEAD').strip()}")
    print("\n== chunks")
    for c in m["chunks"]:
        print(f"{c['chunk_id']} ({c['kind']}): {c['status']}, attempts {c['attempts']}, failures {c['failures']}")
        for s in c["sessions"]:
            print(f"   kernel version {s['kernel_version']}  run {s['run_nonce']}  kernel {s['kernel_status']}  "
                  f"outcome {s['outcome']}  units {s['units_done_this_session']}  ended {s['ended_at']}")
    print("\n== rows")
    base = os.path.join(REPO, "runs", m["campaign"])
    for kind, val in (("agent", validate_agent_row), ("search", validate_search_row)):
        d = os.path.join(base, kind)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            r = read_json(os.path.join(d, f))
            errs = val(r)
            mk = read_json(os.path.join(base, "done", f))
            print(f"{kind} {r['unit_id']}: schema {'ok' if not errs else errs}; marker kernel version {mk['kernel_version']}")
            for s in r["sessions"]:
                print(f"   host {s['host']}  run {s['run_nonce']}  started {s['started_at']}  ended {s['ended_at']}")
            if kind == "search":
                print(f"   complete {r['complete']}, capped {r['capped']} ({r['cap_hit']}), counts {json.dumps(r['counts'], sort_keys=True)}, seconds {r['seconds_spent']}")
    print("\n== the forced checkpoint (dry-02)")
    c2 = [c for c in m["chunks"] if c["chunk_id"] == "dry-02"][0]
    print("sessions: " + "; ".join(f"kernel version {s['kernel_version']} {s['outcome']}" for s in c2["sessions"]))
    log = git("log", "--reverse", "--format=%h %cI %s", "--", f"runs/{m['campaign']}/checkpoints/dry-02/checkpoint.json")
    for line in log.strip().splitlines():
        print(f"checkpoint commit: {line}")
        h = line.split()[0]
        try:
            ck = json.loads(git("show", f"{h}:runs/{m['campaign']}/checkpoints/dry-02/checkpoint.json"))
        except subprocess.CalledProcessError:
            print("   (the checkpoint is removed in this commit: the chunk is done)")
            continue
        print(f"   checkpoint seq {ck['seq']}, run {ck['run_nonce']}, units done {ck['units_done']}, "
              f"unit in progress {ck['unit_in_progress']['unit_id']}")
        for name, v in sorted(ck["payload"].items()):
            print(f"   {name}: {v['bytes']} bytes, {v.get('location', 'git')}")
    p = m["kinds"]["search"]
    n_ref, d_ref = reference(int(p["M"]), [tuple(e) for e in p["edges"]], int(p["goal"]))
    ra = read_json(os.path.join(base, "search", "dry-02-graph-a.json"))
    rb = read_json(os.path.join(base, "search", "dry-02-graph-b.json"))
    print(f"graph-a: states seen {ra['counts']['states_seen']}, goal depth {ra['counts']['solution_length']}, "
          f"sessions {len(ra['sessions'])}; uninterrupted enumeration: {n_ref} states, goal depth {d_ref}; "
          f"{'same' if (ra['counts']['states_seen'], ra['counts']['solution_length']) == (n_ref, d_ref) else 'DIFFERENT'}")
    print(f"graph-b: capped {rb['capped']} by {rb['cap_hit']} at {rb['counts']['states_expanded']} expansions "
          f"(node cap {rb['caps']['node_cap']})")
    print("\n== failures logged")
    lines = open(os.path.join(REPO, "logs", "automation.log"), encoding="utf-8").read().splitlines()
    fl = [x for x in lines if " FAILURE " in x]
    for x in fl:
        print(x)
    print(f"{len(fl)} failure line(s)")
    print("\n== the loop's commits")
    raw = git("log", "--format=%H%x1f%an%x1f%cI%x1f%B%x1e")
    recs = [r.strip("\n").split("\x1f") for r in raw.split("\x1e") if r.strip()]
    loop = [r for r in recs if r[1] == "horizon-loop"]
    multi = [r for r in recs if len(r[3].strip().splitlines()) != 1]
    print(f"commits by horizon-loop: {len(loop)}; commits in the repository with a message of more than one line: {len(multi)}")
    for r in reversed(loop):
        print(f"   {r[0][:7]} {r[2]} {r[3].strip()}")
    print("\n== elapsed")
    disp = [x for x in lines if " DISPATCH " in x]
    pushed = [x for x in lines if " PUSHED " in x]
    coll = [x for x in lines if " COLLECT " in x and "done" in x]
    last = [x for x in coll if f"done {len(m['chunks'])}" in x]
    if disp and last:
        t0, t1, tp = epoch(disp[0].split()[0]), epoch(last[-1].split()[0]), epoch(pushed[0].split()[0])
        print(f"first dispatch {disp[0].split()[0]}; first notebook push that reached Kaggle {pushed[0].split()[0]}; "
              f"last chunk collected {last[-1].split()[0]}")
        print(f"elapsed from the first dispatch: {hms(t1 - t0)}; from the first push that reached Kaggle: {hms(t1 - tp)}")
    else:
        print("the manifest is not complete yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
