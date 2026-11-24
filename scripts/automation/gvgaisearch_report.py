"""
gvgaisearch_report.py -- the dry run of the kind gvgaisearch (rule R8), read from committed files only:
jobs/manifest.json (campaign gvgaisearch-dryrun, code tag automation-v5), jobs/archive/gvgaisearch-dryrun-v4/manifest.json
(the attempt under automation-v4 that failed), the rows under runs/gvgaisearch-dryrun/gvgaisearch/, the session
consoles under logs/kaggle/, logs/automation.log, the git history, and logs/test_gvgaisearch.log for the counts the
same levels gave on the laptop.
Prints: per attempt and session its Kaggle kernel version, run nonce and outcome; per row its schema check, counts,
seconds and the sessions that built it, and whether its counts equal the laptop's; the commits that wrote the chunk's
checkpoint; the runner's lines of every session console; and the automation.log lines of the campaign.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\gvgaisearch_report.py > logs\\gvgaisearch_dryrun_report.log
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from common import load_manifest, read_json  # noqa: E402
from schema import validate_search_row  # noqa: E402

KEYS = ("states_seen", "states_expanded", "solution_length", "seen_at_first_win", "expanded_at_first_win")


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout


def laptop_counts():
    """(game, level) -> the five counts of logs/test_gvgaisearch.log, part 2 (corridor, boxroom level 0) and part 1
    (corridor level 1, boxed in)."""
    out = {}
    with open(os.path.join(REPO, "logs", "test_gvgaisearch.log"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"2\. (\w+): search (\(.*?\)), independent", line)
            if m:
                out[(m.group(1), 0)] = dict(zip(KEYS, ast.literal_eval(m.group(2))))
            m = re.match(r"1\. corridor level 1 \(boxed in\): complete (\d+) (\d+) (\S+)", line)
            if m:
                out[("corridor", 1)] = dict(states_seen=int(m.group(1)), states_expanded=int(m.group(2)),
                                            solution_length=None if m.group(3) == "None" else int(m.group(3)))
    return out


def sessions(m, label):
    for c in m["chunks"]:
        print(f"{label}: chunk {c['chunk_id']} {c['status']}, attempts {c['attempts']}, failures {c['failures']}")
        for s in c["sessions"]:
            print(f"   kernel version {s.get('kernel_version')}  run {s.get('run_nonce')}  outcome {s.get('outcome')}  "
                  f"units done this session {s.get('units_done_this_session')}  ended {s.get('ended_at')}")


def main():
    m = load_manifest(REPO)
    k = m["kinds"]["gvgaisearch"]
    print(f"gvgaisearch dry run -- campaign {m['campaign']}, code tag {m['code_tag']} at "
          f"{git('rev-parse', '--short', m['code_tag'] + '^{commit}').strip()}, state commit "
          f"{git('rev-parse', '--short', 'HEAD').strip()}, workers {k['workers']}, key form {k['key_form']}, "
          f"session work {m['session']['work_seconds']} s")
    print("\n== sessions")
    old = os.path.join(REPO, "jobs", "archive", "gvgaisearch-dryrun-v4", "manifest.json")
    if os.path.exists(old):
        mo = read_json(old)
        sessions(mo, f"attempt under {mo['code_tag']}")
    sessions(m, f"attempt under {m['code_tag']}")
    lap = laptop_counts()
    print("\n== rows")
    base = os.path.join(REPO, "runs", m["campaign"], "gvgaisearch")
    for u in m["units"]:
        p = os.path.join(base, f"{u['unit_id']}.json")
        if not os.path.exists(p):
            print(f"{u['unit_id']}: no row")
            continue
        r = read_json(p)
        errs = validate_search_row(r)
        c = r["counts"]
        print(f"{u['unit_id']} ({u['game']}, level {u['level']}): schema {r['schema']} {'ok' if not errs else errs}; "
              f"complete {r['complete']}; cap hit {r.get('cap_hit')}; "
              + ", ".join(f"{x} {c.get(x)}" for x in KEYS) + f"; seconds {r['seconds_spent']}")
        for s in r["sessions"]:
            print(f"   session: run {s['run_nonce']}  {s['started_at']} to {s['ended_at']}")
        ref = lap.get((u["game"], int(u["level"])))
        if ref:
            same = all(c.get(x) == ref[x] for x in ref)
            print(f"   laptop (logs/test_gvgaisearch.log): " + ", ".join(f"{x} {ref[x]}" for x in ref)
                  + f": {'same' if same else 'DIFFERENT'}")
        else:
            print("   laptop: no reference count")
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
            uip = ck.get("units_in_progress") or {}
            print(f"   seq {ck['seq']}, run {ck['run_nonce']}, units done {ck['units_done']}, in progress "
                  + ", ".join(f"{a} ({b['counts']['states_expanded']} expanded)" for a, b in uip.items()))
    print("\n== runner lines of every session console (logs/kaggle/)")
    for name in sorted(os.listdir(os.path.join(REPO, "logs", "kaggle")),
                       key=lambda n: int(re.search(r"__v(\d+)", n).group(1)) if re.search(r"__v(\d+)", n) else 0):
        if not name.startswith("gd-01__"):
            continue
        print(f"-- {name}")
        with open(os.path.join(REPO, "logs", "kaggle", name), encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("[") or line.startswith("code commit"):
                    print("   " + line.rstrip()[:240])
    print("\n== automation.log lines of this campaign")
    with open(os.path.join(REPO, "logs", "automation.log"), encoding="utf-8") as f:
        for line in f:
            if "gd-01" in line:
                print(line.rstrip()[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
