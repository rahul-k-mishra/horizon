"""
test_loop.py -- the whole loop on this machine, with a fake Kaggle (scripts/automation/fake_kaggle.py),
a local bare git remote, and a local folder in place of GitHub releases.  Plays no game and calls no
service.

It copies the automation files into a fresh repository in a temporary folder, tags the code
automation-v1, writes a fast version of the dry-run manifest (session work 6 s, agent sleep 1 s,
search slowed to about 14 s, payload commit limit 64 KB), and runs ticks until the manifest is
complete.  Expected, and checked:
    dry-01  done in one session
    dry-02  partial (the search stops at the session deadline with its frontier, spill files and
            visited set in a checkpoint; the visited set is over 64 KB, so it goes to the release
            folder), then resumed, and done in a later session; graph-a enumerates all 28,000
            reachable nodes of the dummy graph, the same count as an uninterrupted enumeration, with
            the goal at depth 48; graph-b is capped at its node cap of 500 and recorded as capped
    dry-03  done in one session
    a further tick says "manifest complete" and commits nothing
    after every tick, next-wake gives a sleep inside its bounds while work remains, and "none" once
    the manifest is complete (and "none" in the halt scenario below)
    every row passes its schema; search rows carry no agent field and agent rows no search field
    every commit message is one line
A second scenario gives the agent kind an implementation that does not exist, so every session of
dry-01 fails: after the registered maximum of 3 failures the loop halts, marks the chunk failed, writes
STATE-ready text into logs/automation.log, and runs nothing more.
A third scenario breaks the manifest so that ticks crash before reaching any chunk: each crash adds 1
to the consecutive-crash count in jobs/state.json, a tick that reaches a chunk (after the manifest is
repaired) sets it back to 0, and at the registered maximum (loop.MAX_CRASHES, 12) the loop halts with
STATE-ready text; a crash after the halt is not counted, and next-wake says "none".
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\test_loop.py
Expected last line: OK
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import deque

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from common import load_manifest, read_json, save_manifest, write_json  # noqa: E402
from schema import load_features, load_outcomes, validate_agent_row, validate_search_row  # noqa: E402


def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout


def reference_count(M, edges, goal):
    seen, q, depth = {0}, deque([0]), {0: 0}
    while q:
        n = q.popleft()
        for a, b in edges:
            x = (a * n + b) % M
            if x not in seen:
                seen.add(x)
                depth[x] = depth[n] + 1
                q.append(x)
    return len(seen), depth.get(goal)


def fresh(src, m):
    """The repository's jobs/ may hold a live campaign's progress: start the copy from nothing."""
    for c in m["chunks"]:
        c.update(status="pending", attempts=0, failures=0, sessions=[])
    for u in m["units"]:
        u["status"] = "pending"
    write_json(os.path.join(src, "jobs", "state.json"), dict(dispatch=None, halted=False, halted_at=None, halt_reason=None))
    if os.path.exists(os.path.join(src, "jobs", "lock.json")):
        os.remove(os.path.join(src, "jobs", "lock.json"))


def scenario_halt(env_base, tmp, check):
    """A chunk whose every session fails (unknown agent implementation) must halt the loop after the
    registered maximum of failures, with STATE-ready text in logs/automation.log."""
    src = os.path.join(tmp, "src-halt")
    os.makedirs(src)
    for rel in ("scripts/automation", "kaggle", "jobs"):
        shutil.copytree(os.path.join(REPO, rel), os.path.join(src, rel),
                        ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
    m = load_manifest(src)
    m.update(session=dict(work_seconds=6, checkpoint_reserve_seconds=5, platform_limit_seconds=600))
    fresh(src, m)
    m["kinds"]["agent"].update(agent_impl="not_written", sleep_seconds=1, unit_seconds_cap=2)
    save_manifest(src, m)
    git(src, "init", "-q", "-b", "main")
    git(src, "config", "user.name", "test")
    git(src, "config", "user.email", "test@example.invalid")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "test setup")
    git(src, "tag", "automation-v1")
    bare = os.path.join(tmp, "remote-halt.git")
    git(tmp, "clone", "-q", "--bare", src, bare)
    work = os.path.join(tmp, "work-halt")
    git(tmp, "clone", "-q", bare, work)
    git(work, "config", "user.name", "horizon-loop")
    git(work, "config", "user.email", "loop@example.invalid")
    env = dict(env_base, FAKE_KAGGLE_STORE=os.path.join(tmp, "kaggle-halt"), FAKE_KAGGLE_REPO_URL=bare)
    for i in range(6):
        r = subprocess.run([sys.executable, os.path.join(work, "scripts", "automation", "loop.py"), "tick",
                            "--repo", work], env=env, capture_output=True, text=True)
        print(f"--- halt scenario tick {i + 1} (exit {r.returncode})")
        print((r.stdout + r.stderr).strip())
        check(r.returncode == 0, f"halt scenario tick {i + 1} exit code {r.returncode}")
    st = read_json(os.path.join(work, "jobs", "state.json"))
    m = load_manifest(work)
    c = m["chunks"][0]
    log = open(os.path.join(work, "logs", "automation.log"), encoding="utf-8").read()
    check(st["halted"] and c["status"] == "failed" and c["failures"] == m["max_failures"],
          f"halt scenario: halted {st['halted']}, chunk {c['status']} failures {c['failures']}")
    check("STATE-ready text" in log and "NotImplementedError" in log, "halt scenario: no STATE-ready text in the log")
    check(all(x["status"] == "pending" for x in m["chunks"][1:]), "halt scenario: later chunks were run")
    r = subprocess.run([sys.executable, os.path.join(work, "scripts", "automation", "loop.py"), "next-wake",
                        "--repo", work], env=env, capture_output=True, text=True)
    check(r.stdout.startswith("none halted"), f"halt scenario: next-wake said {r.stdout.strip()!r}")


def scenario_crash(env_base, tmp, check):
    """A tick that crashes before it reaches a chunk (here: a manifest that fails its structural check)
    adds 1 to the consecutive-crash count; a tick that reaches a chunk sets it back to 0; at the
    registered maximum the loop halts with STATE-ready text, and later ticks and next-wake do nothing."""
    sys.path.insert(0, os.path.join(REPO, "scripts", "automation"))
    from loop import MAX_CRASHES  # noqa: E402
    src = os.path.join(tmp, "src-crash")
    os.makedirs(src)
    for rel in ("scripts/automation", "kaggle", "jobs"):
        shutil.copytree(os.path.join(REPO, rel), os.path.join(src, rel),
                        ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
    m = load_manifest(src)
    m.update(session=dict(work_seconds=6, checkpoint_reserve_seconds=5, platform_limit_seconds=600))
    fresh(src, m)
    m["kinds"]["agent"].update(sleep_seconds=1, unit_seconds_cap=2)
    save_manifest(src, m)
    git(src, "init", "-q", "-b", "main")
    git(src, "config", "user.name", "test")
    git(src, "config", "user.email", "test@example.invalid")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "test setup")
    git(src, "tag", "automation-v1")
    bare = os.path.join(tmp, "remote-crash.git")
    git(tmp, "clone", "-q", "--bare", src, bare)
    work = os.path.join(tmp, "work-crash")
    git(tmp, "clone", "-q", bare, work)
    git(work, "config", "user.name", "horizon-loop")
    git(work, "config", "user.email", "loop@example.invalid")
    env = dict(env_base, FAKE_KAGGLE_STORE=os.path.join(tmp, "kaggle-crash"), FAKE_KAGGLE_REPO_URL=bare)
    loop_py = os.path.join(work, "scripts", "automation", "loop.py")

    def set_kind(kind):
        mm = load_manifest(work)
        mm["chunks"][2]["kind"] = kind
        save_manifest(work, mm)
        git(work, "commit", "-q", "-am", f"test: chunk dry-03 kind {kind}")
        git(work, "push", "-q")

    def tick(label):
        r = subprocess.run([sys.executable, loop_py, "tick", "--repo", work], env=env, capture_output=True, text=True)
        print(f"--- crash scenario {label} (exit {r.returncode})")
        lines = [x for x in (r.stdout + r.stderr).strip().splitlines() if "Traceback" not in x and not x.startswith("  ")]
        print("\n".join(lines)[-600:])
        return r, read_json(os.path.join(work, "jobs", "state.json"))

    set_kind("nonsense")
    for i in range(2):
        r, st = tick(f"tick {i + 1}, broken manifest")
        check(r.returncode == 1 and st.get("consecutive_crashes") == i + 1,
              f"crash scenario: tick {i + 1} exit {r.returncode}, count {st.get('consecutive_crashes')}")
    set_kind("agent")
    r, st = tick("tick 3, manifest repaired")
    check(r.returncode == 0 and st.get("consecutive_crashes") == 0 and st.get("dispatch"),
          f"crash scenario: a tick that reaches a chunk must reset the count: exit {r.returncode}, "
          f"count {st.get('consecutive_crashes')}, dispatch {bool(st.get('dispatch'))}")
    set_kind("nonsense")
    for i in range(MAX_CRASHES):
        r, st = tick(f"tick {4 + i}, broken manifest")
        check(r.returncode == 1 and st.get("consecutive_crashes") == i + 1,
              f"crash scenario: tick {4 + i} exit {r.returncode}, count {st.get('consecutive_crashes')}")
        check(bool(st.get("halted")) == (i + 1 == MAX_CRASHES), f"crash scenario: halted {st.get('halted')} after {i + 1} crashes")
    log = open(os.path.join(work, "logs", "automation.log"), encoding="utf-8").read()
    check(f"{MAX_CRASHES} consecutive ticks crashed" in log and "STATE-ready text" in log and "CRASH COUNT reset" in log,
          "crash scenario: no STATE-ready text or no reset line in the log")
    before = git(work, "rev-parse", "HEAD")
    r = subprocess.run([sys.executable, loop_py, "record-crash", "--repo", work, "--reason", "test"], env=env,
                       capture_output=True, text=True)
    check("already halted" in r.stdout and git(work, "rev-parse", "HEAD") == before,
          "crash scenario: a crash after the halt must not be counted or committed")
    r = subprocess.run([sys.executable, loop_py, "next-wake", "--repo", work], env=env, capture_output=True, text=True)
    check(r.stdout.startswith("none halted"), f"crash scenario: next-wake said {r.stdout.strip()!r}")
    msgs = [x for x in git(work, "log", "--format=%s").splitlines() if x.startswith("Loop: tick crashed")]
    check(len(msgs) == 2 + MAX_CRASHES, f"crash scenario: {len(msgs)} crash commits")


def main():
    fails = []

    def check(c, msg):
        if not c:
            fails.append(msg)
            print("FAIL:", msg)
    tmp = tempfile.mkdtemp(prefix="horizon-looptest-")
    try:
        src = os.path.join(tmp, "src")
        os.makedirs(src)
        for rel in ("scripts/automation", "kaggle", "jobs"):
            shutil.copytree(os.path.join(REPO, rel), os.path.join(src, rel),
                            ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
        m = load_manifest(src)
        fresh(src, m)
        m.update(session=dict(work_seconds=6, checkpoint_reserve_seconds=5, platform_limit_seconds=600))
        m["kinds"]["agent"].update(sleep_seconds=1, unit_seconds_cap=2)
        m["kinds"]["search"].update(seconds_per_batch=0.05, checkpoint_every_seconds=2)
        save_manifest(src, m)
        git(src, "init", "-q", "-b", "main")
        git(src, "config", "user.name", "test")
        git(src, "config", "user.email", "test@example.invalid")
        git(src, "add", "-A")
        git(src, "commit", "-q", "-m", "test setup")
        git(src, "tag", "automation-v1")
        bare = os.path.join(tmp, "remote.git")
        git(tmp, "clone", "-q", "--bare", src, bare)
        work = os.path.join(tmp, "work")
        git(tmp, "clone", "-q", bare, work)
        git(work, "config", "user.name", "horizon-loop")
        git(work, "config", "user.email", "loop@example.invalid")
        env = dict(os.environ, KAGGLE_USERNAME="tester",
                   KAGGLE_CMD=json.dumps([sys.executable, os.path.join(HERE, "fake_kaggle.py")]),
                   FAKE_KAGGLE_STORE=os.path.join(tmp, "kaggle"), FAKE_KAGGLE_REPO_URL=bare,
                   HORIZON_RELEASE_DIR=os.path.join(tmp, "releases"))
        env.pop("GITHUB_RUN_ID", None)
        outs, wakes = [], []
        for i in range(12):
            r = subprocess.run([sys.executable, os.path.join(work, "scripts", "automation", "loop.py"), "tick",
                                "--repo", work], env=env, capture_output=True, text=True)
            outs.append(r.stdout + r.stderr)
            print(f"--- tick {i + 1} (exit {r.returncode})\n{(r.stdout + r.stderr).strip()}")
            check(r.returncode == 0, f"tick {i + 1} exit code {r.returncode}")
            w = subprocess.run([sys.executable, os.path.join(work, "scripts", "automation", "loop.py"), "next-wake",
                                "--repo", work, "--min", "5", "--max", "60"], env=env, capture_output=True, text=True)
            print(f"    next-wake: {w.stdout.strip()}")
            wakes.append(w.stdout.split()[0] if w.stdout.strip() else "?")
            if "manifest complete" in r.stdout:
                break
        check(any("manifest complete" in o for o in outs), "the loop never reported 'manifest complete'")
        check(wakes[-1] == "none" and all(w.isdigit() and 5 <= int(w) <= 60 for w in wakes[:-1]),
              f"next-wake must give a bounded sleep while work remains and 'none' at the end: {wakes}")
        before = git(work, "rev-parse", "HEAD")
        r = subprocess.run([sys.executable, os.path.join(work, "scripts", "automation", "loop.py"), "tick",
                            "--repo", work], env=env, capture_output=True, text=True)
        check("manifest complete" in r.stdout and git(work, "rev-parse", "HEAD") == before,
              "a tick on a complete manifest must say so and commit nothing")
        m = load_manifest(work)
        st = {c["chunk_id"]: c for c in m["chunks"]}
        check(all(c["status"] == "done" for c in m["chunks"]), f"chunk status {[c['status'] for c in m['chunks']]}")
        check([s["outcome"] for s in st["dry-01"]["sessions"]] == ["done"], f"dry-01 sessions {st['dry-01']['sessions']}")
        out2 = [s["outcome"] for s in st["dry-02"]["sessions"]]
        check(out2[0] == "partial" and out2[-1] == "done" and "failed" not in out2, f"dry-02 sessions {out2}")
        check([s["outcome"] for s in st["dry-03"]["sessions"]] == ["done"], f"dry-03 sessions {st['dry-03']['sessions']}")
        rel = os.path.join(tmp, "releases", "ckpt-dryrun")
        log = open(os.path.join(work, "logs", "automation.log"), encoding="utf-8").read()
        check("PUSHED chunk dry-02" in log and "partial" in log, "automation.log lacks the partial collection")
        hist = git(work, "log", "--format=%H%x00%B%x00")
        msgs = [x for x in hist.split("\x00") if x.strip()][1::2]
        check(all(len(x.strip().splitlines()) == 1 for x in msgs), "a commit message has more than one line")
        # the checkpoint between the two dry-02 sessions held a release file
        ck_commits = git(work, "log", "--format=%h %s", "--", "runs/dryrun/checkpoints/dry-02/checkpoint.json")
        check(bool(ck_commits.strip()), "no commit touched the dry-02 checkpoint")
        ck_rev = ck_commits.strip().splitlines()[-1].split()[0]
        ck = json.loads(git(work, "show", f"{ck_rev}:runs/dryrun/checkpoints/dry-02/checkpoint.json"))
        locs = {i["location"] for i in ck["payload"].values()}
        check(locs == {"git", "release"}, f"checkpoint payload locations {locs}")
        check(any(n.startswith("spill_") for n in ck["payload"]), "the checkpoint holds no spill file")
        check(not os.path.exists(os.path.join(work, "runs", "dryrun", "checkpoints", "dry-02")),
              "the checkpoint of a done chunk was not removed")
        check(not os.listdir(rel) if os.path.isdir(rel) else True, "release files of a done chunk were not removed")
        # rows
        sp = [os.path.join(work, "runs", "dryrun", "search", f) for f in sorted(os.listdir(os.path.join(work, "runs", "dryrun", "search")))]
        ap = [os.path.join(work, "runs", "dryrun", "agent", f) for f in sorted(os.listdir(os.path.join(work, "runs", "dryrun", "agent")))]
        for p in sp:
            check(not validate_search_row(read_json(p)), f"{p} fails the search schema")
            check(validate_agent_row(read_json(p)) != [], f"{p} passes the agent schema")
        for p in ap:
            check(not validate_agent_row(read_json(p)), f"{p} fails the agent schema")
        feats = load_features(sp)
        n_ref, d_ref = reference_count(28001, [(3, 1), (5, 2), (7, 3)], 27000)
        a = feats[("dummy", "graph-a", 1)]
        check(a["complete"] and a["states_seen"] == n_ref and a["solution_length"] == d_ref,
              f"graph-a {a} against reference {n_ref} states, goal depth {d_ref}")
        b = feats[("dummy", "graph-b", 1)]
        check(b["capped"] and b["cap_hit"] == "node" and b["states_expanded"] == 500, f"graph-b {b}")
        row_a = read_json([p for p in sp if p.endswith("dry-02-graph-a.json")][0])
        check(len(row_a["sessions"]) >= 2 and len({s["run_nonce"] for s in row_a["sessions"]}) >= 2,
              "graph-a's row does not list the two sessions that built it")
        outc = load_outcomes(ap)
        check(set(outc.values().__iter__().__next__()) == {"level1_completed", "levels"}, "outcome loader leaks fields")
        try:
            load_features(ap)
            check(False, "load_features accepted an agent row")
        except ValueError:
            pass
        scenario_halt(env, tmp, check)
        scenario_crash(env, tmp, check)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
