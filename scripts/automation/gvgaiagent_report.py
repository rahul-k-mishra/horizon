"""
gvgaiagent_report.py -- the dry run of the kind gvgaiagent (rule R8), read from committed files only:
jobs/manifest.json (campaign gvgaiagent-dryrun) or, once archived, jobs/archive/gvgaiagent-dryrun/manifest.json; the
rows under runs/gvgaiagent-dryrun/gvgaiagent/; the session consoles under logs/kaggle/; logs/automation.log; the git
history; kaggle/kernel-metadata.json (the image asked for); and logs/test_gvgaiagent.log for the rows the same units
gave on the laptop.
Prints: per session its Kaggle kernel version, run nonce and outcome; per row its schema check, outcome, actions,
first level end, cut flag, seconds (and for I1 the seconds of its own play clock) and the sessions and image that built it, and how it compares with what is known
without Kaggle: allwin level 0 (every action a level end: 300 levels, first level end 1) and corridor level 1 (no
level end) by hand, corridor level 0 from the laptop's rows, and the units with ids ending "-cap" against their
120 s cap; the commits that wrote the chunk's checkpoint; the runner's lines of every session console; and the
automation.log lines of the campaign.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\gvgaiagent_report.py > logs\\gvgaiagent_dryrun_report.log
"""
from __future__ import annotations

import collections
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from common import read_json  # noqa: E402
from schema import validate_agent_row  # noqa: E402

CAMPAIGN = "gvgaiagent-dryrun"
SLACK = 3.0     # seconds over the cap allowed, as in scripts/automation/test_gvgaiagent.py, part 3


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout


def manifest():
    for p in (os.path.join(REPO, "jobs", "manifest.json"),
              os.path.join(REPO, "jobs", "archive", CAMPAIGN, "manifest.json")):
        if os.path.exists(p):
            m = read_json(p)
            if m["campaign"] == CAMPAIGN:
                return m, os.path.relpath(p, REPO).replace("\\", "/")
    raise SystemExit(f"no manifest of {CAMPAIGN}")


def laptop_rows():
    """agent -> (levels, first level end) of corridor level 0, budget 300, seed 1000: logs/test_gvgaiagent.log, part 2."""
    out = {}
    with open(os.path.join(REPO, "logs", "test_gvgaiagent.log"), encoding="utf-8") as f:
        for line in f:
            mm = re.match(r"\s+g-01-(\w+)-corridor-l0-s1000: whole level1_completed \w+, levels (\d+), actions 300, "
                          r"first level end (\w+)", line)
            if mm:
                out[mm.group(1)] = (int(mm.group(2)), None if mm.group(3) == "None" else int(mm.group(3)))
    return out


