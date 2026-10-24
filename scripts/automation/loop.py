"""
loop.py -- one tick of the HORIZON loop (docs/AUTOMATION.md, Section 7).  Standard library plus the
Kaggle command-line tool and git (and gh for checkpoint files too large to commit).  It computes
nothing: it polls Kaggle, collects and verifies a finished session's output, commits it, and pushes
the notebook again for the next chunk.

    python scripts/automation/loop.py tick              one tick (the workflow runs this on its cron and on its own successor)
    python scripts/automation/loop.py status            print the manifest and the dispatch in flight
    python scripts/automation/loop.py prepare-kernel --dir D   write the notebook folder for a manual push
    python scripts/automation/loop.py record-crash --reason R   count a crash of a step before the tick
    python scripts/automation/loop.py next-wake [--min S] [--max S]   after a tick: how long the workflow
                                                        sleeps before it starts its own successor, or "none"

A tick:
    1. git pull.  If jobs/state.json says the loop is halted, say so and stop.
    2. If a dispatch is in flight, ask Kaggle for the kernel's status.  Queued or running: stop (an
       overdue session, past the platform limit plus 30 minutes, counts as a failure).  Finished:
       download its output, verify it against the dispatch and the manifest, commit rows, done-markers,
       checkpoint, console log and the updated manifest in one commit, and release the lock.
    3. If nothing is in flight, pick the next chunk (a partial one first, then a pending one), take the
       lock by committing and pushing jobs/lock.json and the dispatch (a rejected push means another
       runner acted first, and this tick stops), push the notebook, and commit the kernel version.
    4. If every chunk is done, say "manifest complete" and stop.
A tick that ends with an error is a crash: jobs/state.json counts consecutive crashes, a tick that
reaches a chunk sets the count back to 0, and at MAX_CRASHES the loop halts with STATE-ready text.
A chunk's failures are counted (kernel error, missing or invalid output, no progress); at the
registered maximum the loop halts and writes STATE-ready text into logs/automation.log.

Environment: KAGGLE_USERNAME (the account, for the notebook's id) and KAGGLE_API_TOKEN (the Kaggle API
token, read by the Kaggle tool; the workflow fills it from the secret KAGGLE_KEY); GH_TOKEN for gh in Actions.
For tests: KAGGLE_CMD replaces the kaggle command (a JSON list or a shell-style string), HORIZON_RELEASE_DIR replaces GitHub releases with a
local folder, HORIZON_NO_PULL skips git pull and push when the repository has no remote.
"""
from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import (AUTOLOG, LOCK, STATE, check_manifest, checkpoint_reldir, chunk_entry_hash,  # noqa: E402
                    chunk_units, get_chunk, load_manifest, marker_relpath, now_iso, read_json, row_relpath,
                    save_manifest, select_next, sha256_file, unit_done, write_json)
from schema import validate_row  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
RUNNING = ("queued", "running", "new_script", "cancel_requested")
# Consecutive crashed ticks before the loop halts (docs/AUTOMATION.md, Section 7): at the chain's shortest
# spacing of 5 minutes, 12 crashes are an hour of continuous failure, longer than an ordinary outage of
# GitHub, Kaggle or the package index; under the cron alone they are 6 hours.
MAX_CRASHES = 12


def say(s):
    print(f"[{now_iso()}] {s}", flush=True)


