"""
test_gvgaiagent.py -- synthetic tests of the kind gvgaiagent: study 1's agents N, R, I1 and Rand on GVGAI levels
through scripts/automation/agents_gvgai.py, the agent job jobs.run_agent (agent_impl "gvgai") and the runner's agent
pool (runner.Session.run_agent_pool), with rows of the schema horizon.agent.v2.  Only the synthetic levels of
scripts/automation/gvgai_testgames are played; no pilot or confirmatory level.

    1. Units whose outcome is worked out by hand.
       a. allwin level 0: the avatar stands between four goals and walls; touching one goal leaves three, and
          "SpriteCounter stype=goal limit=3 win=True" ends the level with a win.  Every move of the action list
          (left, right, down, up) touches a goal, and a won level starts again at once, so every action is a level
          end: for each agent with a budget of 40 actions, actions 40, levels 40, first level end 1,
          level1_completed true, not cut.
       b. corridor level 1: the avatar is walled in on all four sides and the goal is elsewhere, so no action can
          win: for each agent with a budget of 300, actions 300, levels 0, first level end none, level1_completed
          false, not cut.
       c. Rand on corridor level 0, seed 1000, budget 200: the avatar starts in column 1 of a one-row corridor and
          the goal is in column 4; left and right move it by one (a wall stops it at column 1), down and up hit a
          wall.  The levels and the first level end are computed here by walking that corridor with the same draws,
          numpy default_rng(1000).integers(4), without GVGAI; the row must agree.
    2. A resumed chunk equals an uninterrupted one.  An agent unit is never cut by the session: the runner starts a
       unit only if its own wall-clock cap fits before the work deadline, so the unit (one agent, level and seed) is
       the resumable unit, as the seed was for the kind agent.  A chunk of 8 units (N, R, I1 and Rand on corridor
       level 0 and allwin level 0) runs (i) in one session, and (ii) in a first session whose deadline leaves room
       for the 2 units with a cap of 30 s only (the other 6 have a cap of 100,000 s), whose rows, done-markers and
       checkpoint are then put into the state folder as the loop's integrate puts them, and a second session with
       a later deadline.  The second session must skip the 2 done units and run the 6 others, and every row must
       equal the uninterrupted one in every field except wall-clock times, sessions and written_at.
    3. The unit cap.  (a) The action budget: 1b plays exactly the budget.  (b) The wall-clock cap: each agent on
       corridor level 1 with a budget of 10,000,000 actions and a cap of 5 s stops on its own timer: cut_by_cap
       true, fewer actions than the budget, and the row's seconds at most the cap plus 3 s.  (c) The runner: in 2,
       a unit whose cap does not fit before the deadline is not started.
    4. The frozen files.  agents_gvgai.run_unit checks every file of agents_gvgai.FROZEN (study 1's 9 scripts and
       I1's 6 files) against its registered git blob hash before every unit.  For each of the 15 files in turn, a
       copy of third_party/study1 with one byte added to that file makes jobs.run_agent refuse the unit with an
       error naming that file, before any action is played; the untouched copy is accepted.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\test_gvgaiagent.py > logs\\test_gvgaiagent.log
Expected last line: OK
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import agents_gvgai as G  # noqa: E402
import jobs  # noqa: E402
import runner  # noqa: E402
from common import (chunk_entry_hash, load_manifest, marker_relpath, now_iso, read_json, save_manifest,  # noqa: E402
                    write_json)
from schema import validate_agent_row  # noqa: E402

GAMES = "scripts/automation/gvgai_testgames"
AGENTS = ("N", "R", "I1", "Rand")
FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def unit(agent, game, level, seed=1000, chunk="t-01", campaign="test"):
    return dict(campaign=campaign, unit_id=f"{chunk}-{agent}-{game}-l{level}-s{seed}", chunk_id=chunk, kind="gvgaiagent",
                suite="gvgai", game=game, level=level, agent=agent, seed=seed)


def play(agent, game, level, budget, cap, seed=1000):
    p = dict(agent_impl="gvgai", budget=budget, unit_seconds_cap=cap, games_dir=GAMES)
    return jobs.run_agent(unit(agent, game, level, seed), p, "nonce", "2026-11-25T00:00:00Z")


def summary(row):
    return (f"level1_completed {row['outcome']['level1_completed']}, levels {row['outcome']['levels']}, "
            f"actions {row['agent_stats']['actions']}, first level end {row['agent_stats']['first_level_end']}, "
            f"cut {row['cut_by_cap']}, {row['seconds']} s")


def stable(x):
    """A row without what depends on the clock or the session."""
    if isinstance(x, dict):
        return {k: stable(v) for k, v in x.items()
                if not any(w in k for w in ("second", "time", "sec_per", "written_at", "sessions"))}
    if isinstance(x, list):
        return [stable(v) for v in x]
    return x


def walk_corridor(actions, seed, budget):
    """Rand on corridor level 0 without GVGAI: columns 1 to 4, the goal at 4, a win sends the avatar back to 1."""
    import numpy as np  # noqa: PLC0415
    rng = np.random.default_rng(seed)
    x, levels, first = 1, 0, None
    for n in range(1, budget + 1):
        a = actions[int(rng.integers(len(actions)))]
        if a == "left":
            x = max(1, x - 1)
        elif a == "right":
            x += 1
        if x == 4:
            levels += 1
            first = first if first is not None else n
            x = 1
    return levels, first


# ---------------------------------------------------------------- 2. the runner, two sessions against one
def make_state(root, caps):
    """A state folder with a manifest of one gvgaiagent chunk and a dispatch of it."""
    units = []
    for game in ("corridor", "allwin"):
        for agent in AGENTS:
            u = dict(unit(agent, game, 0, chunk="g-01", campaign="gvgaiagent-test"), status="pending")
            u.pop("campaign")
            units.append(u)
    for u, cap in zip(units, caps):
        u["params"] = dict(unit_seconds_cap=cap)
    m = dict(campaign="gvgaiagent-test", code_tag="test", repository="none/none", kernel_slug="none", max_failures=3,
             payload_commit_limit_bytes=10 ** 9,
             session=dict(work_seconds=0, checkpoint_reserve_seconds=300, platform_limit_seconds=3600),
             kinds=dict(gvgaiagent=dict(agent_impl="gvgai", budget=300, unit_seconds_cap=600, workers=4,
                                        games_dir=os.path.join(G.REPO, GAMES))),
             chunks=[dict(chunk_id="g-01", kind="gvgaiagent", status="running", attempts=1, failures=0, sessions=[])],
             units=units)
    os.makedirs(os.path.join(root, "jobs"))
    save_manifest(root, m)
    write_json(os.path.join(root, "jobs", "state.json"),
               dict(dispatch=dict(nonce="n1", chunk_id="g-01", entry_hash=chunk_entry_hash(m, "g-01")), halted=False))
    return m


def session(root, work, work_seconds, nonce):
    m = load_manifest(root)
    m["session"]["work_seconds"] = work_seconds          # not part of the chunk's entry hash
    save_manifest(root, m)
    st = read_json(os.path.join(root, "jobs", "state.json"))
    st["dispatch"]["nonce"] = nonce
    write_json(os.path.join(root, "jobs", "state.json"), st)
    out = os.path.join(work, f"out-{nonce}")
    wd = os.path.join(work, f"work-{nonce}")
    os.makedirs(wd)
    s = runner.Session(SimpleNamespace(state_repo=root, out=out, work_dir=wd, t0=time.time()))
    s.run()
    s.finish()
    return s.result, s.stage


def integrate(root, res, stage):
    """What scripts/automation/loop.py, integrate, does with a session's rows and checkpoint (no release files)."""
    m = load_manifest(root)
    units = {u["unit_id"]: u for u in m["units"]}
    for r in res["rows"]:
        dst = os.path.join(root, r["path"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(stage, r["path"]), dst)
        write_json(os.path.join(root, marker_relpath(m, units[r["unit_id"]])),
                   dict(unit_id=r["unit_id"], chunk_id="g-01", kind="gvgaiagent", row_path=r["path"],
                        row_sha256=r["sha256"], run_nonce=res["nonce"], kernel_version=0, committed_at=now_iso()))
    ck = os.path.join(stage, "checkpoint")
    dst = os.path.join(root, "runs", m["campaign"], "checkpoints", "g-01")
    shutil.rmtree(dst, ignore_errors=True)
    if os.path.isdir(ck):
        shutil.copytree(ck, dst)


def rows_of(root, res):
    return {r["unit_id"]: read_json(os.path.join(root, r["path"])) for r in res["rows"]}


def main():
    print("== 1. outcomes worked out by hand")
    for agent in AGENTS:
        row = play(agent, "allwin", 0, 40, 600)
        print(f"   {agent} on allwin 0, budget 40: {summary(row)}")
        check(validate_agent_row(row) == [] and row["level"] == 0, f"1a {agent}: a valid horizon.agent.v2 row")
        check((row["agent_stats"]["actions"], row["outcome"]["levels"], row["agent_stats"]["first_level_end"],
               row["outcome"]["level1_completed"], row["cut_by_cap"]) == (40, 40, 1, True, False),
              f"1a {agent}: actions 40, levels 40, first level end 1, completed, not cut")
    for agent in AGENTS:
        row = play(agent, "corridor", 1, 300, 600)
        print(f"   {agent} on corridor 1, budget 300: {summary(row)}")
        check((row["agent_stats"]["actions"], row["outcome"]["levels"], row["agent_stats"]["first_level_end"],
               row["outcome"]["level1_completed"], row["cut_by_cap"]) == (300, 0, None, False, False),
              f"1b {agent}: actions 300, levels 0, no level end, not completed, not cut")
    row = play("Rand", "corridor", 0, 200, 600)
    acts = row["agent_stats"]["adapter"]["action_list"]
    levels, first = walk_corridor(acts, 1000, 200)
    print(f"   Rand on corridor 0, seed 1000, budget 200: {summary(row)}; the walk without GVGAI over {acts}: "
          f"levels {levels}, first level end {first}")
    check(acts == ["left", "right", "down", "up"], "1c the action list is left, right, down, up")
    check((row["outcome"]["levels"], row["agent_stats"]["first_level_end"]) == (levels, first) and levels > 0,
          "1c Rand's levels and first level end equal the walk's")

    print("== 2. a resumed chunk equals an uninterrupted one")
    tmp = tempfile.mkdtemp(prefix="horizon-test-gvgaiagent-")
    try:
        a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")
        caps_two = [30, 30] + [100000] * 6
        make_state(a, caps_two)
        make_state(b, caps_two)
        res_a, stage_a = session(a, os.path.join(tmp, "wa"), 200000, "u1")
        integrate(a, res_a, stage_a)
        whole = rows_of(a, res_a)
        print(f"   uninterrupted: status {res_a['status']}, {len(res_a['units_done_this_session'])} units")
        check(res_a["status"] == "done" and len(whole) == 8, "2 one session with room for every unit finishes all 8")
        res_1, stage_1 = session(b, os.path.join(tmp, "wb"), 60, "s1")
        integrate(b, res_1, stage_1)
        print(f"   first session: status {res_1['status']}, done {res_1['units_done_this_session']}; "
              f"stopped: {res_1.get('stop_reason')}")
        m = load_manifest(b)
        first_two = sorted(u["unit_id"] for u in m["units"][:2])
        check(res_1["status"] == "partial" and sorted(res_1["units_done_this_session"]) == first_two,
              "2 the first session runs the 2 units whose cap fits and starts none of the other 6 (3c)")
        ck = read_json(os.path.join(b, "runs", "gvgaiagent-test", "checkpoints", "g-01", "checkpoint.json"))
        check(sorted(ck["units_done"]) == first_two, "2 its checkpoint lists the 2 units done")
        res_2, stage_2 = session(b, os.path.join(tmp, "wb2"), 200000, "s2")
        integrate(b, res_2, stage_2)
        print(f"   second session: status {res_2['status']}, {len(res_2['units_done_this_session'])} units this session")
        check(res_2["status"] == "done" and len(res_2["units_done_this_session"]) == 6
              and not set(res_2["units_done_this_session"]) & set(first_two),
              "2 the second session skips the 2 done units and runs the other 6")
        resumed = dict(rows_of(b, res_1), **rows_of(b, res_2))
        same = [uid for uid in whole if stable(whole[uid]) == stable(resumed.get(uid))]
        for uid in sorted(whole):
            print(f"   {uid}: whole {summary(whole[uid])} | resumed {summary(resumed[uid])}")
        check(len(same) == 8, f"2 every row of the resumed chunk equals the uninterrupted one but for times "
                              f"({len(same)} of 8)")
        check(all(len(resumed[u]["sessions"]) == 1 for u in resumed) and
              {resumed[u]["sessions"][0]["run_nonce"] for u in first_two} == {"s1"},
              "2 each row names the one session that played it")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("== 3. the wall-clock cap")
    for agent in AGENTS:
        t = time.time()
        row = play(agent, "corridor", 1, 10_000_000, 5)
        print(f"   {agent} on corridor 1, budget 10,000,000, cap 5 s: {summary(row)}; wall {time.time() - t:.1f} s")
        check(row["cut_by_cap"] and row["agent_stats"]["actions"] < 10_000_000 and row["seconds"] <= 8.0,
              f"3b {agent}: stopped by the 5 s cap, cut_by_cap true, seconds at most 8")

    print("== 4. the frozen files, checked before every unit")
    tmp = tempfile.mkdtemp(prefix="horizon-test-frozen-")
    old = G.STUDY1
    try:
        copy = os.path.join(tmp, "study1")
        shutil.copytree(old, copy, ignore=shutil.ignore_patterns("__pycache__"))
        G.STUDY1 = copy
        row = play("Rand", "corridor", 0, 10, 60)
        check(row["agent_stats"]["actions"] == 10, "4 the untouched copy is accepted")
        refused = 0
        for rel in G.FROZEN:
            p = os.path.join(copy, rel)
            data = open(p, "rb").read()
            with open(p, "ab") as f:
                f.write(b"\n")
            try:
                play("N", "corridor", 0, 10, 60)
                print(f"   {rel}: NOT refused")
            except RuntimeError as e:
                if rel in str(e) and "differ" in str(e):
                    refused += 1
            finally:
                with open(p, "wb") as f:
                    f.write(data)
        check(refused == len(G.FROZEN) == 15, f"4 one added byte in any of the {len(G.FROZEN)} frozen files refuses the "
                                              f"unit, naming the file ({refused} refused)")
        check(G.check_frozen() == {}, "4 the copy restored is accepted again")
    finally:
        G.STUDY1 = old
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK" if not FAILS else f"{len(FAILS)} failure(s): " + "; ".join(FAILS))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
