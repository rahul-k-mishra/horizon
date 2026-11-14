"""
engine_semantics.py -- three checks of the recommended engine on the 20 pilot levels (docs/design/ENGINE.md,
Section 3).  The pilot games never enter a confirmatory analysis (docs/PREREG.md, Section 4); no confirmatory
level is played here.  Nothing printed is a search quantity of a level (no state count, win or solution length).

1. The game loop against the forward model.  The search and the agents step a level through GVGAI's forward
   model (StateObservation.advance on a copy, ForwardModel.java).  GVGAI's own game loop (Game.runGame and
   Game.gameCycle) is a separate piece of code.  For seeded random action sequences, the sequence is played by
   the game loop with a player that records the state GVGAI hands it at every decision, and by the forward model
   from the level start.  At every decision before the game ends, the state keys with the game tick must be
   equal.  If the game ends, the final states' keys without the tick must be equal, their statuses equal, and
   their ticks are printed: the game loop counts a tick when a cycle starts (Game.java:1093) and the forward
   model when an advance ends (ForwardModel.java, advance_aux), so after the last cycle they differ by one.
2. The key decides the successors.  The search merges two states whose keys are equal and expands only the first
   path's state.  That is sound only if the key holds everything the successors depend on.  A breadth-first
   search of up to WALK expansions with the registered key; whenever a successor's key was already seen through
   another path, the successors of both paths' states are computed (up to MERGES such pairs per level) and their
   keys and statuses compared.  This is done with the registered key, with the extended key of the bridge (the
   registered fields plus the counters GVGAI keeps per sprite: a Flicker's age, a SpawnPoint's counter and first
   tick, every sprite's health points, the ticks since the last move of a sprite whose cooldown exceeds 1), and,
   for information, with the registered key under the other tick rule.
3. Determinism.  Each sequence of check 1 is played twice through the forward model; the keys must be equal.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\engine_semantics.py --cache D:\\Research\\horizon\\gvgai-cache > logs\\engine_semantics.log

Names since 14 November 2026: the key called "registered" above and in logs/engine_semantics.log is the key of
docs/PREREG.md v0, now called "v0"; the extended key is the registered state (PREREG Section 6, decided that day)
and the default of the search.  --merge-only repeats check 2 alone, with the v0 key and the extended key, at a
larger walk and number of merges (the re-run asked for by that decision):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\engine_semantics.py --cache D:\\Research\\horizon\\gvgai-cache --merge-only --walk 30000 --merges 5000 > logs\\engine_merge_rerun.log
"""
from __future__ import annotations

import argparse
import collections
import os
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts", "automation"))
import sim_gvgai  # noqa: E402


def pilot_games():
    with open(os.path.join(REPO, "logs", "draw_pilot.log"), encoding="utf-8") as f:
        line = next(ln for ln in f.read().splitlines() if ln.startswith("pilot ("))
    return [x.strip() for x in line.split(":", 1)[1].split(",")]


def as_list(o):
    return [bytes(k) for k in o[0]], [int(t) for t in o[1]], int(o[2])


def loop_vs_model(bridge, gf, lf, seq):
    """(agrees, decisions compared, final tick pair or None, first difference or None)."""
    gk, gt, gs = as_list(bridge.gameLoopKeys(gf, lf, seq, True))
    fk, ft, fs = as_list(bridge.forwardKeys(gf, lf, seq, True))
    gk0, _, _ = as_list(bridge.gameLoopKeys(gf, lf, seq, False))
    fk0, _, _ = as_list(bridge.forwardKeys(gf, lf, seq, False))
    ended = gs != 0 or fs != 0
    n_before = min(len(gk), len(fk)) - (1 if ended else 0)
    diff = next((i for i in range(n_before) if gk[i] != fk[i] or gt[i] != ft[i]), None)
    ok = diff is None and len(gk) == len(fk) and gs == fs
    end_ticks = None
    if ok and ended:
        ok = gk0[-1] == fk0[-1]
        end_ticks = (gt[-1], ft[-1])
        if not ok:
            diff = len(gk) - 1
    elif ok and not ended:
        ok = gk[-1] == fk[-1] and gt[-1] == ft[-1]
        if not ok:
            diff = len(gk) - 1
    return ok, n_before, end_ticks, (None if ok else (diff, len(gk), len(fk), gs, fs))