def sh(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r


def kaggle(*args, check=True):
    cmd = os.environ.get("KAGGLE_CMD", "kaggle")
    base = json.loads(cmd) if cmd.startswith("[") else shlex.split(cmd)
    return sh(base + list(args), check=check)


def runner_id():
    if os.environ.get("GITHUB_RUN_ID"):
        return f"actions-{os.environ['GITHUB_RUN_ID']}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    return f"laptop-{socket.gethostname()}"


def epoch(iso):
    return calendar.timegm(time.strptime(iso, "%Y-%m-%dT%H:%M:%SZ"))


# ---------------------------------------------------------------- git
def git(repo, *args, check=True):
    return sh(["git", *args], cwd=repo, check=check)


LOOP_DIRS = ("jobs", "runs", "logs")


def loop_dirs(repo):
    return [d for d in LOOP_DIRS if os.path.exists(os.path.join(repo, d))]


def pull(repo):
    """Start every tick from the last commit: a tick that crashed may have left uncommitted files in
    jobs/, runs/ or logs/, which are discarded (a finished session's output stays on Kaggle and is
    collected again).  Then fast-forward to the remote."""
    dirs = loop_dirs(repo)
    if dirs:
        git(repo, "checkout", "--quiet", "HEAD", "--", *dirs)
        git(repo, "clean", "--quiet", "-fd", "--", *dirs)
    if not os.environ.get("HORIZON_NO_PULL"):
        git(repo, "fetch", "--quiet")
        git(repo, "merge", "--quiet", "--ff-only", "@{u}")


def commit_push(repo, msg):
    """Commit everything under jobs/, runs/ and logs/ with a one-line message and push it.  Returns
    False when the push is rejected (another runner moved main first); the local commit is then
    discarded."""
    dirs = loop_dirs(repo)
    git(repo, "add", "-A", "--", *dirs)
    if not git(repo, "status", "--porcelain", "--", *dirs).stdout.strip():
        return True
    git(repo, "commit", "--quiet", "-m", msg)
    say(f"commit: {msg}")
    if os.environ.get("HORIZON_NO_PULL"):
        return True
    r = git(repo, "push", "--quiet", check=False)
    if r.returncode:
        say(f"push rejected; another runner acted first; discarding this tick's commit\n{r.stderr.strip()}")
        git(repo, "fetch", "--quiet")
        git(repo, "reset", "--quiet", "--hard", "@{u}")
        return False
    return True


# ---------------------------------------------------------------- kaggle
def kernel_ref(m):
    user = os.environ.get("KAGGLE_USERNAME")
    if not user:
        raise RuntimeError("KAGGLE_USERNAME is not set")
    return f"{user}/{m['kernel_slug']}"


def prepare_kernel(repo, m, dest):
    os.makedirs(dest, exist_ok=True)
    shutil.copyfile(os.path.join(repo, "kaggle", "runner.ipynb"), os.path.join(dest, "runner.ipynb"))
    meta = read_json(os.path.join(repo, "kaggle", "kernel-metadata.json"))
    meta["id"] = kernel_ref(m)
    meta["title"] = m["kernel_slug"]
    write_json(os.path.join(dest, "kernel-metadata.json"), meta)
    return dest


def kernel_status(ref):
    out = kaggle("kernels", "status", ref).stdout
    mm = re.search(r'has status "(?:KernelWorkerStatus\.)?([A-Za-z_]+)"', out)
    if not mm:
        raise RuntimeError(f"cannot read the kernel status from: {out!r}")
    return mm.group(1).lower()


def kernel_push(folder):
    r = kaggle("kernels", "push", "-p", folder, check=False)
    mm = re.search(r"Kernel version (\d+) successfully pushed", r.stdout)
    if r.returncode or not mm:
        raise RuntimeError(f"kernel push failed: {r.stdout.strip()} {r.stderr.strip()}")
    return int(mm.group(1))


# ---------------------------------------------------------------- checkpoint files too large to commit
def release_tag(m):
    return f"ckpt-{m['campaign']}"


def release_put(m, path, name):
    local = os.environ.get("HORIZON_RELEASE_DIR")
    tag = release_tag(m)
    if local:
        d = os.path.join(local, tag)
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(path, os.path.join(d, name))
        return Path(os.path.join(d, name)).resolve().as_uri()
    if sh(["gh", "release", "view", tag], check=False).returncode:
        sh(["gh", "release", "create", tag, "--prerelease", "--title", tag, "--notes",
            f"Checkpoint files of campaign {m['campaign']} too large to commit (docs/AUTOMATION.md, Section 4). "
            "Not a release of the code."])
    staged = os.path.join(os.path.dirname(path), name)
    if staged != path:
        shutil.copyfile(path, staged)
    sh(["gh", "release", "upload", tag, staged, "--clobber"])
    return f"https://github.com/{m['repository']}/releases/download/{tag}/{name}"


def release_drop(m, name):
    local = os.environ.get("HORIZON_RELEASE_DIR")
    if local:
        p = os.path.join(local, release_tag(m), name)
        if os.path.exists(p):
            os.remove(p)
        return
    sh(["gh", "release", "delete-asset", release_tag(m), name, "-y"], check=False)


def old_release_names(repo, m, chunk_id):
    cj = os.path.join(repo, checkpoint_reldir(m, chunk_id), "checkpoint.json")
    if not os.path.exists(cj):
        return []
    return [i["asset"] for i in read_json(cj)["payload"].values() if i.get("location") == "release"]


# ---------------------------------------------------------------- the log and the halt
def log_line(repo, text):
    p = os.path.join(repo, AUTOLOG)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{now_iso()} {runner_id()} {' '.join(str(text).split())}\n")   # one line per entry


def counts(m):
    out = {}
    for c in m["chunks"]:
        out[c["status"]] = out.get(c["status"], 0) + 1
    return ", ".join(f"{k} {v}" for k, v in sorted(out.items()))


def failure(repo, m, st, chunk, reason, version, nonce):
    chunk["failures"] += 1
    has_ck = os.path.exists(os.path.join(repo, checkpoint_reldir(m, chunk["chunk_id"]), "checkpoint.json"))
    chunk["status"] = "partial" if has_ck else "pending"
    log_line(repo, f"FAILURE chunk {chunk['chunk_id']} kernel version {version} run {nonce}: {reason} "
                   f"(failure {chunk['failures']} of at most {m['max_failures']})")
    if chunk["failures"] >= m["max_failures"]:
        chunk["status"] = "failed"
        st["halted"] = True
        st["halted_at"] = now_iso()
        st["halt_reason"] = f"chunk {chunk['chunk_id']} failed {chunk['failures']} times; last: {reason}"
        text = (f"STATE-ready text: On {now_iso()} the HORIZON loop halted. Chunk {chunk['chunk_id']} "
                f"({chunk['kind']}) failed {chunk['failures']} times, the registered maximum of "
                f"{m['max_failures']}. Last failure: {reason} (kernel version {version}, run {nonce}). "
                f"Chunks of campaign {m['campaign']}: {counts(m)}. The loop does nothing until the cause is "
                f"found and jobs/state.json \"halted\" is set back to false by hand.")
        log_line(repo, "HALT " + text)
        say(text)


# ---------------------------------------------------------------- collect a finished session
def safe_extract(tar_path, dest):
    with tarfile.open(tar_path, "r:gz") as tar:
        for mem in tar.getmembers():
            p = os.path.normpath(mem.name)
            if p.startswith("..") or os.path.isabs(p) or not (mem.isfile() or mem.isdir()):
                raise ValueError(f"unsafe member in bundle: {mem.name}")
        tar.extractall(dest)


def collect(repo, m, st, kstatus):
    d = st["dispatch"]
    chunk = get_chunk(m, d["chunk_id"])
    version, nonce = d.get("kernel_version"), d["nonce"]
    tmp = tempfile.mkdtemp(prefix="horizon-out-")
    problems = []
    try:
        kaggle("kernels", "output", kernel_ref(m), "-p", tmp)
    except RuntimeError as e:
        problems.append(f"output download failed: {str(e)[:300]}")
    found = {}
    for root, _dirs, files in os.walk(tmp):
        for f in files:
            found.setdefault(f, os.path.join(root, f))
    console = found.get("console.log")
    if console:
        dst = os.path.join(repo, "logs", "kaggle", f"{chunk['chunk_id']}__v{version}.log")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(console, dst)
    res = None
    if "result.json" not in found:
        problems.append(f"no result.json in the session output (kernel status {kstatus})")
    else:
        res = read_json(found["result.json"])
        if res.get("nonce") != nonce or res.get("chunk_id") != chunk["chunk_id"]:
            problems.append(f"result belongs to run {res.get('nonce')} / chunk {res.get('chunk_id')}, not to the dispatch")
        elif res.get("status") not in ("done", "partial"):
            problems.append(f"session status {res.get('status')}: {res.get('error', '')}")
        elif res.get("entry_hash") != chunk_entry_hash(m, chunk["chunk_id"]):
            problems.append("result entry hash differs from the manifest entry")
        elif "bundle.tar.gz" not in found or sha256_file(found["bundle.tar.gz"]) != res.get("bundle_sha256"):
            problems.append("bundle.tar.gz missing or its sha256 differs from result.json")
    stage = os.path.join(tmp, "_stage")
    units = {u["unit_id"]: u for u in chunk_units(m, chunk["chunk_id"])}
    if not problems:
        try:
            safe_extract(found["bundle.tar.gz"], stage)
        except Exception as e:      # noqa: BLE001
            problems.append(f"bundle cannot be read: {e!r}")
    if not problems:
        for r in res["rows"]:
            u = units.get(r["unit_id"])
            p = os.path.join(stage, r["path"])
            if u is None:
                problems.append(f"row of unit {r['unit_id']}, which is not in the chunk")
            elif r["path"] != row_relpath(m, u):
                problems.append(f"row {r['path']} is not at {row_relpath(m, u)}")
            elif not os.path.exists(p) or sha256_file(p) != r["sha256"]:
                problems.append(f"row {r['path']} missing or its sha256 differs")
            else:
                row = read_json(p)
                errs = validate_row(row, u["kind"])
                if errs or row["unit_id"] != u["unit_id"] or row["chunk_id"] != chunk["chunk_id"]:
                    problems.append(f"row {r['path']} fails its schema or identity: {errs}")
        ckd = os.path.join(stage, "checkpoint")
        if res["status"] == "partial":
            cj = os.path.join(ckd, "checkpoint.json")
            if not os.path.exists(cj):
                problems.append("a partial session left no checkpoint")
            else:
                ck = read_json(cj)
                if ck["chunk_id"] != chunk["chunk_id"] or ck["entry_hash"] != chunk_entry_hash(m, chunk["chunk_id"]):
                    problems.append("the checkpoint does not belong to this manifest entry")
                for n, info in ck["payload"].items():
                    if sha256_file(os.path.join(ckd, n)) != info["sha256"]:
                        problems.append(f"checkpoint file {n}: sha256 differs")
    if problems:
        failure(repo, m, st, chunk, "; ".join(problems), version, nonce)
        outcome = "failed"
    else:
        outcome = integrate(repo, m, st, chunk, res, stage, version, nonce)
    chunk["sessions"].append(dict(run_nonce=nonce, kernel_version=version, kernel_status=kstatus, outcome=outcome,
                                  units_done_this_session=(res or {}).get("units_done_this_session", []),
                                  ended_at=(res or {}).get("ended_at")))
    for u in m["units"]:
        if u["chunk_id"] == chunk["chunk_id"]:
            u["status"] = "done" if unit_done(repo, m, u) else u.get("status", "pending")
    st["dispatch"] = None
    lp = os.path.join(repo, LOCK)
    if os.path.exists(lp):
        os.remove(lp)
    log_line(repo, f"COLLECT chunk {chunk['chunk_id']} kernel version {version} run {nonce}: {outcome}; "
                   f"chunks {counts(m)}")
    shutil.rmtree(tmp, ignore_errors=True)
    return f"Loop: {chunk['chunk_id']} {outcome} (kernel version {version})"


def integrate(repo, m, st, chunk, res, stage, version, nonce):
    units = {u["unit_id"]: u for u in chunk_units(m, chunk["chunk_id"])}
    before = {uid for uid, u in units.items() if unit_done(repo, m, u)}
    for r in res["rows"]:
        u = units[r["unit_id"]]
        dst = os.path.join(repo, r["path"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(stage, r["path"]), dst)
        write_json(os.path.join(repo, marker_relpath(m, u)),
                   dict(unit_id=u["unit_id"], chunk_id=chunk["chunk_id"], kind=u["kind"], row_path=r["path"],
                        row_sha256=r["sha256"], run_nonce=nonce, kernel_version=version, committed_at=now_iso()))
    after = {uid for uid, u in units.items() if unit_done(repo, m, u)}
    ck_repo = os.path.join(repo, checkpoint_reldir(m, chunk["chunk_id"]))
    old_assets = old_release_names(repo, m, chunk["chunk_id"])
    prev = read_json(os.path.join(ck_repo, "checkpoint.json")) if os.path.exists(os.path.join(ck_repo, "checkpoint.json")) else None
    if after == set(units):                                   # the completion condition, checked here
        if os.path.isdir(ck_repo):
            shutil.rmtree(ck_repo)
        for a in old_assets:
            release_drop(m, a)
        chunk["status"] = "done"
        return "done"
    # partial: progress means a new unit done, or more search nodes expanded than the last checkpoint had
    ckd = os.path.join(stage, "checkpoint")
    ck = read_json(os.path.join(ckd, "checkpoint.json"))
    progress = bool(after - before)
    ip = ck.get("unit_in_progress")
    if not progress and ip:
        old = (prev or {}).get("unit_in_progress")
        a = old["search"]["counts"]["states_expanded"] if old and old["unit_id"] == ip["unit_id"] else 0
        progress = ip["search"]["counts"]["states_expanded"] > a
    if not progress:
        failure(repo, m, st, chunk, "a partial session made no progress", version, nonce)
        return "failed"
    if os.path.isdir(ck_repo):
        shutil.rmtree(ck_repo)
    os.makedirs(ck_repo)
    limit = int(m["payload_commit_limit_bytes"])
    for n, info in ck["payload"].items():
        src = os.path.join(ckd, n)
        if info["bytes"] > limit:
            asset = f"{chunk['chunk_id']}__s{ck['seq']}__{n}"
            info.update(location="release", asset=asset, url=release_put(m, src, asset))
        else:
            shutil.copyfile(src, os.path.join(ck_repo, n))
            info["location"] = "git"
    write_json(os.path.join(ck_repo, "checkpoint.json"), ck)
    for a in old_assets:
        if a not in {i.get("asset") for i in ck["payload"].values()}:
            release_drop(m, a)
    chunk["status"] = "partial"
    return "partial"


# ---------------------------------------------------------------- dispatch
def dispatch(repo, m, st):
    c = select_next(m)
    if c is None:
        n = len(m["chunks"])
        done = sum(x["status"] == "done" for x in m["chunks"])
        if done == n:
            say(f"manifest complete: {done} of {n} chunks done; nothing to do")
        else:
            say(f"no chunk can be dispatched ({counts(m)})")
        return
    lp = os.path.join(repo, LOCK)
    if os.path.exists(lp):
        lk = read_json(lp)
        if time.time() < epoch(lk["expires_at"]):
            say(f"lock held by {lk['holder']} for {lk['chunk_id']} until {lk['expires_at']}; nothing to do")
            return
        log_line(repo, f"STALE LOCK of {lk['holder']} for {lk['chunk_id']} expired at {lk['expires_at']}; removed")
    nonce = f"{m['campaign']}-{c['chunk_id']}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(3)}"
    limit = float(m["session"]["platform_limit_seconds"]) + 3600
    write_json(lp, dict(holder=runner_id(), chunk_id=c["chunk_id"], nonce=nonce, acquired_at=now_iso(),
                        expires_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + limit))))
    st["dispatch"] = dict(chunk_id=c["chunk_id"], nonce=nonce, entry_hash=chunk_entry_hash(m, c["chunk_id"]),
                          runner=runner_id(), dispatched_at=now_iso(), kernel_version=None, pushed_at=None)
    reached_chunk(repo, st)
    c["status"] = "running"
    c["attempts"] += 1
    save(repo, m, st)
    log_line(repo, f"DISPATCH chunk {c['chunk_id']} ({c['kind']}) attempt {c['attempts']} run {nonce}")
    if not commit_push(repo, f"Loop: dispatch {c['chunk_id']} (attempt {c['attempts']})"):
        return
    folder = prepare_kernel(repo, m, tempfile.mkdtemp(prefix="horizon-kernel-"))
    try:
        v = kernel_push(folder)
    except RuntimeError as e:
        st["dispatch"] = None
        os.remove(lp)
        failure(repo, m, st, c, f"kernel push failed: {str(e)[:300]}", None, nonce)
        save(repo, m, st)
        commit_push(repo, f"Loop: kernel push failed for {c['chunk_id']}")
        return
    st["dispatch"].update(kernel_version=v, pushed_at=now_iso())
    save(repo, m, st)
    log_line(repo, f"PUSHED chunk {c['chunk_id']} as kernel version {v} run {nonce}")
    commit_push(repo, f"Loop: {c['chunk_id']} pushed as kernel version {v}")


