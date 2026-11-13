"""
test_loop.py -- the whole loop on this machine, with a fake Kaggle (scripts/automation/fake_kaggle.py),
a local bare git remote, and a local folder in place of GitHub releases.  Plays no game and calls no
service.

It copies the automation code (not jobs/) into a fresh repository in a temporary folder, writes its own
manifest there (fixture_manifest: the dummy dry run of the kinds agent and search, session work 12 s,
agent sleep 1 s, search slowed to about 14 s, payload commit limit 64 KB), so that it runs the same
whatever campaign is live in jobs/; tags the code automation-v1, and runs ticks until the manifest is
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
A fourth scenario runs the kind devsearch (stage D) through the loop: three MiniGrid units on a pool of two
workers, one slowed so that the first session ends partial with it in a checkpoint; it is resumed in a
later session and must count the same 112 states as an uninterrupted search.  Needs gymnasium and minigrid.
The same scenario runs a second time with the schema horizon.search.v3 of stage E (added 13 November 2026): a
seen cap no unit reaches, every row a valid v3 row, and the resumed unit's first win at 64 states seen.
Five scenarios on refusals and queues (added 12 November 2026), with the fake Kaggle tool's refuse.json and
status.json, each on its own repository:
    refusal      (R1) four pushes refused for a full account, one more than max_failures: no failure, no crash,
                 no halt, the same chunk waiting, next-wake the longest sleep; (R2) an HTTP 429 likewise; (R3)
                 the push accepted: the deferral cleared, and the manifest completes with no failure
    queue        (Q1) a queued session is recorded, next-wake the longest sleep; (Q2) queued past the overdue
                 time, it is not counted overdue; (Q3) once running it is timed from then; (Q4) a queue longer
                 than loop.WAIT_LIMIT_SECONDS halts the loop, no failure, the dispatch kept
    notstarted   (N1) a kernel status the loop does not know is a crash, the dispatch kept; (N2) a session that
                 never started (ERROR, no output, a full-account message) is deferred, not failed
    bound        a refusal that lasts past loop.WAIT_LIMIT_SECONDS halts the loop, with no failure counted
    genuine      an unclassifiable refusal and then the authentication error count failures; the third halts
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
import time
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


def fixture_manifest():
    """The test's own campaign, built here and never read from jobs/: the dummy dry run of the kinds agent
    and search (jobs/archive/dryrun/manifest.json) with fast settings.  dry-01 and dry-03 are one agent unit
    each; dry-02 holds graph-a (28,000 reachable nodes, goal at depth 48) and graph-b (node cap 500)."""
    def unit(chunk, kind, game, **kw):
        u = dict(unit_id=f"{chunk}-{game}" if kind == "search" else f"{chunk}-{game}-seed1", chunk_id=chunk,
                 kind=kind, suite="dummy", game=game, level=None, agent="dummy", seed=1, status="pending")
        if kind == "search":
            u.update(level=1, agent=None, seed=None)
        u.update(kw)
        return u
    return dict(
        campaign="dryrun", code_tag="automation-v1", repository="local/test", kernel_slug="horizon-runner",
        max_failures=3, payload_commit_limit_bytes=65536,
        # 12 s of work: a session spends part of it cloning and running pip before the runner starts, and an
        # agent unit needs 2 s left to start, which 6 s did not always leave; the search of graph-a needs
        # about 14 s, so dry-02 still ends its first session partial.
        session=dict(work_seconds=12, checkpoint_reserve_seconds=5, platform_limit_seconds=600),
        kinds=dict(
            agent=dict(agent_impl="dummy_sleep", budget=None, checkpoint_every_seconds=60, checkpoint_every_units=1,
                       sleep_seconds=1, unit_seconds_cap=2),
            search=dict(simulator="dummy_graph", M=28001, edges=[[3, 1], [5, 2], [7, 3]], goal=27000, batch=100,
                        node_cap=1000000, time_cap_seconds=3600, memory_cap_bytes=25769803776, spill_frontier_over=100,
                        checkpoint_every_nodes=3000, checkpoint_every_seconds=2, seconds_per_batch=0.05)),
        chunks=[dict(chunk_id=c, kind=k, status="pending", attempts=0, failures=0, sessions=[])
                for c, k in (("dry-01", "agent"), ("dry-02", "search"), ("dry-03", "agent"))],
        units=[unit("dry-01", "agent", "sleep"),
               unit("dry-02", "search", "graph-a"),
               unit("dry-02", "search", "graph-b", params=dict(node_cap=500, seconds_per_batch=0.0)),
               unit("dry-03", "agent", "sleep")])


def make_src(tmp, name, m):
    """A source repository for one scenario: the automation code copied from this repository, and a jobs/
    written from nothing (manifest m, no dispatch, not halted, no lock), whatever campaign is live here."""
    src = os.path.join(tmp, name)
    os.makedirs(src)
    for rel in ("scripts/automation", "kaggle"):
        shutil.copytree(os.path.join(REPO, rel), os.path.join(src, rel),
                        ignore=shutil.ignore_patterns("__pycache__", "test_*.py"))
    shutil.copyfile(os.path.join(REPO, ".gitattributes"), os.path.join(src, ".gitattributes"))
    # the fake sessions run the notebook with this interpreter, so the runner's frozen requirements (pinned for
    # Kaggle's image) would be installed into the project's environment; with comments only, the notebook skips
    # the install, and this environment already has gymnasium and minigrid
    with open(os.path.join(src, "kaggle", "requirements-runner.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# left empty by test_loop.py: the notebook installs nothing in the fake sessions\n")
    os.makedirs(os.path.join(src, "jobs"))
    save_manifest(src, m)
    write_json(os.path.join(src, "jobs", "state.json"),
               dict(consecutive_crashes=0, dispatch=None, halted=False, halted_at=None, halt_reason=None))
    return src


def scenario_halt(env_base, tmp, check):
    """A chunk whose every session fails (unknown agent implementation) must halt the loop after the
    registered maximum of failures, with STATE-ready text in logs/automation.log."""
    m = fixture_manifest()
    m["kinds"]["agent"]["agent_impl"] = "not_written"
    src = make_src(tmp, "src-halt", m)
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
    src = make_src(tmp, "src-crash", fixture_manifest())
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


def scenario_devsearch(env_base, tmp, check, v3=False):
    """The kind devsearch through the whole loop: three MiniGrid units on a pool of two workers, one of them
    slowed so that the first session ends at its deadline with that unit in a checkpoint; later sessions
    resume it.  Every row must be a valid horizon.search.v2 row under runs/<campaign>/devsearch/, and the
    resumed unit must count what an uninterrupted search counts (scripts/automation/test_devsearch.py).
    With v3 (stage E) the kind names the schema horizon.search.v3 and a seen cap no unit reaches: every row
    must be a valid v3 row, and the resumed DoorKey unit must also record its first win where an
    uninterrupted search sees it (64 states, scripts/automation/test_devsearch.py)."""
    base = dict(simulator="minigrid", workers=2, node_cap=5000000, time_cap_seconds=14400,
                memory_cap_bytes=6442450944, spill_frontier_over=1000000, checkpoint_every_seconds=600,
                checkpoint_every_nodes=250000, batch=5, eh_state_limit=200000, eh_horizon=400)
    if v3:
        base.update(schema="horizon.search.v3", seen_cap=1000000)
    sfx = "dev3" if v3 else "dev"
    campaign = "devtest3" if v3 else "devtest"
    units = [dict(unit_id="d-01-empty5-s1000", chunk_id="d-01", kind="devsearch", suite="minigrid",
                  game="MiniGrid-Empty-5x5-v0", level=1000, agent=None, seed=None, status="pending"),
             dict(unit_id="d-01-lavagap5-s1000", chunk_id="d-01", kind="devsearch", suite="minigrid",
                  game="MiniGrid-LavaGapS5-v0", level=1000, agent=None, seed=None, status="pending"),
             dict(unit_id="d-01-doorkey5-s1000", chunk_id="d-01", kind="devsearch", suite="minigrid",
                  game="MiniGrid-DoorKey-5x5-v0", level=1000, agent=None, seed=None, status="pending",
                  params=dict(seconds_per_batch=1.0))]
    m = dict(campaign=campaign, code_tag="automation-v1", repository="local/test", kernel_slug="horizon-runner",
             max_failures=3, payload_commit_limit_bytes=65536,
             # 16 s of work, for the same reason as fixture_manifest's 12 s, with MiniGrid's import on top;
             # DoorKey at 1 s a batch (about 23 batches) cannot finish in one session.
             session=dict(work_seconds=16, checkpoint_reserve_seconds=5, platform_limit_seconds=600),
             kinds=dict(devsearch=base),
             chunks=[dict(chunk_id="d-01", kind="devsearch", status="pending", attempts=0, failures=0, sessions=[])],
             units=units)
    src = make_src(tmp, f"src-{sfx}", m)
    git(src, "init", "-q", "-b", "main")
    git(src, "config", "user.name", "test")
    git(src, "config", "user.email", "test@example.invalid")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "test setup")
    git(src, "tag", "automation-v1")
    bare = os.path.join(tmp, f"remote-{sfx}.git")
    git(tmp, "clone", "-q", "--bare", src, bare)
    work = os.path.join(tmp, f"work-{sfx}")
    git(tmp, "clone", "-q", bare, work)
    git(work, "config", "user.name", "horizon-loop")
    git(work, "config", "user.email", "loop@example.invalid")
    env = dict(env_base, FAKE_KAGGLE_STORE=os.path.join(tmp, f"kaggle-{sfx}"), FAKE_KAGGLE_REPO_URL=bare,
               HORIZON_RELEASE_DIR=os.path.join(tmp, f"releases-{sfx}"))
    outs = []
    for i in range(10):
        r = subprocess.run([sys.executable, os.path.join(work, "scripts", "automation", "loop.py"), "tick",
                            "--repo", work], env=env, capture_output=True, text=True)
        outs.append(r.stdout + r.stderr)
        print(f"--- devsearch tick {i + 1} (exit {r.returncode})\n{(r.stdout + r.stderr).strip()[-1500:]}")
        check(r.returncode == 0, f"devsearch tick {i + 1} exit code {r.returncode}")
        if "manifest complete" in r.stdout:
            break
    check(any("manifest complete" in o for o in outs), "devsearch: the loop never reported 'manifest complete'")
    m = load_manifest(work)
    c = m["chunks"][0]
    outcomes = [s["outcome"] for s in c["sessions"]]
    check(c["status"] == "done" and outcomes[0] == "partial" and outcomes[-1] == "done" and "failed" not in outcomes,
          f"devsearch sessions {outcomes}")
    for u in units:
        p = os.path.join(work, "runs", campaign, "devsearch", f"{u['unit_id']}.json")
        check(os.path.exists(p), f"devsearch row missing: {p}")
        if os.path.exists(p):
            row = read_json(p)
            want = "horizon.search.v3" if v3 else "horizon.search.v2"
            check(not validate_search_row(row) and row["schema"] == want,
                  f"{u['unit_id']}: {row['schema']} {validate_search_row(row)}")
            if u["game"] == "MiniGrid-DoorKey-5x5-v0":
                check(row["counts"]["states_seen"] == 112 and len(row["sessions"]) >= 2,
                      f"the resumed DoorKey unit: {row['counts']['states_seen']} states over {len(row['sessions'])} sessions "
                      "(an uninterrupted search sees 112, scripts/automation/test_devsearch.py)")
                if v3:
                    check(row["counts"]["seen_at_first_win"] == 64 and row["caps"]["seen_cap"] == 1000000
                          and row["complete"], f"the resumed DoorKey unit under v3: {row['counts']} {row['caps']}")


def setup_repo(tmp, name, m):
    """Source repository, bare remote and working clone for one scenario; returns the clone."""
    src = make_src(tmp, f"src-{name}", m)
    git(src, "init", "-q", "-b", "main")
    git(src, "config", "user.name", "test")
    git(src, "config", "user.email", "test@example.invalid")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "test setup")
    git(src, "tag", "automation-v1")
    bare = os.path.join(tmp, f"remote-{name}.git")
    git(tmp, "clone", "-q", "--bare", src, bare)
    work = os.path.join(tmp, f"work-{name}")
    git(tmp, "clone", "-q", bare, work)
    git(work, "config", "user.name", "horizon-loop")
    git(work, "config", "user.email", "loop@example.invalid")
    return work, bare


class Kag:
    """One scenario's fake Kaggle store and its loop: ticks, scripted refusals and statuses, edits of state.json."""
    def __init__(self, env_base, tmp, name):
        self.work, bare = setup_repo(tmp, name, fixture_manifest())
        self.store = os.path.join(tmp, f"kaggle-{name}")
        os.makedirs(self.store)
        self.env = dict(env_base, FAKE_KAGGLE_STORE=self.store, FAKE_KAGGLE_REPO_URL=bare,
                        HORIZON_RELEASE_DIR=os.path.join(tmp, f"releases-{name}"))
        self.loop_py = os.path.join(self.work, "scripts", "automation", "loop.py")
        self.name = name

    def refuse(self, left, message="", mode="field"):
        write_json(os.path.join(self.store, "refuse.json"), dict(left=left, message=message, mode=mode))

    def statuses(self, *seq):
        write_json(os.path.join(self.store, "status.json"), list(seq))

    def tick(self, label):
        r = subprocess.run([sys.executable, self.loop_py, "tick", "--repo", self.work], env=self.env,
                           capture_output=True, text=True)
        lines = [x for x in (r.stdout + r.stderr).strip().splitlines() if "Traceback" not in x and not x.startswith("  ")]
        print(f"--- {self.name} scenario {label} (exit {r.returncode})\n" + "\n".join(lines)[-700:])
        return r

    def wake(self):
        return subprocess.run([sys.executable, self.loop_py, "next-wake", "--repo", self.work, "--min", "300",
                               "--max", "1800"], env=self.env, capture_output=True, text=True).stdout.strip()

    def state(self):
        return read_json(os.path.join(self.work, "jobs", "state.json"))

    def chunk(self, cid):
        return next(c for c in load_manifest(self.work)["chunks"] if c["chunk_id"] == cid)

    def log(self):
        p = os.path.join(self.work, "logs", "automation.log")
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

    def edit_state(self, fn, msg):
        st = self.state()
        fn(st)
        write_json(os.path.join(self.work, "jobs", "state.json"), st)
        git(self.work, "commit", "-q", "--allow-empty", "-am", msg)
        git(self.work, "push", "-q")


