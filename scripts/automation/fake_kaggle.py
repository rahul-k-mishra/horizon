"""
fake_kaggle.py -- a stand-in for the Kaggle command-line tool, for scripts/automation/test_loop.py only.

    kernels push -p DIR        runs the notebook's code cell at once, in this process's child, with
                               HORIZON_REPO_URL, HORIZON_WORKING and HORIZON_TMP pointing into the store,
                               and prints "Kernel version N successfully pushed."
    kernels status REF         prints that REF has status "KernelWorkerStatus.COMPLETE"
    kernels output REF -p DIR  copies the latest version's working folder into DIR
The store is the folder named by FAKE_KAGGLE_STORE; the repository URL by FAKE_KAGGLE_REPO_URL.
Two optional files in the store script what Kaggle answers (scripts/automation/test_loop.py, refusal scenario):
    refuse.json   {"left": n, "message": "...", "mode": "field" | "http"}: the next n pushes are refused and run
                  nothing.  "field" prints "Kernel push error: <message>" and exits 0, as kaggle 2.2.4 does when
                  the server's answer carries an error; "http" prints the message to stderr and exits 1, as it
                  does on an HTTP error.  "norun" accepts the push, gives it a version and runs nothing (a session
                  that never starts: its output folder stays empty).
    status.json   a list of statuses ("QUEUED", "RUNNING", "ERROR|<failure message>", "WEIRD", ...); each status
                  call takes the first; an empty or missing list answers COMPLETE.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys


def main(argv):
    store = os.environ["FAKE_KAGGLE_STORE"]
    os.makedirs(store, exist_ok=True)
    vf = os.path.join(store, "version")
    if argv[:2] == ["kernels", "push"]:
        rf = os.path.join(store, "refuse.json")
        rs = json.load(open(rf, encoding="utf-8")) if os.path.exists(rf) else {}
        if rs.get("left", 0) > 0:
            rs["left"] -= 1
            json.dump(rs, open(rf, "w", encoding="utf-8"))
            if rs.get("mode") == "norun":
                v = int(open(vf).read()) + 1 if os.path.exists(vf) else 1
                open(vf, "w").write(str(v))
                os.makedirs(os.path.join(store, f"v{v}", "working"), exist_ok=True)
                print(f"Kernel version {v} successfully pushed.  Please check progress at fake://{v}")
                return 0
            if rs.get("mode") == "http":
                print(rs["message"], file=sys.stderr)
                return 1
            print(f"Kernel push error: {rs['message']}")
            return 0
        folder = argv[argv.index("-p") + 1]
        nb = json.load(open(os.path.join(folder, "runner.ipynb"), encoding="utf-8"))
        code = "".join(nb["cells"][0]["source"])
        v = int(open(vf).read()) + 1 if os.path.exists(vf) else 1
        open(vf, "w").write(str(v))
        base = os.path.join(store, f"v{v}")
        env = dict(os.environ, HORIZON_REPO_URL=os.environ["FAKE_KAGGLE_REPO_URL"],
                   HORIZON_WORKING=os.path.join(base, "working"), HORIZON_TMP=os.path.join(base, "tmp"))
        os.makedirs(env["HORIZON_TMP"], exist_ok=True)
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
        open(os.path.join(base, "notebook_stdout.txt"), "w", encoding="utf-8").write(r.stdout + r.stderr)
        print(f"Kernel version {v} successfully pushed.  Please check progress at fake://{v}")
        return 0
    if argv[:2] == ["kernels", "status"]:
        sf = os.path.join(store, "status.json")
        seq = json.load(open(sf, encoding="utf-8")) if os.path.exists(sf) else []
        ks, _, msg = (seq.pop(0) if seq else "COMPLETE").partition("|")
        json.dump(seq, open(sf, "w", encoding="utf-8"))
        print(f'{argv[2]} has status "KernelWorkerStatus.{ks}"')
        if msg:
            print(f'Failure message: "{msg}"')
        return 0
    if argv[:2] == ["kernels", "output"]:
        dest = argv[argv.index("-p") + 1]
        v = int(open(vf).read())
        src = os.path.join(store, f"v{v}", "working")
        os.makedirs(dest, exist_ok=True)
        for n in os.listdir(src):
            shutil.copyfile(os.path.join(src, n), os.path.join(dest, n))
        return 0
    print(f"fake_kaggle: unsupported {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