def save(repo, m, st):
    save_manifest(repo, m)
    write_json(os.path.join(repo, STATE), st)


def reached_chunk(repo, st):
    """The tick has reached a chunk (it obtained the kernel status of the chunk in flight, or chose a
    chunk to dispatch): the count of consecutive crashes goes back to 0.  Returns True if it changed."""
    n = int(st.get("consecutive_crashes") or 0)
    if not n:
        return False
    st["consecutive_crashes"] = 0
    log_line(repo, f"CRASH COUNT reset to 0 (was {n}): this tick reached a chunk")
    return True


def record_crash(repo, reason):
    """A tick that ended with an error, or a workflow step before the tick that failed, adds 1 to the
    count of consecutive crashes in jobs/state.json; at MAX_CRASHES the loop halts, as a failing chunk
    halts it.  Best effort: if the repository cannot be restored, read or pushed (GitHub unreachable),
    the crash is printed and not recorded."""
    try:
        pull(repo)
    except Exception as e:  # noqa: BLE001 -- recorded locally if the remote is unreachable
        say(f"crash record: could not fast-forward ({e}); recording on the local commit")
    st = read_json(os.path.join(repo, STATE))
    if st.get("halted"):
        say(f"crash not counted: the loop is already halted ({st.get('halt_reason')})")
        return
    n = int(st.get("consecutive_crashes") or 0) + 1
    st["consecutive_crashes"] = n
    reason = " ".join(str(reason).split())[:600]
    log_line(repo, f"CRASH {n} of at most {MAX_CRASHES} consecutive: {reason}")
    if n >= MAX_CRASHES:
        try:
            chunks = counts(load_manifest(repo))
        except Exception as e:  # noqa: BLE001 -- the manifest itself may be the cause
            chunks = f"not readable ({type(e).__name__})"
        st["halted"] = True
        st["halted_at"] = now_iso()
        st["halt_reason"] = f"{n} consecutive ticks crashed; last: {reason}"
        text = (f"STATE-ready text: On {now_iso()} the HORIZON loop halted. {n} consecutive ticks crashed, the "
                f"registered maximum of {MAX_CRASHES}, without a tick reaching a chunk in between. Last crash: "
                f"{reason}. Chunks of the campaign: {chunks}. The loop does nothing until the cause is found "
                f"and jobs/state.json \"halted\" is set back to false and \"consecutive_crashes\" to 0 by hand.")
        log_line(repo, "HALT " + text)
        say(text)
    write_json(os.path.join(repo, STATE), st)
    msg = f"Loop: tick crashed ({n} of {MAX_CRASHES})" + ("; loop halted" if n >= MAX_CRASHES else "")
    try:
        commit_push(repo, msg)
    except Exception as e:  # noqa: BLE001
        say(f"crash record not pushed: {e}")


