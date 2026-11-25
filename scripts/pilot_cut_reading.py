"""
pilot_cut_reading.py -- what an agent unit cap would have cut on the pilot agent run of gate G1 (campaign
gvgai-pilot-agents, kind gvgaiagent; docs/PREREG.md, Section 8), for the draft entry on G3's ceiling and the
proposed rule on cut units (docs/DECISIONS_BEFORE_TAG.md, items 15 and 16).  The pilot games are development
data: nothing here is evidence for the claim, and every figure is EXPLORATORY.  Nothing is adopted here.

Reads only committed files: the manifest of the campaign (jobs/manifest.json, or its archive), the 160 rows under
runs/gvgai-pilot-agents/gvgaiagent/, every committed agent row of the kind gvgaiagent under runs/, and the game
lists of scripts/suite.py.
    1. Units cut at a cap of 1,860, 1,200 and 900 s, per agent.  A unit is counted as cut at cap c if the clock the
       cap stops reached c: I1's own play clock (agent_stats.play_seconds; study 1's adapter checks the cap
       against it), the row's seconds for N and R (their clock starts before the level is built, so it covers
       the row's seconds up to the setup before it, a fraction of a second) and for Rand (the unit's own clock).
       For each cut unit: whether the full run completed the level.  The rows do not record when each action was
       played, so a cut unit's actions at the cap are not known.
    2. Undetermined levels.  A cut unit that completed the level before the cut counts as completed; one that did
       not is open: had it played on, it might have.  With k = half the seeds (5 of the registered 10; 1 of the
       pilot's 2), a level's Y is 1 if at least k seeds completed, 0 if the completed seeds plus the open seeds
       are fewer than k, and undetermined otherwise.  On the pilot, where no unit was cut, "completed before the
       cut" is read as "completed in the full run", which is an upper bound: a completion recorded in the full run
       may have come after the cut.
    3. Three candidate void rules with a threshold of 10% (the excluded share of Section 7.4, rule 3), and what
       each would have done on the pilot at each cap: (a) an agent is void if more than 10% of its units are cut;
       (b) an agent is void if more than 10% of its levels are undetermined; (c) the study is void if more than
       10% of the units of N, R and I1 together are cut.
    4. G3's reading and what moves it: the cap from seed 1000 alone and from seed 1001 alone, the five longest
       units, and the cap with the longest one and two units left out.
    5. The confirmatory agent campaign at a cap of 1,800, 1,860 and 2,400 s, as a bound (every unit runs to its
       cap), in chunks and days, counted as logs/design_budget.log counts them: the 5,000 units of the four agents
       together, with its session length.
    6. Which confirmatory games have ever been played by an agent: every committed agent row of the kind
       gvgaiagent, by game.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\pilot_cut_reading.py > logs\\pilot_cut_reading.log
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import suite  # noqa: E402

CAMPAIGN = "gvgai-pilot-agents"
AGENTS = ("N", "R", "I1", "Rand")
EVIDENCE = ("N", "R", "I1")
CAPS = (1_860, 1_200, 900)
THRESHOLD = 0.10                  # docs/PREREG.md, Section 7.4, rule 3
WORK, WORKERS = 28_800, 4
SESSION = 32_460                  # a session with the loop's largest gap, at most (logs/design_budget.log, Section 2)
CONF_UNITS = 25 * 5 * 10          # per agent (logs/design_budget.log)


def g3(longest):
    return int(math.ceil(2 * longest / 60.0) * 60)


def clock(r):
    if r["agent"] == "I1" and r["agent_stats"].get("play_seconds") is not None:
        return float(r["agent_stats"]["play_seconds"])
    return float(r["seconds"])


def manifest():
    for p in (os.path.join(REPO, "jobs", "manifest.json"),
              os.path.join(REPO, "jobs", "archive", CAMPAIGN, "manifest.json")):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                m = json.load(f)
            if m["campaign"] == CAMPAIGN:
                return m
    raise SystemExit(f"no manifest of {CAMPAIGN}")


def level_states(rows, cap, k):
    """{(game, level): 'Y=1' | 'Y=0' | 'undetermined'} for one agent's rows at cap c."""
    by = {}
    for r in rows:
        by.setdefault((r["game"], int(r["level"])), []).append(r)
    out = {}
    for key, rs in sorted(by.items()):
        done = sum(1 for r in rs if r["outcome"]["level1_completed"])     # completed before the cut (upper bound)
        open_ = sum(1 for r in rs if clock(r) > cap and not r["outcome"]["level1_completed"])
        out[key] = "Y=1" if done >= k else "Y=0" if done + open_ < k else "undetermined"
    return out


