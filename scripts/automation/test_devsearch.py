"""
test_devsearch.py -- synthetic tests of stage D's search (kind devsearch): the effective-horizon bound
(eh.py), the MiniGrid simulator (sim_minigrid.py) inside run_search (jobs.py), and resuming from a saved
state.  Needs gymnasium 1.3.0 and minigrid 3.1.0.  Plays no agent; reads no study-1 file.

    1. eh.effective_horizon on a two-state example worked by hand (the start; action 0 wins, action 1 stays;
       T = 2): Q1_1 = (1, 1/2), V*_1 = 1, so EH_1 = 1 + log2(1 / 0.25) + log2(6 ln 8) = 6.6412;
       Q2_1 = (1, 1) has no gap, and at t = 2 Q2_2 = (1, 0) gives a term log2(1 x 1 / 1) = 0, so
       EH_2 = 2 + 0 + log2(6 ln 16) = 6.0562; EH_3 = 3 + log2(6 ln 32) = 7.3781; EH = 6.0562 with k = 2.
    2. eh.effective_horizon against a separate loop-by-loop implementation of the same definitions on
       40 random small MDPs.
    3. The MiniGrid search against a plain breadth-first search that deep-copies every state
       (sim_minigrid.naive_counts): the same states seen, states expanded, shortest solution and distinct
       successors, on six levels covering moves, a locked door and key, lava, a box, and a BabyAI instruction.
    4. A search stopped early, saved with SearchState.save, loaded and finished gives the same counts and
       the same effective-horizon bound as an uninterrupted one.
    5. A Dynamic-Obstacles level is refused.
Run with warnings as errors (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe -W error scripts\\automation\\test_devsearch.py
Expected last line: OK
"""
from __future__ import annotations

