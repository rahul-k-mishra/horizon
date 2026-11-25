"""
make_gvgaiagent_dryrun_manifest.py -- writes jobs/gvgaiagent_dryrun/manifest.json, the dry run of the kind gvgaiagent
through the loop (rule R8, as for the kinds devsearch and gvgaisearch, docs/DRYRUN_DEVSEARCH.md and
docs/DRYRUN_GVGAISEARCH.md).  It is not the loop's manifest until it is copied to jobs/manifest.json.

One chunk, a-01, of 36 units, every one on a synthetic level of scripts/automation/gvgai_testgames; no pilot or
confirmatory level is played:
    12 units whose rows are known from the laptop: N, R, I1 and Rand, seed 1000, budget 300 actions, cap 240 s, on
       allwin level 0 (every action wins: 300 levels, first level end 1), corridor level 1 (no action can win: 0
       levels) and corridor level 0 (the laptop's rows are in logs/test_gvgaiagent.log, part 2);
    24 units that run to their wall-clock cap (ids ending "-cap"): N, R, I1 and Rand, seeds 1000 to 1005, on corridor level 1 with a
       budget of 10,000,000 actions and a cap of 120 s, so that the chunk holds about 6 rounds of 120 s on 4 workers,
       more than a session of 600 s of work can hold: the chunk must end partial, with a checkpoint, and be resumed.
The code is named by the full hash of the commit that holds the kind's code and pins (CODE_REF), not by a tag: no
tag is cut in the session that built the kind (the runner checks out any commit the manifest names,
kaggle/runner.ipynb, git worktree add).
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\make_gvgaiagent_dryrun_manifest.py > logs\\make_gvgaiagent_dryrun_manifest.log
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
from common import chunk_entry_hash, check_manifest  # noqa: E402

CODE_REF = "e608f7577820569fef94bb40b89db19839a8cda3"   # the kind's code and the runner pins, 25 November 2026
AGENTS = ("N", "R", "I1", "Rand")
KIND = dict(agent_impl="gvgai", budget=300, unit_seconds_cap=240, workers=4,
            games_dir="scripts/automation/gvgai_testgames")
SESSION = dict(work_seconds=600, checkpoint_reserve_seconds=300, platform_limit_seconds=3600)
SLOW = dict(budget=10_000_000, unit_seconds_cap=120)


def main():
    units = []

    def add(agent, game, level, seed, params=None):
        u = dict(unit_id=f"a-01-{agent}-{game}-l{level}-s{seed}" + ("-cap" if params else ""), chunk_id="a-01", kind="gvgaiagent", suite="gvgai",
                 game=game, level=level, agent=agent, seed=seed, status="pending")
        if params:
            u["params"] = params
        units.append(u)
    for game, level in (("allwin", 0), ("corridor", 1), ("corridor", 0)):
        for agent in AGENTS:
            add(agent, game, level, 1000)
    for seed in range(1000, 1006):
        for agent in AGENTS:
            add(agent, "corridor", 1, seed, dict(SLOW))
    m = dict(campaign="gvgaiagent-dryrun", code_tag=CODE_REF, repository="rahul-k-mishra/horizon",
             kernel_slug="horizon-runner", max_failures=3, payload_commit_limit_bytes=50_000_000, session=SESSION,
             kinds=dict(gvgaiagent=KIND),
             chunks=[dict(chunk_id="a-01", kind="gvgaiagent", status="pending", attempts=0, failures=0, sessions=[])],
             units=units)
    errs = check_manifest(m)
    if errs:
        raise SystemExit(f"manifest check failed: {errs}")
    d = os.path.join(REPO, "jobs", "gvgaiagent_dryrun")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    quick = [u for u in units if "params" not in u]
    slow = [u for u in units if "params" in u]
    print(f"campaign {m['campaign']}, code {CODE_REF}, kind gvgaiagent, 1 chunk, {len(units)} units")
    print(f"session: {SESSION}")
    print(f"kind params: {KIND}")
    print(f"{len(quick)} units at the kind's params (budget 300, cap 240 s): allwin 0, corridor 1, corridor 0 x N, R, I1, Rand, seed 1000")
    print(f"{len(slow)} units with params {SLOW}: corridor 1 x N, R, I1, Rand x seeds 1000 to 1005")
    rounds = -(-len(slow) // KIND["workers"])
    print(f"the capped units alone: {rounds} rounds of {SLOW['unit_seconds_cap']} s on {KIND['workers']} workers = "
          f"{rounds * SLOW['unit_seconds_cap']} s, against {SESSION['work_seconds']} s of work per session")
    print(f"entry hash of a-01: {chunk_entry_hash(m, 'a-01')}")
    print("written: jobs/gvgaiagent_dryrun/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