def ago(hours):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - hours * 3600))


FULL = "Maximum batch CPU session count of 5 reached."     # the form assumed for a full account (not verified)


def scenario_refusal(env_base, tmp, check):
    """A push refused because the account is full, or by a busy server, is neither a failure of the chunk nor a
    crash: the loop waits and pushes the same chunk again on a later tick."""
    k = Kag(env_base, tmp, "refusal")
    # (R1) four refusals in a row, more than max_failures (3), in the form kaggle 2.2.4 prints a server error
    k.refuse(4, FULL)
    for i in range(4):
        r = k.tick(f"R1 tick {i + 1}, account full")
        st, c = k.state(), k.chunk("dry-01")
        check(r.returncode == 0 and not st.get("halted") and c["failures"] == 0 and c["status"] == "pending"
              and c["attempts"] == 0 and not st.get("dispatch") and int(st.get("consecutive_crashes") or 0) == 0
              and (st.get("deferral") or {}).get("count") == i + 1,
              f"R1 refusal {i + 1}: exit {r.returncode}, halted {st.get('halted')}, failures {c['failures']}, "
              f"status {c['status']}, attempts {c['attempts']}, deferral {st.get('deferral')}")
    w = k.wake()
    check(w.startswith("1800 push of dry-01 deferred"), f"R1 next-wake while deferred: {w!r}")
    # (R2) an HTTP 429 from the push, exit code 1
    k.refuse(1, "429 Client Error: Too Many Requests for url: https://www.kaggle.com/api/v1/kernels/push", "http")
    r = k.tick("R2 tick, HTTP 429")
    st, c = k.state(), k.chunk("dry-01")
    check(r.returncode == 0 and c["failures"] == 0 and (st.get("deferral") or {}).get("last_class") == "rate limit"
          and (st.get("deferral") or {}).get("count") == 5, f"R2: failures {c['failures']}, deferral {st.get('deferral')}")
    # (R3) the account frees a slot: the same chunk is pushed, the deferral cleared, and the manifest completes
    r = k.tick("R3 tick 1, push accepted")
    st, c = k.state(), k.chunk("dry-01")
    check(r.returncode == 0 and (st.get("dispatch") or {}).get("chunk_id") == "dry-01" and st.get("deferral") is None
          and c["attempts"] == 1 and "DEFERRAL cleared" in k.log(),
          f"R3: dispatch {st.get('dispatch')}, deferral {st.get('deferral')}, attempts {c['attempts']}")
    finish(k, "R3", check)


