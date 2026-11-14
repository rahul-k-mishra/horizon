"""
BRUTUS-G, milestone 1: can the agent work out, from the FRAMES ALONE and in a few moves, what it
controls and what each action does?

Nothing here reads a game's source.  The game is played through the public engine, frames in,
actions out, exactly as on Kaggle.  So this is fair to run on the HELD-OUT games.

Per game:
  LEARN  (--learn moves): press each available keyboard action in turn.  After each press, find
         what moved: for every colour, the cells of that colour that disappeared and the cells
         that appeared.  If they are the same shape shifted by one offset, that colour moved by
         that offset.  An action's effect is the offset seen most often for it.
  TEST   (--test moves):  press actions at random.  Before each press, PREDICT where the
         controlled object will be afterwards; after it, CHECK.  A press into a wall leaves the
         object where it was; that is scored separately, because knowing walls is milestone 2.

Reported per game:
  controls   the colour found to move under the keyboard, or "-" if none
  actions    the offset learned for each action
  moved ok   of the test presses where the object moved, the share that moved exactly as predicted
  stayed     the share of test presses where it did not move at all (walls, or no effect)
  click      for click-only games: the share of clicks that changed anything

Time is capped per game (--game-seconds) and in total (--total-seconds); a game that runs out of
time is reported as such, never left running.  One process per game.

    python g_control_probe.py                        the 18 held-out games
    python g_control_probe.py --games ls20,m0r0      any list
    python g_control_probe.py --train                the 7 train games, for comparison
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
HELD_OUT = ["ar25", "bp35", "cd82", "cn04", "g50t", "ka59", "r11l", "re86", "s5i5",
            "sb26", "sc25", "sk48", "sp80", "su15", "tn36", "tr87", "wa30"]
TRAIN = ["tu93", "ls20", "vc33", "m0r0", "ft09", "lp85", "lf52", "dc22"]
KEYS = (1, 2, 3, 4, 5, 7)


def grid(raw):
    g = np.zeros((64, 64), dtype=np.int16)
    f = np.asarray(raw.frame[-1]) if raw.frame else None
    if f is not None and f.ndim == 2:
        h, w = f.shape
        g[:min(h, 64), :min(w, 64)] = f[:64, :64]
    return g


def shift_of(before, after):
    """{colour: (dx, dy)} for every colour whose disappearing cells, shifted by one offset,
    are exactly its appearing cells.  Row 0 and row 63 are left out: bars and counters live there."""
    b, a = before[1:63], after[1:63]
    out = {}
    for c in np.unique(np.concatenate([b[b != a], a[b != a]])):
        gone = np.argwhere((b == c) & (a != c))
        came = np.argwhere((a == c) & (b != c))
        if len(gone) == 0 or len(came) == 0 or len(gone) != len(came) or len(gone) > 400:
            continue
        d = came.mean(0) - gone.mean(0)
        dy, dx = int(round(d[0])), int(round(d[1]))
        if (dx, dy) == (0, 0):
            continue
        moved = {(int(y) + dy, int(x) + dx) for y, x in gone}
        if moved == {(int(y), int(x)) for y, x in came}:
            out[int(c)] = (dx, dy)
    # A piece sliding across a coloured region makes that REGION look as if it moved the same
    # distance the other way: the cells the piece covers vanish from it and the cells it uncovers
    # reappear.  MEASURED on dc22 (moved to TRAIN for this): the probe took the room for the
    # player, learned every direction backwards, and looked for walls in the wrong place.  When
    # two colours shift by exactly opposite offsets, the one with more cells on screen is the
    # ground, not the thing that moved.
    for c1 in list(out):
        for c2 in list(out):
            if c1 < c2 and c1 in out and c2 in out and \
                    out[c1] == (-out[c2][0], -out[c2][1]):
                n1, n2 = int((b == c1).sum()), int((b == c2).sum())
                out.pop(c1 if n1 > n2 else c2)
    return out


def pick_object(seen, keys, bg):
    """Which colour is the thing being controlled?  The one whose movement is most CONSISTENT:
    for each action, the times it moved by that action's usual offset, minus the times it moved
    by any other offset; ties go to the colour with fewer cells.  MEASURED on tu93 (a train
    game): the player there is two colours, and one of them is a single cell showing which way
    it faces - it jumps 7 or 8 cells as the player turns.  Picking the colour with the fewest
    cells chose that flicker over the steady signal; consistency does not."""
    score = Counter()
    for a in keys:
        per = defaultdict(Counter)
        for (c, d), n in seen[a].items():
            per[c][d] += n
        for c, ds in per.items():
            if c == bg:
                continue
            top = ds.most_common(1)[0][1]
            score[c] += top - (sum(ds.values()) - top)
    if not score:
        return None
    best = max(score.values())
    if best <= 0:
        return None
    return best, [c for c, v in score.items() if v == best]


def locate(frame, colour):
    ys, xs = np.nonzero(frame[1:63] == colour)
    if len(ys) == 0:
        return None
    return float(xs.mean()), float(ys.mean())


def one(args):
    game, env_dir, learn, test, seconds, seed = args
    import logging
    logging.disable(logging.CRITICAL)
    from arc_agi import Arcade
    from arcengine import GameAction
    t0 = time.time()
    rng = random.Random(seed)
    arc = Arcade(operation_mode="offline", environments_dir=env_dir)
    env = arc.make(game)
    raw = env.observation_space
    avail = [int(a) for a in (raw.available_actions or [])]
    keys = [a for a in avail if a in KEYS]
    res = dict(game=game, actions=avail, controls="-", effects={}, moved_ok=None, stayed=None,
               click_effect=None, timed_out=False, presses=0)

    def press(a, x=0, y=0):
        nonlocal raw
        if raw.state.name in ("WIN", "GAME_OVER"):
            raw = env.step(GameAction.RESET)
        before = grid(raw)
        if a == 6:
            raw = env.step(GameAction.ACTION6, data={"x": x, "y": y})
        else:
            raw = env.step(GameAction.from_id(a))
        res["presses"] += 1
        return before, grid(raw)

    if not keys:
        # a click-only game: measure only how often a click changes anything
        changed = 0
        for i in range(learn + test):
            if time.time() - t0 > seconds:
                res["timed_out"] = True
                break
            b, a = press(6, rng.randrange(64), rng.randrange(64))
            changed += int((b[1:63] != a[1:63]).any())
        res["click_effect"] = round(changed / max(1, res["presses"]), 3)
        return res

    # LEARN
    seen = defaultdict(Counter)            # action -> Counter of (colour, offset)
    for i in range(learn):
        if time.time() - t0 > seconds:
            res["timed_out"] = True
            return res
        a = keys[i % len(keys)]
        b, af = press(a)
        for c, d in shift_of(b, af).items():
            seen[a][(c, d)] += 1
    # the most common colour on screen is the background; it never counts as the thing moved
    frame = grid(raw)
    bg = int(np.bincount(frame[1:63].ravel().clip(0, 15), minlength=16).argmax())
    picked = pick_object(seen, keys, bg)
    if picked is None:
        return res
    _best, tied = picked
    colour = min(tied, key=lambda c: int((frame == c).sum()))
    effects = {}
    for a in keys:
        ds = Counter({d: n for (c, d), n in seen[a].items() if c == colour})
        if ds:
            effects[a] = ds.most_common(1)[0][0]
    res["controls"] = colour
    res["effects"] = {str(a): list(d) for a, d in effects.items()}

    # TEST
    moved = right = stayed = 0
    for i in range(test):
        if time.time() - t0 > seconds:
            res["timed_out"] = True
            break
        a = rng.choice(keys)
        b, af = press(a)
        # the SAME exact-shift test as in LEARN.  MEASURED on ls20: averaging every cell of the
        # colour drifted whenever that colour also appeared elsewhere on screen, and scored a
        # correctly learned avatar at 0%.
        shifts = shift_of(b, af)
        if colour not in shifts:
            stayed += 1
            continue
        moved += 1
        if a in effects and tuple(effects[a]) == tuple(shifts[colour]):
            right += 1
    res["moved_ok"] = round(right / moved, 3) if moved else None
    res["stayed"] = round(stayed / max(1, test), 3)
    res["seconds"] = round(time.time() - t0, 1)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", default=None)
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--learn", type=int, default=20)
    ap.add_argument("--test", type=int, default=40)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--game-seconds", type=float, default=300)
    ap.add_argument("--total-seconds", type=float, default=3600)
    ap.add_argument("--env-dir", default=os.path.join(HERE, "environment_files"))
    ap.add_argument("--tag", default="m1")
    args = ap.parse_args()
    games = args.games.split(",") if args.games else (TRAIN if args.train else HELD_OUT)
    print(f"{len(games)} games, learn {args.learn} moves, test {args.test} moves, "
          f"cap {args.game_seconds:.0f}s per game and {args.total_seconds:.0f}s in total\n")
    print(f"{'game':6} {'controls':>8} {'moved ok':>9} {'stayed':>7} {'click':>6}  effects learned")
    t0 = time.time()
    rows = []
    jobs = [(g, args.env_dir, args.learn, args.test, args.game_seconds, 1234 + i)
            for i, g in enumerate(games)]
    with Pool(args.workers) as pool:
        it = pool.imap_unordered(one, jobs)
        for _ in jobs:
            left = args.total_seconds - (time.time() - t0)
            if left <= 0:
                print("TOTAL TIME CAP REACHED - stopping")
                pool.terminate()
                break
            try:
                r = it.next(timeout=left)
            except Exception:
                print("TOTAL TIME CAP REACHED - stopping")
                pool.terminate()
                break
            rows.append(r)
            mo = "-" if r["moved_ok"] is None else f"{100 * r['moved_ok']:.0f}%"
            st = "-" if r["stayed"] is None else f"{100 * r['stayed']:.0f}%"
            ck = "-" if r["click_effect"] is None else f"{100 * r['click_effect']:.0f}%"
            flag = "  (TIMED OUT)" if r["timed_out"] else ""
            print(f"{r['game']:6} {str(r['controls']):>8} {mo:>9} {st:>7} {ck:>6}  {r['effects']}{flag}",
                  flush=True)
    kb = [r for r in rows if r["click_effect"] is None]
    found = [r for r in kb if r["controls"] != "-"]
    good = [r for r in found if r["moved_ok"] is not None and r["moved_ok"] >= 0.9]
    print(f"\nkeyboard games: {len(kb)}   controlled object found: {len(found)}   "
          f"predicted its moves correctly (90%+ of the time): {len(good)}")
    print(f"click-only games: {len(rows) - len(kb)}   wall clock {time.time() - t0:.0f}s")
    json.dump(rows, open(os.path.join(HERE, f"g_control_{args.tag}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
