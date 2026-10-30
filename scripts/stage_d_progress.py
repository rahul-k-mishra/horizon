"""
stage_d_progress.py -- where stage D (campaign dev-minigrid, kind devsearch) stands while it runs:
the seconds, cap and state of every completed unit, the slowest ten, the caps hit, the sessions each
finished chunk needed, and the wall-clock time each finished chunk took from its first dispatch to its
last collection.  From the finished chunks it states the time the pending chunks would take if they
behaved as the finished ones did, and the bound the registered caps put on them.  It reads no result
of the search other than seconds, caps and state, decides nothing and changes no file under jobs/ or
runs/.

Reads only committed files: runs/dev-minigrid/devsearch/*.json, jobs/manifest.json and
logs/automation.log.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\stage_d_progress.py > logs\\stage_d_progress.log
"""
from __future__ import annotations

import collections
import datetime as dt
import glob
import json
import os
import re
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ROWS = os.path.join(REPO, "runs", "dev-minigrid", "devsearch")
EVENT = re.compile(r"^(\S+) \S+ (DISPATCH|COLLECT) chunk (d-\d+) ")
OUTCOME = re.compile(r": (partial|done|failed);")


def ts(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def hours(s):
    return f"{s / 3600:.2f} h"


def main():
    with open(os.path.join(REPO, "jobs", "manifest.json"), encoding="utf-8") as f:
        m = json.load(f)
    if m["campaign"] != "dev-minigrid":
        raise SystemExit(f"jobs/manifest.json is campaign {m['campaign']}, not dev-minigrid")
    kp = m["kinds"]["devsearch"]
    sess = m["session"]
    per_chunk = collections.Counter(u["chunk_id"] for u in m["units"])
    print(f"stage_d_progress: campaign {m['campaign']}, code tag {m['code_tag']}, "
          f"{len(m['chunks'])} chunks, {len(m['units'])} units")
    print(f"registered caps: time {kp['time_cap_seconds']} s, nodes {kp['node_cap']}, "
          f"memory {kp['memory_cap_bytes']} bytes; {kp['workers']} workers; "
          f"session work {sess['work_seconds']} s, checkpoint reserve {sess['checkpoint_reserve_seconds']} s")
    status = collections.Counter(c["status"] for c in m["chunks"])
    print("chunks by status: " + ", ".join(f"{k} {v}" for k, v in sorted(status.items())))

    rows = []
    for p in sorted(glob.glob(os.path.join(ROWS, "*.json"))):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        rows.append(r)
    print(f"\nrows read: {len(rows)}")
    print("\n== every completed unit: unit, seconds, state, cap hit, sessions it spanned ==")
    for r in rows:
        state = "capped" if r["capped"] else ("complete" if r["complete"] else "not complete, not capped")
        print(f"  {r['unit_id']}  {r['seconds_spent']:10.1f} s  {state:8s}  "
              f"cap {r['cap_hit'] or '-':6s}  sessions {len(r['sessions'])}")

    secs = sorted(r["seconds_spent"] for r in rows)
    total = sum(secs)
    print("\n== seconds per unit ==")
    print(f"  total {total:.1f} s ({hours(total)} of worker time)")
    print(f"  min {secs[0]:.1f}, median {statistics.median(secs):.1f}, mean {total / len(secs):.1f}, max {secs[-1]:.1f}")
    for q in (0.25, 0.75, 0.90):
        print(f"  quantile {q:.2f}: {secs[min(len(secs) - 1, int(q * len(secs)))]:.1f} s")
    for lim in (60, 600, 3600):
        print(f"  units under {lim} s: {sum(s < lim for s in secs)}")
    print("  share of all worker seconds taken by the slowest k units:")
    desc = secs[::-1]
    for k in (10, 20, 40, 60):
        print(f"    k={k}: {sum(desc[:k]) / total:.4f}")

    print("\n== the slowest ten units ==")
    for r in sorted(rows, key=lambda r: -r["seconds_spent"])[:10]:
        print(f"  {r['unit_id']}  {r['seconds_spent']:.1f} s  capped {r['capped']}  cap {r['cap_hit']}  "
              f"states expanded {r['counts']['states_expanded']}")

    print("\n== caps hit ==")
    caps = collections.Counter(r["cap_hit"] for r in rows if r["capped"])
    print(f"  units capped: {sum(caps.values())} of {len(rows)}")
    for k, v in sorted(caps.items()):
        print(f"    cap {k}: {v}")
    print(f"  complete: {sum(r['complete'] for r in rows)}")
    print(f"  neither complete nor capped: {sum(not r['complete'] and not r['capped'] for r in rows)}")
    for k in sorted(caps):
        cs = sorted(r["seconds_spent"] for r in rows if r["cap_hit"] == k)
        print(f"    seconds of units capped by {k}: min {cs[0]:.1f}, median {statistics.median(cs):.1f}, max {cs[-1]:.1f}")
    print(f"  units at {kp['time_cap_seconds']} s or more: {sum(s >= kp['time_cap_seconds'] for s in secs)} "
          f"(the slowest ten are drawn from these, in order of seconds to the tenth of a second)")
    print(f"  units spanning more than one session: {sum(len(r['sessions']) > 1 for r in rows)}")

    print("\n== per game: units, capped, worker seconds ==")
    byg = collections.defaultdict(list)
    for r in rows:
        byg[(r["chunk_id"], r["game"])].append(r)
    for (c, g), rs in sorted(byg.items()):
        print(f"  {c} {g}: {len(rs)} units, capped {sum(x['capped'] for x in rs)}, "
              f"{sum(x['seconds_spent'] for x in rs):.1f} s")
    games_capped = sum(any(x["capped"] for x in rs) for rs in byg.values())
    games_all = sum(all(x["capped"] for x in rs) for rs in byg.values())
    print(f"  games with at least one capped unit: {games_capped} of {len(byg)}; with every unit capped: {games_all}")
    slow = sum(x["seconds_spent"] for rs in byg.values() if any(x["capped"] for x in rs) for x in rs)
    print(f"  share of all worker seconds in the games with a capped unit: {slow / total:.4f}")
    print(f"  chunks are filled in the manifest's order of game names, so the finished chunks are not a random draw of the games")

    events = collections.defaultdict(list)
    with open(os.path.join(REPO, "logs", "automation.log"), encoding="utf-8") as f:
        for line in f:
            e = EVENT.match(line)
            if e:
                o = OUTCOME.search(line)
                events[e.group(3)].append((ts(e.group(1)), e.group(2), o.group(1) if o else None))

    print("\n== finished chunks: sessions, capped units, worker seconds, wall-clock first dispatch to last collect ==")
    walls, nsess, gaps = [], [], []
    byc = collections.defaultdict(list)
    for r in rows:
        byc[r["chunk_id"]].append(r)
    for c in m["chunks"]:
        if c["status"] != "done":
            continue
        ev = events[c["chunk_id"]]
        disp = [t for t, k, _ in ev if k == "DISPATCH"]
        coll = [t for t, k, _ in ev if k == "COLLECT"]
        wall = (coll[-1] - disp[0]).total_seconds()
        walls.append(wall)
        nsess.append(len(c["sessions"]))
        gaps += [(d - k).total_seconds() for k, d in zip(coll, disp[1:])]
        rs = byc[c["chunk_id"]]
        print(f"  {c['chunk_id']}: {len(rs)} of {per_chunk[c['chunk_id']]} units, sessions {len(c['sessions'])}, "
              f"capped {sum(x['capped'] for x in rs)}, worker {sum(x['seconds_spent'] for x in rs):.1f} s, "
              f"wall {hours(wall)}")
    print(f"  sessions per finished chunk: " + ", ".join(f"{k} sessions: {v} chunks"
                                                       for k, v in sorted(collections.Counter(nsess).items())))
    print(f"  sessions in all: {sum(nsess)}, mean {sum(nsess) / len(nsess):.3f}")
    print(f"  wall per chunk: min {hours(min(walls))}, median {hours(statistics.median(walls))}, "
          f"mean {hours(sum(walls) / len(walls))}, max {hours(max(walls))}")
    print(f"  collect to next dispatch of the same chunk: {len(gaps)} gaps, max {max(gaps):.0f} s")
    # the gap from one chunk's last collect to the next chunk's first dispatch
    order = [c["chunk_id"] for c in m["chunks"] if events[c["chunk_id"]]]
    between = []
    for a, b in zip(order, order[1:]):
        between.append((min(t for t, k, _ in events[b] if k == "DISPATCH")
                        - max(t for t, k, _ in events[a] if k == "COLLECT")).total_seconds())
    print(f"  last collect of a chunk to first dispatch of the next: max {max(between):.0f} s")
    pw = []
    for c in m["chunks"]:
        ev = events[c["chunk_id"]]
        d = [t for t, k, _ in ev if k == "DISPATCH"]
        k_ = [(t, o) for t, k, o in ev if k == "COLLECT"]
        for t0, (t1, o) in zip(d, k_):
            if o == "partial":
                pw.append((t1 - t0).total_seconds())
    print(f"  partial sessions: {len(pw)}; dispatch to collect: min {hours(min(pw))}, max {hours(max(pw))}")

    first = min(t for ev in events.values() for t, k, _ in ev if k == "DISPATCH")
    last = max(t for c in m["chunks"] if c["status"] == "done" for t, k, _ in events[c["chunk_id"]] if k == "COLLECT")
    print(f"  stage D first dispatch {first:%Y-%m-%dT%H:%M:%SZ}, last collect of a finished chunk "
          f"{last:%Y-%m-%dT%H:%M:%SZ}: {hours((last - first).total_seconds())} for {len(walls)} chunks")

    pending = [c["chunk_id"] for c in m["chunks"] if c["status"] == "pending"]
    running = [c for c in m["chunks"] if c["status"] not in ("done", "pending")]
    n = len(pending)
    print(f"\n== the {n} pending chunks, if they behave as the {len(walls)} finished ones ==")
    print("  basis: wall per finished chunk, first dispatch to last collect, from logs/automation.log; "
          "it includes the loop's gaps between sessions")
    for name, w in (("min", min(walls)), ("median", statistics.median(walls)),
                    ("mean", sum(walls) / len(walls)), ("max", max(walls))):
        print(f"  {n} x {name} {hours(w)} = {hours(n * w)} = {n * w / 86400:.2f} days")
    mean_partial = sum(pw) / len(pw)
    cap_s = kp["time_cap_seconds"]
    work_cap = kp["workers"] * sess["work_seconds"]
    worst = -(-per_chunk[pending[0]] * cap_s // work_cap)
    print(f"\n== the bound from the registered caps ==")
    print(f"  a unit takes at most {cap_s} s of one worker; a session gives {kp['workers']} x {sess['work_seconds']} "
          f"= {work_cap} worker seconds")
    print(f"  a chunk of {per_chunk[pending[0]]} units every one at the time cap needs "
          f"{per_chunk[pending[0]]} x {cap_s} / {work_cap} = {per_chunk[pending[0]] * cap_s / work_cap:.2f}, "
          f"so {worst} sessions (more if four capped units do not fill a session evenly)")
    print(f"  mean partial session, dispatch to collect: {hours(mean_partial)}")
    print(f"  {n} chunks x {worst} sessions x {hours(mean_partial)} = {hours(n * worst * mean_partial)} "
          f"= {n * worst * mean_partial / 86400:.2f} days, if every pending unit hit the time cap")
    print(f"  {n} chunks x 1 session, if no pending unit is slow: at least {n} sessions")
    for c in running:
        rs = byc[c["chunk_id"]]
        left = per_chunk[c["chunk_id"]] - len(rs)
        print(f"\n  chunk {c['chunk_id']} ({c['status']}): {len(rs)} of {per_chunk[c['chunk_id']]} units done "
              f"after {len(c['sessions'])} session(s), capped {sum(x['capped'] for x in rs)}; not in the {n}; "
              f"its {left} units left need at most {left} x {cap_s} / {work_cap} = {left * cap_s / work_cap:.2f} "
              f"sessions of work")

    print("\n== games of the units still to run ==")
    rest = [u for u in m["units"] if u["status"] != "done"]
    seen = collections.OrderedDict()
    for u in rest:
        seen.setdefault((u["chunk_id"], u["game"]), 0)
        seen[(u["chunk_id"], u["game"])] += 1
    print(f"  units not done: {len(rest)}")
    for (c, g), k in seen.items():
        print(f"  {c} {g}: {k}")


if __name__ == "__main__":
    main()
