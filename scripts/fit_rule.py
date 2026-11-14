"""
fit_rule.py -- the fit rule of docs/PREREG.md, Section 4 [decided 14 Nov 2026], applied to the 30 deterministic
games, with what it does to the suite.  Reads only committed files (scripts/suite.py: docs/design/vgdl_scan.json,
the vendored level files, the pilot draw; logs/engine_speed.log; docs/truth/gvgai.json).  Plays no game.

Prints:
    1. the frame: the largest grid the frame contract can present, and where that limit comes from;
    2. per deterministic game, the size of each of its five levels (rows x columns, as GVGAI reads the level file)
       and whether the game fits; then every game the rule removes, with its grid size and the frame's size;
    3. the pilot draw: the draw of seed 20261024 as made on the 30 games, and, for the record, the draw the same
       seed would give on the games that fit;
    4. the coincidence, recorded so that a reader can see it was noticed and not used: the speed of every game
       removed, from logs/engine_speed.log (the laptop measurement of 14 November 2026), its rank among the
       confirmatory games, and how many of its levels would reach the time cap, against every other game; and the
       laptop bound on the confirmatory search with and without the games removed;
    5. the mechanics score S_M of the confirmatory games before and after the rule (docs/truth/gvgai.json, level 0,
       as scripts/sdd.py reads it), and the study's floor of 20 games (PREREG Section 7.6).
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\fit_rule.py > logs\\fit_rule.log
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import draw_pilot  # noqa: E402
import suite  # noqa: E402

PRED = ("A1", "A2", "A3", "A4", "A5")


def speeds():
    """{(game, level): (expansions per second, reaches the time cap, bound in s)} from logs/engine_speed.log."""
    out = {}
    pat = re.compile(r"^(\w+)\s+(\d) \|[^|]*\|[^|]*\|[^|]*\|\s*(\d+)\s*\|[^|]*\|\s*(\d+)( \(time cap\))?\s*$")
    with open(os.path.join(REPO, "logs", "engine_speed.log"), encoding="utf-8") as f:
        for ln in f:
            m = pat.match(ln.rstrip("\n"))
            if m:
                out[(m.group(1), int(m.group(2)))] = (int(m.group(3)), bool(m.group(5)), int(m.group(4)))
    return out


def sm_of(games):
    with open(os.path.join(REPO, "docs", "truth", "gvgai.json"), encoding="utf-8") as f:
        t = json.load(f)["games"]
    return {g: sum(t[g]["levels"]["0"][p]["verdict"] == "holds" for p in PRED) for g in games}


def dist(sm):
    c = collections.Counter(sm.values())
    return ", ".join(f"S_M={v}: {c[v]} games" for v in sorted(c))


def main():
    det = suite.deterministic()
    pil = suite.pilot()
    print("== 1. the frame")
    print(f"canvas {suite.CANVAS} x {suite.CANVAS} (study 1, env_frame.CANVAS); grid placed at row offset "
          f"{suite.ROW_OFFSET}, column 0; the frozen agent code reads rows 1 to 62 only (study 1, g_motion.py:30-31); "
          f"so the largest grid it can present at one cell per level cell is {suite.FRAME_ROWS} rows x "
          f"{suite.FRAME_COLS} columns")
    print("rule: a game is eligible only if every one of its levels 0 to 4 has at most "
          f"{suite.FRAME_ROWS} rows and at most {suite.FRAME_COLS} columns")

    print(f"\n== 2. the {len(det)} deterministic games (rows x columns per level, as GVGAI reads the level file)")
    removed = []
    for g in det:
        sizes = [suite.level_size(g, lv) for lv in suite.LEVELS]
        ok = suite.fits(g)
        role = "pilot" if g in pil else "confirmatory"
        print(f"{g:17s} {role:12s} " + "  ".join(f"{r}x{c}" for r, c in sizes) + f"  | {'fits' if ok else 'DOES NOT FIT'}")
        if not ok:
            removed.append((g, role, sizes))
    print(f"\nremoved by the rule: {len(removed)} game(s)")
    for g, role, sizes in removed:
        bad = [(lv, r, c) for lv, (r, c) in enumerate(sizes) if r > suite.FRAME_ROWS or c > suite.FRAME_COLS]
        print(f"  {g} ({role}): " + "; ".join(f"level {lv} {r} rows x {c} columns" for lv, r, c in bad)
              + f"; the frame holds {suite.FRAME_ROWS} rows x {suite.FRAME_COLS} columns")
    others = [g for g, _r, _s in removed if g != "garbagecollector"]
    print(f"games other than garbagecollector that fail the rule: {len(others)}" + (f" ({', '.join(others)})" if others else ""))
    conf = suite.confirmatory()
    print(f"confirmatory games after the rule: {len(conf)}, {5 * len(conf)} levels: {', '.join(conf)}")

    print("\n== 3. the pilot draw (seed 20261024)")
    print(f"as made on the {len(det)} deterministic games (logs/draw_pilot.log), and as used: {', '.join(pil)}; "
          f"every pilot game fits: {all(suite.fits(g) for g in pil)}")
    fit = [g for g in det if suite.fits(g)]
    alt = sorted(fit[i] for i in np.random.default_rng(draw_pilot.SEED).choice(len(fit), draw_pilot.N_PILOT, replace=False))
    print(f"the same seed on the {len(fit)} games that fit would draw: {', '.join(alt)}"
          + ("; the same pilot" if alt == pil else "; a different pilot"))
    print("the draw stands as made on the 30 games: it was drawn on 24 October 2026, before the rule; the pilot games "
          "have been used since (logs/engine_semantics.log, logs/engine_speed.log, jobs/pilot_search/manifest.json); "
          "the rule is applied to the confirmatory games after the draw, and it removes no pilot game")

    print("\n== 4. the coincidence (logs/engine_speed.log, laptop, 14 November 2026); recorded, not used by the rule")
    sp = speeds()
    conf_before = [g for g in det if g not in pil]
    per_game = {g: (min(sp[(g, lv)][0] for lv in suite.LEVELS), sum(sp[(g, lv)][1] for lv in suite.LEVELS))
                for g in conf_before if all((g, lv) in sp for lv in suite.LEVELS)}
    order = sorted(per_game, key=lambda g: per_game[g][0])
    for g, _role, _s in removed:
        if g in per_game:
            print(f"  {g}: slowest level {per_game[g][0]} expansions per second, rank {order.index(g) + 1} of "
                  f"{len(order)} confirmatory games from the slowest; levels whose bound reaches the time cap: "
                  f"{per_game[g][1]} of 5")
    rest = [g for g in order if g not in {x for x, _r, _s in removed}]
    capped_rest = {g: per_game[g][1] for g in rest if per_game[g][1]}
    print(f"  the slowest game that fits: {rest[0]}, {per_game[rest[0]][0]} expansions per second; games that fit with "
          f"a level whose bound reaches the time cap: {len(capped_rest)}"
          + (f" ({', '.join(f'{g} {n}' for g, n in capped_rest.items())})" if capped_rest else ""))
    worker = 4 * 28800
    for lab, games in (("all 26 games before the rule", conf_before), (f"the {len(conf)} games after the rule", conf)):
        tot = sum(sp[(g, lv)][2] for g in games for lv in suite.LEVELS)
        print(f"  the laptop bound for 2,000,000 states, summed over the levels of {lab} (per-level bounds as printed "
              f"in logs/engine_speed.log, each rounded to the second): {tot} worker-seconds, {tot / worker:.2f} "
              f"sessions of {worker} worker-seconds")
    print("  the rule's reason is the frame: a grid wider than 64 columns or taller than 62 rows cannot be presented "
          "to the agents at one cell per level cell; the speed of a game plays no part in it")

    print("\n== 5. the mechanics score of the confirmatory games (docs/truth/gvgai.json, level 0)")
    before, after = sm_of(conf_before), sm_of(conf)
    print(f"before the rule ({len(before)} games): {dist(before)}")
    print(f"after the rule ({len(after)} games): {dist(after)}")
    for g, _role, _s in removed:
        if g in before:
            print(f"  {g}: S_M = {before[g]}")
    print(f"the study is void below 20 confirmatory games (PREREG Section 7.6): {len(conf)} remain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
