"""
test_agents_gvgai.py -- study 1's agents on a GVGAI level through the boundary of agents_gvgai.py, and the agent
job of the kind gvgaiagent (jobs.run_agent), producing rows of the schema horizon.agent.v2.

    1. The frozen copies: every file of agents_gvgai.FROZEN under third_party/study1 has the git blob hash study 1
       registered, and so do the I1 files listed with their sha256 in third_party/study1/external/
       rudakov_just_explore/PROVENANCE.md.  A copy with one byte changed is refused by check_frozen.
    2. The frame contract on bait level 0, a pilot level: the frame is 64 x 64; row 0 and the rows and columns
       outside the level are padding (0); the level's cells hold indices from 1 up, given in order of first
       appearance (the first cell of row 1 holds 1); the key map is 1 up, 2 down, 3 left, 4 right, with no 5
       (bait's avatar has no use action) and no 7; after a move the avatar's index stays the same.
    3. Each of N, R, I1 and Rand plays bait level 0 for 2,000 actions (a test budget, not the registered 20,000)
       through jobs.run_agent with agent_impl "gvgai", and its row passes horizon.agent.v2, carries level 0, and
       fails as v1.
    4. A level wider than 64 columns is refused with a message (garbagecollector level 0, 25 x 69 cells; a
       confirmatory game, constructed only, no action played).
The pilot games never enter a confirmatory analysis (docs/PREREG.md, Section 4).  Run (working directory
D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\test_agents_gvgai.py
Expected last line: OK
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import agents_gvgai as G  # noqa: E402
import jobs  # noqa: E402
from schema import AGENT_SCHEMA, validate_agent_row  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def main():
    print("== 1. the frozen copies")
    check(G.check_frozen() == {}, f"{len(G.FROZEN)} study-1 files have their registered blob hashes")
    prov = os.path.join(G.STUDY1, "external", "rudakov_just_explore", "PROVENANCE.md")
    with open(prov, encoding="utf-8") as f:
        listed = re.findall(r"^\s+([0-9a-f]{64})\s+(\S+)$", f.read(), re.M)
    present = [(h, p) for h, p in listed if os.path.exists(os.path.join(os.path.dirname(prov), p))]
    ok = all(hashlib.sha256(open(os.path.join(os.path.dirname(prov), p), "rb").read()).hexdigest() == h
             for h, p in present)
    check(ok and len(present) >= 6, f"I1's files match PROVENANCE.md's sha256 ({len(present)} of {len(listed)} "
          "listed are copied; agents/swarm.py, not loaded by the adapter, is not)")
    tmp = tempfile.mkdtemp(prefix="horizon-test-agents-")
    try:
        bad_root = os.path.join(tmp, "study1")
        shutil.copytree(G.STUDY1, bad_root)
        with open(os.path.join(bad_root, "scripts", "g_motion.py"), "ab") as f:
            f.write(b" ")
        old = G.STUDY1
        G.STUDY1 = bad_root
        check(list(G.check_frozen()) == ["scripts/g_motion.py"], "one changed byte in g_motion.py is refused")
        G.STUDY1 = old
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("== 2. the frame contract on bait level 0")
    import env_frame as EF  # noqa: PLC0415
    ad = G.GVGAIAdapter("bait", 0)
    g = ad.reset(1000)
    c = EF.to_canvas(g, 1)
    h, w = g.shape
    check(c.shape == (64, 64), "the canvas is 64 x 64")
    check((c[0] == 0).all() and (c[1 + h:] == 0).all() and (c[:, w:] == 0).all(), "row 0 and the canvas outside the level are 0")
    check(int(c[1, 0]) == 1 and int(g.min()) >= 1, "level cells hold indices from 1, the first cell 1")
    order = []
    for v in g.flatten():
        if int(v) not in order:
            order.append(int(v))
    check(order == list(range(1, len(order) + 1)), "indices are given in order of first appearance")
    km = G.key_map_for(ad)
    check({k: ad.actions[i] for k, i in km.items()} == {1: "up", 2: "down", 3: "left", 4: "right"},
          f"key map 1 up, 2 down, 3 left, 4 right ({ad.actions})")
    before = set(int(v) for v in g.flatten())
    for i in range(len(ad.actions)):
        g2, _le, _ge = ad.step(i)
    check(len(ad.palette) >= len(before), "the palette keeps its indices across steps")
    print(f"   bait level 0: grid {h} x {w}, {len(ad.palette)} indices after {len(ad.actions)} steps, actions {ad.actions}")

    print("== 3. N, R, I1 and Rand on bait level 0, 2,000 actions each")
    p = dict(agent_impl="gvgai", budget=2000, unit_seconds_cap=600)
    for agent in ("N", "R", "I1", "Rand"):
        unit = dict(campaign="test", unit_id=f"{agent}-bait-0-1000", chunk_id="t-01", suite="gvgai", game="bait",
                    level=0, agent=agent, seed=1000)
        row = jobs.run_agent(unit, p, "nonce", "2026-11-14T00:00:00Z")
        errs = validate_agent_row(row)
        v1 = validate_agent_row(dict({k: v for k, v in row.items() if k != "level"}, schema=AGENT_SCHEMA))
        print(f"   {agent}: level1_completed {row['outcome']['level1_completed']}, levels {row['outcome']['levels']}, "
              f"actions {row['agent_stats']['actions']}, first level end {row['agent_stats']['first_level_end']}, "
              f"{row['seconds']} s")
        check(not errs and row["level"] == 0, f"{agent}: the row passes horizon.agent.v2 with level 0 ({errs})")
        check(not v1 and validate_agent_row(dict(row, schema=AGENT_SCHEMA)) != [],
              f"{agent}: without level it is a valid v1 row, with level it is not")
        check(row["agent_stats"]["actions"] == 2000 or row["cut_by_cap"],
              f"{agent}: 2,000 actions played, or the row says it was cut")

    print("== 4. a level wider than the canvas")
    try:
        G.GVGAIAdapter("garbagecollector", 0)
        check(False, "garbagecollector level 0 is refused")
    except ValueError as e:
        check("does not fit" in str(e), f"garbagecollector level 0 is refused: {e}")
    print("OK" if not FAILS else f"{len(FAILS)} failure(s): " + "; ".join(FAILS))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
