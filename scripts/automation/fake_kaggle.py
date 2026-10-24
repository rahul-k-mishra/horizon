"""
fake_kaggle.py -- a stand-in for the Kaggle command-line tool, for scripts/automation/test_loop.py only.

    kernels push -p DIR        runs the notebook's code cell at once, in this process's child, with
                               HORIZON_REPO_URL, HORIZON_WORKING and HORIZON_TMP pointing into the store,
                               and prints "Kernel version N successfully pushed."
    kernels status REF         prints that REF has status "KernelWorkerStatus.COMPLETE"
    kernels output REF -p DIR  copies the latest version's working folder into DIR
The store is the folder named by FAKE_KAGGLE_STORE; the repository URL by FAKE_KAGGLE_REPO_URL.
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
        print(f'{argv[2]} has status "KernelWorkerStatus.COMPLETE"')
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
