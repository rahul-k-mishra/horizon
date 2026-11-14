"""
make_gvgai_manifests.py -- writes two manifests of the kind gvgaisearch, neither of which is the loop's manifest:

    jobs/gvgaisearch_dryrun/manifest.json   the dry run of the kind through the loop (rule R8, as for the kind
                                            devsearch, docs/DRYRUN_DEVSEARCH.md): the synthetic games of
                                            scripts/automation/gvgai_testgames (corridor levels 0 and 1, whose
                                            counts are worked out by hand in scripts/automation/test_gvgaisearch.py,
                                            and boxroom level 0, slowed down so that it outlasts its first session
                                            and must resume from a checkpoint); sessions of 180 s of work.
    jobs/pilot_search/manifest.json         the pilot search of docs/PREREG.md, Section 8 (decision 10 of 14 November
                                            2026): the 20 levels of the 4 pilot games of logs/draw_pilot.log, seen cap
                                            2,000,000, the other caps of Section 6, the registered state key (the
                                            extended key, decided 14 November 2026); and the same 20 levels again
                                            under the v0 key that decision replaced (unit params key_form "v0", unit
                                            ids ending "-v0"), only so that the effect of the key on the states seen
                                            can be measured on pilot levels (PREREG Section 6).  G3 and the pilot's
                                            counts are read from the extended-key units alone.

Both name the code tag CODE_TAG, which does not exist yet: it is cut on the commit that holds the GVGAI code when a
manifest is installed as jobs/manifest.json, after stage E's campaign is done (the loop runs one manifest at a
time; docs/STATE.md).  The pilot's chunking uses the per-level upper bounds of logs/engine_speed.log (seconds for
2,000,000 states on the laptop), packed longest first to at most LOAD of a session (4 workers x 28,800 s).
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\make_gvgai_manifests.py > logs\\make_gvgai_manifests.log
"""
from __future__ import annotations

import heapq
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
from common import check_manifest  # noqa: E402

CODE_TAG = "automation-v4"
SEEN_CAP = 2_000_000
LOAD = 0.60
BASE = dict(simulator="gvgai", key_form="extended", workers=4, schema="horizon.search.v3", seen_cap=SEEN_CAP,
            node_cap=5_000_000, time_cap_seconds=14400, memory_cap_bytes=6442450944, spill_frontier_over=1_000_000,
            checkpoint_every_seconds=600, checkpoint_every_nodes=250000, batch=200, eh_state_limit=0, eh_horizon=0)
SESSION = dict(work_seconds=28800, checkpoint_reserve_seconds=900, platform_limit_seconds=32400)
DRY_SESSION = dict(work_seconds=180, checkpoint_reserve_seconds=300, platform_limit_seconds=3600)


def manifest(campaign, kind, session, units_spec, payload_limit):
    chunks, units = [], []
    for cid, specs in units_spec:
        chunks.append(dict(chunk_id=cid, kind="gvgaisearch", status="pending", attempts=0, failures=0, sessions=[]))
        for game, level, params, *suffix in specs:
            u = dict(unit_id=f"{cid}-{game}-l{level}{suffix[0] if suffix else ''}", chunk_id=cid, kind="gvgaisearch", suite="gvgai", game=game,
                     level=level, agent=None, seed=None, status="pending")
            if params:
                u["params"] = params
            units.append(u)
    m = dict(campaign=campaign, code_tag=CODE_TAG, repository="rahul-k-mishra/horizon", kernel_slug="horizon-runner",
             max_failures=3, payload_commit_limit_bytes=payload_limit, session=session,
             kinds=dict(gvgaisearch=kind), chunks=chunks, units=units)
    errs = check_manifest(m)
    if errs:
        raise SystemExit(f"manifest check failed: {errs}")
    return m


def write(m, folder):
    d = os.path.join(REPO, "jobs", folder)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "manifest.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    return os.path.relpath(p, REPO)


def lpt(times, workers):
    load = [0.0] * workers
    for t in sorted(times, reverse=True):
        heapq.heappush(load, heapq.heappop(load) + t)
    return max(load)