def merge_check(bridge, cache, game, level, tick, walk, merges, form="v0"):
    """BFS with the key `form` and tick rule `tick`; at a merge, both paths' successors are compared."""
    sim = sim_gvgai.GVGAISim(dict(with_tick={game: tick}, gvgai_cache=cache, key_form=form), dict(game=game, level=level))
    first = {}
    key0, w0, l0 = sim.root_info()
    first[key0] = sim.root_enc()
    q = collections.deque([sim.root_enc()] if not (w0 or l0) else [])
    pending, expanded = [], 0
    while q and expanded < walk:
        enc = q.popleft()
        expanded += 1
        _pk, kids = sim.expand(enc)
        for _a, enc2, key2, win, loss in kids:
            if key2 in first:
                if first[key2] != enc2 and len(pending) < merges and not (win or loss):
                    pending.append((first[key2], enc2))
                continue
            first[key2] = enc2
            if not (win or loss):
                q.append(enc2)
    bad = 0
    for e1, e2 in pending:
        s1 = [(k[2], k[3], k[4]) for k in sim.expand(e1)[1]]
        s2 = [(k[2], k[3], k[4]) for k in sim.expand(e2)[1]]
        bad += int(s1 != s2)
    return len(pending), bad


def merge_only(a):
    """Check 2 alone on the 20 pilot levels, with the v0 key and the extended (registered) key."""
    sim_gvgai.start_jvm(a.cache)
    games = pilot_games()
    print(f"== check 2 alone (--merge-only); pilot games: {', '.join(games)}; levels 0 to 4")
    print(f"a breadth-first search of up to {a.walk} expansions per level; up to {a.merges} merges compared per level "
          f"and key form; a merge is a successor whose key was already seen through another path, and both "
          f"paths' states are expanded and their successors' keys and statuses compared")
    print("nothing printed is a search quantity of a level (no state count, win or solution length)")
    print("\n== per level: game level | tick in the key | v0 key: merges compared, differing | extended key: merges "
          "compared, differing")
    tot = collections.Counter()
    t0 = time.time()
    for g in games:
        tick = sim_gvgai.with_tick(g)
        for lv in range(5):
            c0 = merge_check(None, a.cache, g, lv, tick, a.walk, a.merges, form="v0")
            c1 = merge_check(None, a.cache, g, lv, tick, a.walk, a.merges, form="extended")
            tot.update(v0=c0[0], v0_bad=c0[1], ext=c1[0], ext_bad=c1[1])
            print(f"{g:14s} {lv} | {'yes' if tick else 'no '} | {c0[0]}, {c0[1]} | {c1[0]}, {c1[1]}", flush=True)
    print("\n== totals")
    print(f"v0 key: {tot['v0']} merges compared, {tot['v0_bad']} with different successors")
    print(f"extended key: {tot['ext']} merges compared, {tot['ext_bad']} with different successors")
    print(f"wall time {time.time() - t0:.0f} s")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--sequences", type=int, default=50)
    ap.add_argument("--length", type=int, default=200)
    ap.add_argument("--walk", type=int, default=3000)
    ap.add_argument("--merges", type=int, default=500)
    ap.add_argument("--seed", type=int, default=20261114)
    ap.add_argument("--merge-only", action="store_true", help="check 2 alone, v0 key and extended key")
    a = ap.parse_args()
    if a.merge_only:
        return merge_only(a)
    bridge = sim_gvgai.start_jvm(a.cache)
    games = pilot_games()
    print(f"== pilot games: {', '.join(games)}; levels 0 to 4; seed {a.seed}")
    print(f"check 1 and 3: {a.sequences} random sequences of {a.length} actions per level; check 2: a breadth-first "
          f"search of up to {a.walk} expansions per level, up to {a.merges} merges compared")
    print("\n== per level: game level | registered key holds the tick | check 1: sequences agreeing, decisions "
          "compared, games ended (tick at the end: game loop, forward model) | check 3: replayed identically | "
          "check 2, merges compared and differing: registered key | extended key | registered key, other tick rule")
    tot = collections.Counter()
    end_offsets = collections.Counter()
    t0 = time.time()
    for g in games:
        gf, _ = sim_gvgai.level_paths(g, 0)
        reg_tick = sim_gvgai.with_tick(g)
        for lv in range(5):
            _, lf = sim_gvgai.level_paths(g, lv)
            gf_, lf_ = gf.replace("\\", "/"), lf.replace("\\", "/")
            rng = random.Random(f"{a.seed}-{g}-{lv}")
            root = bridge.load(gf_, lf_, 0)
            n_act = len(bridge.actionNames(root))
            agree = steps = det = ended = 0
            first_diff = None
            offs = collections.Counter()
            for k in range(a.sequences):
                seq = bytes(rng.randrange(n_act) for _ in range(a.length))
                ok, n, end_ticks, diff = loop_vs_model(bridge, gf_, lf_, seq)
                f1 = as_list(bridge.forwardKeys(gf_, lf_, seq, True))
                f2 = as_list(bridge.forwardKeys(gf_, lf_, seq, True))
                det += int(f1 == f2)
                agree += int(ok)
                steps += n
                if end_ticks:
                    ended += 1
                    offs[end_ticks[1] - end_ticks[0]] += 1
                if diff and first_diff is None:
                    first_diff = (k,) + diff
            c_reg = merge_check(bridge, a.cache, g, lv, reg_tick, a.walk, a.merges)
            c_ext = merge_check(bridge, a.cache, g, lv, reg_tick, a.walk, a.merges, form="extended")
            c_oth = merge_check(bridge, a.cache, g, lv, not reg_tick, a.walk, a.merges)
            tot.update(seq=a.sequences, agree=agree, steps=steps, det=det, ended=ended, reg=c_reg[0], reg_bad=c_reg[1],
                       ext=c_ext[0], ext_bad=c_ext[1], oth=c_oth[0], oth_bad=c_oth[1])
            end_offsets.update(offs)
            off_txt = ", ".join(f"{v} with the forward model {d:+d}" for d, v in sorted(offs.items())) or "none ended"
            print(f"{g:14s} {lv} | {'yes' if reg_tick else 'no '} | {agree}/{a.sequences}, {steps}, {ended} ({off_txt}) | "
                  f"{det}/{a.sequences} | {c_reg[0]}, {c_reg[1]} | {c_ext[0]}, {c_ext[1]} | {c_oth[0]}, {c_oth[1]}")
            if first_diff:
                k, i, lg, lfm, gs, fs = first_diff
                print(f"   first difference: sequence {k}, decision {i}; keys recorded {lg} (game loop), {lfm} "
                      f"(forward model); final status {gs} and {fs}")
    print("\n== totals")
    print(f"check 1: {tot['agree']} of {tot['seq']} sequences agree, {tot['steps']} decisions compared before any end; "
          f"{tot['ended']} sequences ended the game; tick at the end, forward model minus game loop: "
          + ", ".join(f"{d:+d} in {v}" for d, v in sorted(end_offsets.items())))
    print(f"check 2, registered key: {tot['reg']} merges compared, {tot['reg_bad']} with different successors")
    print(f"check 2, extended key: {tot['ext']} merges compared, {tot['ext_bad']} with different successors")
    print(f"check 2, registered key under the other tick rule (information only): {tot['oth']} merges compared, "
          f"{tot['oth_bad']} with different successors")
    print(f"check 3: {tot['det']} of {tot['seq']} sequences replayed identically")
    print(f"wall time {time.time() - t0:.0f} s")


if __name__ == "__main__":
    sys.exit(main())