import math
import os
import shutil
import sys
import tempfile
import time
import warnings

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
warnings.filterwarnings("ignore", message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pygame.*")
import eh  # noqa: E402
import jobs  # noqa: E402
from schema import SEARCH_SCHEMA_V2, validate_search_row  # noqa: E402

LEVELS = [("MiniGrid-Empty-5x5-v0", 1000), ("MiniGrid-DoorKey-5x5-v0", 1000), ("MiniGrid-LavaGapS5-v0", 1000),
          ("MiniGrid-Fetch-5x5-N2-v0", 1001), ("BabyAI-GoToRedBallNoDists-v0", 1000), ("BabyAI-UnlockLocal-v0", 1002)]
PARAMS = dict(simulator="minigrid", node_cap=5_000_000, time_cap_seconds=14400, memory_cap_bytes=6442450944,
              spill_frontier_over=1_000_000, checkpoint_every_seconds=600, checkpoint_every_nodes=250000,
              batch=200, eh_state_limit=200000, eh_horizon=400)


def reference_eh(nxt, rows, win, loss, start, T, A):
    """The same definitions as eh.py, written with plain loops and dictionaries."""
    rowof = {s: i for i, s in enumerate(rows)}
    n = len(win)
    term = [win[s] or loss[s] for s in range(n)]

    def R(i, a):
        return 1.0 if win[nxt[i][a]] else 0.0
    V = {name: {T + 1: [0.0] * n} for name in ("rand", "star", "w1", "w2")}
    for t in range(T, 0, -1):
        for name in V:
            V[name][t] = [0.0] * n
        for s in range(n):
            if term[s] or s not in rowof:
                continue
            i = rowof[s]
            q1 = [R(i, a) + V["rand"][t + 1][nxt[i][a]] for a in range(A)]
            V["rand"][t][s] = sum(q1) / A
            V["w1"][t][s] = max(q1)
            V["star"][t][s] = max(R(i, a) + V["star"][t + 1][nxt[i][a]] for a in range(A))
            V["w2"][t][s] = max(R(i, a) + V["w1"][t + 1][nxt[i][a]] for a in range(A))
    if V["star"][1][start] <= 0:
        return None, None
    X = {1: "rand", 2: "w1", 3: "w2"}

    def close(a, b):
        return a >= b - 1e-9 * max(abs(a), abs(b))
    results = {}
    for k in (1, 2, 3):
        def Q(t, s, k=k):
            i = rowof[s]
            return [R(i, a) + V[X[k]][t + 1][nxt[i][a]] for a in range(A)], \
                   [R(i, a) + V["star"][t + 1][nxt[i][a]] for a in range(A)]
        G, ok = {start}, True
        for t in range(1, T + 1):
            G = {s for s in G if not term[s]}
            nG = set()
            for s in G:
                qk, qs = Q(t, s)
                m = max(qk)
                for a in range(A):
                    if close(qk[a], m):
                        if not close(qs[a], V["star"][t][s]):
                            ok = False
                        nG.add(nxt[rowof[s]][a])
            if not ok:
                break
            G = nG
        if not ok:
            continue
        O, best = {start}, -math.inf
        for t in range(1, T + 1):
            O = {s for s in O if not term[s]}
            nO = set()
            for s in O:
                qk, qs = Q(t, s)
                m = max(qk)
                rest = [qk[a] for a in range(A) if not close(qk[a], m)]
                vs = V["star"][t][s]
                if rest and vs > 0:
                    gap = m - max(rest)
                    for a in range(A):
                        if qk[a] * vs > 0:
                            best = max(best, math.log(qk[a] * vs / gap ** 2) / math.log(A))
                for a in range(A):
                    if close(qs[a], vs):
                        nO.add(nxt[rowof[s]][a])
            O = nO
        results[k] = float(k) if best == -math.inf else k + best + math.log(6 * math.log(2 * T * A ** k)) / math.log(A)
    if not results:
        return None, None
    k = min(results, key=results.get)
    return results[k], k


def main():
    fails = []

    def check(c, msg):
        if not c:
            fails.append(msg)
            print("FAIL:", msg)

    # 1. the hand example
    r = eh.effective_horizon(nxt=[[1, 0]], rows=[0], win=[False, True], loss=[False, False], start=0, T=2)
    check(r["k"] == 2 and abs(r["eh"] - 6.0562) < 1e-4, f"hand example: {r}")
    check(abs(r["per_k"][1]["eh"] - 6.6412) < 1e-4 and abs(r["per_k"][3]["eh"] - 7.3781) < 1e-4, f"hand example per k: {r['per_k']}")

    # 2. against the loop-by-loop reference
    rng = np.random.default_rng(7)
    agree = 0
    for _ in range(40):
        n, A, T = int(rng.integers(4, 12)), int(rng.integers(2, 4)), int(rng.integers(2, 8))
        win = [False] * n
        loss = [False] * n
        win[n - 1] = True
        if n > 5:
            loss[n - 2] = True
        rows = [s for s in range(n) if not (win[s] or loss[s])]
        nxt = [[int(rng.integers(0, n)) for _ in range(A)] for _ in rows]
        got = eh.effective_horizon(nxt, rows, np.array(win), np.array(loss), start=0, T=T, A=A)
        ref, ref_k = reference_eh(nxt, rows, win, loss, 0, T, A)
        same = (ref is None and got["eh"] is None) or (ref is not None and got["eh"] is not None
                                                       and abs(ref - got["eh"]) < 1e-9 and ref_k == got["k"])
        agree += same
        check(same, f"random MDP n={n} A={A} T={T}: eh.py {got['eh']} (k {got['k']}, {got['status']}), reference {ref} (k {ref_k})")
    print(f"effective horizon: {agree} of 40 random MDPs agree with the reference")

    # 3. against the plain search
    from sim_minigrid import naive_counts  # noqa: PLC0415
    tmp = tempfile.mkdtemp(prefix="horizon-devsearch-")
    try:
        for game, seed in LEVELS:
            unit = dict(campaign="t", unit_id=f"{game}-{seed}", chunk_id="c", suite="minigrid", game=game, level=seed)
            st, row, state = jobs.run_search(unit, PARAMS, os.path.join(tmp, "w"), None, time.time() + 600,
                                             lambda s: None, "nonce", "2026-10-25T00:00:00Z", schema=SEARCH_SCHEMA_V2)
            ref = naive_counts(game, seed)
            mine = dict(states_seen=row["counts"]["states_seen"], states_expanded=row["counts"]["states_expanded"],
                        solution_length=row["counts"]["solution_length"],
                        successors_distinct=state.extra["successors_distinct"])
            print(f"{game} seed {seed}: {mine}; plain search {ref}; EH {row['measures']['eh']} ({row['measures']['eh_status']})", flush=True)
            check(mine == ref, f"{game} {seed}: snapshot search {mine} differs from the plain search {ref}")
            check(st == "complete" and not validate_search_row(row), f"{game}: row {st}, {validate_search_row(row)}")
            check(row["measures"]["eh_status"] in ("ok", "ok, no gap on the optimal states", "goal beyond horizon",
                                                   "not solvable"), f"{game}: eh status {row['measures']['eh_status']}")

        # 4. stop, save, load, finish
        game, seed = "MiniGrid-DoorKey-5x5-v0", 1000
        unit = dict(campaign="t", unit_id="resume", chunk_id="c", suite="minigrid", game=game, level=seed)
        p = dict(PARAMS, batch=5)
        whole = jobs.run_search(unit, p, os.path.join(tmp, "a"), None, time.time() + 600, lambda s: None, "n",
                                "2026-10-25T00:00:00Z", schema=SEARCH_SCHEMA_V2)[1]
        st, row, state = jobs.run_search(unit, p, os.path.join(tmp, "b"), None, time.time(), lambda s: None, "n",
                                         "2026-10-25T00:00:00Z", schema=SEARCH_SCHEMA_V2)
        check(st == "stopped" and row is None, f"the search should stop at a past deadline: {st}")
        meta = state.save(os.path.join(tmp, "ck"), os.path.join(tmp, "b"))
        state2 = jobs.SearchState.load(os.path.join(tmp, "ck"), meta, os.path.join(tmp, "c"))
        st2, row2, _ = jobs.run_search(unit, p, os.path.join(tmp, "c"), state2, time.time() + 600, lambda s: None, "n",
                                       "2026-10-25T00:00:00Z", schema=SEARCH_SCHEMA_V2)
        check(st2 == "complete" and row2["counts"]["states_seen"] == whole["counts"]["states_seen"]
              and row2["counts"]["solution_length"] == whole["counts"]["solution_length"]
              and row2["measures"]["eh"] == whole["measures"]["eh"]
              and row2["measures"]["branching"] == whole["measures"]["branching"],
              f"resumed search differs: {row2['counts']} {row2['measures']} against {whole['counts']} {whole['measures']}")

        # 5. Dynamic-Obstacles is refused
        try:
            jobs.run_search(dict(unit, game="MiniGrid-Dynamic-Obstacles-5x5-v0"), PARAMS, os.path.join(tmp, "d"),
                            None, time.time() + 60, lambda s: None, "n", "x", schema=SEARCH_SCHEMA_V2)
            check(False, "Dynamic-Obstacles must be refused")
        except ValueError as e:
            check("excluded" in str(e), f"Dynamic-Obstacles refused for the wrong reason: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
