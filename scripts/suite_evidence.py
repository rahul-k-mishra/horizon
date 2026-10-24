"""
suite_evidence.py -- the evidence for the feasibility verdicts of docs/DESIGN.md, Section 3.

Fetches public records with curl and the gh tool (PyPI's JSON API and GitHub's API; no credential of
the author is needed for them), saves every raw answer it uses in docs/design/suite_evidence.json
(committed with the log), and prints from that file:
    - per package on PyPI: whether it exists, its latest version, the upload date of that version, and
      whether it has a CPython 3.11 Linux x86_64 wheel or a wheel for every platform;
    - per source repository: the date of its last push and its licence;
    - Griddly at tag 1.6.6: the single-player GDY files, the distinct games among them (a partially
      observable variant is the same game), how many sit under GVGAI/ and Mini-Grid/, and the lines of
      python/griddly/GymWrapper.py that define clone and get_state;
    - GVGAI at commit e58ff6597319155218759cc178931e05b81b524c: the number of Java source files under src/,
      and the lines of src/core/game/StateObservation.java that define copy and advance;
    - the Python 3 fork of py-vgdl: the game descriptions under vgdl/games.
Plays nothing.  Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\suite_evidence.py > logs\\suite_evidence.log
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "design", "suite_evidence.json")
GVGAI = "e58ff6597319155218759cc178931e05b81b524c"
PACKAGES = ["griddly", "minatar", "JPype1", "vgdl", "py-vgdl", "gvgai-gym", "gym-gvgai"]
REPOS = ["Bam4d/Griddly", "GAIGResearch/GVGAI", "schaul/py-vgdl", "rubenvereecken/py-vgdl", "rubenrtorrado/GVGAI_GYM",
         "kenjyoung/MinAtar"]


def gh(path, raw=False):
    cmd = ["gh", "api", path] + (["-H", "Accept: application/vnd.github.raw"] if raw else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"gh api {path}: {r.stderr.strip()}")
    return r.stdout if raw else json.loads(r.stdout)


def pypi(name):
    r = subprocess.run(["curl", "-s", "-m", "60", "-w", "\n%{http_code}", f"https://pypi.org/pypi/{name}/json"],
                       capture_output=True, text=True, encoding="utf-8")
    body, code = r.stdout.rsplit("\n", 1)
    if code != "200":
        return dict(status=int(code))
    d = json.loads(body)
    v = d["info"]["version"]
    return dict(status=200, version=v, requires_python=d["info"].get("requires_python"),
                files=[dict(filename=f["filename"], upload_time=f["upload_time"]) for f in d["releases"].get(v, [])])


def lines_matching(text, pattern):
    return [i + 1 for i, ln in enumerate(text.splitlines()) if re.search(pattern, ln)]


def fetch():
    ev = dict(pypi={p: pypi(p) for p in PACKAGES}, repos={})
    for r in REPOS:
        d = gh(f"repos/{r}")
        ev["repos"][r] = dict(pushed_at=d["pushed_at"], archived=d["archived"],
                              license=(d.get("license") or {}).get("spdx_id"))
    tree = gh("repos/Bam4d/Griddly/git/trees/1.6.6?recursive=1")
    ev["griddly_gdy"] = sorted(t["path"] for t in tree["tree"] if t["path"].startswith("resources/games/Single-Player/")
                               and t["path"].endswith(".yaml"))
    gw = gh("repos/Bam4d/Griddly/contents/python/griddly/GymWrapper.py?ref=1.6.6", raw=True)
    ev["griddly_wrapper_lines"] = dict(clone=lines_matching(gw, r"def clone\("), get_state=lines_matching(gw, r"def get_state\("))
    tree = gh(f"repos/GAIGResearch/GVGAI/git/trees/{GVGAI}?recursive=1")
    ev["gvgai_java_sources"] = sum(1 for t in tree["tree"] if t["path"].startswith("src/") and t["path"].endswith(".java"))
    so = gh(f"repos/GAIGResearch/GVGAI/contents/src/core/game/StateObservation.java?ref={GVGAI}", raw=True)
    ev["gvgai_stateobservation_lines"] = dict(copy=lines_matching(so, r"public StateObservation copy\("),
                                              advance=lines_matching(so, r"public void advance\("))
    tree = gh("repos/rubenvereecken/py-vgdl/git/trees/HEAD?recursive=1")
    ev["pyvgdl_fork_games"] = sorted(t["path"] for t in tree["tree"] if re.fullmatch(r"vgdl/games/[a-z0-9_]+\.txt", t["path"])
                                     and "_lvl" not in t["path"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ev, f, indent=1, sort_keys=True)


def report():
    ev = json.load(open(OUT, encoding="utf-8"))
    print("== PyPI")
    for p, d in ev["pypi"].items():
        if d["status"] != 200:
            print(f"{p}: not on PyPI (HTTP {d['status']})")
            continue
        names = [f["filename"] for f in d["files"]]
        up = min((f["upload_time"] for f in d["files"]), default=None)
        cp311 = any("cp311" in n and "manylinux" in n and "x86_64" in n for n in names)
        anyplat = any(n.endswith("py3-none-any.whl") for n in names)
        print(f"{p}: version {d['version']}, uploaded {up}, CPython 3.11 Linux x86_64 wheel: {'yes' if cp311 else 'no'}, "
              f"wheel for every platform: {'yes' if anyplat else 'no'}")
    print("\n== source repositories")
    for r, d in ev["repos"].items():
        print(f"{r}: last push {d['pushed_at']}, archived {d['archived']}, licence {d['license']}")
    print("\n== Griddly, tag 1.6.6")
    games = ev["griddly_gdy"]
    distinct = sorted({re.sub(r"_partially_observable$", "", os.path.splitext(g)[0]) for g in games})
    print(f"single-player GDY files: {len(games)}; distinct games: {len(distinct)}; under GVGAI/: "
          f"{sum('/GVGAI/' in g for g in distinct)}; under Mini-Grid/: {sum('/Mini-Grid/' in g for g in distinct)}")
    print("distinct games: " + ", ".join(g.split("/")[-1] for g in distinct))
    print(f"python/griddly/GymWrapper.py: def clone at line(s) {ev['griddly_wrapper_lines']['clone']}, "
          f"def get_state at line(s) {ev['griddly_wrapper_lines']['get_state']}")
    print(f"\n== GVGAI, commit {GVGAI}")
    print(f"Java source files under src/: {ev['gvgai_java_sources']}")
    print(f"src/core/game/StateObservation.java: copy at line(s) {ev['gvgai_stateobservation_lines']['copy']}, "
          f"advance at line(s) {ev['gvgai_stateobservation_lines']['advance']}")
    print("\n== py-vgdl, Python 3 fork (rubenvereecken/py-vgdl)")
    print(f"game descriptions under vgdl/games: {len(ev['pyvgdl_fork_games'])}: "
          + ", ".join(os.path.basename(g) for g in ev["pyvgdl_fork_games"]))
    print(f"\nraw records: {os.path.relpath(OUT, REPO)}")


def main():
    if "--report-only" not in sys.argv:
        fetch()
    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
