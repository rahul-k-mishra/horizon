"""
engine_speed.py -- the speed of the recommended engine, GVGAI's own Java forward model called through JPype
(docs/design/ENGINE.md, Section 4), on this machine.

For every level file of the 30 deterministic games (150 levels), through the code the search job runs
(scripts/automation/sim_gvgai.py and the bridge): load the level; then walk from the level start with seeded
random actions and, at every state of the walk, call the search's expansion (the state's key, and for every
action a copy, GVGAI's advance and the successor's key), hashing every key with jobs.h64 as the search does.
The walk restarts from the start when it meets a terminal state or reaches DEPTH actions (300 by default),
so that the bridge's stack of copies stays as deep as a breadth-first frontier's sequences.  The first WARM expansions of each level are
not timed (the JVM compiles the code on its first calls); the next N are.  This is a walk, not a search: it
records no count of reachable states, no win and no solution length, so it reads nothing of a level's search
quantities.

Printed per level: the actions, the key's size in bytes, expansions per second and successors per second.
Then the estimate: a breadth-first search to S states expands at most S states, so S / (expansions per
second) bounds its time from above, the frontier's replay costing one advance per expansion as in the walk.
Per level, that bound for S = 2,000,000 capped at the time cap of 14,400 s; summed over the 130 confirmatory
levels and over the 20 pilot levels; and set against the session of docs/design/params_v0.json (4 workers x
28,800 s) and the 17 confirmatory search chunks of logs/design_budget.log.

Run (working directory D:\\Research\\horizon\\repo; JAVA_HOME may name a JDK 21, else the pinned Temurin is
downloaded into the cache folder):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\engine_speed.py --cache D:\\Research\\horizon\\gvgai-cache > logs\\engine_speed.log
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts", "automation"))
import sim_gvgai  # noqa: E402
from jobs import h64  # noqa: E402

S_TARGET = 2_000_000
TIME_CAP = 14_400.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, help="folder for the JDK and the compiled classes (outside the repository)")
    ap.add_argument("--warm", type=int, default=300)
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=20261114)
    ap.add_argument("--depth", type=int, default=300)
    a = ap.parse_args()
    with open(os.path.join(REPO, "docs", "design", "vgdl_scan.json"), encoding="utf-8") as f:
        det = sorted(g["game"] for g in json.load(f)["games"] if g["deterministic"])
    with open(os.path.join(REPO, "logs", "draw_pilot.log"), encoding="utf-8") as f:
        pilot_text = f.read()
    line = next(ln for ln in pilot_text.splitlines() if ln.startswith("pilot ("))
    pilot = [x.strip() for x in line.split(":", 1)[1].split(",")]
    with open(os.path.join(REPO, "docs", "design", "params_v0.json"), encoding="utf-8") as f:
        params = json.load(f)
    t0 = time.time()
    jdk = sim_gvgai.ensure_jdk(a.cache)
    t1 = time.time()
    classes = sim_gvgai.build(jdk, a.cache)
    t2 = time.time()
    bridge = sim_gvgai.start_jvm(a.cache)
    import jpype  # noqa: PLC0415
    print("== the machine and the engine")
    print(f"python {platform.python_version()}, {platform.system()} {platform.release()}, processor {platform.processor()}, "
          f"{os.cpu_count()} logical CPUs")
    print(f"JPype {jpype.__version__}; JVM {jpype.java.lang.System.getProperty('java.vm.name')} "
          f"{jpype.java.lang.System.getProperty('java.version')}; options {' '.join(sim_gvgai.JVM_OPTIONS)}")
    print(f"GVGAI source: {len(sim_gvgai.java_sources())} Java files (vendored src/ and the bridge), "
          f"digest {sim_gvgai.source_digest(sim_gvgai.java_sources())[:16]}; JDK ready in {t1 - t0:.1f} s, "
          f"build {t2 - t1:.1f} s (0 when the classes were already built), JVM start {time.time() - t2:.1f} s")
    print(f"walk: {a.warm} expansions untimed, then {a.n} timed, per level; restart at a terminal state or at "
          f"{a.depth} actions; seed {a.seed}")

    print("\n== per level: game level | actions | key bytes | load s | expansions/s | successors/s | "
          "bound for 2,000,000 states (s, capped at 14,400)")
    rows = []
    for g in det:
        tick = sim_gvgai.with_tick(g)
        for lv in range(5):
            rng = random.Random(f"{a.seed}-{g}-{lv}")
            tl = time.perf_counter()
            sim = sim_gvgai.GVGAISim(dict(with_tick={g: tick}, gvgai_cache=a.cache), dict(game=g, level=lv))
            load = time.perf_counter() - tl
            key0, _w, _l = sim.root_info()
            h64(key0)
            enc = sim.root_enc()
            done = 0
            elapsed = 0.0
            succ = 0
            while done < a.warm + a.n:
                ts = time.perf_counter()
                pkey, kids = sim.expand(enc)
                h64(pkey)
                for _a, _e, k, _win, _loss in kids:
                    h64(k)
                te = time.perf_counter()
                if done >= a.warm:
                    elapsed += te - ts
                    succ += len(kids)
                done += 1
                live = [k for k in kids if not (k[3] or k[4])]
                enc = rng.choice(live)[1] if live and len(enc) < a.depth else sim.root_enc()
            eps = a.n / elapsed
            bound = min(S_TARGET / eps, TIME_CAP)
            rows.append(dict(game=g, level=lv, actions=len(sim.actions), key=len(key0), load=load, eps=eps,
                             sps=succ / elapsed, bound=bound, tick=tick))
            print(f"{g:16s} {lv} | {len(sim.actions)} | {len(key0):6d} | {load:5.2f} | {eps:8.0f} | {succ / elapsed:8.0f} | "
                  f"{bound:7.0f}{' (time cap)' if bound >= TIME_CAP else ''}")

    def summary(name, rs):
        tot = sum(r["bound"] for r in rs)
        capped = sum(1 for r in rs if r["bound"] >= TIME_CAP)
        worker = params["workers"] * params["work_seconds"] if "workers" in params and "work_seconds" in params \
            else 4 * 28_800
        print(f"{name}: {len(rs)} levels; expansions/s median {sorted(r['eps'] for r in rs)[len(rs) // 2]:.0f}, "
              f"slowest {min(r['eps'] for r in rs):.0f} ({min(rs, key=lambda r: r['eps'])['game']} "
              f"{min(rs, key=lambda r: r['eps'])['level']}), fastest {max(r['eps'] for r in rs):.0f}; "
              f"levels whose bound reaches the time cap: {capped}; sum of the bounds {tot:.0f} worker-seconds, "
              f"{tot / worker:.2f} sessions of {worker} worker-seconds, so at least {math.ceil(tot / worker)} "
              "sessions if packed perfectly")
        return tot

    print("\n== the estimate (upper bounds for a search of 2,000,000 states; expanded <= seen)")
    conf = [r for r in rows if r["game"] not in pilot]
    pil = [r for r in rows if r["game"] in pilot]
    small = min({r["game"] for r in conf}, key=lambda g: next(r["key"] for r in conf if r["game"] == g and r["level"] == 0))
    r0 = next(r for r in conf if r["game"] == small and r["level"] == 0)
    print(f"the smallest confirmatory level 0 by key size: {small}, {r0['eps']:.0f} expansions/s, "
          f"{S_TARGET / r0['eps']:.0f} s for 2,000,000 states")
    summary("confirmatory", conf)
    summary("pilot", pil)
    print("charged at the whole time cap instead, 130 confirmatory levels need 17 chunks at most (logs/design_budget.log)")
    print(f"games whose state key holds the tick: {sum(1 for g in det if sim_gvgai.with_tick(g))} of {len(det)}")
    print(f"\nwall time of this script: {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
