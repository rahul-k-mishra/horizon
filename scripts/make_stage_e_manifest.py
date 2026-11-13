"""
make_stage_e_manifest.py -- writes the manifest of stage E, the censored development search
(docs/design/STAGE_E_OPTIONS.md, Section 4), to jobs/stage_e/manifest.json.  It is not the loop's manifest: it
replaces jobs/manifest.json only when the stage is launched.

Stage E searches the same 1,560 development units as stage D (study 1's confirmatory MiniGrid/BabyAI games in
the macro condition, seeds 1000 to 1009, Dynamic-Obstacles left out; the unit list is read from stage D's
manifest, jobs/stage_d/manifest.json, so the two stages hold the same units) with the kind devsearch under the
row schema horizon.search.v3: a cap of SEEN_CAP states seen, and the states seen at the first win recorded.
From its rows the censored scores H_C = -log10 min(R, C) and L_C (the fewest actions to a win if a win was seen
among the first C states, otherwise beyond C) are exact for every C up to SEEN_CAP.  Stage D's rows cannot give
L_C, because they do not record when the first win was seen.  Every other cap is stage D's: node cap
5,000,000 (never reached first, since a search sees at least as many states as it expands), time cap 14,400 s,
6 GiB per worker, spill at 1,000,000, checkpoints every 600 s or 250,000 expansions, the effective-horizon
bound for levels of at most 200,000 states with T = 400.

Chunks.  Each unit's time is estimated from its stage D row: its seconds if stage D finished it at or below
SEEN_CAP states, otherwise its seconds scaled by SEEN_CAP / states seen.  Units are packed, longest first,
into chunks whose estimated work is at most LOAD of one session's capacity (4 workers x 28,800 s), and the
four-worker finishing time of every chunk, by longest-first scheduling, is printed.  A chunk that overruns its
session resumes from its checkpoint in the next one, as in stage D.
Expected wall-clock: for each chunk its four-worker finishing time plus OVERHEAD seconds for the notebook's
start and the loop's poll; an estimate, stated with its assumption.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\make_stage_e_manifest.py > logs\\make_stage_e_manifest.log
"""
from __future__ import annotations

import glob
import heapq
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
from common import check_manifest  # noqa: E402

SEEN_CAP = 2_000_000
LOAD = 0.60
OVERHEAD = 2700          # notebook start allowance 900 s plus up to 30 min between the session's end and the poll
CAMPAIGN, CODE_TAG = "dev-minigrid-e", "automation-v3"
KIND = dict(simulator="minigrid", condition="macro", workers=4, schema="horizon.search.v3", seen_cap=SEEN_CAP,
            node_cap=5_000_000, time_cap_seconds=14400, memory_cap_bytes=6442450944, spill_frontier_over=1_000_000,
            checkpoint_every_seconds=600, checkpoint_every_nodes=250000, batch=200, eh_state_limit=200000,
            eh_horizon=400)
SESSION = dict(work_seconds=28800, checkpoint_reserve_seconds=900, platform_limit_seconds=32400)


def lpt_makespan(times, workers):
    load = [0.0] * workers
    heapq.heapify(load)
    for t in sorted(times, reverse=True):
        heapq.heappush(load, heapq.heappop(load) + t)
    return max(load)


