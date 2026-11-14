"""
engine_evidence.py -- the public records behind docs/design/ENGINE.md, Section 2: every way found to step a
VGDL game from Python, with its licence, its last change, whether it installs from PyPI, and which of the 30
deterministic games of the suite it carries.

Fetches public records with curl and the gh tool (PyPI's JSON API and GitHub's API; no credential of the author
is needed for them), saves every raw answer it uses in docs/design/engine_evidence.json (committed with the
log), and prints from that file:
    - per package on PyPI: whether it exists, its latest version and that version's upload date, and whether it
      has a wheel for CPython 3.11 and 3.13 on Linux x86_64 (the laptop's Python and the Kaggle image's);
    - per source repository: last push, licence, archived;
    - per repository that interprets VGDL in Python (or JAX): how many files in its tree are named after one of
      the 30 deterministic games of docs/design/vgdl_scan.json, and which games those are;
    - per repository that drives GVGAI's Java over a socket (GVGAI's own Python client, the GVGAI gym wrapper):
      every line of its Python files that defines or calls copy or advance, the two calls a breadth-first search
      needs (src/core/game/StateObservation.java, vendored), so that a reader can see what each one copies;
    - for VGDLx, the README's own statement of how it was checked against GVGAI;
    - the JDK: Temurin 21's release record from the Adoptium API for Linux x86_64 and Windows x64 (version,
      file name, sha256, date), and the PyPI records of jdk4py and install-jdk.
Plays nothing.  --offline prints from the saved file without fetching.  Run (working directory
D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\engine_evidence.py > logs\\engine_evidence.log
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "design", "engine_evidence.json")
GVGAI = "e58ff6597319155218759cc178931e05b81b524c"
PACKAGES = ["JPype1", "py4j", "jdk4py", "install-jdk", "griddly", "vgdl", "py-vgdl", "pyvgdl", "gvgai", "gvgai-gym",
            "gym-gvgai", "gym-vgdl"]
INTERPRETERS = ["schaul/py-vgdl", "rubenvereecken/py-vgdl", "tsividis/vgdl", "shepardxia/VGDLx", "EndingCredits/gym_vgdl",
                "Bam4d/Griddly"]
SOCKET = {"GAIGResearch/GVGAI": "clients/GVGAI-PythonClient/", "rubenrtorrado/GVGAI_GYM": ""}
OTHER = ["jpype-project/jpype", "py4j/py4j"]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout, r.stderr


def gh(path, raw=False):
    code, out, err = run(["gh", "api", path] + (["-H", "Accept: application/vnd.github.raw"] if raw else []))
    if code:
        return dict(error=err.strip()[:300])
    return out if raw else json.loads(out)


def curl_json(url):
    code, out, _ = run(["curl", "-s", "-m", "60", "-w", "\n%{http_code}", url])
    body, status = out.rsplit("\n", 1)
    return int(status), (json.loads(body) if status == "200" else None)


def pypi(name):
    status, d = curl_json(f"https://pypi.org/pypi/{name}/json")
    if status != 200:
        return dict(status=status)
    v = d["info"]["version"]
    return dict(status=200, version=v, license=d["info"].get("license") or d["info"].get("license_expression"),
                requires_python=d["info"].get("requires_python"),
                files=[dict(filename=f["filename"], upload_time=f["upload_time"]) for f in d["releases"].get(v, [])])


def repo_record(name, with_tree=True):
    r = gh(f"repos/{name}")
    if "error" in r:
        return dict(error=r["error"])
    rec = dict(pushed_at=r["pushed_at"], archived=r["archived"], license=(r.get("license") or {}).get("spdx_id"),
               default_branch=r["default_branch"])
    if with_tree:
        t = gh(f"repos/{name}/git/trees/{r['default_branch']}?recursive=1")
        rec["tree"] = [e["path"] for e in t.get("tree", []) if e["type"] == "blob"]
        rec["tree_truncated"] = t.get("truncated")
    return rec


def fetch():
    ev = dict(pypi={p: pypi(p) for p in PACKAGES}, repos={}, socket_files={}, temurin={})
    for name in INTERPRETERS + list(SOCKET) + OTHER:
        ev["repos"][name] = repo_record(name, with_tree=name not in OTHER)
    for name, prefix in SOCKET.items():
        rec = ev["repos"][name]
        if name == "GAIGResearch/GVGAI":
            t = gh(f"repos/{name}/git/trees/{GVGAI}?recursive=1")
            rec["tree"] = [e["path"] for e in t.get("tree", []) if e["type"] == "blob"]
            ref = GVGAI
        else:
            ref = rec.get("default_branch")
        files = {}
        for p in rec.get("tree", []):
            if p.startswith(prefix) and p.endswith(".py"):
                files[p] = gh(f"repos/{name}/contents/{p}?ref={ref}", raw=True)
        ev["socket_files"][name] = dict(ref=ref, files=files)
    readme = gh("repos/shepardxia/VGDLx/readme", raw=True)
    ev["vgdlx_readme_head"] = readme.splitlines()[:6] if isinstance(readme, str) else readme
    for os_name in ("linux", "windows"):
        status, d = curl_json("https://api.adoptium.net/v3/assets/release_name/eclipse/jdk-21.0.13%2B9"
                              f"?architecture=x64&image_type=jdk&os={os_name}&project=jdk")
        if d:
            b = d["binaries"][0]
            ev["temurin"][os_name] = dict(release=d["release_name"], name=b["package"]["name"], link=b["package"]["link"],
                                          sha256=b["package"]["checksum"], updated_at=b["updated_at"])
        else:
            ev["temurin"][os_name] = dict(status=status)
    reduce(ev)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ev, f, indent=1, sort_keys=True)


def suite_games():
    with open(os.path.join(REPO, "docs", "design", "vgdl_scan.json"), encoding="utf-8") as f:
        return sorted(g["game"] for g in json.load(f)["games"] if g["deterministic"])


def reduce(ev):
    """Keeps only what is printed: per repository the number of files in its tree and the paths named after a
    game of the suite (not the whole tree); per socket client the number of Python files and the lines with
    copy( or advance(, with their numbers (not the files)."""
    det = suite_games()
    pat = [re.compile(rf"(^|/){re.escape(g)}(_lvl\d+)?\.(txt|vgdl|yaml|yml|py)$", re.I) for g in det]
    for r in ev["repos"].values():
        if "tree" in r:
            r["tree_files"] = len(r["tree"])
            r["suite_files"] = sorted(p for p in r["tree"] if any(x.search(p) for x in pat))
            del r["tree"]
    for s in ev["socket_files"].values():
        lines = {}
        for p, txt in s["files"].items():
            if isinstance(txt, str):
                hits = [[i + 1, ln.strip()[:90]] for i, ln in enumerate(txt.splitlines())
                        if re.search(r"\b(copy|advance)\s*\(", ln)]
                if hits:
                    lines[p] = hits
        s["python_files"] = len(s["files"])
        s["lines"] = lines
        del s["files"]


def wheel(files, tag):
    return any(tag in f["filename"] and "manylinux" in f["filename"] and "x86_64" in f["filename"] for f in files) \
        or any(f["filename"].endswith("-none-any.whl") for f in files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if not a.offline:
        fetch()
    with open(OUT, encoding="utf-8") as f:
        ev = json.load(f)
    with open(os.path.join(REPO, "docs", "design", "vgdl_scan.json"), encoding="utf-8") as f:
        det = sorted(g["game"] for g in json.load(f)["games"] if g["deterministic"])
    print(f"== the suite: {len(det)} deterministic games (docs/design/vgdl_scan.json)")

    print("\n== PyPI")
    for p, d in sorted(ev["pypi"].items(), key=lambda x: x[0].lower()):
        if d["status"] != 200:
            print(f"{p}: not on PyPI (HTTP {d['status']})")
            continue
        up = min((f["upload_time"] for f in d["files"]), default="?")
        print(f"{p}: version {d['version']}, uploaded {up}, licence {d['license']!s:.40}, "
              f"wheel CPython 3.11 Linux x86_64: {'yes' if wheel(d['files'], 'cp311') else 'no'}, "
              f"3.13: {'yes' if wheel(d['files'], 'cp313') else 'no'}")

    print("\n== source repositories")
    for name, r in sorted(ev["repos"].items(), key=lambda x: x[0].lower()):
        if "error" in r:
            print(f"{name}: {r['error']}")
            continue
        print(f"{name}: last push {r['pushed_at']}, archived {r['archived']}, licence {r['license']}")

    print("\n== VGDL interpreted in Python or JAX (or, for Griddly, in C++ from GDY files): files named after a game of the suite")
    pat = {g: re.compile(rf"(^|/){re.escape(g)}(_lvl\d+)?\.(txt|vgdl|yaml|yml|py)$", re.I) for g in det}
    for name in INTERPRETERS:
        r = ev["repos"][name]
        if "error" in r:
            continue
        hit = sorted({g for g in det for p in r["suite_files"] if pat[g].search(p)})
        print(f"{name}: {r['tree_files']} files; games of the suite named by a file: {len(hit)} of {len(det)}"
              f"{': ' + ', '.join(hit) if hit else ''}")

    print("\n== GVGAI's Java over a socket: Python files that define or call copy or advance")
    for name, s in ev["socket_files"].items():
        hits = [f"   {p}:{i}: {ln}" for p, ls in sorted(s["lines"].items()) for i, ln in ls]
        print(f"{name} at {s['ref'][:12]}: {s['python_files']} Python files; lines with copy( or advance(: {len(hits)}")
        print("\n".join(hits))

    print("\n== VGDLx: the first lines of its README (its own claim, not checked here)")
    for ln in ev.get("vgdlx_readme_head") or []:
        if ln.strip():
            print("   " + ln.strip())

    print("\n== the JDK (Adoptium API)")
    for k, t in ev["temurin"].items():
        if "release" in t:
            print(f"Temurin {t['release']} {k}: {t['name']}, sha256 {t['sha256']}, updated {t['updated_at']}")
        else:
            print(f"Temurin {k}: no record (HTTP {t.get('status')})")
    print(f"\nraw records: {os.path.relpath(OUT, REPO)}")


if __name__ == "__main__":
    main()
