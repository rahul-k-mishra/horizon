"""
devsearch_report.py -- the dry run of the kind devsearch (stage D), read from committed files only: jobs/manifest.json
(campaign devsearch-dryrun), the rows under runs/devsearch-dryrun/devsearch/, logs/automation.log, the git history,
and logs/test_devsearch.log for the counts the same levels gave on this laptop in the synthetic tests.
Prints: per session of the chunk its Kaggle kernel version, run nonce and outcome; per row its schema check,
counts, branching, effective-horizon bound, seconds and the sessions that built it; the commits that wrote the
chunk's checkpoint and what it held; and whether each row's states seen, states expanded and shortest
solution equal the laptop's.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\devsearch_report.py > logs\\devsearch_dryrun_report.log
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


def git(*a):
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, check=True).stdout


def laptop_counts():
    out = {}
    with open(os.path.join(REPO, "logs", "test_devsearch.log"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"(\S+) seed (\d+): (\{.*?\}); plain search", line)
            if m:
                out[(m.group(1), int(m.group(2)))] = ast.literal_eval(m.group(3))
    return out


def main():
    m = load_manifest(REPO)
    print(f"devsearch dry run -- campaign {m['campaign']}, code tag {m['code_tag']}, state commit "
          f"{git('rev-parse', '--short', 'HEAD').strip()}, workers {m['kinds']['devsearch']['workers']}")
    for c in m["chunks"]:
        print(f"\n== chunk {c['chunk_id']}: {c['status']}, attempts {c['attempts']}, failures {c['failures']}")
        for s in c["sessions"]:
            print(f"   kernel version {s['kernel_version']}  run {s['run_nonce']}  outcome {s['outcome']}  "
                  f"units {s['units_done_this_session']}  ended {s['ended_at']}")
    lap = laptop_counts()
    print("\n== rows")
    base = os.path.join(REPO, "runs", m["campaign"], "devsearch")
    for u in m["units"]:
        p = os.path.join(base, f"{u['unit_id']}.json")
        if not os.path.exists(p):
            print(f"{u['unit_id']}: no row")
            continue
        r = read_json(p)
        errs = validate_search_row(r)
        c = r["counts"]
        print(f"{u['unit_id']} ({u['game']}, seed {u['level']}): schema {r['schema']} {'ok' if not errs else errs}; "
              f"complete {r['complete']}; states seen {c['states_seen']}, expanded {c['states_expanded']}, "
              f"shortest solution {c['solution_length']}; branching {r['measures']['branching']:.4f}; "
              f"EH {r['measures']['eh']} (k {r['measures']['eh_k']}, {r['measures']['eh_status']}); seconds {r['seconds_spent']}")
        for s in r["sessions"]:
            print(f"   session: host {s['host']}  run {s['run_nonce']}  {s['started_at']} to {s['ended_at']}")
        ref = lap.get((u["game"], int(u["level"])))
        if ref:
            same = (c["states_seen"], c["states_expanded"], c["solution_length"]) == \
                   (ref["states_seen"], ref["states_expanded"], ref["solution_length"])
            print(f"   laptop (logs/test_devsearch.log): seen {ref['states_seen']}, expanded {ref['states_expanded']}, "
                  f"shortest {ref['solution_length']}: {'same' if same else 'DIFFERENT'}")
    print("\n== checkpoint commits")
    cid = m["chunks"][0]["chunk_id"]
    path = f"runs/{m['campaign']}/checkpoints/{cid}/checkpoint.json"
    for line in git("log", "--reverse", "--format=%h %cI %s", "--", path).strip().splitlines():
        print(f"{line}")
        try:
            ck = json.loads(git("show", f"{line.split()[0]}:{path}"))
        except subprocess.CalledProcessError:
            print("   (checkpoint removed: the chunk is done)")
            continue
        uip = ck.get("units_in_progress") or {}
        print(f"   seq {ck['seq']}, run {ck['run_nonce']}, units done {ck['units_done']}, in progress "
              + ", ".join(f"{k} ({v['counts']['states_expanded']} expanded)" for k, v in uip.items()))
        print(f"   payload: {len(ck['payload'])} files, locations "
              f"{sorted({i.get('location', 'git') for i in ck['payload'].values()})}")
    print("\n== automation.log lines of this campaign")
    with open(os.path.join(REPO, "logs", "automation.log"), encoding="utf-8") as f:
        for line in f:
            if "ds-01" in line:
                print(line.rstrip()[:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
