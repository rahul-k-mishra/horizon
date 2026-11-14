"""
test_gvgaisearch.py -- synthetic tests of the kind gvgaisearch: GVGAI's forward model through the bridge
(sim_gvgai.py, gvgai_java/core/game/HorizonBridge.java) inside run_search (jobs.py), rows of the schema
horizon.search.v3 unchanged.  The games are written by this test into a temporary folder; no game of the suite
is played.  Needs JPype and a JDK (JAVA_HOME, or the pinned Temurin downloaded into HORIZON_GVGAI_CACHE).

    1. A level whose counts are worked out by hand.  corridor: a row of three floor cells with the avatar on the
       first and a goal beyond the third, walls round it; a MovingAvatar steps back from walls; the goal is
       killed when the avatar enters it and its count reaching 0 is a win.  The states are the avatar on cell 1,
       2 or 3, and the win state: 4 seen.  The three non-terminal states are expanded: 3.  The shortest win is
       right, right, right: 3.  Breadth first from cell 1: the start is seen first (1); cell 2 is seen while
       expanding the start (2); cell 3 while expanding cell 2 (3); the win while expanding cell 3, the third
       expansion: seen_at_first_win 4, expanded_at_first_win 3.  Distinct successors other than the state
       itself: cell 1 has {2}, cell 2 has {1, 3}, cell 3 has {2, win}: branching 5 / 3.
       A second level of the same game, the avatar boxed in by walls, has one state and no win: complete,
       1 seen, 1 expanded, solution length null.
    2. The same counts from an independent breadth-first search written in this file, which holds a GVGAI copy
       of every frontier state in memory instead of replaying action sequences, on corridor and on boxroom (a
       room of 4 x 4 cells with two boxes the avatar pushes and a goal): states seen, states expanded, solution length,
       seen_at_first_win and expanded_at_first_win, and the distinct successors summed.
    3. The seen cap on boxroom: with seen caps of 20, 100 and 300, the search stops as capped "seen" with
       states seen at least the cap and less than the cap plus the number of actions (the check falls between
       expansions), states expanded equal to the independent search's at the moment the cap was passed, and
       the first win recorded exactly when the independent search had seen it by then, and null otherwise.
    4. A search stopped by a deadline after a few expansions, saved with SearchState.save, loaded and finished
       gives the row counts of an uninterrupted search (boxroom, no cap reached: the search completes).
    5. The row passes the schema horizon.search.v3 and is refused as v2.
    6. A state key does not depend on the order in which GVGAI created the sprites.  paint: two dots, two cells
       either side of the avatar; entering a dot transforms it into a new sprite of type painted.  Painting the
       left dot first and the right dot first, and walking back to the middle, gives the same key, though GVGAI
       created the two painted sprites in opposite orders (the game has no win, so it goes on).  With one dot
       painted, the key differs.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\automation\\test_gvgaisearch.py
Expected last line: OK
"""
from __future__ import annotations

import collections
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import jobs  # noqa: E402
import sim_gvgai  # noqa: E402
from schema import SEARCH_SCHEMA_V2, SEARCH_SCHEMA_V3, validate_search_row  # noqa: E402

CORRIDOR = """BasicGame square_size=10
    SpriteSet
        floor > Immovable hidden=True
        goal > Immovable
        avatar > MovingAvatar
        wall > Immovable
    LevelMapping
        A > avatar floor
        g > goal floor
        . > floor
        w > wall
    InteractionSet
        avatar wall > stepBack
        goal avatar > killSprite scoreChange=1
    TerminationSet
        SpriteCounter stype=goal limit=0 win=True
"""
CORRIDOR_LEVELS = ["wwwwww\nwA..gw\nwwwwww\n", "wwwww\nwwAww\nwwwww\nwg..w\nwwwww\n"]

BOXROOM = """BasicGame square_size=10
    SpriteSet
        floor > Immovable hidden=True
        goal > Immovable
        box > Passive
        avatar > MovingAvatar
        wall > Immovable
    LevelMapping
        A > avatar floor
        g > goal floor
        1 > box floor
        . > floor
        w > wall
    InteractionSet
        avatar wall > stepBack
        box avatar > bounceForward
        box wall box > undoAll
        goal avatar > killSprite scoreChange=1
    TerminationSet
        SpriteCounter stype=goal limit=0 win=True
"""
BOXROOM_LEVELS = ["wwwwww\nw....w\nw.1..w\nw..A.w\nw.1.gw\nwwwwww\n"]