def main():
    with open(os.path.join(REPO, "jobs", "stage_d", "manifest.json"), encoding="utf-8") as f:
        d_units = json.load(f)["units"]
    rows = {}
    for p in glob.glob(os.path.join(REPO, "runs", "dev-minigrid", "devsearch", "*.json")):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        rows[(r["game"], int(r["level"]))] = r
    est = {}
    for u in d_units:
        r = rows[(u["game"], int(u["level"]))]
        seen, sec = r["counts"]["states_seen"], float(r["seconds_spent"])
        est[(u["game"], int(u["level"]))] = sec if (r["complete"] and seen <= SEEN_CAP) else sec * min(1.0, SEEN_CAP / seen)
    capacity = KIND["workers"] * SESSION["work_seconds"]
    order = sorted(est, key=lambda k: (-est[k], k))
    bins = []                                   # [load, [keys]]
    for k in order:
        for b in bins:
            if b[0] + est[k] <= LOAD * capacity:
                b[0] += est[k]
                b[1].append(k)
                break
        else:
            bins.append([est[k], [k]])
    chunks, units, spans = [], [], []
    for i, (load, keys) in enumerate(bins):
        cid = f"e-{i + 1:03d}"
        chunks.append(dict(chunk_id=cid, kind="devsearch", status="pending", attempts=0, failures=0, sessions=[]))
        for g, s in keys:                       # longest first inside the chunk
            units.append(dict(unit_id=f"{cid}-{g}-s{s}", chunk_id=cid, kind="devsearch", suite="minigrid", game=g,
                              level=s, agent=None, seed=None, status="pending"))
        spans.append(lpt_makespan([est[k] for k in keys], KIND["workers"]))
    m = dict(campaign=CAMPAIGN, code_tag=CODE_TAG, repository="rahul-k-mishra/horizon", kernel_slug="horizon-runner",
             max_failures=3, payload_commit_limit_bytes=50_000_000, session=SESSION, kinds=dict(devsearch=KIND),
             chunks=chunks, units=units)
    errs = check_manifest(m)
    if errs:
        raise SystemExit(f"manifest check failed: {errs}")
    out_dir = os.path.join(REPO, "jobs", "stage_e")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1, sort_keys=True)

    total = sum(est.values())
    games = sorted({u["game"] for u in units})
    print(f"stage E: campaign {CAMPAIGN}, code tag {CODE_TAG}, kind devsearch, row schema {KIND['schema']}")
    print(f"units: {len(units)} ({len(games)} games x seeds 1000 to 1009), the units of jobs/stage_d/manifest.json; "
          f"stage D rows read: {len(rows)}")
    print(f"caps: seen cap {SEEN_CAP:,} states; node cap {KIND['node_cap']:,}; time cap {KIND['time_cap_seconds']} s; "
          f"memory {KIND['memory_cap_bytes']} bytes per worker; spill at {KIND['spill_frontier_over']:,}; "
          f"checkpoints every {KIND['checkpoint_every_seconds']} s or {KIND['checkpoint_every_nodes']:,} expansions")
    over_d = sum(1 for k in est if not (rows[k]["complete"] and rows[k]["counts"]["states_seen"] <= SEEN_CAP))
    print(f"units stage D did not finish at or below the seen cap (estimated by scaling): {over_d}; largest unit "
          f"estimate {max(est.values()):.0f} s (time cap {KIND['time_cap_seconds']} s)")
    print(f"estimated work: {total:.0f} worker-seconds; one session's capacity {capacity} worker-seconds "
          f"({KIND['workers']} workers x {SESSION['work_seconds']} s); chunks packed to at most {LOAD:.0%} of it")
    print(f"chunks: {len(chunks)}; units per chunk {min(len(b[1]) for b in bins)} to {max(len(b[1]) for b in bins)}; "
          f"estimated four-worker finishing time per chunk {min(spans):.0f} to {max(spans):.0f} s "
          f"(work limit {SESSION['work_seconds']} s); chunks estimated to need a second session: "
          f"{sum(sp > SESSION['work_seconds'] for sp in spans)}")
    wall = sum(sp + OVERHEAD for sp in spans)
    print(f"expected wall-clock, one session at a time, each chunk's finishing time plus {OVERHEAD} s: "
          f"{wall:.0f} s = {wall / 86400:.2f} days; sessions expected {len(chunks)}")
    ub = math.ceil(len(units) * KIND["time_cap_seconds"] / capacity)
    print(f"sessions at most, if every unit used its whole time cap: {ub}")
    print(f"written {os.path.relpath(os.path.join(out_dir, 'manifest.json'), REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
