"""
check_runner_freeze.py -- is kaggle/requirements-runner.txt a complete freeze for the Kaggle image that stage D
ran on (docs/STATE.md, amendment s)?

The runner installs the file into Kaggle's image, not into an empty environment, so check_freeze.sh's empty
install does not apply here; and there is no Python 3.13 on the laptop.  This checks instead, from committed
files and PyPI only:
    1. every line of the file is an exact pin;
    2. pip download --no-deps of each pinned file as a wheel for Kaggle's platform (manylinux x86_64, CPython
       3.13, read from logs/envprobe.log), so that every pin can be installed there without building;
    3. every requirement each wheel declares (extras left out, markers evaluated for that platform) names a
       package pinned in the file, at a version the requirement allows; so pip has nothing left to choose;
    4. every module outside the standard library that scripts/automation imports (tests left out) is provided
       by a pinned package;
    5. the pins equal the versions the probe found installed on stage D's image (logs/envprobe.log).
The import of these exact versions on that image is in logs/envprobe.log ("imported").
Since 14 November 2026 the probe log read is logs/envprobe_v4.log, the probe of the pins of code tag automation-v4
(JPype1 and packaging added; the JDK and GVGAI build checked there); modules that scripts/automation imports from
scripts/ or from the copies under third_party/study1/scripts come with the clone and count as local.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\automation\\check_runner_freeze.py > logs\\check_runner_freeze.log
Expected last line: OK
"""
from __future__ import annotations

import ast
import email.parser
import glob
import os
import re
import subprocess
import sys
import tempfile
import zipfile

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REQ = os.path.join(REPO, "kaggle", "requirements-runner.txt")
# the probe of the pins of code tag automation-v4 (14 November 2026); logs/envprobe.log is the probe of 1 November
PROBE_LOG = os.path.join(REPO, "logs", "envprobe_v4.log")
# the module a distribution provides, where the names differ
PROVIDES = {"numpy": "numpy", "gymnasium": "gymnasium", "minigrid": "minigrid", "JPype1": "jpype"}
# modules of this repository that scripts/automation imports from outside its folder (scripts/ and the copies of
# study 1 under third_party/study1/scripts); they come with the clone, not from pip
REPO_MODULES = ("scripts", os.path.join("third_party", "study1", "scripts"))


def main():
    fails = []

    def check(c, msg):
        print(("ok   " if c else "FAIL ") + msg)
        if not c:
            fails.append(msg)

    log = open(PROBE_LOG, encoding="utf-8").read()
    m = re.search(r"probe python: (\d+)\.(\d+)\.(\d+) .*\((CPython), (x86_64),", log)
    pyver = f"{m.group(1)}.{m.group(2)}"
    print(f"Kaggle's Python from logs/envprobe.log: {m.group(1)}.{m.group(2)}.{m.group(3)} {m.group(4)} {m.group(5)}")
    image = re.search(r"probe image: (\S+)", log).group(1)
    print(f"probe image: {image}")
    probe_tree = dict(re.findall(r"^    ([A-Za-z0-9_.-]+)==(\S+)$",
                                 log.split("as installed:")[1].split("packages the install")[0], re.M))
    env = dict(os_name="posix", sys_platform="linux", platform_system="Linux", platform_machine="x86_64",
               platform_python_implementation="CPython", implementation_name="cpython",
               python_version=pyver, python_full_version=f"{pyver}.{m.group(3)}", extra="")

    lines = [x.strip() for x in open(REQ, encoding="utf-8") if x.strip() and not x.lstrip().startswith("#")]
    pins = {}
    for x in lines:
        mm = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)", x)
        check(bool(mm), f"step 1: exact pin: {x}")
        if mm:
            pins[canonicalize_name(mm.group(1))] = mm.group(2)
    print(f"pins: {len(pins)}")

    tmp = tempfile.mkdtemp(prefix="runner-freeze-")
    plat = []
    for p in ("manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64", "linux_x86_64"):
        plat += ["--platform", p]
    r = subprocess.run([sys.executable, "-m", "pip", "download", "--quiet", "--disable-pip-version-check",
                        "--no-deps", "--only-binary=:all:", "--python-version", pyver, "--implementation", "cp",
                        *plat, "-d", tmp, "-r", REQ], capture_output=True, text=True)
    check(r.returncode == 0, f"step 2: every pin has a wheel for CPython {pyver} manylinux x86_64"
                             + ("" if r.returncode == 0 else f": {r.stderr.strip()[-400:]}"))
    wheels = sorted(glob.glob(os.path.join(tmp, "*.whl")))
    print(f"wheels: {len(wheels)}")
    for w in wheels:
        print(f"    {os.path.basename(w)}")
    check(len(wheels) == len(pins), "step 2: one wheel per pin")

    for w in wheels:
        with zipfile.ZipFile(w) as z:
            meta = [n for n in z.namelist() if n.endswith(".dist-info/METADATA")][0]
            msg = email.parser.Parser().parsestr(z.read(meta).decode("utf-8"))
        name = canonicalize_name(msg["Name"])
        for req in msg.get_all("Requires-Dist") or []:
            rq = Requirement(req)
            if rq.marker is not None and not rq.marker.evaluate(env):
                continue
            n = canonicalize_name(rq.name)
            ok = n in pins and rq.specifier.contains(pins[n], prereleases=True)
            check(ok, f"step 3: {name} {msg['Version']} needs {rq.name}{rq.specifier or ''}: "
                      f"pinned {pins.get(n, 'NOT PINNED')}")

    d = os.path.join(REPO, "scripts", "automation")
    local = {f[:-3] for f in os.listdir(d) if f.endswith(".py")}
    for rel in REPO_MODULES:
        local |= {f[:-3] for f in os.listdir(os.path.join(REPO, rel)) if f.endswith(".py")}
    mods = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith(".py") or f.startswith("test_") or f in ("check_runner_freeze.py", "envprobe.py"):
            continue
        for n in ast.walk(ast.parse(open(os.path.join(d, f), encoding="utf-8").read())):
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else \
                [n.module] if isinstance(n, ast.ImportFrom) and n.module and n.level == 0 else []
            for x in names:
                top = x.split(".")[0]
                if top not in sys.stdlib_module_names and top not in local:
                    mods.setdefault(top, set()).add(f)
    for mod, files in sorted(mods.items()):
        dist = {v: k for k, v in PROVIDES.items()}.get(mod)
        check(dist is not None and canonicalize_name(dist) in pins,
              f"step 4: module {mod} (imported by {', '.join(sorted(files))}) comes from a pinned package")

    probe = {canonicalize_name(k): v for k, v in probe_tree.items()}
    check(probe == pins, f"step 5: the pins equal the versions the probe found on the image: "
                         f"{sorted(pins.items())} against {sorted(probe.items())}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