def finish(k, label, check):
    """Tick until the manifest is complete; every chunk must end done with no failure."""
    for i in range(8):
        r = k.tick(f"{label} finish tick {i + 1}")
        if "manifest complete" in r.stdout or k.state().get("halted"):
            break
    m = load_manifest(k.work)
    check(all(c["status"] == "done" and c["failures"] == 0 for c in m["chunks"]) and not k.state().get("halted"),
          f"{label}: end state {[(c['chunk_id'], c['status'], c['failures']) for c in m['chunks']]}, "
          f"halted {k.state().get('halted')}")
    msgs = [x for x in git(k.work, "log", "--format=%H%x00%B%x00").split("\x00") if x.strip()][1::2]
    check(all(len(x.strip().splitlines()) == 1 for x in msgs), f"{label}: a commit message has more than one line")


def push_ago(hours):
    return lambda s: (s.get("dispatch") or {}).update(pushed_at=ago(hours))


def scenario_queue(env_base, tmp, check):
    """A session Kaggle keeps queued is not counted overdue while it waits and is never pushed twice; once seen
    running it is timed from then; a queue longer than loop.WAIT_LIMIT_SECONDS halts the loop with STATE-ready
    text, no failure counted and the dispatch kept."""
    k = Kag(env_base, tmp, "queue")
    k.tick("Q1 tick 1, push dry-01")
    k.statuses("QUEUED", "QUEUED", "RUNNING")
    r = k.tick("Q1 tick 2, queued")
    st = k.state()
    check(r.returncode == 0 and (st.get("dispatch") or {}).get("queued_seen_at") and "QUEUED chunk dry-01" in k.log(),
          f"Q1: queue not recorded: {st.get('dispatch')}")
    w = k.wake()
    check(w.startswith("1800 dry-01"), f"Q1: next-wake while queued must be the longest sleep: {w!r}")
    k.edit_state(push_ago(1), "test: dry-01 pushed an hour ago")
    r = k.tick("Q2 tick, queued past the overdue time (600 s + 1800 s)")
    st, c = k.state(), k.chunk("dry-01")
    check(r.returncode == 0 and c["failures"] == 0 and st.get("dispatch") and c["status"] == "running",
          f"Q2: a queued session was counted overdue: failures {c['failures']}, status {c['status']}")
    r = k.tick("Q3 tick, running")
    st, c = k.state(), k.chunk("dry-01")
    check(r.returncode == 0 and c["failures"] == 0 and (st.get("dispatch") or {}).get("started_seen_at"),
          f"Q3: start not recorded, or counted overdue from the push: failures {c['failures']}, {st.get('dispatch')}")
    k.tick("Q4 tick 1, collect dry-01 and push dry-02")
    k.statuses("QUEUED")
    k.edit_state(push_ago(25), "test: dry-02 pushed 25 hours ago")
    r = k.tick("Q4 tick 2, queued 25 h")
    st, c = k.state(), k.chunk("dry-02")
    check(r.returncode == 0 and st.get("halted") and c["failures"] == 0
          and (st.get("dispatch") or {}).get("chunk_id") == "dry-02"
          and "stayed queued" in k.log() and "STATE-ready text" in k.log(),
          f"Q4: halted {st.get('halted')}, failures {c['failures']}, dispatch {bool(st.get('dispatch'))}")
    k.edit_state(lambda s: s.update(halted=False, halted_at=None, halt_reason=None), "test: halt cleared by hand")
    finish(k, "Q4", check)


