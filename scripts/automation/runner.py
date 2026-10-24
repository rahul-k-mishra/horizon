"""
runner.py -- runs one chunk inside a Kaggle CPU session (docs/AUTOMATION.md, Sections 3 and 4).
Started by kaggle/runner.ipynb; standard library only.

    1. Read jobs/state.json of the state checkout (the repository's main branch as cloned at session
       start).  No dispatch: write result.json with status "idle" and stop (the registration run).
    2. Check the manifest and the dispatched chunk: the chunk's entry hash (common.chunk_entry_hash)
       must equal the hash the loop recorded when it dispatched the chunk.
    3. Compute the session deadline from the session's start time t0: work stops at
       t0 + session.work_seconds; the checkpoint must be written and verified by
       t0 + session.work_seconds + session.checkpoint_reserve_seconds.
    4. Find the chunk's committed checkpoint, if any, verify it against the manifest entry and the
       recorded file hashes, and continue from it.  Units with a valid done-marker are skipped.
    5. Run the units in order.  An agent unit (one seed) starts only if its wall-clock cap fits before
       the deadline.  A search unit runs until it completes, hits a cap, or reaches the deadline.
       Checkpoints are written at the registered interval (seconds and work units) and at the end of an
       unfinished session.
    6. Write /kaggle/working/result.json and /kaggle/working/bundle.tar.gz (rows and checkpoint).  The
       chunk is reported "done" only when every unit has a row; otherwise "partial".  Any exception
       gives status "failed" with its traceback, and the runner still exits normally, so that the
       session ends "complete" and the loop collects the evidence.
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import sys
import tarfile
import time
import traceback
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import (STATE, check_manifest, checkpoint_reldir, chunk_entry_hash, chunk_units, get_chunk,  # noqa: E402
                    load_manifest, now_iso, read_json, row_relpath, sha256_file, unit_done, unit_params,
                    write_json)
from jobs import SearchState, run_agent, run_search, session_entry  # noqa: E402
from schema import validate_row  # noqa: E402

CKPT = "horizon.checkpoint.v1"
RESULT = "horizon.result.v1"


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def fetch_checkpoint(state_repo, m, chunk_id, dest):
    """Copy the committed checkpoint of a chunk into dest, fetching release-held files by URL.
    Returns its checkpoint.json, or None if the chunk has none."""
    src = os.path.join(state_repo, checkpoint_reldir(m, chunk_id))
    cj = os.path.join(src, "checkpoint.json")
    if not os.path.exists(cj):
        return None
    ck = read_json(cj)
    os.makedirs(dest, exist_ok=True)
    for name, info in ck["payload"].items():
        target = os.path.join(dest, name)
        if info.get("location") == "release":
            with urllib.request.urlopen(info["url"]) as r, open(target, "wb") as f:
                shutil.copyfileobj(r, f)
        else:
            shutil.copyfile(os.path.join(src, name), target)
        if sha256_file(target) != info["sha256"]:
            raise ValueError(f"checkpoint file {name}: sha256 differs from checkpoint.json")
    return ck


class Session:
    def __init__(self, args):
        self.state_repo, self.out = args.state_repo, args.out
        self.t0 = args.t0 if args.t0 else time.time()
        self.started = iso(self.t0)
        self.work_dir = args.work_dir
        self.stage = os.path.join(args.work_dir, "stage")
        self.result = dict(schema=RESULT, host=socket.gethostname(), t0=self.started, status="failed",
                           rows=[], checkpoint=None, units_done=[], units_done_this_session=[], progress={})
        self.seq = 0

    def say(self, s):
        print(f"[{now_iso()}] {s}", flush=True)

    def write_checkpoint(self, m, chunk, done, in_progress, nonce):
        """Write stage/checkpoint/: checkpoint.json and its payload, then re-read and verify it."""
        d = os.path.join(self.stage, "checkpoint")
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
        self.seq += 1
        ip = None
        if in_progress is not None:
            unit, st = in_progress
            meta = st.save(d, os.path.join(self.work_dir, "search"))
            ip = dict(unit_id=unit["unit_id"], search=meta)
        payload = {n: dict(sha256=sha256_file(os.path.join(d, n)), bytes=os.path.getsize(os.path.join(d, n)))
                   for n in sorted(os.listdir(d))}
        ck = dict(schema=CKPT, campaign=m["campaign"], chunk_id=chunk["chunk_id"], kind=chunk["kind"],
                  entry_hash=chunk_entry_hash(m, chunk["chunk_id"]), seq=self.seq, units_done=sorted(done),
                  unit_in_progress=ip, payload=payload, run_nonce=nonce, written_at=now_iso())
        write_json(os.path.join(d, "checkpoint.json"), ck)
        back = read_json(os.path.join(d, "checkpoint.json"))       # verify what was written
        assert back == ck, "checkpoint.json does not read back equal"
        for n, info in payload.items():
            assert sha256_file(os.path.join(d, n)) == info["sha256"], f"checkpoint file {n} changed"
        self.say(f"checkpoint {self.seq}: {len(done)} units done, in progress "
                 f"{ip['unit_id'] if ip else 'none'}, {len(payload)} payload files")
        return ck

    def run(self):
        st = read_json(os.path.join(self.state_repo, STATE))
        d = st.get("dispatch")
        if not d:
            self.result["status"] = "idle"
            self.say("no dispatch in jobs/state.json: nothing to run (registration run)")
            return
        nonce = d["nonce"]
        self.result.update(chunk_id=d["chunk_id"], nonce=nonce)
        m = load_manifest(self.state_repo)
        errs = check_manifest(m)
        if errs:
            raise ValueError(f"manifest check failed: {errs}")
        chunk = get_chunk(m, d["chunk_id"])
        eh = chunk_entry_hash(m, chunk["chunk_id"])
        if eh != d["entry_hash"]:
            raise ValueError("the manifest entry of the dispatched chunk differs from the dispatch record")
        self.result.update(entry_hash=eh, campaign=m["campaign"], kind=chunk["kind"])
        s = m["session"]
        deadline = self.t0 + float(s["work_seconds"])
        hard_stop = deadline + float(s["checkpoint_reserve_seconds"])
        self.result.update(deadline=iso(deadline), hard_stop=iso(hard_stop))
        self.say(f"chunk {chunk['chunk_id']} ({chunk['kind']}), nonce {nonce}; work deadline {iso(deadline)}, "
                 f"checkpoint by {iso(hard_stop)}")

        units = [dict(u, campaign=m["campaign"]) for u in chunk_units(m, chunk["chunk_id"])]
        done = {u["unit_id"] for u in units if unit_done(self.state_repo, m, u)}
        ck_dir = os.path.join(self.work_dir, "ckpt_in")
        ck = fetch_checkpoint(self.state_repo, m, chunk["chunk_id"], ck_dir)
        resume = None
        if ck is not None:
            if ck["schema"] != CKPT or ck["chunk_id"] != chunk["chunk_id"] or ck["kind"] != chunk["kind"] \
                    or ck["entry_hash"] != eh:
                raise ValueError("the committed checkpoint does not belong to this manifest entry")
            self.seq = int(ck["seq"])
            missing = set(ck["units_done"]) - done
            if missing:
                raise ValueError(f"checkpoint lists units done without valid done-markers: {sorted(missing)}")
            if ck["unit_in_progress"]:
                ip = ck["unit_in_progress"]
                resume = (ip["unit_id"], SearchState.load(ck_dir, ip["search"], os.path.join(self.work_dir, "search")))
            self.say(f"resuming from checkpoint {ck['seq']} of run {ck['run_nonce']}: {len(done)} units done, "
                     f"in progress {resume[0] if resume else 'none'}")
        else:
            self.say(f"no checkpoint: starting the chunk; {len(done)} units already have done-markers")
        start_done = set(done)
        stop_reason = None

        for u in units:
            if u["unit_id"] in done:
                continue
            p = unit_params(m, u)
            if chunk["kind"] == "agent":
                left = deadline - time.time()
                if left < float(p["unit_seconds_cap"]):
                    stop_reason = f"deadline: {left:.0f} s left, a seed needs up to {p['unit_seconds_cap']} s"
                    break
                self.say(f"agent unit {u['unit_id']} (seed {u['seed']}): start")
                row = run_agent(u, p, nonce, self.started)
            else:
                state = resume[1] if resume and resume[0] == u["unit_id"] else None
                self.say(f"search unit {u['unit_id']}: {'resume' if state else 'start'}")

                def on_ck(stt, u=u):
                    self.write_checkpoint(m, chunk, done, (u, stt), nonce)
                status, row, stt = run_search(u, p, os.path.join(self.work_dir, "search"), state, deadline, on_ck,
                                              nonce, self.started)
                self.result["progress"][u["unit_id"]] = dict(states_expanded=stt.counts["states_expanded"])
                if status == "stopped":
                    stt.sessions.append(session_entry(nonce, self.started))
                    self.write_checkpoint(m, chunk, done, (u, stt), nonce)
                    stop_reason = "deadline reached inside a search unit"
                    break
                self.say(f"search unit {u['unit_id']}: {status}, {stt.counts['states_seen']} states seen")
            errs = validate_row(row, chunk["kind"])
            if errs:
                raise ValueError(f"row of {u['unit_id']} fails its schema: {errs}")
            rel = row_relpath(m, u)
            write_json(os.path.join(self.stage, rel), row)
            self.result["rows"].append(dict(unit_id=u["unit_id"], path=rel,
                                            sha256=sha256_file(os.path.join(self.stage, rel))))
            done.add(u["unit_id"])
            if chunk["kind"] == "agent":
                self.write_checkpoint(m, chunk, done, None, nonce)   # every unit: the seed boundary
        all_done = all(u["unit_id"] in done for u in units)
        if all_done:
            shutil.rmtree(os.path.join(self.stage, "checkpoint"), ignore_errors=True)
        elif not os.path.exists(os.path.join(self.stage, "checkpoint", "checkpoint.json")):
            self.write_checkpoint(m, chunk, done, None, nonce)
        if os.path.exists(os.path.join(self.stage, "checkpoint", "checkpoint.json")):
            ckd = os.path.join(self.stage, "checkpoint")
            self.result["checkpoint"] = {n: sha256_file(os.path.join(ckd, n)) for n in sorted(os.listdir(ckd))}
        self.result.update(status="done" if all_done else "partial", stop_reason=stop_reason,
                           units_done=sorted(done), units_done_this_session=sorted(done - start_done),
                           before_hard_stop=time.time() <= hard_stop)
        self.say(f"chunk {chunk['chunk_id']}: {self.result['status']}; units done {len(done)} of {len(units)}"
                 + (f"; stopped: {stop_reason}" if stop_reason else ""))

    def finish(self):
        os.makedirs(self.out, exist_ok=True)
        os.makedirs(self.stage, exist_ok=True)
        with tarfile.open(os.path.join(self.out, "bundle.tar.gz"), "w:gz") as tar:
            for name in sorted(os.listdir(self.stage)):
                tar.add(os.path.join(self.stage, name), arcname=name)
        self.result["bundle_sha256"] = sha256_file(os.path.join(self.out, "bundle.tar.gz"))
        self.result["ended_at"] = now_iso()
        write_json(os.path.join(self.out, "result.json"), self.result)
        self.say(f"wrote result.json (status {self.result['status']}) and bundle.tar.gz")


def main(argv=None):
    ap = argparse.ArgumentParser(description="run one dispatched chunk")
    ap.add_argument("--state-repo", required=True)
    ap.add_argument("--out", default="/kaggle/working")
    ap.add_argument("--work-dir", default=os.path.join("/tmp", "horizon-work"))
    ap.add_argument("--t0", type=float, default=None, help="session start, seconds since the epoch")
    args = ap.parse_args(argv)
    if os.path.isdir(args.work_dir):
        shutil.rmtree(args.work_dir)
    os.makedirs(args.work_dir)
    s = Session(args)
    try:
        s.run()
    except Exception as e:          # the evidence goes back to the loop, which counts a failure
        s.result.update(status="failed", error=repr(e)[:500], trace=traceback.format_exc()[-3000:])
        s.say(f"FAILED: {e!r}")
    s.finish()
    return 0


if __name__ == "__main__":
    sys.exit(main())
