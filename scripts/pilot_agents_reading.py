"""
pilot_agents_reading.py -- reads the pilot agent run of gate G1 (campaign gvgai-pilot-agents, kind gvgaiagent;
docs/PREREG.md, Section 8; scripts/make_pilot_agents_manifest.py) for gate G3 and item 15 of
docs/DECISIONS_BEFORE_TAG.md.  The pilot games are development data: nothing here is evidence for the claim, and
every figure is EXPLORATORY.  Nothing is adopted here; the cap, G3's ceiling and the agent family are the author's.

Reads only committed files: the manifest (jobs/manifest.json, or jobs/archive/gvgai-pilot-agents/manifest.json
once archived), the rows under runs/gvgai-pilot-agents/gvgaiagent/, and the loop's record in the manifest.
    1. G1: per agent, the units with a row, the units that played the full 20,000 actions, the units cut by the run's
       own cap, and the chunks' failures (an error in a unit fails its session; the loop counts it).
    2. G3: per agent, the longest and median seconds of a unit of 20,000 actions (the row's "seconds", the unit's
       wall-clock time), the level and seed of the longest, and the cap "twice the longest pilot time for 20,000
       actions, rounded up to a whole minute"; the same over all agents, which is G3's cap; and whether each is at
       most 1,800 s.
    3. Time outside the agent's own play clock.  I1: the row's seconds less agent_stats.play_seconds, study 1's play
       timer, which starts after the level and I1 are built (study 1, scripts/e1_rudakov_adapter.py); N and R:
       their clock (study 1, scripts/g_agent.py, play, t0) starts before the level is built, so their rows hold no
       separate play time and their cap already covers setup; Rand: the unit's own clock.
    4. Item 15's options with these times: the confirmatory agent campaign (25 games x 5 levels x 10 seeds = 1,250
       units per agent) under each, as a bound (every unit runs to its cap; the runner starts a unit only if its cap
       fits before the work deadline: 4 workers x floor(28,800 / cap) units per chunk) and as a projection (each
       agent's pilot median seconds per unit, 1,250 units, on 4 workers x 28,800 s of work per chunk).
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\pilot_agents_reading.py > logs\\pilot_agents_reading.log
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
from schema import validate_agent_row  # noqa: E402

CAMPAIGN = "gvgai-pilot-agents"
AGENTS = ("N", "R", "I1", "Rand")
BUDGET = 20_000
CEILING = 1_800
WORK, WORKERS = 28_800, 4
CONF_UNITS = 25 * 5 * 10          # per agent: docs/PREREG.md, Sections 4 and 7 (logs/design_budget.log)


def g3(longest):
    return int(math.ceil(2 * longest / 60.0) * 60)


def per_chunk(cap):
    return WORKERS * (WORK // cap)


def manifest():
    for p in (os.path.join(REPO, "jobs", "manifest.json"),
              os.path.join(REPO, "jobs", "archive", CAMPAIGN, "manifest.json")):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                m = json.load(f)
            if m["campaign"] == CAMPAIGN:
                return m, os.path.relpath(p, REPO).replace("\\", "/")
    raise SystemExit(f"no manifest of {CAMPAIGN}")


def main():
    m, mpath = manifest()
    k = m["kinds"]["gvgaiagent"]
    print(f"pilot agent run -- campaign {CAMPAIGN} ({mpath}), code {m['code_tag']}; budget {k['budget']}, run cap "
          f"{k['unit_seconds_cap']} s, workers {k['workers']}.  EXPLORATORY, development data (PREREG Section 8).")
    rows = {}
    for u in m["units"]:
        p = os.path.join(REPO, "runs", CAMPAIGN, "gvgaiagent", f"{u['unit_id']}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                rows[u["unit_id"]] = json.load(f)
    print("\n== 1. G1: the agents play 20,000 actions on 2 seeds of every pilot unit without an error")
    for c in m["chunks"]:
        print(f"chunk {c['chunk_id']}: {c['status']}, attempts {c['attempts']}, failures {c['failures']}, sessions "
              f"{len(c['sessions'])}: " + "; ".join(f"v{s.get('kernel_version')} {s.get('outcome')}" for s in c["sessions"]))
    bad_schema = [uid for uid, r in rows.items() if validate_agent_row(r) or r.get("schema") != "horizon.agent.v2"]
    print(f"rows {len(rows)} of {len(m['units'])}; rows failing horizon.agent.v2: {bad_schema or 'none'}")
    full = {}
    for a in AGENTS:
        us = [u for u in m["units"] if u["agent"] == a]
        rs = [rows[u["unit_id"]] for u in us if u["unit_id"] in rows]
        f20 = [r for r in rs if r["agent_stats"]["actions"] == BUDGET and not r["cut_by_cap"]]
        cut = [r for r in rs if r["cut_by_cap"]]
        full[a] = f20
        print(f"  {a}: units {len(us)}, rows {len(rs)}, played 20,000 actions {len(f20)}, short of 20,000 actions (cut_by_cap, by the run's cap or otherwise) {len(cut)}"
              + (": " + ", ".join(f"{r['unit_id']} ({r['agent_stats']['actions']} actions, {r['seconds']} s)" for r in cut) if cut else ""))
    print("\n== 2. G3: seconds of a unit of 20,000 actions (the row's wall-clock seconds)")
    longest_all = 0.0
    med = {}
    for a in AGENTS:
        rs = full[a]
        if not rs:
            print(f"  {a}: no unit of 20,000 actions")
            continue
        top = max(rs, key=lambda r: r["seconds"])
        med[a] = statistics.median(r["seconds"] for r in rs)
        longest_all = max(longest_all, top["seconds"])
        print(f"  {a}: {len(rs)} units; median {med[a]:.1f} s, longest {top['seconds']} s ({top['game']} level "
              f"{top['level']}, seed {top['seed']}); G3's rule on it: {g3(top['seconds'])} s, "
              f"{'at most' if g3(top['seconds']) <= CEILING else 'ABOVE'} {CEILING} s")
    cut_any = sum(r["cut_by_cap"] for r in rows.values())
    complete = len(rows) == len(m["units"]) and not cut_any
    print(f"  all agents: longest {longest_all} s; G3's cap {g3(longest_all)} s, "
          f"{'at most' if g3(longest_all) <= CEILING else 'ABOVE'} the ceiling of {CEILING} s"
          + ("" if complete else "  (the run is not complete: rows missing or units cut; this is not G3's reading)"))
    print("  per level, the longest of the two seeds, seconds (N / R / I1 / Rand):")
    for g in sorted({u["game"] for u in m["units"]}):
        for lv in range(5):
            cells = []
            for a in AGENTS:
                xs = [r["seconds"] for r in rows.values() if r["agent"] == a and r["game"] == g and r["level"] == lv]
                cells.append(f"{max(xs):.1f}" if xs else "-")
            print(f"    {g} {lv}: " + " / ".join(cells))
    print("\n== 3. time outside the agent's own play clock")
    out = sorted(((round(r["seconds"] - float(r["agent_stats"]["play_seconds"]), 3), r["unit_id"], r["seconds"])
                  for r in rows.values() if r["agent"] == "I1" and r["agent_stats"].get("play_seconds") is not None),
                 reverse=True)
    if out:
        xs = [x for x, _, _ in out]
        print(f"  I1: {len(out)} rows; seconds outside its play clock: median {statistics.median(xs):.3f}, largest "
              f"{xs[0]} ({out[0][1]}, unit {out[0][2]} s), smallest {xs[-1]}; as a share of the unit's seconds, "
              f"largest {max(x / s for x, _, s in out if s):.4f}")
        print("  I1, the ten largest: " + ", ".join(f"{u} {x}" for x, u, _ in out[:10]))
    print("  N and R: their clock starts before the level is built (study 1, g_agent.play), so the rows hold no "
          "separate play time; Rand: the unit's own clock")
    print("\n== 4. item 15's options with these times (EXPLORATORY; nothing adopted)")
    if not complete:
        print("  not computed: the run is not complete")
        return 0
    tops = {a: max(r["seconds"] for r in full[a]) for a in AGENTS}
    caps = {a: g3(tops[a]) for a in AGENTS}
    cap_all = g3(longest_all)

    def cost(cap_of):
        bound = sum(math.ceil(CONF_UNITS / per_chunk(cap_of[a])) for a in AGENTS) if all(
            cap_of[a] <= WORK for a in AGENTS) else None
        proj = sum(CONF_UNITS * med[a] for a in AGENTS) / (WORKERS * WORK)
        return bound, proj
    one = {a: cap_all for a in AGENTS}
    b, p = cost(one)
    print(f"  (i) keep G3 as registered: one cap of {cap_all} s for every agent; G3 "
          f"{'passes' if cap_all <= CEILING else 'FAILS and the study is Void'}"
          + (f"; the confirmatory agent campaign at most {b} chunks (bound), about {p:.1f} chunks of work (projection)" if cap_all <= CEILING else ""))
    for ceil in (2_400, 3_600):
        print(f"  (ii) raise G3's ceiling to {ceil} s: the same cap of {cap_all} s "
              f"{'passes' if cap_all <= ceil else 'still FAILS'}"
              + (f"; at most {b} chunks (bound), about {p:.1f} (projection)" if cap_all <= ceil else ""))
    b3, p3 = cost(caps)
    print(f"  (iii) one cap per agent by the same rule: " + ", ".join(f"{a} {caps[a]} s" for a in AGENTS)
          + f"; with the ceiling of {CEILING} s applied to each: "
          + ", ".join(f"{a} {'passes' if caps[a] <= CEILING else 'FAILS'}" for a in AGENTS)
          + f"; at most {b3} chunks (bound), about {p3:.1f} (projection)")
    print("  (iv) run G1's pilot agents before the tag: this run; the choice among (i) to (iii) is made with these "
          "times known")
    return 0


if __name__ == "__main__":
    sys.exit(main())
