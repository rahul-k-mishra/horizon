"""
make_pilot_agents_manifest.py -- writes jobs/pilot_agents/manifest.json, the pilot agent run of gate G1
(docs/PREREG.md, Section 8): N, R, I1 and Rand each play 20,000 actions on 2 seeds of every pilot unit, kind
gvgaiagent, through the loop.  Run before the tag at the author's direction of 25 November 2026, as the pilot
search was (decision 10); see docs/STATE.md, amendment (ak).  It is not the loop's manifest until it is copied to
jobs/manifest.json.

    games     the 4 pilot games of scripts/suite.py pilot() (bait, labyrinthdual, rivers, watergame), levels 0 to 4,
              the 20 pilot units of Section 8; GVGAI's vendored games (no games_dir).
    agents    N, R, I1, Rand (Section 3).
    seeds     1000 and 1001: Section 8 says "2 seeds" and Section 3 registers the agent seeds as 1000 to 1009, so
              the first two of them.
    budget    20,000 actions (Sections 7 and 8).
    cap       7,200 s per unit.  The cap of this run is not the registered agent unit cap, which G3 sets from this
              run's times; it is set high so that no unit is cut before 20,000 actions (G1 asks for 20,000 actions,
              and G3 reads the time for 20,000).  Any unit near it already decides G3 (its ceiling is 1,800 s, so a
              time above 900 s fails it).  The runner starts a unit only if its cap fits before the session's work
              deadline (scripts/automation/runner.py, run_agent_pool).
    chunks    2 of 80 units, each all four agents on two pilot games, so that each holds one kind and a mix of slow
              and fast units (the loop runs one session at a time, docs/AUTOMATION.md).
    session   as the pilot search: work 28,800 s, checkpoint reserve 900 s, platform limit 32,400 s, 4 workers.
    code      CODE_REF, the full hash of the commit of the kind's code and pins (no tag is cut before prereg-v1).

It also prints the planning figures asked for before the launch: the worst-case bound, in which every unit runs to
its cap, and a projection.  The projection is EXPLORATORY, not a pilot time: the laptop's seconds for 2,000
actions on bait level 0 (logs/test_agents_gvgai.log), taken as linear in actions, divided by the median
Kaggle/laptop ratio of the GVGAI engine on the pilot search (logs/pilot_reading.log, 0.388).  How fast the agents'
own Python runs on Kaggle was measured only on a synthetic level, where two sessions differed by a factor near two
(logs/gvgaiagent_dryrun_report.log); I1 may also grow faster than linearly in actions.
And it checks that the pilot games enter no confirmatory analysis: none is among scripts/suite.py confirmatory(),
and the campaign is not scripts/analyze_horizon.py's CONFIRMATORY_CAMPAIGN, the only campaign that script reads.
Reads only committed files.  Runs no game.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\make_pilot_agents_manifest.py > logs\\make_pilot_agents_manifest.log
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "automation"))
sys.dont_write_bytecode = True
import suite  # noqa: E402
from common import chunk_entry_hash, check_manifest  # noqa: E402

CODE_REF = "e296372656d9cd7f257e0aa46db8795872e3c346"   # the kind's code and pins as of 25 November 2026 (checked in main)
CAMPAIGN = "gvgai-pilot-agents"
AGENTS = ("N", "R", "I1", "Rand")
SEEDS = (1000, 1001)
BUDGET = 20_000
CAP = 7_200
KIND = dict(agent_impl="gvgai", budget=BUDGET, unit_seconds_cap=CAP, workers=4)
SESSION = dict(work_seconds=28_800, checkpoint_reserve_seconds=900, platform_limit_seconds=32_400)
STARTUP, GAP = 900, 1_800      # docs/design/params_v0.json: startup allowance and the loop's largest gap
RATIO = 0.388                  # logs/pilot_reading.log, Section 5, median Kaggle/laptop ratio


def laptop_2000():
    out = {}
    with open(os.path.join(REPO, "logs", "test_agents_gvgai.log"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s+(N|R|I1|Rand): level1_completed \w+, levels \d+, actions 2000, .* ([\d.]+) s$", line)
            if m:
                out[m.group(1)] = float(m.group(2))
    with open(os.path.join(REPO, "logs", "pilot_reading.log"), encoding="utf-8") as f:
        if f"median {RATIO}," not in f.read():
            raise SystemExit("logs/pilot_reading.log does not give the median ratio used here")
    return out


def main():
    import subprocess  # noqa: PLC0415
    full = subprocess.run(["git", "rev-parse", CODE_REF], cwd=REPO, capture_output=True, text=True)
    if full.returncode != 0 or full.stdout.strip() != CODE_REF:
        raise SystemExit(f"CODE_REF {CODE_REF} is not a commit of this repository")
    pilot = suite.pilot()
    conf = suite.confirmatory()
    games_by_chunk = {"g1-01": pilot[:2], "g1-02": pilot[2:]}
    units = []
    for cid, games in games_by_chunk.items():
        for g in games:
            for lv in suite.LEVELS:
                for seed in SEEDS:
                    for a in AGENTS:
                        units.append(dict(unit_id=f"{cid}-{a}-{g}-l{lv}-s{seed}", chunk_id=cid, kind="gvgaiagent",
                                          suite="gvgai", game=g, level=lv, agent=a, seed=seed, status="pending"))
    m = dict(campaign=CAMPAIGN, code_tag=CODE_REF, repository="rahul-k-mishra/horizon", kernel_slug="horizon-runner",
             max_failures=3, payload_commit_limit_bytes=50_000_000, session=SESSION, kinds=dict(gvgaiagent=KIND),
             chunks=[dict(chunk_id=c, kind="gvgaiagent", status="pending", attempts=0, failures=0, sessions=[])
                     for c in games_by_chunk],
             units=units)
    errs = check_manifest(m)
    if errs:
        raise SystemExit(f"manifest check failed: {errs}")
    d = os.path.join(REPO, "jobs", "pilot_agents")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1, sort_keys=True)

    print(f"campaign {CAMPAIGN}, kind gvgaiagent, code {CODE_REF}")
    print(f"pilot games (scripts/suite.py pilot()): {pilot}; levels {list(suite.LEVELS)}; {len(pilot) * len(suite.LEVELS)} pilot units")
    print(f"agents {list(AGENTS)}, seeds {list(SEEDS)}, budget {BUDGET} actions, cap {CAP} s per unit")
    print(f"units: {len(units)} = {len(pilot) * len(suite.LEVELS)} levels x {len(AGENTS)} agents x {len(SEEDS)} seeds")
    for cid, games in games_by_chunk.items():
        n = sum(u["chunk_id"] == cid for u in units)
        print(f"chunk {cid}: games {games}, {n} units, entry hash {chunk_entry_hash(m, cid)}")
    print(f"session: {SESSION}; workers {KIND['workers']}")

    print("\n== the pilot games enter no confirmatory analysis")
    both = sorted(set(pilot) & set(conf))
    print(f"pilot games among scripts/suite.py confirmatory() ({len(conf)} games): {both or 'none'}")
    src = open(os.path.join(REPO, "scripts", "analyze_horizon.py"), encoding="utf-8").read()
    cc = re.search(r'^CONFIRMATORY_CAMPAIGN = "([^"]+)"', src, re.M).group(1)
    print(f"scripts/analyze_horizon.py reads only campaign {cc!r} and only confirmatory games; this campaign is "
          f"{CAMPAIGN!r}: {'different' if cc != CAMPAIGN else 'THE SAME'}")
    if both or cc == CAMPAIGN:
        raise SystemExit("a pilot game or this campaign could enter the confirmatory analysis")

    print("\n== wall-clock, the worst-case bound: every unit runs to its cap")
    rounds = (SESSION["work_seconds"] - CAP) // CAP + 1          # a unit starts while its cap fits before the deadline
    per_session = KIND["workers"] * rounds
    sessions = sum(math.ceil(sum(u["chunk_id"] == c for u in units) / per_session) for c in games_by_chunk)
    span = STARTUP + SESSION["work_seconds"] + SESSION["checkpoint_reserve_seconds"] + GAP
    print(f"a worker starts at most {rounds} capped units in a session's {SESSION['work_seconds']} s of work: "
          f"{per_session} units per session; {sessions} sessions for the two chunks; at most {span} s each with startup, "
          f"checkpoint reserve and the loop's largest gap: {sessions * span / 3600:.1f} h ({sessions * span / 86400:.2f} days)")

    print("\n== wall-clock, a projection (EXPLORATORY; not a pilot time)")
    lap = laptop_2000()
    per_unit = {a: lap[a] * BUDGET / 2000 / RATIO for a in AGENTS}
    for a in AGENTS:
        print(f"  {a}: laptop {lap[a]} s for 2,000 actions on bait level 0 (logs/test_agents_gvgai.log); "
              f"x {BUDGET // 2000} / {RATIO} = {per_unit[a]:.0f} s per unit")
    tot_h = 0.0
    for c in games_by_chunk:
        work = sum(per_unit[u["agent"]] for u in units if u["chunk_id"] == c)
        wall = work / KIND["workers"]
        tot_h += (STARTUP + wall + GAP) / 3600
        print(f"  chunk {c}: {work:.0f} worker-seconds, {wall:.0f} s on {KIND['workers']} workers "
              f"({'fits' if wall <= SESSION['work_seconds'] else 'does NOT fit'} one session's {SESSION['work_seconds']} s of work)")
    print(f"  both chunks, with startup and the loop's largest gap each: about {tot_h:.1f} h, if a Kaggle slot is free")
    print(f"  the longest projected unit, I1, {per_unit['I1']:.0f} s, is {per_unit['I1'] / CAP:.2f} of the cap")
    print("written: jobs/pilot_agents/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
