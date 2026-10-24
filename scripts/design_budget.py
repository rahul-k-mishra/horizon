"""
design_budget.py -- the session arithmetic and the compute budget of docs/DESIGN.md (Sections 9 and 10).

Reads only committed files: docs/design/params_v0.json (the design values) and docs/design/vgdl_scan.json
(the number of deterministic GVGAI games and their level files, from scripts/vgdl_scan.py).  Runs no
experiment.  Prints:
    1. the latest end of a session after the notebook starts, and its margin to the commonly stated
       12-hour limit and to the 9-hour design limit;
    2. per stage (development, pilot, confirmatory) and job kind, the units, the units per chunk and the
       chunks, as upper bounds from the registered caps, and the wall-clock days if every chunk used its
       whole session and the loop's largest gap;
    3. the same for the agent kind at each unit cap in params agent_unit_cap_seconds_shown, since the
       registered cap is set by the pilot (docs/PREREG.md, Section 9);
    4. what excluding within-game pairs from both AUROCs costs (docs/PREREG.md, Section 7.2): the most
       within-game pairs a game of 5 levels can hold, and their largest share of all pairs when the share
       of completed units is at the edges of the void band and at one half.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\design_budget.py > logs\\design_budget.log
"""
from __future__ import annotations

import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def hm(s):
    s = int(round(s))
    return f"{s} s ({s // 3600} h {s % 3600 // 60:02d} min)"


def main():
    p = json.load(open(os.path.join(REPO, "docs", "design", "params_v0.json"), encoding="utf-8"))
    scan = json.load(open(os.path.join(REPO, "docs", "design", "vgdl_scan.json"), encoding="utf-8"))
    s = p["session"]
    print("== 1. the session")
    end = s["startup_allowance_seconds"] + s["work_seconds"] + s["search_batch_seconds_max"] + s["checkpoint_reserve_seconds"]
    print(f"startup allowance {s['startup_allowance_seconds']} + work {s['work_seconds']} + one search batch "
          f"{s['search_batch_seconds_max']} + checkpoint reserve {s['checkpoint_reserve_seconds']} = latest end {hm(end)}")
    for name, lim in (("commonly stated limit", s["commonly_stated_limit_seconds"]), ("design limit", s["design_limit_seconds"])):
        print(f"{name} {hm(lim)}: margin {hm(lim - end)}; {'inside' if end < lim else 'NOT inside'}")
    print(f"project rule R4 (every chunk inside 11 h = 39600 s): {'yes' if end < 39600 else 'NO'}")
    w = p["machine"]["workers"]
    mem = p["machine"]["search_memory_cap_bytes_per_worker"]
    print(f"search memory: {w} workers x {mem} bytes = {w * mem} bytes, against {p['machine']['ram_bytes']} bytes "
          f"({'inside' if w * mem < p['machine']['ram_bytes'] else 'NOT inside'})")

    det = [g for g in scan["games"] if g["deterministic"]]
    lv = p["suite"]["levels_per_game_used"]
    n_games = len(det)
    n_pilot = p["suite"]["pilot_games"]
    n_conf = n_games - n_pilot
    levels = lambda n: n * lv  # noqa: E731
    agents = p["agents"]
    seeds = p["seeds"]
    cap_s = p["search"]["time_cap_seconds"]
    capacity = w * s["work_seconds"]
    per_session = s["startup_allowance_seconds"] + s["work_seconds"] + s["search_batch_seconds_max"] + \
        s["checkpoint_reserve_seconds"] + s["loop_gap_seconds_max"]
    print(f"\n== 2. the budget (one session at a time; a chunk holds work for {w} workers x {s['work_seconds']} s "
          f"= {capacity} worker-seconds; a session with the loop's largest gap takes at most {hm(per_session)})")
    print(f"deterministic GVGAI games {n_games} (docs/design/vgdl_scan.json), {lv} levels each; pilot {n_pilot} games, "
          f"confirmatory {n_conf} games = {levels(n_conf)} level units")
    rows = []

    def stage(label, units, cap):
        per = capacity // cap
        chunks = math.ceil(units / per)
        rows.append((label, units, cap, per, chunks))
        print(f"{label}: {units} units, cap {cap} s, {per} units per chunk, {chunks} chunks at most, "
              f"{chunks * per_session / 86400:.1f} days at most")
        return chunks

    dev = stage("development search (stage D, kind devsearch), MiniGrid/BabyAI macro, one unit per (game, seed)",
                p["development"]["minigrid_games"] * p["development"]["seeds"], p["development"]["search_time_cap_seconds"])
    pil_s = stage("pilot search", levels(n_pilot), cap_s)
    pil_a = stage("pilot agents (cap at its largest)", levels(n_pilot) * len(agents) * p["pilot"]["seeds"], p["agent_unit_cap_seconds_max"])
    con_s = stage("confirmatory search", levels(n_conf), cap_s)
    print("\n== 3. confirmatory agents, by the unit cap the pilot sets")
    for cap in p["agent_unit_cap_seconds_shown"]:
        con_a = stage(f"confirmatory agents, cap {cap} s", levels(n_conf) * len(agents) * seeds, cap)
        tot = dev + pil_s + pil_a + con_s + con_a
        print(f"   all stages with this cap: {tot} chunks at most, {tot * per_session / 86400:.1f} days at most")

    print("\n== 4. between-game pairs")
    units = levels(n_conf)
    within_max = (lv // 2) * (lv - lv // 2)
    print(f"a game of {lv} levels holds at most {within_max} (completed, not completed) pairs of its own; "
          f"{n_conf} games at most {n_conf * within_max}")
    for share in (0.10, 0.50, 0.90):
        n1 = round(units * share)
        total = n1 * (units - n1)
        print(f"completed share {share:.2f} ({n1} of {units} units): {total} pairs in all; within-game pairs removed "
              f"at most {n_conf * within_max}, {100 * n_conf * within_max / total:.1f}% of them")
    print("the bootstrap still resamples the games with replacement; pairs between two draws of the same game are "
          "within-game and excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