def tick(repo):
    """One tick; an error anywhere in it is recorded as a crash (record_crash) and the exit code is 1."""
    try:
        return _tick(repo)
    except Exception as e:  # noqa: BLE001 -- every error of a tick is a crash
        import traceback
        traceback.print_exc()
        record_crash(repo, f"{type(e).__name__}: {e}")
        return 1


def _tick(repo):
    pull(repo)
    m = load_manifest(repo)
    errs = check_manifest(m)
    if errs:
        raise RuntimeError(f"manifest check failed: {errs}")
    st = read_json(os.path.join(repo, STATE))
    if st.get("halted"):
        say(f"loop halted since {st.get('halted_at')}: {st.get('halt_reason')}; nothing done")
        return 0
    d = st.get("dispatch")
    if d:
        ks = kernel_status(kernel_ref(m))
        reset = reached_chunk(repo, st)
        started = d.get("pushed_at") or d["dispatched_at"]
        overdue = time.time() - epoch(started) > float(m["session"]["platform_limit_seconds"]) + 1800
        if ks in RUNNING and not overdue:
            say(f"{d['chunk_id']} on kernel version {d.get('kernel_version')} is {ks} (pushed {started}); nothing to do")
            if reset:
                write_json(os.path.join(repo, STATE), st)
                commit_push(repo, "Loop: crash count reset")
            return 0
        if ks in RUNNING:
            chunk = get_chunk(m, d["chunk_id"])
            failure(repo, m, st, chunk, f"session overdue ({ks} since {started})", d.get("kernel_version"), d["nonce"])
            chunk["sessions"].append(dict(run_nonce=d["nonce"], kernel_version=d.get("kernel_version"),
                                          kernel_status=ks, outcome="failed", units_done_this_session=[], ended_at=None))
            st["dispatch"] = None
            if os.path.exists(os.path.join(repo, LOCK)):
                os.remove(os.path.join(repo, LOCK))
            msg = f"Loop: {d['chunk_id']} overdue (kernel version {d.get('kernel_version')})"
        else:
            msg = collect(repo, m, st, ks)
        save(repo, m, st)
        if not commit_push(repo, msg):
            return 0
        if st.get("halted"):
            return 0
    dispatch(repo, m, st)
    return 0


