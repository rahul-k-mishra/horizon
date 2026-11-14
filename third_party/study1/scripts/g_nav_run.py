"""
G-NAV against the held-out-best explorer (hash_state), same games, same seeds, one process per
game run, worker pool.  Reports the numbers the formula pays for: PER LEVEL, the scorecard's own
action count against the human count and the level score, plus every G-NAV counter, so a failure
is named, not averaged away.

    python g_nav_run.py --games train    --seeds 2 --budget 3000  --workers 8      (quick check)
    python g_nav_run.py --games train    --seeds 4 --budget 20000 --workers 8      (train verdict)
    python g_nav_run.py --games heldout  --seeds 4 --budget 20000 --workers 8      (measured, never chosen on)
    python g_nav_run.py --games tu93,ls20 --modes nav --seeds 1 --budget 2000     (one game, look at it)
    python g_nav_run.py --games tu93,dc22,ls20 --modes hash_state,nav,nav_oracle --seeds 10 --budget 20000 --tag e9_oracle_3x10   (E9)

Writes navrun_<tag>.json (rows in the ablate format, so g_decompose.py reads it too).

RESUMING (--resume).  Every run appends its row to navrun_<tag>.json.partial.jsonl as it
completes; the partial file is removed when all runs have finished.  Re-running the SAME command
with --resume keeps the completed (game, seed, mode) rows found in navrun_<tag>.json (if it exists)
and in the partial file, runs only the missing ones, and writes the merged file.  A row is kept
only if it was run with this --budget: it used exactly --budget actions, or it won the game at or
before --budget (runs are deterministic given the seed, so a won run is the same at any larger
budget).  A row that used fewer actions without winning (cut by --game-seconds, or run with a
smaller budget) is not kept and is run again.  A row with more actions than --budget comes from another budget: the script stops.
Kept rows are copied unchanged.  Without --resume every run is played and navrun_<tag>.json is
written atomically (temp file, then rename); a stale partial file from an earlier stopped run is
kept as <partial>.prev rather than read.

EXISTING OUTPUT (changed 26 Sep 2026; docs/TOG_PLAN_v2.md Section 8).  If navrun_<tag>.json
already exists the script stops before playing anything, naming the file: pass --force to replace
it, or use a new --tag.  --resume reads and extends it as above.  Before this change a completed
run's file could be replaced silently by a different run with the same tag.

    python g_nav_run.py --games all --modes hash_state --seeds 4 --budget 100000 --tag e3_hash_25x4_100k --resume

VERDICT RULE (train only): nav is accepted if its train mean score is >= hash_state's and no
train game loses a level on the seed-mean.  The held-out table is printed and never used to
choose anything.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict, Counter
from dataclasses import asdict
from multiprocessing import Pool

import g_agent as A
import g_control_probe as M1

HERE = os.path.dirname(os.path.abspath(__file__))
KEYBOARD_TRAIN = ["tu93", "ls20", "dc22", "m0r0", "lf52"]
MODES = {
    "hash_state": {"mode": "hash"},
    "nav":        {"mode": "hash"},            # same explorer underneath, plus the hook
    "nav_oracle": {"mode": "hash"},            # E9: nav plus the true goal colour (tu93, dc22 only)
}


def one(job):
    game, cfg_d, seconds, env_dir, mode = job
    import logging
    logging.disable(logging.CRITICAL)
    try:
        if mode == "nav":
            import g_nav
            r = g_nav.play(game, A.Config(**cfg_d), env_dir, seconds=seconds)
        elif mode == "nav_oracle":
            import g_nav
            r = g_nav.play(game, A.Config(**cfg_d), env_dir, seconds=seconds,
                           oracle=g_nav.ColourOracle(game))
        else:
            r = A.play(game, A.Config(**cfg_d), env_dir, seconds=seconds)
    except Exception as e:
        import traceback
        r = dict(game=game, levels=0, score=0.0, error=repr(e)[:300],
                 trace=traceback.format_exc()[-1500:], diag={}, level_log=[])
    r["mode"], r["seed"] = mode, cfg_d["seed"]
    return r


def level_line(r):
    """per level: scorecard actions / human -> level score; falls back to level_log if the card
    data is missing (then it is marked ~, and is an undercount)."""
    ca, cb, cs = r.get("card_levels"), r.get("card_baseline"), r.get("card_scores")
    if ca and cb:
        parts = []
        for i, (a, h) in enumerate(zip(ca, cb)):
            if a == 0 and i >= r.get("levels", 0):
                break
            s = cs[i] if cs and i < len(cs) else 0.0
            done = i < r.get("levels", 0)
            parts.append(f"L{i + 1}:{a}/{h}->{s:.1f}" if done else f"L{i + 1}:{a}/{h} unfinished")
        return "  ".join(parts)
    return "~" + "  ".join(f"L{L.get('level', 0) + 1}:{L.get('actions')} {L.get('ended')}"
                            for L in r.get("level_log", []))


def nav_line(r):
    n = r.get("nav")
    if not n:
        return "-"
    c = n.get("counters", {})
    keys = ["avatar_found", "step_ok", "step_bumped", "step_mispredict", "obs_ok", "obs_bumped",
            "obs_mispredict", "wall_contradicted", "goal_recorded", "goal_targets",
            "goal_reached_no_end", "goal_confirmed", "frontier_exhausted", "deaths", "replans"]
    s = " ".join(f"{k}={c[k]}" for k in keys if k in c)
    fb = [f"L{L['level'] + 1}:{L['fallback']}" for L in n.get("levels", []) if L.get("fallback")]
    goals = [f"L{L['level'] + 1}:{L['goal']}" for L in n.get("levels", []) if L.get("goal")]
    return (s + (" | fallback " + ",".join(fb) if fb else "") + (" | goal " + " ".join(goals) if goals else "")
            + f" | eff {n.get('eff')} walls {n.get('walls')} deadly {n.get('deadly')} avoid_near {n.get('avoid_near')} co_movers {n.get('co_movers')}/{n.get('key_presses_sampled')}")


def resume_rows(out_path, part, budget, wanted):
    """Completed rows of this tag run with this budget (see RESUMING in the docstring)."""
    src = []
    if os.path.exists(out_path):
        src += [("output", r) for r in json.load(open(out_path))]
    if os.path.exists(part):
        src += [("partial", json.loads(l)) for l in open(part) if l.strip()]
    kept, rerun = {}, []
    for where, r in src:
        key = (r.get("game"), r.get("seed"), r.get("mode"))
        if key not in wanted or r.get("error"):
            continue
        acts = int(r.get("actions", -1))
        if acts > budget:
            raise SystemExit(f"STOP: {key} in the {where} file has {acts} actions, more than "
                             f"--budget {budget}: it was run with another budget; not mixed")
        if acts == budget or (r.get("state") == "WIN" and acts <= budget):
            kept.setdefault(key, r)
        else:
            rerun.append(key)
    rerun = sorted(set(rerun) - set(kept))
    print(f"resume: {len(kept)} completed rows kept from {out_path} and its partial file"
          + (f"; {len(rerun)} rows that did not use the full budget and did not win (cut by the clock, or run with a smaller budget) will be run again: {rerun[:6]}"
             f"{' ...' if len(rerun) > 6 else ''}" if rerun else ""))
    return list(kept.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default="train", help="train | heldout | keyboard | all | comma list")
    ap.add_argument("--modes", default="hash_state,nav")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--budget", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--game-seconds", type=float, default=900)
    ap.add_argument("--hours", type=float, default=9.0)
    ap.add_argument("--env-dir", default=os.path.join(HERE, "environment_files"))
    ap.add_argument("--tag", default="navrun")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="replace an existing navrun_<tag>.json (without it the script stops)")
    ap.add_argument("--resume", action="store_true",
                    help="keep completed rows of this tag (output file and partial file) run with "
                         "the same budget; run only the missing ones")
    args = ap.parse_args()
    games = (M1.TRAIN if args.games == "train" else M1.HELD_OUT if args.games == "heldout"
             else KEYBOARD_TRAIN if args.games == "keyboard"
             else M1.TRAIN + M1.HELD_OUT if args.games == "all" else args.games.split(","))
    modes = [m for m in args.modes.split(",") if m in MODES]
    if "nav_oracle" in modes and any(g in M1.HELD_OUT for g in games):
        raise SystemExit("STOP: nav_oracle (E9) is for the source-informed train games tu93, dc22 and "
                         "ls20 only; never a held-out game (docs/E9_protocol.md)")
    jobs = [(g, asdict(A.Config(max_actions=args.budget, seed=1000 + s, **MODES[m])),
             args.game_seconds, args.env_dir, m)
            for s in range(args.seeds) for m in modes for g in games]
    out_path = os.path.join(HERE, f"navrun_{args.tag}.json")
    if os.path.exists(out_path) and not args.resume and not args.force:
        raise SystemExit(f"STOP: {out_path} already exists. Pass --force to replace it, or use a new "
                         f"--tag (or --resume to continue it).")
    part = out_path + ".partial.jsonl"
    kept = []
    if args.resume:
        kept = resume_rows(out_path, part, args.budget, {(g, 1000 + s, m) for s in range(args.seeds)
                                                         for m in modes for g in games})
        have = {(r["game"], r["seed"], r["mode"]) for r in kept}
        jobs = [j for j in jobs if (j[0], j[1]["seed"], j[4]) not in have]
    elif os.path.exists(part):
        os.replace(part, part + ".prev")
    print(f"{len(games)} games x {modes} x {args.seeds} seeds = {len(jobs)} runs, "
          f"{args.budget} actions, {args.workers} workers\n", flush=True)
    t0, rows = time.time(), list(kept)
    finished = True
    with Pool(args.workers) as pool:
        it = pool.imap_unordered(one, jobs)
        for i in range(len(jobs)):
            try:
                r = it.next(timeout=max(1, args.hours * 3600 - (time.time() - t0)))
            except Exception:
                print("TIME CAP REACHED - reporting what finished")
                pool.terminate()
                finished = False
                break
            rows.append(r)
            with open(part, "a") as f:
                f.write(json.dumps(r) + "\n")
            if not args.quiet:
                print(f"[{i + 1}/{len(jobs)} {(time.time() - t0) / 60:.0f} min] {r['game']} {r['mode']:10} "
                      f"seed {r['seed']} score {r.get('score', 0):8.4f} levels {r.get('levels', 0)} "
                      f"actions {r.get('actions', '?')}" + (f"  ERROR {r['error']}" if r.get("error") else ""),
                      flush=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rows, f, indent=1)
    os.replace(tmp, out_path)
    if finished and os.path.exists(part):
        os.remove(part)

    # ---- summary
    by = defaultdict(list)
    for r in rows:
        by[(r["mode"], r["game"])].append(r)
    for r in rows:
        if r.get("error"):
            print(f"\nERROR {r['game']} {r['mode']} seed {r['seed']}: {r['error']}\n{r.get('trace', '')}")
    print(f"\n{'game':6} {'mode':10} {'mean':>8} {'levels':>7}  per seed: score/levels")
    for g in games:
        for m in modes:
            v = by.get((m, g), [])
            if not v:
                continue
            ms = sum(x["score"] for x in v) / len(v)
            ml = sum(x["levels"] for x in v) / len(v)
            per = " ".join(f"{x['score']:.3f}/{x['levels']}" for x in sorted(v, key=lambda x: x["seed"]))
            print(f"{g:6} {m:10} {ms:8.4f} {ml:7.2f}  {per}")
    print("\nPER LEVEL (scorecard actions / human -> level score), and the G-NAV counters:")
    for g in games:
        for m in modes:
            for r in sorted(by.get((m, g), []), key=lambda x: x["seed"]):
                print(f"{g:6} {m:10} s{r['seed']} {level_line(r)}")
                if m == "nav":
                    print(f"{'':6} {'':10}       {nav_line(r)}")
    tr = [g for g in games if g in M1.TRAIN]
    ho = [g for g in games if g in M1.HELD_OUT]
    print()
    for name, gs in (("TRAIN", tr), ("HELD-OUT", ho)):
        if not gs:
            continue
        line = []
        for m in modes:
            v = [x for g in gs for x in by.get((m, g), [])]
            if v:
                line.append(f"{m} mean {sum(x['score'] for x in v) / len(v):.4f} "
                            f"levels {sum(x['levels'] for x in v) / max(1, args.seeds):.1f}/seed")
        print(f"{name:9} ({len(gs)} games): " + " | ".join(line))
    if tr and "nav" in modes and "hash_state" in modes:
        lost = []
        for g in tr:
            a = by.get(("hash_state", g), []); b = by.get(("nav", g), [])
            if a and b and sum(x["levels"] for x in b) / len(b) < sum(x["levels"] for x in a) / len(a) - 1e-9:
                lost.append(g)
        va = [x for g in tr for x in by.get(("hash_state", g), [])]
        vb = [x for g in tr for x in by.get(("nav", g), [])]
        if va and vb:
            ma, mb = sum(x["score"] for x in va) / len(va), sum(x["score"] for x in vb) / len(vb)
            print(f"\nTRAIN VERDICT: nav {mb:.4f} vs hash_state {ma:.4f}; games losing levels: {lost or 'none'}"
                  f" -> {'ACCEPT' if mb >= ma and not lost else 'REJECT'}")
    if "nav" in modes:
        print("\nCENSUS (nav arm): per game, is there a controllable avatar, and what happened")
        print(f"{'game':6} {'avatar':>8} {'accepted keys -> step (agree/presses)':52} {'first-level outcome by seed'}")
        for g in games:
            v = sorted(by.get(("nav", g), []), key=lambda x: x["seed"])
            if not v:
                continue
            found = [int(x.get("nav", {}).get("counters", {}).get("avatar_found", 0)) for x in v]
            keys = {}
            for x in v:
                for k, info in x.get("nav", {}).get("learn", {}).items():
                    if info.get("decided") == "accepted":
                        keys.setdefault(k, []).append(f"{info['shift']} {info['agree']}/{info['presses']}")
            kstr = "; ".join(f"{k}:{'|'.join(sorted(set(vv)))}" for k, vv in sorted(keys.items())) or "-"
            outs = []
            for x in v:
                lv = (x.get("nav", {}).get("levels") or [{}])[0]
                outs.append(lv.get("fallback") or ("won" if x.get("levels", 0) >= 1 else "unfinished"))
            print(f"{g:6} {sum(found)}/{len(found):>5}  {kstr[:52]:52} {' '.join(outs)}")
    if ho:
        print("HELD-OUT is measured only; it is never used to choose.")


if __name__ == "__main__":
    main()