def main():
    m, mpath = manifest()
    k = m["kinds"]["gvgaiagent"]
    asked = read_json(os.path.join(REPO, "kaggle", "kernel-metadata.json")).get("docker_image")
    print(f"gvgaiagent dry run -- campaign {m['campaign']} ({mpath}), code {m['code_tag']}, state commit "
          f"{git('rev-parse', '--short', 'HEAD').strip()}; kind params {json.dumps(k, sort_keys=True)}; "
          f"session {json.dumps(m['session'], sort_keys=True)}")
    print(f"image asked for in kaggle/kernel-metadata.json: {asked}")
    print("\n== sessions")
    for c in m["chunks"]:
        print(f"chunk {c['chunk_id']} {c['status']}, attempts {c['attempts']}, failures {c['failures']}")
        for s in c["sessions"]:
            print(f"   kernel version {s.get('kernel_version')}  run {s.get('run_nonce')}  outcome {s.get('outcome')}  "
                  f"units done this session {len(s.get('units_done_this_session') or [])}  ended {s.get('ended_at')}")
    lap = laptop_rows()
    print(f"\nlaptop rows of corridor level 0 (logs/test_gvgaiagent.log, part 2), levels and first level end: {lap}")
    print("\n== rows")
    base = os.path.join(REPO, "runs", m["campaign"], "gvgaiagent")
    tally = collections.Counter()
    images = collections.Counter()
    nonces = collections.Counter()
    capped_seconds = []
    i1_outside = []
    for u in m["units"]:
        p = os.path.join(base, f"{u['unit_id']}.json")
        if not os.path.exists(p):
            print(f"{u['unit_id']}: no row")
            tally["missing"] += 1
            continue
        r = read_json(p)
        errs = validate_agent_row(r)
        tally["valid" if not errs and r["schema"] == "horizon.agent.v2" else "invalid"] += 1
        got = (r["agent_stats"]["actions"], r["outcome"]["levels"], r["agent_stats"]["first_level_end"],
               r["outcome"]["level1_completed"], r["cut_by_cap"])
        for s in r["sessions"]:
            images[(s.get("kaggle_env") or {}).get("KAGGLE_DOCKER_IMAGE")] += 1
            nonces[s["run_nonce"]] += 1
        print(f"{u['unit_id']}: schema {r['schema']} {'ok' if not errs else errs}; level {r['level']}; actions {got[0]}, "
              f"levels {got[1]}, first level end {got[2]}, completed {got[3]}, cut {got[4]}; seconds {r['seconds']}; "
              f"run {', '.join(s['run_nonce'] for s in r['sessions'])}")
        if u["agent"] == "I1":
            ps = r["agent_stats"].get("play_seconds")
            if ps is not None:
                print(f"   I1's own play clock (study 1's timer, which the cap stops): {ps} s; seconds outside it "
                      f"(setup and teardown in the unit): {round(r['seconds'] - float(ps), 3)}")
                i1_outside.append((round(r["seconds"] - float(ps), 3), u["unit_id"]))
        if u["unit_id"].endswith("-cap"):
            cap = float(u["params"]["unit_seconds_cap"])
            ok = got[4] and got[1] == 0 and got[0] < int(u["params"]["budget"]) and r["seconds"] <= cap + SLACK
            capped_seconds.append(r["seconds"])
            print(f"   expected: stopped by its {cap:.0f} s cap, cut, 0 levels, seconds at most {cap + SLACK:.0f}: "
                  f"{'yes' if ok else 'NO'}")
            tally["cap as expected" if ok else "cap NOT as expected"] += 1
        elif u["game"] == "allwin":
            ok = got == (300, 300, 1, True, False)
            print(f"   by hand: actions 300, levels 300, first level end 1, completed, not cut: {'same' if ok else 'DIFFERENT'}")
            tally["hand same" if ok else "hand DIFFERENT"] += 1
        elif u["game"] == "corridor" and int(u["level"]) == 1:
            ok = got == (300, 0, None, False, False)
            print(f"   by hand: actions 300, levels 0, no level end, not completed, not cut: {'same' if ok else 'DIFFERENT'}")
            tally["hand same" if ok else "hand DIFFERENT"] += 1
        else:
            ref = lap.get(u["agent"])
            ok = ref is not None and (got[1], got[2]) == ref and got[0] == 300
            print(f"   laptop: levels {ref[0] if ref else None}, first level end {ref[1] if ref else None}, "
                  f"actions 300: {'same' if ok else 'DIFFERENT'}")
            tally["laptop same" if ok else "laptop DIFFERENT"] += 1
    print("\n== totals")
    print(f"units {len(m['units'])}: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    if capped_seconds:
        print(f"capped units: seconds from {min(capped_seconds)} to {max(capped_seconds)}")
    if i1_outside:
        print("I1 seconds outside its own play clock, largest first: "
              + ", ".join(f"{u} {x}" for x, u in sorted(i1_outside, reverse=True)))
    print(f"rows by session run: {dict(sorted(nonces.items()))}")
    print("images named by the rows' session entries:")
    for img, n in images.most_common():
        print(f"   {n:4d}  {img}  {'(the image asked for)' if img == asked else '(NOT the image asked for)'}")
    print("\n== checkpoint commits")
    for c in m["chunks"]:
        path = f"runs/{m['campaign']}/checkpoints/{c['chunk_id']}/checkpoint.json"
        for line in git("log", "--reverse", "--format=%h %cI %s", "--", path).strip().splitlines():
            print(line)
            try:
                ck = json.loads(git("show", f"{line.split()[0]}:{path}"))
            except subprocess.CalledProcessError:
                print("   (checkpoint removed: the chunk is done)")
                continue
            print(f"   seq {ck['seq']}, run {ck['run_nonce']}, units done {len(ck['units_done'])}")
    print("\n== runner lines of every session console (logs/kaggle/)")
    names = [n for n in os.listdir(os.path.join(REPO, "logs", "kaggle")) if n.startswith("a-01__")]
    for name in sorted(names, key=lambda n: int(re.search(r"__v(\d+)", n).group(1)) if re.search(r"__v(\d+)", n) else 0):
        print(f"-- {name}")
        with open(os.path.join(REPO, "logs", "kaggle", name), encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("[") or line.startswith("code commit") or line.startswith("state commit"):
                    print("   " + line.rstrip()[:240])
    print("\n== automation.log lines of this campaign")
    with open(os.path.join(REPO, "logs", "automation.log"), encoding="utf-8") as f:
        for line in f:
            if "a-01" in line or CAMPAIGN in line:
                print(line.rstrip()[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
