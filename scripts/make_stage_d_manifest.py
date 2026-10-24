"""
make_stage_d_manifest.py -- writes the manifest of stage D, the development search (docs/DESIGN.md, Section 2.1),
to jobs/stage_d/manifest.json.  It is not the loop's manifest: it replaces jobs/manifest.json only when the
stage is launched, after the dry run of the kind devsearch is committed.

Reads study 1's truth table through study 1's own parser (read-only, as scripts/oracle_v2.py does) for the
list of its confirmatory MiniGrid/BabyAI games.  Units: one per (game, seed) for seeds 1000 to 1009, the
macro condition, kind devsearch; games whose sprites move at random (Dynamic-Obstacles) are left out.
Caps are the registered values (docs/PREREG.md, Section 6): node cap 5,000,000, time cap 14,400 s, memory
6 GiB per worker, spill at 1,000,000 frontier entries, checkpoints every 600 s or 250,000 expansions; the
effective-horizon bound for levels of at most 200,000 states with T = 400.  Session values are the study's
(docs/AUTOMATION.md, Section 3).  Chunks hold GAMES_PER_CHUNK games each, in name order.
Prints the counts and the chunk arithmetic: the chunks in the manifest, and the upper bound on sessions if
every unit used its whole time cap.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\make_stage_d_manifest.py > logs\\make_stage_d_manifest.log
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
from common import check_manifest  # noqa: E402

SEEDS = range(1000, 1010)
GAMES_PER_CHUNK = 4
EXCLUDED = ("Dynamic-Obstacles",)
KIND = dict(simulator="minigrid", condition="macro", workers=4, node_cap=5_000_000, time_cap_seconds=14400,
            memory_cap_bytes=6442450944, spill_frontier_over=1_000_000, checkpoint_every_seconds=600,
            checkpoint_every_nodes=250000, batch=200, eh_state_limit=200000, eh_horizon=400)
SESSION = dict(work_seconds=28800, checkpoint_reserve_seconds=900, platform_limit_seconds=32400)


def main(argv=None):
    import oracle_v2 as O  # noqa: PLC0415
    old = r"D:\Research\arc3\repo"
    O.load_old(old)
    C = O.C
    truth = C.parse_truth_minigrid(os.path.join(old, "docs", "GROUND_TRUTH_minigrid.md"))
    conf = sorted(C.confirmatory("minigrid", truth))
    games = [g for g in conf if not any(x in g for x in EXCLUDED)]
    left_out = [g for g in conf if g not in games]
    chunks, units = [], []
    for i in range(0, len(games), GAMES_PER_CHUNK):
        cid = f"d-{i // GAMES_PER_CHUNK + 1:03d}"
        chunks.append(dict(chunk_id=cid, kind="devsearch", status="pending", attempts=0, failures=0, sessions=[]))
        for g in games[i:i + GAMES_PER_CHUNK]:
            for s in SEEDS:
                units.append(dict(unit_id=f"{cid}-{g}-s{s}", chunk_id=cid, kind="devsearch", suite="minigrid", game=g,
                                  level=s, agent=None, seed=None, status="pending"))
    m = dict(campaign="dev-minigrid", code_tag="automation-v2", repository="rahul-k-mishra/horizon",
             kernel_slug="horizon-runner", max_failures=3, payload_commit_limit_bytes=50_000_000,
             session=SESSION, kinds=dict(devsearch=KIND), chunks=chunks, units=units)
    errs = check_manifest(m)
    if errs:
        raise SystemExit(f"manifest check failed: {errs}")
    out_dir = os.path.join(REPO, "jobs", "stage_d")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    capacity = KIND["workers"] * SESSION["work_seconds"]
    print(f"study 1 confirmatory MiniGrid/BabyAI games: {len(conf)}; left out (sprites move at random): {len(left_out)} "
          f"({', '.join(left_out)}); in stage D: {len(games)}")
    print(f"units: {len(games)} games x {len(SEEDS)} seeds = {len(units)}; chunks in the manifest: {len(chunks)} "
          f"({GAMES_PER_CHUNK} games, {GAMES_PER_CHUNK * len(SEEDS)} units each, the last with "
          f"{len(units) - (len(chunks) - 1) * GAMES_PER_CHUNK * len(SEEDS)})")
    ub = math.ceil(len(units) * KIND["time_cap_seconds"] / capacity)
    print(f"sessions at most, if every unit used its whole time cap of {KIND['time_cap_seconds']} s on {KIND['workers']} "
          f"workers x {SESSION['work_seconds']} s: {ub}")
    print(f"sessions at least: {len(chunks)} (one per chunk, if each chunk finishes in one session)")
    print(f"written {os.path.relpath(os.path.join(out_dir, 'manifest.json'), REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