PAINT = """BasicGame square_size=10
    SpriteSet
        floor > Immovable hidden=True
        dot > Immovable
        painted > Immovable
        avatar > MovingAvatar
        wall > Immovable
    LevelMapping
        A > avatar floor
        1 > dot floor
        . > floor
        w > wall
    InteractionSet
        avatar wall > stepBack
        dot avatar > transformTo stype=painted
    TerminationSet
        SpriteCounter stype=avatar limit=0 win=False
"""
PAINT_LEVELS = ["wwwwwww\nw1.A.1w\nwwwwwww\n"]
PARAMS = dict(simulator="gvgai", node_cap=5_000_000, time_cap_seconds=14400, memory_cap_bytes=6442450944,
              spill_frontier_over=1_000_000, checkpoint_every_seconds=600, checkpoint_every_nodes=250000,
              batch=50, seen_cap=2_000_000, schema=SEARCH_SCHEMA_V3)


def cache_dir():
    return os.environ.get("HORIZON_GVGAI_CACHE") or os.path.join(tempfile.gettempdir(), "horizon-gvgai")


def write_games(d):
    for name, desc, levels in (("corridor", CORRIDOR, CORRIDOR_LEVELS), ("boxroom", BOXROOM, BOXROOM_LEVELS),
                               ("paint", PAINT, PAINT_LEVELS)):
        with open(os.path.join(d, f"{name}.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(desc)
        for i, lv in enumerate(levels):
            with open(os.path.join(d, f"{name}_lvl{i}.txt"), "w", encoding="utf-8", newline="\n") as f:
                f.write(lv)


def unit(game, level):
    return dict(campaign="test", unit_id=f"{game}-{level}", chunk_id="t-01", suite="gvgai", game=game, level=level)


def search(games_dir, game, level, work, **over):
    p = dict(PARAMS, games_dir=games_dir, gvgai_cache=cache_dir(), **over)
    st, row, state = jobs.run_search(unit(game, level), p, work, None, time.time() + 3600, lambda s: None,
                                     "nonce", "2026-11-14T00:00:00Z", schema=SEARCH_SCHEMA_V3)
    return st, row, state


def reference(bridge, games_dir, game, level, tick=False, stop_seen=None):
    """Breadth first with a GVGAI copy of every frontier state held in memory."""
    gf, lf = sim_gvgai.level_paths(game, level, games_dir)
    root = bridge.load(gf.replace("\\", "/"), lf.replace("\\", "/"), 0)
    acts = list(bridge.actions(root))
    k0 = jobs.h64(bytes(bridge.key(root, tick)))
    seen, q = {k0}, collections.deque()
    c = dict(seen=1, expanded=0, length=None, seen_win=None, exp_win=None, distinct=0)
    st0 = int(bridge.status(root))
    if st0 == 1:
        c.update(length=0, seen_win=1, exp_win=0)
    if st0 == 0:
        q.append((root, 0))
    while q and (stop_seen is None or c["seen"] < stop_seen):
        s, depth = q.popleft()
        c["expanded"] += 1
        pk = jobs.h64(bytes(bridge.key(s, tick)))
        dist = set()
        for a in acts:
            t = s.copy()
            t.advance(a)
            k = jobs.h64(bytes(bridge.key(t, tick)))
            if k != pk:
                dist.add(k)
            if k in seen:
                continue
            seen.add(k)
            c["seen"] += 1
            stt = int(bridge.status(t))
            if stt == 1 and c["length"] is None:
                c.update(length=depth + 1, seen_win=c["seen"], exp_win=c["expanded"])
            if stt == 0:
                q.append((t, depth + 1))
        c["distinct"] += len(dist)
    return c


def check(cond, msg, fails):
    if not cond:
        fails.append(msg)
        print("FAIL", msg)


def main():
    fails = []
    tmp = tempfile.mkdtemp(prefix="horizon-test-gvgai-")
    try:
        games = os.path.join(tmp, "games")
        os.makedirs(games)
        write_games(games)
        bridge = sim_gvgai.start_jvm(cache_dir())

        # 1. by hand
        st, row, state = search(games, "corridor", 0, os.path.join(tmp, "w1"))
        c = row["counts"]
        print("1. corridor level 0:", st, {k: c[k] for k in ("states_seen", "states_expanded", "solution_length",
                                                              "seen_at_first_win", "expanded_at_first_win")},
              "branching", row["measures"]["branching"])
        check(st == "complete" and row["complete"] and not row["capped"], "corridor: complete", fails)
        check((c["states_seen"], c["states_expanded"], c["solution_length"]) == (4, 3, 3), "corridor: 4 seen, 3 expanded, length 3", fails)
        check((c["seen_at_first_win"], c["expanded_at_first_win"]) == (4, 3), "corridor: first win at 4 seen, 3 expanded", fails)
        check(abs(row["measures"]["branching"] - 5 / 3) < 1e-12, "corridor: branching 5/3", fails)
        st, row, _ = search(games, "corridor", 1, os.path.join(tmp, "w1b"))
        c = row["counts"]
        print("1. corridor level 1 (boxed in):", st, c["states_seen"], c["states_expanded"], c["solution_length"])
        check(st == "complete" and (c["states_seen"], c["states_expanded"], c["solution_length"]) == (1, 1, None),
              "boxed-in level: 1 seen, 1 expanded, no win", fails)

        # 2. against the independent search
        for g in ("corridor", "boxroom"):
            st, row, state = search(games, g, 0, os.path.join(tmp, f"w2{g}"))
            c = row["counts"]
            ref = reference(bridge, games, g, 0)
            got = (c["states_seen"], c["states_expanded"], c["solution_length"], c["seen_at_first_win"],
                   c["expanded_at_first_win"], state.extra["successors_distinct"])
            want = (ref["seen"], ref["expanded"], ref["length"], ref["seen_win"], ref["exp_win"], ref["distinct"])
            print(f"2. {g}: search {got}, independent {want}")
            check(got == want, f"{g}: counts equal the independent search", fails)
            check(st == "complete", f"{g}: complete", fails)
        full_box = ref

        # 3. the seen cap
        n_act = 4
        for cap in (20, 100, 300):
            st, row, _ = search(games, "boxroom", 0, os.path.join(tmp, f"w3{cap}"), seen_cap=cap)
            c = row["counts"]
            ref = reference(bridge, games, "boxroom", 0, stop_seen=cap)
            print(f"3. seen cap {cap}: {st}, cap_hit {row['cap_hit']}, seen {c['states_seen']}, expanded {c['states_expanded']} "
                  f"(independent: seen {ref['seen']}, expanded {ref['expanded']}), first win {c['seen_at_first_win']}")
            check(st == "capped" and row["cap_hit"] == "seen", f"cap {cap}: capped by seen", fails)
            check(cap <= c["states_seen"] < cap + n_act, f"cap {cap}: seen within one state's successors", fails)
            check((c["states_seen"], c["states_expanded"]) == (ref["seen"], ref["expanded"]),
                  f"cap {cap}: counts equal the independent search stopped at the cap", fails)
            won = full_box["seen_win"] is not None and full_box["seen_win"] <= c["states_seen"]
            check((c["seen_at_first_win"], c["expanded_at_first_win"]) ==
                  ((full_box["seen_win"], full_box["exp_win"]) if won else (None, None)),
                  f"cap {cap}: first win exact", fails)

        # 4. resume
        st_full, row_full, _ = search(games, "boxroom", 0, os.path.join(tmp, "w4a"))
        p = dict(PARAMS, games_dir=games, gvgai_cache=cache_dir(), batch=5)
        work = os.path.join(tmp, "w4b")
        st1, _, s1 = jobs.run_search(unit("boxroom", 0), p, work, None, time.time() - 1, lambda s: None,
                                     "n1", "2026-11-14T00:00:00Z", schema=SEARCH_SCHEMA_V3)
        meta = s1.save(os.path.join(tmp, "ck"), work)
        s2 = jobs.SearchState.load(os.path.join(tmp, "ck"), meta, os.path.join(tmp, "w4c"))
        st2, row2, _ = jobs.run_search(unit("boxroom", 0), p, os.path.join(tmp, "w4c"), s2, time.time() + 3600,
                                       lambda s: None, "n2", "2026-11-14T00:00:00Z", schema=SEARCH_SCHEMA_V3)
        print(f"4. stopped after {s1.counts['states_expanded']} expansions ({st1}); resumed: {st2}, "
              f"counts equal: {row2['counts'] == row_full['counts']}")
        check(st1 == "stopped" and 0 < s1.counts["states_expanded"] < row_full["counts"]["states_expanded"],
              "resume: the first part stopped early", fails)
        check(row2["counts"] == row_full["counts"] and row2["cap_hit"] == row_full["cap_hit"],
              "resume: counts equal an uninterrupted search", fails)
        check(row2["measures"]["branching"] == row_full["measures"]["branching"], "resume: branching equal", fails)

        # 5. schema
        e3 = validate_search_row(row_full)
        bad = dict(row_full, schema=SEARCH_SCHEMA_V2)
        print(f"5. v3 errors {e3}; as v2: {len(validate_search_row(bad))} errors")
        check(not e3, "row passes v3", fails)
        check(len(validate_search_row(bad)) > 0, "row refused as v2", fails)

        # 6. the key ignores the order in which GVGAI created the sprites
        gf, lf = sim_gvgai.level_paths("paint", 0, games)
        root = bridge.load(gf.replace("\\", "/"), lf.replace("\\", "/"), 0)
        acts = list(bridge.actions(root))
        idx = {str(a).replace("ACTION_", "")[0]: i for i, a in enumerate(acts)}

        def play(seq):
            s = root.copy()
            for ch in seq:
                s.advance(acts[idx[ch]])
            return bytes(bridge.key(s, False))
        left_first, right_first, half = play("LLRRRRLL"), play("RRLLLLRR"), play("LLRR")
        print(f"6. left first and right first give equal keys: {left_first == right_first}; "
              f"one dot painted differs: {half != left_first}")
        check(left_first == right_first, "creation order does not enter the key", fails)
        check(half != left_first, "a different state gives a different key", fails)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("FAILED: " + "; ".join(fails) if fails else "OK")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