def main():
    dry_kind = dict(BASE, games_dir="scripts/automation/gvgai_testgames", with_tick={"corridor": False, "boxroom": False})
    dry = manifest("gvgaisearch-dryrun", dry_kind, DRY_SESSION,
                   [("gd-01", [("corridor", 0, None), ("corridor", 1, None),
                               ("boxroom", 0, dict(batch=5, seconds_per_batch=0.5))])], 65536)
    print(f"dry run: campaign {dry['campaign']}, code tag {CODE_TAG}, {len(dry['units'])} units in 1 chunk, sessions of "
          f"{DRY_SESSION['work_seconds']} s of work; boxroom level 0 slowed to 0.5 s per 5 expansions, so that its "
          f"2,756 expansions (logs/test_gvgaisearch.log) take about 276 s and need a second session")
    print(f"written {write(dry, 'gvgaisearch_dryrun')}")

    with open(os.path.join(REPO, "logs", "draw_pilot.log"), encoding="utf-8") as f:
        line = next(ln for ln in f.read().splitlines() if ln.startswith("pilot ("))
    pilot = [x.strip() for x in line.split(":", 1)[1].split(",")]
    bound = {}
    with open(os.path.join(REPO, "logs", "engine_speed.log"), encoding="utf-8") as f:
        for ln in f:
            m = re.match(r"^(\S+)\s+(\d) \|.*\|\s+(\d+)(?: \(time cap\))?\s*$", ln.rstrip())
            if m and m.group(1) in pilot:
                bound[(m.group(1), int(m.group(2)))] = float(m.group(3))
    if len(bound) != 20:
        raise SystemExit(f"logs/engine_speed.log gives bounds for {len(bound)} of the 20 pilot levels")
    cap = BASE["workers"] * SESSION["work_seconds"]
    bins = []
    # every pilot level twice: under the registered (extended) key, and under the v0 key for the measurement only
    items = {(g, lv, form): t for (g, lv), t in bound.items() for form in ("extended", "v0")}
    for k in sorted(items, key=lambda x: (-items[x], x)):
        for b in bins:
            if b[0] + items[k] <= LOAD * cap:
                b[0] += items[k]
                b[1].append(k)
                break
        else:
            bins.append([items[k], [k]])
    spec = [(f"p-{i + 1:02d}", [(g, lv, None) if f == "extended" else (g, lv, dict(key_form="v0"), "-v0")
                                for g, lv, f in keys]) for i, (_l, keys) in enumerate(bins)]
    pil = manifest("gvgai-pilot-search", dict(BASE), SESSION, spec, 50_000_000)
    print(f"\npilot search: campaign {pil['campaign']}, code tag {CODE_TAG}, games {', '.join(pilot)}, "
          f"{len(pil['units'])} units; seen cap {SEEN_CAP:,}, time cap {BASE['time_cap_seconds']} s, "
          f"{BASE['memory_cap_bytes']} bytes per worker; key form {BASE['key_form']} on "
          f"{sum(1 for u in pil['units'] if 'params' not in u)} units, v0 on "
          f"{sum(1 for u in pil['units'] if u.get('params', {}).get('key_form') == 'v0')} (ids ending -v0, for the "
          f"measurement of the key's effect only)")
    for (load, keys), (cid, _s) in zip(bins, spec):
        print(f"chunk {cid}: {len(keys)} units, sum of the laptop bounds {load:.0f} worker-seconds ({load / cap:.0%} of a "
              f"session), four-worker finishing time by the bounds {lpt([items[k] for k in keys], 4):.0f} s of "
              f"{SESSION['work_seconds']} s")
    print("every unit is charged the bound of its level as logs/engine_speed.log measured it, under the v0 key; the "
          "extended key adds six numbers per sprite to each key, and its speed is not measured")
    print("the bounds are the laptop's (logs/engine_speed.log); a Kaggle session's speed is not known until it runs, "
          "and a chunk that overruns resumes from its checkpoint")
    print(f"written {write(pil, 'pilot_search')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
