"""
g2_replay.py -- gate G2 of docs/PREREG.md, Section 8, as registered on 26 November 2026: on every pilot level,
1,000 random action sequences of length 200, each replayed twice from the level start, give identical state
hashes at every step.  Run by the author on his laptop before the tag (the exception to Section 9 recorded in
PREREG Section 8; docs/DECISIONS_BEFORE_TAG.md, item 17).  The pilot games never enter a confirmatory analysis.

What it does, as registered:
    levels      the 20 pilot levels: the games of logs/draw_pilot.log in their order there (game index 0 to 3),
                levels 0 to 4.
    sequences   per level, numpy.random.default_rng([20261126, game index, level]).integers(0, A, size=(1000, 200)),
                A the number of actions in the adapter's list (HorizonBridge.actions: the avatar's available
                actions without ACTION_NIL, in GVGAI's order); each action drawn uniformly from that list.
    replay      HorizonBridge.forwardKeys: the level is loaded from its files, and the sequence is played through
                GVGAI's forward model from the start.  The state key is taken before each action and after the
                last action played.  If the game ends (a win, a loss, or GVGAI's tick limit) before the 200th
                action, the replay stops there; the actions left are not played.
    hash        the search's own hash: jobs.h64 (blake2b, 8 bytes) of the registered key, HorizonBridge.key, form
                EXTENDED, with the game tick where sim_gvgai.with_tick says (docs/PREREG.md, Section 6).  Per
                sequence the row keeps the number of actions played, the final status, and the SHA-256 of the
                list of 64-bit hashes at every step; two replays agree at every step exactly when the two
                SHA-256 values are equal (bar a collision of SHA-256), the steps are equal and the statuses
                are equal.
    processes   the first replays of every level run in one pool of worker processes (pass 1); that pool is
                closed, and the second replays run in a new pool (pass 2).  Each worker process starts its own
                JVM.  So the two replays of a sequence never share a process or a JVM.  Each row carries a random
                token of the process that wrote it, and the comparison checks that the tokens of the two passes
                are disjoint.
    platform    the author's laptop: CPython of D:\\Research\\horizon\\.venv, JPype1, and the pinned Temurin JDK and
                the GVGAI classes compiled from the vendored source by scripts/automation/sim_gvgai.py; each row
                records the platform, the JDK folder and the classes folder.
G2 passes if every one of the 20 levels has 1,000 sequences in each pass, the same actions in both passes (the
SHA-256 of the action array), and, for every sequence, the same digest, steps and status in both.

Parallel form (rule R4): a pool of --workers processes; one unit per (pass, level), 40 units; two chunks, pass-1
and pass-2, each far inside 11 hours on 4 cores (EXPLORATORY projection, logs/g2_cost.log: under an hour for
both); a done-marker per unit under <out>/done; the manifest <out>/manifest.json, written on the first run and
checked on every later one.  Resumable: run the same command again and finished units are skipped.

The single command (in cmd, working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\g2_replay.py > logs\\g2_replay.log 2>&1
Its rows go to runs/g2-replay (rows/, done/, manifest.json); the console ends with "G2: PASS" or "G2: FAIL" and
returns 0, 1, or 2 if units are missing.  Commit the rows, the done-markers, the manifest and the console.
Options other than --cache, --out and --workers are for the tests (scripts/test_g2_replay.py) and make the run
"not G2".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True

SEED, SEQUENCES, LENGTH, PASSES = 20261126, 1000, 200, (1, 2)
SCHEMA = "horizon.g2.v1"
DEFAULT_CACHE = r"D:\Research\horizon\gvgai-cache"
DEFAULT_OUT = os.path.join(REPO, "runs", "g2-replay")
_TOKEN = uuid.uuid4().hex     # one per process: a worker process imports this module afresh


def pilot_games():
    with open(os.path.join(REPO, "logs", "draw_pilot.log"), encoding="utf-8") as f:
        line = next(ln for ln in f.read().splitlines() if ln.startswith("pilot ("))
    return [x.strip() for x in line.split(":", 1)[1].split(",")]


def registered_levels():
    return [(g, lv) for g in pilot_games() for lv in range(5)]


def sequences(seed, game_index, level, n_actions, n, length):
    return np.random.default_rng([seed, game_index, level]).integers(0, n_actions, size=(n, length), dtype=np.int64)


def unit_id(p, game, level):
    return f"r{p}-{game}-l{level}"


def digest(hashes):
    return hashlib.sha256(b"".join(int(h).to_bytes(8, "little") for h in hashes)).hexdigest()


def run_unit(a):
    """Worker: replays the sequences of one level once and writes the row, then the done-marker."""
    import jobs        # noqa: PLC0415
    import sim_gvgai   # noqa: PLC0415
    t0 = time.time()
    jdk = sim_gvgai.ensure_jdk(a["cache"])
    classes = sim_gvgai.build(jdk, a["cache"])
    bridge = sim_gvgai.start_jvm(a["cache"])
    gf, lf = sim_gvgai.level_paths(a["game"], a["level"], a["games_dir"])
    gf, lf = gf.replace("\\", "/"), lf.replace("\\", "/")
    names = [str(x) for x in bridge.actionNames(bridge.load(gf, lf, 0))]
    tick = bool(sim_gvgai.with_tick(a["game"], a["games_dir"]))
    acts = sequences(a["seed"], a["game_index"], a["level"], len(names), a["sequences"], a["length"])
    digests, steps, statuses = [], [], []
    for seq in acts:
        keys, _ticks, status = bridge.forwardKeys(gf, lf, bytes(int(x) for x in seq), tick)
        hs = [jobs.h64(bytes(k)) for k in keys]
        digests.append(digest(hs))
        steps.append(len(hs) - 1)
        statuses.append(int(status))
    row = dict(schema=SCHEMA, unit=a["unit"], replay_pass=a["pass"], game=a["game"], level=a["level"],
               game_index=a["game_index"], seed=a["seed"], sequences=a["sequences"], length=a["length"],
               n_actions=len(names), action_names=names, with_tick=tick, key_form="EXTENDED", hash="jobs.h64",
               actions_sha256=hashlib.sha256(acts.tobytes()).hexdigest(), digests=digests, steps=steps,
               statuses=statuses, process_token=_TOKEN, pid=os.getpid(), seconds=round(time.time() - t0, 3),
               platform=platform.platform(), python=platform.python_version(), jdk=os.path.basename(jdk),
               classes=os.path.basename(classes), written_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    path = os.path.join(a["out"], "rows", a["unit"] + ".json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(row, f)
    os.replace(path + ".tmp", path)
    with open(os.path.join(a["out"], "done", a["unit"] + ".done"), "w", encoding="utf-8") as f:
        f.write(row["written_at"] + "\n")
    return a["unit"], row["seconds"], row["pid"]


def manifest(levels, seed, n, length, games_dir):
    games = list(dict.fromkeys(g for g, _ in levels))
    return dict(gate="G2", schema=SCHEMA, seed=seed, sequences=n, length=length, games_dir=games_dir,
                levels=[[g, lv, games.index(g)] for g, lv in levels],
                chunks=[dict(chunk=f"pass-{p}", units=[unit_id(p, g, lv) for g, lv in levels]) for p in PASSES])


def compare(out, man):
    """(lines, status): status 'identical', 'different' or 'incomplete'."""
    lines, status = [], "identical"
    tot = dict(levels=0, seq=0, same=0, states=0, ended=0)
    tokens = {p: set() for p in PASSES}
    for g, lv, _gi in man["levels"]:
        rows = {}
        for p in PASSES:
            fn = os.path.join(out, "rows", unit_id(p, g, lv) + ".json")
            if not os.path.exists(os.path.join(out, "done", unit_id(p, g, lv) + ".done")) or not os.path.exists(fn):
                rows = None
                break
            with open(fn, encoding="utf-8") as f:
                rows[p] = json.load(f)
        if rows is None:
            lines.append(f"{g:14s} {lv} | missing")
            status = "incomplete"
            continue
        a, b = rows[1], rows[2]
        for p in PASSES:
            tokens[p].add(rows[p]["process_token"])
        problems = []
        for k in ("schema", "seed", "sequences", "length", "n_actions", "with_tick", "actions_sha256"):
            if a[k] != b[k]:
                problems.append(f"{k} differs")
        if len(a["digests"]) != man["sequences"] or len(b["digests"]) != man["sequences"]:
            problems.append(f"sequences {len(a['digests'])} and {len(b['digests'])}, not {man['sequences']}")
        n = min(len(a["digests"]), len(b["digests"]))
        same = [i for i in range(n) if a["digests"][i] == b["digests"][i] and a["steps"][i] == b["steps"][i]
                and a["statuses"][i] == b["statuses"][i]]
        diff = [i for i in range(n) if i not in set(same)]
        if diff:
            i = diff[0]
            problems.append(f"{len(diff)} sequence(s) differ; first: sequence {i}, steps {a['steps'][i]} and "
                            f"{b['steps'][i]}, status {a['statuses'][i]} and {b['statuses'][i]}, digests "
                            f"{'equal' if a['digests'][i] == b['digests'][i] else 'different'}")
        ended = sum(s < man["length"] for s in a["steps"])
        states = sum(s + 1 for s in a["steps"])
        tot.update(levels=tot["levels"] + 1, seq=tot["seq"] + n, same=tot["same"] + len(same),
                   states=tot["states"] + states, ended=tot["ended"] + ended)
        lines.append(f"{g:14s} {lv} | actions {a['n_actions']} | tick {'yes' if a['with_tick'] else 'no '} | "
                     f"identical {len(same)} of {n} | states hashed {states} in each pass | ended before "
                     f"{man['length']} actions {ended} | seconds {a['seconds']:.1f} and {b['seconds']:.1f}"
                     + ("" if not problems else " | " + "; ".join(problems)))
        if problems:
            status = "different"
    shared = tokens[1] & tokens[2]
    lines.append("")
    lines.append(f"processes: pass 1 {len(tokens[1])}, pass 2 {len(tokens[2])}, shared by both passes {len(shared)}")
    if shared:
        status = "different" if status == "identical" else status
        lines.append("the two passes shared a process: not the registered form")
    lines.append(f"levels compared {tot['levels']} of {len(man['levels'])}; sequences identical {tot['same']} of "
                 f"{tot['seq']}; states hashed in each pass {tot['states']}; sequences that ended the game "
                 f"before {man['length']} actions {tot['ended']}")
    return lines, status


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--games-dir", default=None, help="tests only")
    ap.add_argument("--levels", default=None, help="tests only: game:level,game:level,...")
    ap.add_argument("--sequences", type=int, default=SEQUENCES, help="tests only")
    ap.add_argument("--length", type=int, default=LENGTH, help="tests only")
    ap.add_argument("--stop-after", type=int, default=None, help="tests only: run at most this many units, then stop")
    a = ap.parse_args(argv)
    levels = registered_levels() if a.levels is None else \
        [(x.split(":")[0], int(x.split(":")[1])) for x in a.levels.split(",")]
    registered = (a.levels is None and a.games_dir is None and a.sequences == SEQUENCES and a.length == LENGTH
                  and a.stop_after is None)
    man = manifest(levels, SEED, a.sequences, a.length, a.games_dir)
    for d in ("rows", "done"):
        os.makedirs(os.path.join(a.out, d), exist_ok=True)
    mp = os.path.join(a.out, "manifest.json")
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as f:
            if json.load(f) != man:
                print(f"{mp} differs from this run's manifest: refused (use the same options, or another --out)")
                return 3
    else:
        with open(mp, "w", encoding="utf-8") as f:
            json.dump(man, f, indent=1)
    print(f"G2 of docs/PREREG.md, Section 8 (registered 26 November 2026){'' if registered else ': TEST PARAMETERS, not G2'}")
    print(f"levels {len(levels)}; sequences {a.sequences} of {a.length} actions per level; seed {SEED}; "
          f"workers {a.workers}; out {os.path.relpath(a.out, REPO) if a.out.startswith(REPO) else a.out}")
    budget = a.stop_after
    for p in PASSES:
        pending = [(g, lv, gi) for g, lv, gi in man["levels"]
                   if not os.path.exists(os.path.join(a.out, "done", unit_id(p, g, lv) + ".done"))]
        done_before = len(man["levels"]) - len(pending)
        if budget is not None:
            pending = pending[:max(budget, 0)]
            budget -= len(pending)
        print(f"== pass {p} (chunk pass-{p}): {done_before} unit(s) already done, {len(pending)} to run, in a new pool")
        if not pending:
            continue
        jobs_ = [dict(unit=unit_id(p, g, lv), game=g, level=lv, game_index=gi, seed=SEED, sequences=a.sequences,
                      length=a.length, cache=a.cache, out=a.out, games_dir=a.games_dir, **{"pass": p})
                 for g, lv, gi in pending]
        with ProcessPoolExecutor(a.workers) as ex:     # closed before the next pass: no process is shared
            for unit, secs, pid in ex.map(run_unit, jobs_):
                print(f"  {unit}: {secs:.1f} s, process {pid}")
        sys.stdout.flush()
    print("\n== comparison of the two replays")
    lines, status = compare(a.out, man)
    print("\n".join(lines))
    if status == "incomplete":
        print("incomplete: run the same command again to finish")
        return 2
    print(f"result: {status}")
    if registered:
        print("G2: PASS" if status == "identical" else "G2: FAIL")
    else:
        print("not G2: test parameters")
    return 0 if status == "identical" else 1


if __name__ == "__main__":
    sys.exit(main())
