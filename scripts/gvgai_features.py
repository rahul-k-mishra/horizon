"""
gvgai_features.py -- writes docs/truth/gvgai_features.json, the three nuisance features of every confirmatory level
(docs/PREREG.md, Section 7.7: "grid area, action count and colour count (study 1's nuisance features)"), read by
scripts/analyze_horizon.py as {game: {level: {area, actions, colours}}}.

Each feature is read from the level as GVGAI builds it at its start, through the adapter the agents play
(scripts/automation/agents_gvgai.py, GVGAIAdapter), so that it means for a GVGAI level what study 1's row field
meant for a MiniGrid or Procgen game (study 1's adapter record: grid, action_list, n_colours):
    area      rows x columns of the level's grid, one cell per level cell (the adapter's grid_shape);
    actions   the avatar's available actions without ACTION_NIL (the adapter's action list);
    colours   the number of distinct cells at the level's start, a cell being the set of sprite types drawn in it
              (the adapter's palette after reset; a hidden or invisible sprite is not drawn, so a cell of hidden
              floor alone is the empty set, which counts like any other set).
Study 1 read n_colours from each agent's own row, after play, so it depended on what the agent had seen.  Here no
agent plays: the features are read from the level's start only, the same for every agent and seed, because
Section 9 of docs/PREREG.md allows features from search rows, truth tables and this file only, and outcomes only
from agent rows.  No action is taken in any level.

Before it reads any level of the study the script checks the three features on the synthetic test levels of
scripts/automation/gvgai_testgames against values worked out by hand from their files, and checks area against
the level file's own size (scripts/suite.py, level_size) on every level; it stops on any difference and writes
nothing.

The games are scripts/suite.py's confirmatory() (the deterministic games, less the pilot games and the games that
do not fit the frame), levels 0 to 4.  Needs JPype and the pinned JDK (scripts/automation/sim_gvgai.py), as the
laptop tests of the GVGAI kinds do.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\gvgai_features.py > logs\\gvgai_features.log
"""
from __future__ import annotations

import collections
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
import suite  # noqa: E402
import agents_gvgai  # noqa: E402

OUT = os.path.join(REPO, "docs", "truth", "gvgai_features.json")
TEST_GAMES = "scripts/automation/gvgai_testgames"
# worked out by hand from the files under scripts/automation/gvgai_testgames: floor is hidden, so it is not drawn;
# A is avatar on floor, g goal on floor, w wall, . floor; MovingAvatar offers left, right, down and up
BY_HAND = {
    ("allwin", 0): dict(area=5 * 5, actions=4, colours=3),     # {wall}, {goal}, {avatar}
    ("corridor", 0): dict(area=3 * 6, actions=4, colours=4),   # {wall}, {avatar}, {} (floor), {goal}
    ("corridor", 1): dict(area=5 * 5, actions=4, colours=4),   # {wall}, {avatar}, {goal}, {} (floor)
}


def cache():
    return os.environ.get("HORIZON_GVGAI_CACHE") or os.path.join(tempfile.gettempdir(), "horizon-gvgai")


def features(game, level, games_dir=None):
    ad = agents_gvgai.GVGAIAdapter(game, level, cache(), games_dir)
    ad.reset(0)
    if ad.steps != 0:
        raise RuntimeError(f"{game} level {level}: an action was taken")
    return dict(area=int(ad.grid_shape[0] * ad.grid_shape[1]), actions=len(ad.actions), colours=len(ad.palette)), \
        tuple(ad.grid_shape), list(ad.actions)


def main():
    print("== 1. the synthetic test levels against the values worked out by hand")
    bad = 0
    for (g, lv), want in BY_HAND.items():
        got, shape, acts = features(g, lv, TEST_GAMES)
        ok = got == want
        bad += not ok
        print(f"  {g} level {lv}: grid {shape[0]} x {shape[1]}, actions {acts}; got {got}, by hand {want}: "
              f"{'same' if ok else 'DIFFERENT'}")
    if bad:
        print(f"{bad} test level(s) differ from the hand values; nothing written")
        return 1

    games = suite.confirmatory()
    print(f"\n== 2. the confirmatory games ({len(games)}, scripts/suite.py confirmatory()), levels 0 to 4, at the level's start")
    out = {}
    for g in games:
        out[g] = {}
        for lv in suite.LEVELS:
            got, shape, acts = features(g, lv)
            size = suite.level_size(g, lv)
            if tuple(shape) != tuple(size):
                print(f"  {g} level {lv}: GVGAI's grid {shape} differs from the level file's size {size}; nothing written")
                return 1
            out[g][str(lv)] = got
            print(f"  {g} level {lv}: grid {shape[0]} x {shape[1]} (the level file's size too), area {got['area']}, "
                  f"actions {got['actions']} {acts}, colours {got['colours']}")
    n = sum(len(v) for v in out.values())
    print(f"\n== 3. summary: {len(out)} games, {n} levels")
    for f in ("area", "actions", "colours"):
        vals = [out[g][lv][f] for g in out for lv in out[g]]
        dist = collections.Counter(vals)
        print(f"  {f}: from {min(vals)} to {max(vals)}, {len(dist)} distinct values"
              + (f"; levels per value {dict(sorted(dist.items()))}" if f != "area" else ""))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"written: {os.path.relpath(OUT, REPO).replace(os.sep, '/')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
