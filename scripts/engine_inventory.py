"""
engine_inventory.py -- what of GVGAI is vendored under third_party/gvgai, against the upstream tree at the
pinned commit (docs/design/ENGINE.md, Section 1).

Reads GitHub's record of the upstream tree at commit e58ff6597319155218759cc178931e05b81b524c (fetched once with
the gh tool and saved in docs/design/gvgai_upstream_tree.json; --fetch fetches it again) and the files git holds
under third_party/gvgai, at a commit given by --before and in the index now.  A vendored file is the same file
as upstream when its git blob hash equals the upstream blob hash.  Prints, per top folder of the upstream tree,
how many files exist upstream, how many were vendored at --before, and how many are vendored now; for a vendored file whose blob differs
from upstream, whether it differs in line endings only (third_party/gvgai/README.md is HORIZON's own note under
the upstream name); then which
upstream files of the engine (src/) are not vendored, grouped by folder.  Plays nothing.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\engine_inventory.py --before f29827c > logs\\engine_inventory.log
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMIT = "e58ff6597319155218759cc178931e05b81b524c"
TREE = os.path.join(REPO, "docs", "design", "gvgai_upstream_tree.json")
PREFIX = "third_party/gvgai/"


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", check=True).stdout


def vendored(rev):
    """{upstream path: blob} for files under third_party/gvgai at rev, or in the index when rev is None."""
    if rev is None:
        out = git("ls-files", "-s", "--", PREFIX)
        rows = [ln.split(None, 3) for ln in out.splitlines()]
        items = [(r[3], r[1]) for r in rows]
    else:
        out = git("ls-tree", "-r", rev, "--", PREFIX)
        rows = [ln.split(None, 3) for ln in out.splitlines()]
        items = [(r[3], r[2]) for r in rows]
    return {p[len(PREFIX):]: b for p, b in items}


def line_ending_only(paths, upstream, rev):
    """Split paths into those whose content equals the upstream blob apart from carriage returns, and the rest.
    The upstream blob is fetched from GitHub by its hash; the vendored one is read from rev (or the index)."""
    same, other = [], []
    for p in paths:
        r = subprocess.run(["gh", "api", f"repos/GAIGResearch/GVGAI/git/blobs/{upstream[p]}",
                            "-H", "Accept: application/vnd.github.raw"], capture_output=True, check=True)
        spec = f"{rev}:{PREFIX}{p}" if rev else f":{PREFIX}{p}"
        mine = subprocess.run(["git", "show", spec], cwd=REPO, capture_output=True, check=True).stdout
        (same if r.stdout.replace(b"\r", b"") == mine.replace(b"\r", b"") else other).append(p)
    return same, other


def top(path):
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True, help="commit before this session's vendoring")
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args()
    if a.fetch or not os.path.exists(TREE):
        r = subprocess.run(["gh", "api", f"repos/GAIGResearch/GVGAI/git/trees/{COMMIT}?recursive=1"],
                           capture_output=True, text=True, encoding="utf-8", check=True)
        d = json.loads(r.stdout)
        keep = dict(sha=d["sha"], truncated=d["truncated"],
                    tree=[dict(path=e["path"], sha=e["sha"], size=e.get("size")) for e in d["tree"] if e["type"] == "blob"])
        with open(TREE, "w", encoding="utf-8", newline="\n") as f:
            json.dump(keep, f, indent=0)
    with open(TREE, encoding="utf-8") as f:
        up = json.load(f)
    if up["truncated"]:
        raise SystemExit("the upstream tree record is truncated")
    upstream = {e["path"]: e["sha"] for e in up["tree"]}
    before, now = vendored(a.before), vendored(None)

    print(f"== upstream GVGAI at commit {up['sha']}: {len(upstream)} files (GitHub's tree record, {os.path.relpath(TREE, REPO)})")
    for name, v in (("at " + a.before, before), ("now (index)", now)):
        same = sum(1 for p, b in v.items() if upstream.get(p) == b)
        other = sorted(p for p in v if p not in upstream)
        diff = sorted(p for p, b in v.items() if p in upstream and upstream[p] != b)
        print(f"vendored {name}: {len(v)} files; {same} equal to the upstream blob; {len(diff)} differ; "
              f"{len(other)} not in upstream: {', '.join(other) or 'none'}")
        if diff:
            crlf, other_diff = line_ending_only(diff, upstream, rev=a.before if name.startswith("at ") else None)
            print(f"   of the {len(diff)} that differ, {len(crlf)} are equal to upstream once carriage returns are "
                  f"removed from both (line endings only); the others: {', '.join(other_diff) or 'none'}")

    print("\n== per top folder: upstream files / vendored at --before / vendored now")
    cu, cb, cn = collections.Counter(), collections.Counter(), collections.Counter()
    for p in upstream:
        cu[top(p)] += 1
    for p in before:
        if p in upstream:
            cb[top(p)] += 1
    for p in now:
        if p in upstream:
            cn[top(p)] += 1
    for k in sorted(cu):
        print(f"{k:32s} {cu[k]:5d} {cb[k]:5d} {cn[k]:5d}")

    print("\n== engine source (src/): upstream files not vendored at --before, by folder")
    miss = collections.Counter(os.path.dirname(p) for p in upstream if p.startswith("src/") and p not in before)
    for k in sorted(miss):
        print(f"{k:48s} {miss[k]:4d}")
    print(f"total {sum(miss.values())} of {sum(1 for p in upstream if p.startswith('src/'))} src/ files")
    java_up = sum(1 for p in upstream if p.startswith("src/") and p.endswith(".java"))
    java_now = sum(1 for p in now if p.startswith("src/") and p.endswith(".java") and upstream.get(p) == now[p])
    print(f"\n== now: {java_now} of {java_up} upstream Java source files under src/ vendored, each equal to its upstream blob")
    rest = sorted({top(p) for p in upstream if p not in now})
    print("upstream folders or files not vendored now: " + ", ".join(rest))


if __name__ == "__main__":
    main()