def scenario_not_started(env_base, tmp, check):
    """A pushed session that never runs: an unknown kernel status is a crash with the dispatch kept; then ERROR
    with a full-account failure message and no output is deferred, not counted as a failure."""
    k = Kag(env_base, tmp, "notstarted")
    k.refuse(1, mode="norun")
    k.tick("N1 tick 1, push dry-01, which never runs")
    k.statuses("WEIRD", f"ERROR|{FULL}")
    r = k.tick("N1 tick 2, unknown status")
    st, c = k.state(), k.chunk("dry-01")
    check(r.returncode == 1 and st.get("consecutive_crashes") == 1
          and (st.get("dispatch") or {}).get("chunk_id") == "dry-01" and c["failures"] == 0,
          f"N1: unknown status: exit {r.returncode}, crashes {st.get('consecutive_crashes')}, "
          f"failures {c['failures']}, dispatch {bool(st.get('dispatch'))}")
    r = k.tick("N2 tick, ERROR, session never started")
    st, c = k.state(), k.chunk("dry-01")
    check(r.returncode == 0 and c["failures"] == 0 and c["status"] == "pending" and not st.get("dispatch")
          and st.get("consecutive_crashes") == 0 and (st.get("deferral") or {}).get("count") == 1
          and c["sessions"] and c["sessions"][-1]["outcome"] == "not started",
          f"N2: not-started session: failures {c['failures']}, status {c['status']}, deferral {st.get('deferral')}")
    finish(k, "N2", check)


