"""
The registered runner for suites B and C (docs/PREREG.md v1.1 draft; docs/ADAPTER_FEASIBILITY.md).
It plays the frozen agents R (mode hash_state), N (mode nav) and I1 (mode i1) through the suite
adapters, without editing any frozen file:
    - the ARC shim of scripts/env_frame.py stands in for arc_agi/arcengine, with the accepted key maps
      (env_frame.KEY_MAPS; items 9-11), the canvas placement (row offset 1, padding 0; items 12-13)
      and each adapter's RESET semantics (minigrid "replay", procgen no-op; items 14-15);
    - R and N are called exactly as scripts/g_nav_run.py calls them (g_nav_run.py:60-78, 166):
      Config(max_actions=budget, seed=s, **MODES[mode]), g_nav.play for nav, g_agent.play for
      hash_state; I1 through scripts/i1_suite_adapter.py (C1-C5).
At start it checks the six frozen blob hashes against PREREG.md Section 5.4 and refuses to run if any
differs.  Rows follow PREREG.md Section 9.3: one JSON file per (suite, condition, agent, game, seed),
runs/suites/<suite>/<condition>/<mode>/<game>__<seed>.json, holding a one-element list (the format
scripts/analyze_*.py read).  Field `seconds` is the run's wall time measured by this script (the cap of
PREREG v1.1 D5 is computed from the pilot rows by scripts/pilot_cap.py).  Rows cut by the wall-clock cap (actions < budget) are kept and marked
cut_by_cap.  Worker pool, spawn-safe (the shim is installed inside the worker), resume-safe (an
existing row without error is skipped unless --force), atomic writes.

--games    comma list, or "pilot" (PREREG.md Section 8), or "confirmatory" (the truth table minus
           exclusions and pilots)
--dry-run  builds each environment once (one reset, no step) and prints the action map; plays nothing

Run in the suite's venv: .venv_games for minigrid, .venv_procgen for procgen.  Commands:
docs/W2_COMMANDS.md.

EXPECTED OUTPUT (shape):
    frozen blob hashes: 6 of 6 match PREREG.md Section 5.4
    run_suite minigrid macro: 6 games x 10 seeds x 3 modes = 180 jobs, N to run, 8 workers
    done <game> seed <s> <mode>: levels L actions A [cut] [ERROR ...]
    summary: N rows, N errors, N cut by the cap
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import env_frame as EF  # noqa: E402

# PREREG.md Section 5.4 (commit 8d209b3; unchanged at tag prereg-v1)
EXPECTED_BLOBS = {
    "scripts/g_agent.py": "72585a4dbb926d4512ff9596f58118a176bb0646",
    "scripts/g_nav.py": "a8a7eb61e62a658c239b98e0224e3588a662d1a0",
    "scripts/g_motion.py": "14018512a5c6b0efc81aed61c5466654d338be0b",
    "scripts/g_control_probe.py": "d5ff2a4dc77b9e1148929e7db03fe99a9d2b0bf8",
    "scripts/g_nav_run.py": "2cc0146a697e525e5873d4e29cb80f4ae8bd6297",
    "scripts/g_census_table.py": "488feaca9c10985c4d0ff62791ceb4fa6fa6b9a8",
}
CONDITIONS = {"minigrid": ("raw", "macro"), "procgen": ("center_off", "center_on")}
AGENT = {"hash_state": "R", "nav": "N", "i1": "I1"}


def check_frozen():
    got = EF.frozen_hashes()
    bad = {f: (got.get(f), h) for f, h in EXPECTED_BLOBS.items() if got.get(f) != h}
    return got, bad


def make_factory(suite, condition):
    def make(game):
        if suite == "procgen":
            from adapter_procgen import ProcgenAdapter
            return ProcgenAdapter(game, condition)
        from adapter_minigrid import MinigridAdapter
        return MinigridAdapter(game, condition, episode_seeding="replay")
    return make


def select_games(suite, spec):
    import analyze_common as C
    if suite == "minigrid":
        truth = C.parse_truth_minigrid(os.path.join(REPO, "docs", "GROUND_TRUTH_minigrid.md"))
        pilots = list(C.PILOTS_B)
    else:
        truth = C.parse_truth_procgen(os.path.join(REPO, "docs", "GROUND_TRUTH_procgen.md"))
        pilots = list(C.PILOTS_C)
    if spec == "pilot":
        return pilots
    if spec == "confirmatory":
        return C.confirmatory(suite, truth)
    games = [g for g in spec.split(",") if g]
    unknown = [g for g in games if g not in truth]
    if unknown:
        sys.exit(f"STOP: not registered in the {suite} truth table: {unknown}")
    excluded = [g for g in games if truth[g]["status"].startswith("excluded")]
    if excluded:
        sys.exit(f"STOP: excluded ids: {excluded}")
    return games


def out_path(out, suite, cond, mode, game, seed):
    return os.path.join(out, suite, cond, mode, f"{game}__{seed}.json")


def one(job):
    suite, cond, game, seed, mode, budget, seconds, out = job
    import logging
    logging.disable(logging.CRITICAL)
    make = make_factory(suite, cond)
    env = None
    t0 = time.time()
    try:
        if mode == "i1":
            import i1_suite_adapter as I
            r, env = I.play(game, seed, budget, seconds, suite, cond, make)
        else:
            made = EF.install_arc_shim(make, seed,
                                       key_map=lambda ad: EF.resolve_key_map(suite, cond, ad), row_offset=1)
            import g_agent as A
            from g_nav_run import MODES
            cfg_d = asdict(A.Config(max_actions=budget, seed=seed, **MODES[mode]))
            if mode == "nav":
                import g_nav
                r = g_nav.play(game, A.Config(**cfg_d), REPO, seconds=seconds)
            else:
                r = A.play(game, A.Config(**cfg_d), REPO, seconds=seconds)
            env = made[-1] if made else None
    except Exception as e:
        import traceback
        r = dict(game=game, levels=0, error=repr(e)[:300], trace=traceback.format_exc()[-1500:], diag={}, level_log=[])
    r["mode"], r["seed"] = mode, seed
    r.update(suite=suite, condition=cond, agent=AGENT[mode], score=None)
    acts = int(r.get("actions", 0) or 0)
    r["level1_completed"] = int(r.get("levels", 0) or 0) >= 1
    r["level1_actions"] = env.first_level_end if env is not None else None
    r["cut_by_cap"] = ("error" not in r) and acts < budget
    # seconds = this run's wall time, measured here for every mode (PREREG v1.1 D5; scripts/pilot_cap.py);
    # the agent's own timer, if it reported one, is kept as agent_seconds
    if "seconds" in r:
        r["agent_seconds"] = r["seconds"]
    r["budget"], r["seconds_cap"], r["seconds"] = budget, seconds, round(time.time() - t0, 1)
    if env is not None:
        rec = env.adapter.record()
        rec["key_map"] = {str(k): env.adapter.actions[i] for k, i in env.key_map.items()}
        rec["canvas"] = dict(size=EF.CANVAS, row_offset=env.row_offset, padding=EF.PAD)
        rec["run_suite_blob"] = EF.git_blob_hash("scripts/run_suite.py")
        if mode == "i1":
            rec["i1_suite_adapter_blob"] = EF.git_blob_hash("scripts/i1_suite_adapter.py")
        r["adapter"] = rec
        try:
            env.adapter.close()
        except Exception:
            pass
    if mode == "nav" and isinstance(r.get("nav"), dict):
        import analyze_common as C
        r["census"] = C.census_from_report(r["nav"])
    p = out_path(out, suite, cond, mode, game, seed)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump([r], f, default=str)
    os.replace(tmp, p)
    return game, seed, mode, r.get("levels"), acts, r["cut_by_cap"], r.get("error")


def dry_run(suite, conds, games):
    print("dry run: one reset per environment, no step")
    for cond in conds:
        make = make_factory(suite, cond)
        for g in games:
            try:
                ad = make(g)
                grid = ad.reset(1000)
                km = EF.resolve_key_map(suite, cond, ad)
                ki = EF.resolve_key_map(suite, cond, ad, ids=EF.I1_KEYS)
                print(f"{suite} {cond} {g}: grid {list(grid.shape)} colours {int(grid.max())} actions {ad.actions}")
                print(f"    R/N key map {{ARC id: action}} = {{{', '.join(f'{k}: {ad.actions[i]}' for k, i in sorted(km.items()))}}}")
                print(f"    I1 key map = {{{', '.join(f'{k}: {ad.actions[i]}' for k, i in sorted(ki.items()))}}}")
                ad.close()
            except Exception as e:
                print(f"{suite} {cond} {g}: ERROR {type(e).__name__}: {e}")


def main():
    ap = argparse.ArgumentParser(description="Registered runner for suites B and C")
    ap.add_argument("--suite", required=True, choices=sorted(CONDITIONS))
    ap.add_argument("--condition", required=True, help="one condition or a comma list")
    ap.add_argument("--games", required=True, help='comma list, "pilot" or "confirmatory"')
    ap.add_argument("--modes", default="hash_state,nav")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--budget", type=int, default=20000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seconds", type=float, default=None, help="wall-clock cap per run (PREREG v1.1 item 16)")
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "suites"))
    ap.add_argument("--resume", action="store_true", help="skip rows already written without error (default on)")
    ap.add_argument("--force", action="store_true", help="rerun rows that exist")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    got, bad = check_frozen()
    if bad:
        for f, (g, h) in bad.items():
            print(f"FROZEN FILE CHANGED: {f} blob {g} != PREREG {h}")
        sys.exit("STOP: a frozen census file differs from PREREG.md Section 5.4")
    print(f"frozen blob hashes: {len(EXPECTED_BLOBS)} of {len(EXPECTED_BLOBS)} match PREREG.md Section 5.4")

    conds = [c for c in args.condition.split(",") if c]
    for c in conds:
        if c not in CONDITIONS[args.suite]:
            sys.exit(f"STOP: condition {c} is not a {args.suite} condition {CONDITIONS[args.suite]}")
    modes = [m for m in args.modes.split(",") if m]
    for m in modes:
        if m not in AGENT:
            sys.exit(f"STOP: unknown mode {m}")
    games = select_games(args.suite, args.games)
    if args.dry_run:
        dry_run(args.suite, conds, games)
        return
    if args.seconds is None:
        sys.exit("STOP: --seconds (the registered cap, PREREG v1.1 item 16) is required for a run")

    jobs = []
    for c in conds:
        for g in games:
            for s in range(args.seeds):
                for m in modes:
                    seed = 1000 + s
                    p = out_path(args.out, args.suite, c, m, g, seed)
                    if os.path.exists(p) and not args.force:
                        with open(p, encoding="utf-8") as f:
                            if "error" not in json.load(f)[0]:
                                continue
                    jobs.append((args.suite, c, g, seed, m, args.budget, args.seconds, args.out))
    total = len(conds) * len(games) * args.seeds * len(modes)
    print(f"run_suite {args.suite} {','.join(conds)}: {len(games)} games x {args.seeds} seeds x {len(modes)} modes"
          f"{' x ' + str(len(conds)) + ' conditions' if len(conds) > 1 else ''} = {total} jobs, "
          f"{len(jobs)} to run, {args.workers} workers", flush=True)
    n_err = n_cut = 0
    if jobs:
        with Pool(args.workers) as pool:
            for g, s, m, lv, acts, cut, err in pool.imap_unordered(one, jobs):
                n_err += bool(err)
                n_cut += bool(cut)
                print(f"done {g} seed {s} {m}: levels {lv} actions {acts}" + (" CUT" if cut else "")
                      + (f" ERROR {err}" if err else ""), flush=True)
    print(f"summary: {len(jobs)} rows written this call, {n_err} errors, {n_cut} cut by the cap")


if __name__ == "__main__":
    main()
