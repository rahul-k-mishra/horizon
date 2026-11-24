"""
test_gvgai_setup_race.py -- three worker processes set up GVGAI in one empty cache folder at the same time, as the
runner's pool does in a Kaggle session (the dry run of 23 November 2026 failed there with FileNotFoundError;
docs/STATE.md, amendment ac).

    control  ensure_jdk_unlocked and build_unlocked, the code of automation-v4: at least one worker must fail
    locked   ensure_jdk and build, which take sim_gvgai.setup_lock: every worker must succeed, and all must
             return the same JDK home and classes folder

The JDK download is replaced by a slow copy of the pinned archive from a local file (HORIZON_JDK_ARCHIVE, or
the Temurin archive found in HORIZON_GVGAI_CACHE or the default cache), so the test does not depend on the
network and the copy is slow enough for the workers to overlap.  Its sha256 is still checked by ensure_jdk.

    python scripts/automation/test_gvgai_setup_race.py > logs/test_gvgai_setup_race.log
"""
from __future__ import annotations

import concurrent.futures as cf
import os
import shutil
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import sim_gvgai  # noqa: E402

WORKERS = 3


def archive():
    t = sim_gvgai.TEMURIN["windows" if os.name == "nt" else "linux"]
    cands = [os.environ.get("HORIZON_JDK_ARCHIVE")]
    for d in (os.environ.get("HORIZON_GVGAI_CACHE"), os.path.join(tempfile.gettempdir(), "horizon-gvgai"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "gvgai-cache")):
        if d:
            cands.append(os.path.join(d, t["name"]))
    for c in cands:
        if c and os.path.exists(c) and sim_gvgai.sha256_file(c) == t["sha256"]:
            return c
    raise SystemExit("no local copy of the pinned JDK archive; set HORIZON_JDK_ARCHIVE")


def worker(args):
    cache, src, locked = args

    def slow_copy(url, dst):
        with open(src, "rb") as a, open(dst, "wb") as b:
            while True:
                c = a.read(1 << 22)
                if not c:
                    break
                b.write(c)
                time.sleep(0.05)
    urllib.request.urlretrieve = slow_copy
    os.environ.pop("JAVA_HOME", None)
    try:
        if locked:
            jdk = sim_gvgai.ensure_jdk(cache)
            classes = sim_gvgai.build(jdk, cache)
        else:
            jdk = sim_gvgai.ensure_jdk_unlocked(cache)
            classes = sim_gvgai.build_unlocked(jdk, cache)
        return "ok", os.path.relpath(jdk, cache), os.path.relpath(classes, cache)
    except Exception as e:  # noqa: BLE001 -- the error is the result of the control
        return "error", type(e).__name__, None


def run(src, locked):
    cache = tempfile.mkdtemp(prefix="gvgai-race-")
    try:
        with cf.ProcessPoolExecutor(WORKERS) as ex:
            return list(ex.map(worker, [(cache, src, locked)] * WORKERS))
    finally:
        shutil.rmtree(cache, ignore_errors=True)


def main():
    src = archive()
    print(f"platform {os.name}; {WORKERS} workers on one empty cache folder; JDK archive copied from a local file")
    ok = True
    ctl = run(src, locked=False)
    print(f"control (no lock): {ctl}")
    if all(r[0] == "ok" for r in ctl):
        print("note: the control did not fail on this run; the race depends on timing")
    res = run(src, locked=True)
    print(f"locked: {res}")
    if not all(r[0] == "ok" for r in res):
        ok = False
        print("FAIL: a worker failed under the lock")
    if len({(r[1], r[2]) for r in res}) != 1:
        ok = False
        print("FAIL: the workers returned different JDK homes or classes folders")
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