def main():
    m = manifest()
    rows = []
    for u in m["units"]:
        with open(os.path.join(REPO, "runs", CAMPAIGN, "gvgaiagent", f"{u['unit_id']}.json"), encoding="utf-8") as f:
            rows.append(json.load(f))
    seeds = sorted({int(r["seed"]) for r in rows})
    k = len(seeds) // 2
    print(f"pilot agent run -- campaign {CAMPAIGN}, {len(rows)} rows, seeds {seeds}, budget {m['kinds']['gvgaiagent']['budget']}, "
          f"run cap {m['kinds']['gvgaiagent']['unit_seconds_cap']} s.  EXPLORATORY, development data (PREREG Section 8).")
    print(f"rows cut by the run's own cap: {sum(bool(r['cut_by_cap']) for r in rows)}")

    print("\n== 1. units that a cap would have cut (I1: its play clock; N, R, Rand: the row's seconds)")
    for cap in CAPS:
        cut = [r for r in rows if clock(r) > cap]
        per = ", ".join(f"{a} {sum(r['agent'] == a for r in cut)} of {sum(r['agent'] == a for r in rows)}" for a in AGENTS)
        print(f"  cap {cap} s: {len(cut)} of {len(rows)} units cut ({per})")
        for r in sorted(cut, key=lambda r: -clock(r)):
            print(f"    {r['agent']} {r['game']} level {r['level']} seed {r['seed']}: {clock(r):.3f} s; "
                  f"full run {'completed' if r['outcome']['level1_completed'] else 'did not complete'} the level")
    near = sorted(clock(r) for r in rows)
    print(f"  the five longest clocks: {', '.join(f'{x:.3f}' for x in near[-5:])} s")

    print(f"\n== 2. undetermined levels per agent (k = {k} of {len(seeds)} seeds; completion before the cut read as "
          "completion in the full run, an upper bound)")
    undet = {}
    for cap in CAPS:
        for a in AGENTS:
            st = level_states([r for r in rows if r["agent"] == a], cap, k)
            u = [key for key, s in st.items() if s == "undetermined"]
            undet[(cap, a)] = (len(u), len(st))
            print(f"  cap {cap} s, {a}: {len(u)} of {len(st)} levels undetermined"
                  + (": " + ", ".join(f"{g} {lv}" for g, lv in u) if u else ""))

    print(f"\n== 3. candidate void rules at {THRESHOLD:.0%}, on the pilot")
    for cap in CAPS:
        line = []
        for a in EVIDENCE:
            n = sum(r["agent"] == a for r in rows)
            c = sum(r["agent"] == a and clock(r) > cap for r in rows)
            line.append(f"{a} {c}/{n} = {c / n:.3f} {'VOID' if c / n > THRESHOLD else 'not void'}")
        print(f"  cap {cap} s, (a) share of units cut: " + "; ".join(line))
        line = []
        for a in EVIDENCE:
            u, n = undet[(cap, a)]
            line.append(f"{a} {u}/{n} = {u / n:.3f} {'VOID' if u / n > THRESHOLD else 'not void'}")
        print(f"  cap {cap} s, (b) share of levels undetermined: " + "; ".join(line))
        ev = [r for r in rows if r["agent"] in EVIDENCE]
        c = sum(clock(r) > cap for r in ev)
        print(f"  cap {cap} s, (c) N, R and I1 together: {c}/{len(ev)} = {c / len(ev):.3f} cut, study "
              f"{'VOID' if c / len(ev) > THRESHOLD else 'not void'}")

    print("\n== 4. G3's reading and what moves it (the row's seconds, as G3 reads them)")
    secs = sorted(rows, key=lambda r: -float(r["seconds"]))
    print(f"  all {len(rows)} units: longest {secs[0]['seconds']} s, G3's cap {g3(float(secs[0]['seconds']))} s")
    for s in seeds:
        top = max((r for r in rows if int(r["seed"]) == s), key=lambda r: float(r["seconds"]))
        print(f"  seed {s} alone: longest {top['seconds']} s ({top['agent']} {top['game']} level {top['level']}), "
              f"G3's cap {g3(float(top['seconds']))} s")
    print("  the five longest units: " + "; ".join(
        f"{r['agent']} {r['game']} {r['level']} s{r['seed']} {r['seconds']}" for r in secs[:5]))
    for drop in (1, 2):
        print(f"  the {drop} longest left out: longest {secs[drop]['seconds']} s, G3's cap {g3(float(secs[drop]['seconds']))} s")
    for a in AGENTS:
        pairs = {}
        for r in rows:
            if r["agent"] == a:
                pairs.setdefault((r["game"], r["level"]), []).append(float(r["seconds"]))
        q, key, xs = max((max(v) / min(v), key, sorted(v)) for key, v in pairs.items() if len(v) == 2 and min(v) > 0)
        print(f"  {a}: the two seeds differ most on {key[0]} level {key[1]}: {xs[0]} and {xs[1]} s, ratio {q:.2f}")

    print(f"\n== 5. the confirmatory agent campaign, bound (every unit runs to its cap): the {len(AGENTS) * CONF_UNITS} "
          "units of the four agents together, as logs/design_budget.log counts them")
    for cap in (1_800, 1_860, 2_400):
        per = WORKERS * (WORK // cap)
        chunks = math.ceil(len(AGENTS) * CONF_UNITS / per)
        print(f"  cap {cap} s: {per} units per chunk, {chunks} chunks at most, {chunks * SESSION / 86_400:.1f} days at most")

    print("\n== 6. confirmatory games ever played by an agent (every committed row of the kind gvgaiagent)")
    conf = set(suite.confirmatory())
    played = {}
    for p in glob.glob(os.path.join(REPO, "runs", "*", "gvgaiagent", "*.json")):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        played.setdefault(r["game"], set()).add(r["campaign"])
    print("  games with an agent row: " + "; ".join(f"{g} ({', '.join(sorted(c))})" for g, c in sorted(played.items())))
    hit = sorted(conf & set(played))
    print(f"  confirmatory games with an agent row: {len(hit)} of {len(conf)}" + (f": {', '.join(hit)}" if hit else ""))
    print(f"  confirmatory games never played by an agent: {len(conf) - len(hit)} of {len(conf)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
