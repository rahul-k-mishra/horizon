"""
envprobe.py -- push the environment probe (kaggle/envprobe/probe.ipynb) to Kaggle once, and collect what it
found: the Kaggle image's digest, its Python, and the exact version of every package that
kaggle/requirements-runner.txt needs there (docs/STATE.md, amendment s).  The probe is a notebook of its own,
<user>/horizon-envprobe, apart from the runner and the campaign; it runs no search.

    python scripts/automation/envprobe.py push --user <kaggle account>
    python scripts/automation/envprobe.py collect --user <kaggle account> > logs/envprobe.log
    python scripts/automation/envprobe.py push --user <account> --docker-image gcr.io/kaggle-images/python@sha256:<digest>
        asks Kaggle for that image (does the metadata pin the image?); collect with the same --docker-image
    python scripts/automation/envprobe.py push --user <account> --ref <commit or tag>
        installs kaggle/requirements-runner.txt from that ref instead of the notebook's TAG (14 November 2026: the
        pins of code tag automation-v4, probed at the commit that carries them before the tag is cut); collect then
        also prints the kind gvgaisearch's checks (JPype, the pinned JDK, the GVGAI build)

collect also reads, from the committed rows of stage D (runs/dev-minigrid/devsearch/*.json), the image digests
that stage D's sessions recorded, and says whether the probe ran on the same image.  It changes no file in the
repository; its console is the log.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SLUG = "horizon-envprobe"


def kaggle(cmd, *a):
    r = subprocess.run([cmd, *a], capture_output=True, text=True)
    out = "\n".join(x for x in (r.stdout + r.stderr).splitlines() if "outdated" not in x)
    if r.returncode:
        raise SystemExit(f"kaggle {' '.join(a)} failed ({r.returncode}): {out}")
    return out


def stage_d_images():
    seen = {}
    for p in glob.glob(os.path.join(REPO, "runs", "dev-minigrid", "devsearch", "*.json")):
        for s in json.load(open(p, encoding="utf-8")).get("sessions", []):
            img = (s.get("kaggle_env") or {}).get("KAGGLE_DOCKER_IMAGE")
            seen[img] = seen.get(img, 0) + 1
    return seen


def push(a):
    tmp = tempfile.mkdtemp(prefix="envprobe-")
    try:
        nb = open(os.path.join(REPO, "kaggle", "envprobe", "probe.ipynb"), encoding="utf-8").read()
        if a.ref:
            old = 'TAG = \\"automation-v2\\"'
            if nb.count(old) != 1:
                raise SystemExit("the probe notebook's TAG line was not found once")
            nb = nb.replace(old, f'TAG = \\"{a.ref}\\"')
            print(f"ref installed from: {a.ref}")
        with open(os.path.join(tmp, "probe.ipynb"), "w", encoding="utf-8", newline="") as f:
            f.write(nb)
        meta = json.load(open(os.path.join(REPO, "kaggle", "envprobe", "kernel-metadata.json"), encoding="utf-8"))
        meta["id"] = f"{a.user}/{SLUG}"
        if a.docker_image:                    # the image Kaggle is asked to run (kernel-metadata "docker_image")
            meta["docker_image"] = a.docker_image
        print(f"metadata pushed: {json.dumps(meta, sort_keys=True)}")
        json.dump(meta, open(os.path.join(tmp, "kernel-metadata.json"), "w", encoding="utf-8"), indent=1)
        print(kaggle(a.kaggle, "kernels", "push", "-p", tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def collect(a):
    ref = f"{a.user}/{SLUG}"
    status = kaggle(a.kaggle, "kernels", "status", ref)
    print(f"status: {status}")
    if "COMPLETE" not in status.upper():
        print("not complete; nothing collected")
        return 1
    tmp = tempfile.mkdtemp(prefix="envprobe-out-")
    try:
        kaggle(a.kaggle, "kernels", "output", ref, "-p", tmp)
        p = os.path.join(tmp, "probe.json")
        if not os.path.exists(p):
            print("no probe.json in the output; console.log follows")
            c = os.path.join(tmp, "console.log")
            print(open(c, encoding="utf-8").read() if os.path.exists(c) else "(no console.log)")
            return 1
        d = json.load(open(p, encoding="utf-8"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"probe image: {d['docker_image']}")
    if a.docker_image:
        print(f"image asked for in the metadata: {a.docker_image}")
        print(f"the session ran on the image asked for: {'yes' if d['docker_image'] == a.docker_image else 'NO'}")
    print(f"probe python: {d['python']} ({d['implementation']}, {d['machine']}, {d['python_executable']})")
    print(f"code tag {d['code_tag']} at {d['code_commit']}")
    print("requirements-runner.txt at that ref:")
    print("".join(f"    {x}\n" for x in d["requirements_runner"].splitlines()), end="")
    imgs = stage_d_images()
    print("stage D image digests in the committed rows (sessions recorded):")
    for img, n in sorted(imgs.items(), key=lambda kv: -kv[1]):
        print(f"    {n:5d}  {img}")
    same = set(imgs) == {d["docker_image"]}
    print(f"probe on the image of every stage D session: {'yes' if same else 'NO'}")
    print(f"imported: {d['imported']}")
    if "gvgai" in d:
        g = d["gvgai"]
        print(f"the image's own Java: {d.get('image_java')} (not used: sim_gvgai.ensure_jdk takes only the pinned build)")
        print(f"JDK: {g['jdk_home']}; pinned build: {g['jdk_pinned']}; release: {g['jdk_release']}")
        print(f"JDK archive sha256 {g['jdk_archive_sha256']}; pinned {g['jdk_archive_pinned']}; "
              f"{'equal' if g['jdk_archive_sha256'] == g['jdk_archive_pinned'] else 'DIFFERENT'}")
        print(f"GVGAI and the bridge compiled: {g['java_sources']} Java files; JDK {g['seconds_jdk']} s, build and JVM "
              f"start {g['seconds_build_and_jvm']} s")
        print(f"synthetic level corridor 0 loaded: actions {g['corridor_0_actions']}, key {g['corridor_0_key_bytes']} bytes")
    elif a.ref:
        print("NO gvgai section in probe.json")
    print("the runner's requirements and every package they need, as installed:")
    for k, v in d["runner_tree"].items():
        print(f"    {k}=={v}")
    before = {x.split('==')[0].lower(): x for x in d["freeze_before"] if "==" in x}
    after = {x.split('==')[0].lower(): x for x in d["freeze_after"] if "==" in x}
    changed = sorted(k for k in after if before.get(k) != after[k])
    print(f"packages the install added or changed: {[after[k] + ' (was ' + before.get(k, 'absent') + ')' for k in changed]}")
    print(f"packages in the image before the install: {len(d['freeze_before'])}; after: {len(d['freeze_after'])}")
    print("pip freeze after the install:")
    for x in d["freeze_after"]:
        print(f"    {x}")
    return 0 if same else 2


def main():
    ap = argparse.ArgumentParser(description="the HORIZON environment probe")
    ap.add_argument("command", choices=("push", "collect"))
    ap.add_argument("--user", required=True, help="the Kaggle account")
    ap.add_argument("--kaggle", default="kaggle", help="the kaggle command")
    ap.add_argument("--docker-image", help="push: the image to ask for; collect: the image that was asked for")
    ap.add_argument("--ref", help="push: the ref whose requirements-runner.txt the probe installs; collect: the same")
    a = ap.parse_args()
    return push(a) if a.command == "push" else collect(a)


if __name__ == "__main__":
    sys.exit(main())
