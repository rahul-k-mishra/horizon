"""
check_agent_copies.py -- the copy check of docs/PREREG.md, Section 2: study 1's agents, as copied into
third_party/study1, are run on a sample of study 1's MiniGrid/BabyAI units under study 1's conditions, and every
field of each new row is compared with study 1's committed row for the same unit.

What runs.  Study 1's own runner function, run_suite.one, copied byte for byte with the files it calls from study
1's tag prereg-v1.1 (third_party/study1/scripts): the agents N (mode nav), R (mode hash_state) and I1 (mode i1),
the frame contract env_frame.py, the MiniGrid adapter adapter_minigrid.py and analyze_common.py (for the census
field of N's rows).  Every file's git blob hash is checked first against the hash study 1 registered or recorded
in its rows (agents_gvgai.FROZEN and EXTRA below); the run stops on any difference.  The conditions are those
recorded in each committed row: suite minigrid, condition macro, the row's seed, budget (20,000 actions) and
wall-clock cap (seconds_cap).  New rows are written to a temporary folder outside the repository and deleted;
nothing under runs/ is read or written in this repository.  Study 1's repository is only read.

The sample.  The units (game, seed) that have a committed row for all three agents in study 1's
runs/suites/minigrid/macro; numpy default_rng(SEED) draws PER_FAMILY units from the MiniGrid games and PER_FAMILY
from the BabyAI games, without replacement.

The comparison.  For each (unit, agent), the committed row and the new row are compared field by field, nested
fields included.  Fields that are wall-clock times are left out and listed (TIME_FIELDS); everything else must be
equal: the outcome (levels, level1_completed, level1_actions, actions, state), the agent's own counters (diag,
level_log, states_seen, effects, trials, chose, nav, census; for I1 stopped, time_truncated, levels_true and its
diag), and the adapter's record (colours, grid, primitive steps, key map, blob hashes).  Every difference is printed
with both values.

Run (working directory D:\\Research\\horizon\\repo; study 1's repository read from --old-repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\check_agent_copies.py --workers 6 > logs\\check_agent_copies.log
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STUDY1 = os.path.join(REPO, "third_party", "study1")
sys.path.insert(0, os.path.join(STUDY1, "scripts"))
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True

SEED, PER_FAMILY = 20261114, 6
SUITE, CONDITION = "minigrid", "macro"
MODES = ("nav", "hash_state", "i1")
# the three files the copy check adds to agents_gvgai.FROZEN: their blob hashes at study 1's tag prereg-v1.1, the
# same hashes study 1's rows record (adapter.adapter_blob and adapter.run_suite_blob)
EXTRA = {
    "scripts/adapter_minigrid.py": "370028ab178eaed65803d2f0f7d86c29adf14328",
    "scripts/run_suite.py": "1360b0a65c587ee04ab47e4ab2dca8625a67ad6e",
    "scripts/analyze_common.py": "caad22731807db78aff9c92c993a79a63f042ec3",
}
TIME_FIELDS = ("seconds", "agent_seconds", "play_seconds", "game_seconds", "sec_per_action", "env_sec_per_action")


def blob_hash(path):
    import hashlib  # noqa: PLC0415
    with open(path, "rb") as f:
        data = f.read()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check_copies():
    import agents_gvgai as G  # noqa: PLC0415
    bad = dict(G.check_frozen())
    for rel, h in EXTRA.items():
        got = blob_hash(os.path.join(STUDY1, rel))
        if got != h:
            bad[rel] = (got, h)
    return bad, len(G.FROZEN) + len(EXTRA)


def row_path(root, mode, game, seed):
    return os.path.join(root, "runs", "suites", SUITE, CONDITION, mode, f"{game}__{seed}.json")


def sample_units(old):
    d = os.path.join(old, "runs", "suites", SUITE, CONDITION)
    per_mode = []
    for m in MODES:
        names = {f[:-5] for f in os.listdir(os.path.join(d, m)) if f.endswith(".json")}
        per_mode.append(names)
    common = sorted(set.intersection(*per_mode))
    units = [(n.rsplit("__", 1)[0], int(n.rsplit("__", 1)[1])) for n in common]
    rng = np.random.default_rng(SEED)
    out = []
    for fam in ("MiniGrid", "BabyAI"):
        pool = [u for u in units if u[0].startswith(fam)]
        idx = rng.choice(len(pool), PER_FAMILY, replace=False)
        out += [pool[i] for i in sorted(idx)]
    return out, len(units)


def diff(a, b, path=""):
    """[(path, committed value, new value)] for every field that differs, wall-clock fields left out."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k in TIME_FIELDS:
                continue
            p = f"{path}.{k}" if path else str(k)
            if k not in a or k not in b:
                out.append((p, a.get(k, "<absent>"), b.get(k, "<absent>")))
            else:
                out += diff(a[k], b[k], p)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append((path + ".length", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append((path, a, b))
    return out


def short(v, n=110):
    s = json.dumps(v, default=str)
    return s if len(s) <= n else s[:n] + "..."


def run_job(job):
    import run_suite  # noqa: PLC0415 -- study 1's runner, copied byte for byte
    return run_suite.one(job)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-repo", default=r"D:\Research\arc3\repo")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    bad, n_files = check_copies()
    if bad:
        for rel, (got, h) in bad.items():
            print(f"COPY DIFFERS: {rel} blob {got}, expected {h}")
        print("STOP: a copied file differs from study 1's")
        return 1
    print(f"copies: {n_files} files of third_party/study1/scripts have study 1's blob hashes")
    vers = {p: md.version(p) for p in ("numpy", "minigrid", "gymnasium", "pillow", "pygame-ce")}
    print(f"this machine: Python {platform.python_version()}, " + ", ".join(f"{p} {v}" for p, v in vers.items()))
    print("study 1 (docs/PREREG.md v1, Section 3.2 of its repository): Python 3.11.9, minigrid 3.1.0, gymnasium 1.3.0")
    units, n_units = sample_units(a.old_repo)
    print(f"sample: {len(units)} of the {n_units} units with a committed row for all of {', '.join(MODES)} "
          f"(numpy default_rng({SEED}), {PER_FAMILY} MiniGrid and {PER_FAMILY} BabyAI); suite {SUITE}, condition {CONDITION}")
    for g, s in units:
        print(f"  {g} seed {s}")
    old_rows, jobs = {}, []
    tmp = tempfile.mkdtemp(prefix="horizon-copycheck-")
    try:
        for g, s in units:
            for m in MODES:
                with open(row_path(a.old_repo, m, g, s), encoding="utf-8") as f:
                    r = json.load(f)[0]
                old_rows[(g, s, m)] = r
                jobs.append((SUITE, CONDITION, g, s, m, int(r["budget"]), float(r["seconds_cap"]), tmp))
        budgets = sorted({j[5] for j in jobs})
        caps = sorted({j[6] for j in jobs})
        print(f"conditions from the committed rows: budget {budgets}, wall-clock cap {caps} s; {len(jobs)} runs, "
              f"{a.workers} workers")
        t0 = time.time()
        with Pool(a.workers) as pool:
            for res in pool.imap_unordered(run_job, sorted(jobs, key=lambda j: j[4] != "i1")):
                g, s, m, lv, acts, cut, err = res
                print(f"  ran {g} seed {s} {m}: levels {lv} actions {acts}" + (" CUT" if cut else "")
                      + (f" ERROR {err}" if err else ""), flush=True)
        print(f"wall time {time.time() - t0:.0f} s")
        print("\n== comparison per (unit, agent): committed row of study 1 against the new row; wall-clock fields "
              f"left out: {', '.join(TIME_FIELDS)}")
        n_match = n_outcome = 0
        all_diffs = []
        for g, s in units:
            for m in MODES:
                with open(os.path.join(tmp, SUITE, CONDITION, m, f"{g}__{s}.json"), encoding="utf-8") as f:
                    new = json.load(f)[0]
                old = old_rows[(g, s, m)]
                d = diff(old, new)
                same_outcome = all(old.get(k) == new.get(k) for k in ("levels", "level1_completed", "level1_actions",
                                                                       "actions", "state"))
                n_match += int(not d)
                n_outcome += int(same_outcome)
                print(f"{g} seed {s} {m}: " + ("identical" if not d else f"{len(d)} field(s) differ")
                      + f"; outcome {'same' if same_outcome else 'DIFFERENT'} (levels {old.get('levels')} / "
                      f"{new.get('levels')}, level1_completed {old.get('level1_completed')} / {new.get('level1_completed')}, "
                      f"level1_actions {old.get('level1_actions')} / {new.get('level1_actions')})")
                for p, x, y in d:
                    print(f"    {p}: committed {short(x)} | new {short(y)}")
                    all_diffs.append((g, s, m, p))
        n = len(units) * len(MODES)
        print("\n== totals")
        print(f"units compared: {len(units)}; runs compared: {n} ({len(units)} per agent for N, R and I1)")
        print(f"identical in every field but wall-clock time: {n_match} of {n}")
        print(f"same outcome (levels, level1_completed, level1_actions, actions, state): {n_outcome} of {n}")
        paths = sorted({p.split("[")[0] for _g, _s, _m, p in all_diffs})
        print(f"fields that differ anywhere: {', '.join(paths) if paths else 'none'}")
        return 0 if n_match == n else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