def next_wake(repo, lo, hi):
    """Seconds until the next tick is worth running, or None when the loop has nothing left to do
    (halted, or every chunk done with nothing in flight).  Read from the committed files only."""
    m = load_manifest(repo)
    st = read_json(os.path.join(repo, STATE))
    if st.get("halted"):
        return None, f"halted since {st.get('halted_at')}"
    d = st.get("dispatch")
    if not d and all(c["status"] == "done" for c in m["chunks"]):
        return None, f"manifest complete: {counts(m)}"
    if not d and select_next(m) is None:
        return None, f"no chunk can run: {counts(m)}"
    if d and d.get("pushed_at"):
        end = epoch(d["pushed_at"]) + float(m["session"]["work_seconds"]) + float(m["session"]["checkpoint_reserve_seconds"])
        left = int(end - time.time())
        return max(lo, min(hi, left)), f"{d['chunk_id']} on kernel version {d.get('kernel_version')}, session due to end in {left} s"
    return lo, "work remains and nothing is in flight"


def status(repo):
    m = load_manifest(repo)
    st = read_json(os.path.join(repo, STATE))
    print(f"campaign {m['campaign']}, code tag {m['code_tag']}; chunks: {counts(m)}")
    for c in m["chunks"]:
        print(f"  {c['chunk_id']} {c['kind']} {c['status']} attempts {c['attempts']} failures {c['failures']} "
              f"sessions {[(s['kernel_version'], s['outcome']) for s in c['sessions']]}")
    print(f"dispatch: {json.dumps(st.get('dispatch'))}; halted: {st.get('halted')}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="the HORIZON loop")
    ap.add_argument("command", choices=("tick", "status", "prepare-kernel", "next-wake", "record-crash"))
    ap.add_argument("--reason", default="a workflow step before the tick failed", help="record-crash: the cause")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--dir", help="folder for prepare-kernel")
    ap.add_argument("--min", type=int, default=300, help="next-wake: shortest sleep, seconds")
    ap.add_argument("--max", type=int, default=1800, help="next-wake: longest sleep, seconds")
    a = ap.parse_args(argv)
    if a.command == "record-crash":
        record_crash(a.repo, a.reason)
        return 0
    if a.command == "next-wake":
        secs, why = next_wake(a.repo, a.min, a.max)
        print(f"{'none' if secs is None else secs} {why}")
        return 0
    if a.command == "tick":
        return tick(a.repo)
    if a.command == "status":
        status(a.repo)
        return 0
    if not a.dir:
        ap.error("prepare-kernel needs --dir")
    print(prepare_kernel(a.repo, load_manifest(a.repo), a.dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
