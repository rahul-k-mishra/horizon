"""
check_no_aid.py -- searches the tracked files of this repository for any name of a writing or coding aid, an
attribution trailer or a phrase that credits such an aid (rule R2, docs/RULES.md), prints every hit and
exits 1 if there is one, 0 if there is none.

What is searched, for every tracked file (git ls-files), or for every file of a commit with --rev:
    - the path, every directory name and the file name;
    - the text, line by line (UTF-8, or UTF-16 with a byte-order mark);
    - a file that is not text: its raw bytes (which holds a PDF's Info dictionary and an uncompressed XMP
      packet, and a PNG's tEXt chunks), and also the members of a zip file (docx, xlsx, pptx: docProps and
      every part), the content of a gzip file, every Flate stream of a PDF, and the zTXt and iTXt chunks of
      a PNG.
Notebooks (.ipynb) and JSON files are text and are searched whole, metadata and cell outputs included.

The patterns are matched without regard to case.  They are stored ROT13-encoded in PATTERNS_ROT13 so that
this file does not match itself; patterns() decodes them.

What is allowed (step 1 of the scrub of 14 November 2026, docs/STATE.md amendment (z)):
    - ALLOW_TERMS: exact terms, matched with case, that may contain a pattern as part of another word or
      name (an identifier, a Word style name, a game's sprite name) or that are subject-matter names of
      the field.  A hit is allowed when one occurrence of such a term on the same line covers it.
    - ALLOW_PATH_TERMS: exact terms allowed in one path only, stored ROT13-encoded as well (package names in the
      committed consoles of the Kaggle environment probe; a docstring of a test).
    - SKIP_PREFIXES: vendored upstream code under third_party/, which is not changed; its hits are printed
      in a separate section and do not count.
Any other hit counts.

Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\check_no_aid.py > logs\\check_no_aid.log
    ... scripts\\check_no_aid.py --rev prereg-v1      (the files as stored at a tag or commit)
It reads files only.  Tested by scripts/test_check_no_aid.py.  scripts/zenodo_deposit.py runs it on the tagged
commit and stops if it finds a hit; docs/registration/ZENODO.md runs it before the tag is made.
"""
import argparse
import codecs
import gzip
import io
import os
import re
import subprocess
import sys
import zipfile
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATTERNS_ROT13 = [
    "abercyl@naguebcvp.pbz", "ynetr ynathntr zbqry", "ynathntr zbqry", "pb-nhguberq-ol", "pbnhguberq",
    "trarengrq jvgu", "jvgu gur uryc bs", "jevggra jvgu", "nv-trarengrq", "nv nffvfgrq", "nv-nffvfgrq",
    "nffvfgnag", "pynhqr", "naguebcvp", "pbcvybg", "pungtcg", "bcranv", "trzvav", "tcg", "yyz",
]

ALLOW_TERMS = [
    # subject-matter names of the field, cited titles and journal names (none matches a pattern today;
    # listed so that a later pattern cannot take them)
    "General Video Game AI", "GVGAI", "ARC-AGI-3", "ARC-AGI", "ARC Prize",
    "IEEE Trans. Comput. Intell. AI Games", "AAAI",
    # a pattern inside another word
    "tblCellMar",      # a Word table style element
    "fullmatch",       # Python's re.fullmatch
    "fullMolar",       # sprites of the GVGAI game plaqueattack (fullMolarInf, fullMolarSup)
]

ALLOW_PATH_TERMS_ROT13 = {
    # two package names among those installed in Kaggle's image, as listed by the environment probe
    # (amendments s and t); committed consoles, not changed
    "logs/envprobe.log": ["yvgryyz==", "bcranv=="],
    "logs/envprobe_pin.log": ["yvgryyz==", "bcranv=="],
    # a docstring that says a test's reference code uses plain loops and dictionaries
    "scripts/automation/test_devsearch.py": ["jevggra jvgu cynva ybbcf"],
}
ALLOW_PATH_TERMS = {p: [codecs.decode(t, "rot13") for t in ts] for p, ts in ALLOW_PATH_TERMS_ROT13.items()}

SKIP_PREFIXES = ["third_party/"]


def patterns():
    return [codecs.decode(p, "rot13") for p in PATTERNS_ROT13]


def _regex():
    return re.compile("|".join(re.escape(p) for p in patterns()), re.I)


USE_ALLOW = [True]


def _allowed(path, line, start, end):
    if not USE_ALLOW[0]:
        return False
    terms = ALLOW_TERMS + ALLOW_PATH_TERMS.get(path, [])
    for t in terms:
        i = line.find(t)
        while i != -1:
            if i <= start and end <= i + len(t):
                return True
            i = line.find(t, i + 1)
    return False