def scenario_refusal_bound(env_base, tmp, check):
    """A refusal that persists past loop.WAIT_LIMIT_SECONDS halts the loop with STATE-ready text, without
    counting a failure of the chunk."""
    k = Kag(env_base, tmp, "bound")
    k.refuse(99, FULL)
    k.tick("tick 1, account full")
    k.edit_state(lambda s: (s.get("deferral") or {}).update(since=ago(25)), "test: refusals began 25 hours ago")
    r = k.tick("tick 2, account still full")
    st, c = k.state(), k.chunk("dry-01")
    check(r.returncode == 0 and st.get("halted") and c["failures"] == 0 and c["status"] == "pending"
          and "could not be started" in k.log() and "STATE-ready text" in k.log(),
          f"bound: halted {st.get('halted')}, failures {c['failures']}, status {c['status']}")
    check(k.wake().startswith("none halted"), "bound: next-wake after the halt")


def scenario_genuine(env_base, tmp, check):
    """A push refused for a genuine fault still counts a failure of the chunk and halts at max_failures: an
    unclassifiable text once, then the authentication error of the first dry run (logs/automation.log line 2)."""
    k = Kag(env_base, tmp, "genuine")
    k.refuse(1, "The server answered something this loop has never seen.")
    k.tick("tick 1, unclassifiable refusal")
    check(k.chunk("dry-01")["failures"] == 1 and not k.state().get("deferral"),
          f"genuine: an unclassifiable refusal must count a failure: {k.chunk('dry-01')['failures']}")
    k.refuse(2, "Authentication required to call the Kaggle API.")
    for i in range(2):
        k.tick(f"tick {2 + i}, authentication refused")
    st, c = k.state(), k.chunk("dry-01")
    check(st.get("halted") and c["status"] == "failed" and c["failures"] == 3 and "STATE-ready text" in k.log()
          and "failed 3 times" in k.log(), f"genuine: halted {st.get('halted')}, chunk {c['status']} failures {c['failures']}")


def main():
    fails = []

    def check(c, msg):
        if not c:
            fails.append(msg)
            print("FAIL:", msg)
    tmp = tempfile.mkdtemp(prefix="horizon-looptest-")
    try:
        src = make_src(tmp, "src", fixture_manifest())
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
        all_locs = []
        for line in ck_commits.strip().splitlines():
            try:
                ck = json.loads(git(work, "show", f"{line.split()[0]}:runs/dryrun/checkpoints/dry-02/checkpoint.json"))
            except subprocess.CalledProcessError:
                continue                          # the commit that removed the checkpoint
            all_locs.append({i["location"] for i in ck["payload"].values()})
        check(any(x == {"git", "release"} for x in all_locs),
              f"no dry-02 checkpoint held files both in git and in the release folder: {all_locs}")
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
        scenario_devsearch(env, tmp, check)
        scenario_devsearch(env, tmp, check, v3=True)
        scenario_refusal(env, tmp, check)
        scenario_queue(env, tmp, check)
        scenario_not_started(env, tmp, check)
        scenario_refusal_bound(env, tmp, check)
        scenario_genuine(env, tmp, check)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
