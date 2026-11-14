"""
history_cost.py -- reads the git history of this repository and prints what a rewrite of it would touch
(docs/STATE.md, amendment (z)).  It reads only; it rewrites nothing, and nothing in this repository runs
a rewrite.

For the commit given by --before (the last commit before the scrub of 14 November 2026, b9e5180) and the
history up to it, it prints:
    1. the commits, and how many name each author and committer identity;
    2. the commit messages and tag messages that hold any pattern of scripts/check_no_aid.py (none expected);
    3. the commits whose tree holds a path that matches a pattern, the first of them, and the last;
    4. every tag: its kind (annotated or lightweight) and its commit;
    5. for every tracked file of --at (default HEAD) outside third_party/ and runs/, the distinct commits
       of the history it names by a hash of 7 to 40 hex digits; the totals; and the files under runs/
       that name any commit;
    6. the field names of the rows under runs/*/devsearch/ and of their session entries.
Patterns found are printed by number only, as scripts/check_no_aid.py --counts prints them.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\history_cost.py --before b9e5180 > logs\\history_cost.log
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_no_aid as C  # noqa: E402

REPO = C.REPO


def git(*args):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--at", default="HEAD")
    a = ap.parse_args(argv)
    rx = C._regex()
    index = {p.lower(): i for i, p in enumerate(C.patterns())}
    before = git("rev-parse", "--verify", a.before + "^{commit}").strip()
    at = git("rev-parse", "--verify", a.at + "^{commit}").strip()
    print(f"before: {before}  at: {at}")

    # 1. commits and identities
    log = git("log", "--format=%H%x1f%an <%ae>%x1f%cn <%ce>%x1f%B%x1e", before).split("\x1e")
    commits = []
    for rec in log:
        rec = rec.strip("\n")
        if rec:
            h, au, co, msg = rec.split("\x1f", 3)
            commits.append((h, au, co, msg))
    print(f"\n1. commits up to --before: {len(commits)}")
    ids = collections.Counter((au, co) for _, au, co, _ in commits)
    for (au, co), n in sorted(ids.items(), key=lambda x: -x[1]):
        name_a, name_c = au.split(" <")[0], co.split(" <")[0]
        print(f"   {n} commits: author {name_a}, committer {name_c}")

    # 2. messages
    hits = [(h, sorted({index[m.group(0).lower()] for m in rx.finditer(msg)})) for h, _, _, msg in commits]
    hits = [x for x in hits if x[1]]
    print(f"\n2. commit messages with a pattern: {len(hits)}")
    for h, nums in hits:
        print(f"   {h[:7]}: " + ", ".join(f"#{n:02d}" for n in nums))
    tags = [t for t in git("tag", "-l").split("\n") if t]
    tag_hits = 0
    print(f"   tags: {len(tags)}")
    tag_rows = []
    for t in tags:
        kind = git("cat-file", "-t", t).strip()
        commit = git("rev-list", "-n", "1", t).strip()
        tag_rows.append((t, kind, commit))
        if kind == "tag":
            body = git("cat-file", "-p", t).split("\n\n", 1)[1] if "\n\n" in git("cat-file", "-p", t) else ""
            if rx.search(body):
                tag_hits += 1
                print(f"   tag {t}: message has a pattern")
    print(f"   tag messages with a pattern: {tag_hits} (annotated tags: {sum(1 for r in tag_rows if r[1] == 'tag')})")

    # 3. trees
    with_path = []
    for h, _, _, _ in commits:
        names = git("ls-tree", "-r", "--name-only", h)
        if any(rx.search(p) for p in names.split("\n") if p and not p.startswith("third_party/")):
            with_path.append(h)
    print(f"\n3. commits whose tree holds a path with a pattern: {len(with_path)} of {len(commits)}")
    if with_path:
        print(f"   first (oldest): {with_path[-1]}  last: {with_path[0]}")
    root = git("rev-list", "--max-parents=0", before).split()
    print(f"   root commit(s): {', '.join(root)}")

    # 4. tags
    print("\n4. tags")
    for t, kind, commit in tag_rows:
        print(f"   {t}: {'annotated' if kind == 'tag' else 'lightweight'}, commit {commit}")

    # 5. hashes named in files
    allc = [h for h in git("rev-list", "--all").split() if h]
    by7 = collections.defaultdict(list)
    for h in allc:
        by7[h[:7]].append(h)
    hexrx = re.compile(r"\b[0-9a-f]{7,40}\b")

    def commits_named(text):
        found = set()
        for tok in set(hexrx.findall(text)):
            for h in by7.get(tok[:7], []):
                if h.startswith(tok):
                    found.add(h)
        return found

    files = [p for p in git("ls-tree", "-r", "--name-only", at).split("\n") if p]
    per = {}
    runs_files = 0
    runs_naming = 0
    for p in files:
        if p.startswith("third_party/"):
            continue
        try:
            text = git("show", f"{at}:{p}")
        except (SystemExit, UnicodeDecodeError):
            continue
        named = commits_named(text)
        if p.startswith("runs/"):
            runs_files += 1
            runs_naming += bool(named)
            continue
        if named:
            per[p] = named
    print(f"\n5. tracked files at --at, outside third_party/ and runs/, that name a commit of the history: {len(per)}")
    kaggle = [p for p in per if p.startswith("logs/kaggle/")]
    for p in sorted(per):
        if not p.startswith("logs/kaggle/"):
            print(f"   {p}: {len(per[p])}")
    print(f"   logs/kaggle/: {len(kaggle)} session consoles, naming {len(set().union(*[per[p] for p in kaggle])) if kaggle else 0} distinct commits")
    print(f"   (file, commit) citations in all: {sum(len(v) for v in per.values())}")
    print(f"   files under runs/: {runs_files}; of them naming a commit: {runs_naming}")

    # 6. row fields
    keys, skeys = collections.Counter(), collections.Counter()
    nrows = 0
    for p in files:
        if re.match(r"runs/[^/]+/devsearch/.*\.json$", p):
            row = json.loads(git("show", f"{at}:{p}"))
            nrows += 1
            keys.update(row.keys())
            for s in row.get("sessions", []):
                skeys.update(s.keys())
    print(f"\n6. devsearch rows: {nrows}")
    print(f"   row fields: {', '.join(sorted(keys))}")
    print(f"   session fields: {', '.join(sorted(skeys))}")
    camp = collections.Counter(p.split("/")[1] for p in files if re.match(r"runs/[^/]+/devsearch/.*\.json$", p))
    for c, n in sorted(camp.items()):
        print(f"   {c}: {n} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