def _text(data):
    if data[:3] == codecs.BOM_UTF8:
        data = data[3:]
    if data[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _png_chunks(data):
    """The text of the zTXt and iTXt chunks of a PNG, decompressed where needed."""
    out = []
    p = 8
    while p + 8 <= len(data):
        ln = int.from_bytes(data[p:p + 4], "big")
        typ = data[p + 4:p + 8]
        body = data[p + 8:p + 8 + ln]
        try:
            if typ == b"zTXt":
                key, rest = body.split(b"\0", 1)
                out.append((typ.decode() + ":" + key.decode("latin-1"), zlib.decompress(rest[1:])))
            elif typ == b"iTXt":
                key, rest = body.split(b"\0", 1)
                flag = rest[0]
                rest = rest[2:]
                _lang, rest = rest.split(b"\0", 1)
                tkey, text = rest.split(b"\0", 1)
                out.append((typ.decode() + ":" + key.decode("latin-1"), tkey + b"\n" + (zlib.decompress(text) if flag else text)))
        except Exception:
            pass
        p += 12 + ln
    return out


def scan_bytes(path, where, data, rx, hits, depth=0):
    """Appends (path, where, matched text, context) for every hit in data that is not allowed."""
    text = _text(data)
    if text is not None:
        for n, line in enumerate(text.splitlines(), 1):
            for m in rx.finditer(line):
                if not _allowed(path, line, m.start(), m.end()):
                    s, e = max(0, m.start() - 60), min(len(line), m.end() + 60)
                    hits.append((path, f"{where}line {n}", m.group(0), line[s:e].strip()))
        return
    raw = data.decode("latin-1")
    for m in rx.finditer(raw):
        s, e = max(0, m.start() - 60), min(len(raw), m.end() + 60)
        ctx = raw[s:e]
        if not _allowed(path, ctx, m.start() - s, m.end() - s):
            hits.append((path, f"{where}byte {m.start()}", m.group(0), re.sub(r"[^ -~]", ".", ctx)))
    if depth > 3:
        return
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for name in z.namelist():
                    for m in rx.finditer(name):
                        if not _allowed(path, name, m.start(), m.end()):
                            hits.append((path, f"{where}zip member name", m.group(0), name))
                    scan_bytes(path, f"{where}zip member {name}: ", z.read(name), rx, hits, depth + 1)
        except zipfile.BadZipFile:
            pass
    elif data[:2] == b"\x1f\x8b":
        try:
            scan_bytes(path, f"{where}gzip content: ", gzip.decompress(data), rx, hits, depth + 1)
        except OSError:
            pass
    elif data[:5] == b"%PDF-":
        for i, m in enumerate(re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S)):
            try:
                inner = zlib.decompress(m.group(1))
            except zlib.error:
                continue
            scan_bytes(path, f"{where}pdf stream {i}: ", inner, rx, hits, depth + 1)
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        for name, inner in _png_chunks(data):
            scan_bytes(path, f"{where}png {name}: ", inner, rx, hits, depth + 1)


def _git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def tracked(repo, rev=None):
    """Yields (path, bytes) for every tracked file, from the working tree, or as stored at rev."""
    if rev is None:
        for p in _git(repo, "ls-files", "-z").decode("utf-8").split("\0"):
            if p:
                full = os.path.join(repo, *p.split("/"))
                if os.path.isfile(full):
                    with open(full, "rb") as f:
                        yield p, f.read()
        return
    commit = _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()
    paths = [p for p in _git(repo, "ls-tree", "-r", "-z", "--name-only", commit).decode("utf-8").split("\0") if p]
    proc = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        for p in paths:
            proc.stdin.write(f"{commit}:{p}\n".encode("utf-8"))
            proc.stdin.flush()
            header = proc.stdout.readline().decode().split()
            if len(header) < 3 or header[1] != "blob":
                continue
            data = proc.stdout.read(int(header[2]))
            proc.stdout.read(1)
            yield p, data
    finally:
        proc.stdin.close()
        proc.wait()


def scan(repo=REPO, rev=None):
    """Returns (hits, skipped, files): the hits that count, the hits under SKIP_PREFIXES, the files read."""
    rx = _regex()
    hits, skipped, files = [], [], 0
    for path, data in tracked(repo, rev):
        files += 1
        found = []
        for m in rx.finditer(path):
            if not _allowed(path, path, m.start(), m.end()):
                found.append((path, "path", m.group(0), path))
        scan_bytes(path, "", data, rx, found)
        (skipped if any(path.startswith(s) for s in SKIP_PREFIXES) else hits).extend(found)
    return hits, skipped, files


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--rev", default=None, help="search the files as stored at this commit or tag")
    ap.add_argument("--no-allow", action="store_true", help="ignore the allow-list (third_party/ still apart)")
    ap.add_argument("--counts", action="store_true",
                    help="print counts per file and pattern number only, with every match in a path masked")
    a = ap.parse_args(argv)
    USE_ALLOW[0] = not a.no_allow
    try:
        hits, skipped, files = scan(a.repo, a.rev)
    finally:
        USE_ALLOW[0] = True
    print(f"searched {files} tracked files ({'commit ' + a.rev if a.rev else 'working tree'}), "
          f"{len(PATTERNS_ROT13)} patterns, "
          + ("allow-list not used" if a.no_allow else
             f"{len(ALLOW_TERMS)} allowed terms, {sum(len(v) for v in ALLOW_PATH_TERMS.values())} allowed terms by path"))
    print(f"third_party (vendored, not changed, not counted): {len(skipped)} hit(s) in "
          f"{len(set(h[0] for h in skipped))} file(s)")
    if a.counts:
        rx = _regex()
        index = {p.lower(): i for i, p in enumerate(patterns())}
        for label, group in (("skipped", skipped), ("HIT", hits)):
            per = {}
            for h in group:
                per.setdefault(h[0], []).append(index[h[2].lower()])
            for path in sorted(per):
                masked = rx.sub(lambda m: f"<#{index[m.group(0).lower()]:02d}>", path)
                nums = ", ".join(f"#{n:02d} x{per[path].count(n)}" for n in sorted(set(per[path])))
                print(f"  {label}  {masked}  {len(per[path])} hit(s): {nums}")
        print(f"files with a counted hit: {len(set(h[0] for h in hits))}")
    else:
        for h in skipped:
            print("  skipped  %s  %s  [%s]  %s" % h)
        for h in hits:
            print("  HIT  %s  %s  [%s]  %s" % h)
    print(f"hits: {len(hits)}")
    print("clean" if not hits else "NOT CLEAN")
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main())
