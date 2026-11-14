"""
test_zenodo_deposit.py -- tests scripts/zenodo_deposit.py on a git repository it makes in a temporary folder.
It reads no file of this repository other than the script under test.

Checks:
    1. on an annotated tag, every listed file is written byte for byte as committed, its SHA-256 and git blob
       hash in SHA256SUMS.txt equal values computed here, the description names the tag, the commit and every
       SHA-256, and the list file itself is included;
    2. the files are taken from the tag, not the working tree or a later commit;
    3. protocol.zip is the same on a second run;
    4. a listed file missing at the tag stops the script; a lightweight tag stops it; a tag date other than
       today returns 2 with a warning.
Run: D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\test_zenodo_deposit.py > logs\\test_zenodo_deposit.log
"""
import hashlib
import io
import os
import subprocess
import sys
import tempfile
import zipfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zenodo_deposit as Z  # noqa: E402

FAILS = []


def check(cond, what):
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def git(repo, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.org", GIT_COMMITTER_NAME="T",
               GIT_COMMITTER_EMAIL="t@example.org")
    r = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", *args], capture_output=True, env=env)
    assert r.returncode == 0, r.stderr
    return r.stdout.decode().strip()


def write(repo, path, data):
    full = os.path.join(repo, *path.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)


def rd(path, text=True):
    with open(path, "r" if text else "rb", **({"encoding": "utf-8"} if text else {})) as f:
        return f.read()


def run(argv):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = Z.main(argv)
    except SystemExit as e:
        return ("exit", str(e)), buf.getvalue()
    return code, buf.getvalue()


def main():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "repo")
        os.makedirs(repo)
        git(repo, "init", "-q")
        files = {"docs/PREREG.md": b"# protocol\nline two\n", "scripts/a.py": b"print(1)\n",
                 "data/b.bin": bytes(range(256))}
        listing = b"# comment\n\ndocs/PREREG.md\nscripts/a.py\n# not listed: c\ndata/b.bin\n"
        for p, d in files.items():
            write(repo, p, d)
        write(repo, Z.LIST_PATH, listing)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "one")
        git(repo, "tag", "-a", "prereg-v1", "-m", "registration")
        commit = git(repo, "rev-parse", "HEAD")
        day = git(repo, "for-each-ref", "refs/tags/prereg-v1", "--format=%(taggerdate:short)")
        # a later commit and a dirty working tree must not leak into the deposit
        write(repo, "docs/PREREG.md", b"# changed after the tag\n")
        git(repo, "commit", "-q", "-am", "two")
        write(repo, "scripts/a.py", b"print(2)\n")

        out = os.path.join(tmp, "out")
        code, text = run(["--tag", "prereg-v1", "--repo", repo, "--out", out, "--today", day])
        check(code == 0, f"annotated tag on its own day returns 0 (got {code})")
        expect = dict(files)
        expect[Z.LIST_PATH] = listing
        for p, d in expect.items():
            check(rd(os.path.join(out, "protocol", *p.split("/")), False) == d,
                  f"{p} written as committed at the tag")
        sums = rd(os.path.join(out, "SHA256SUMS.txt"))
        desc = rd(os.path.join(out, "description.txt"))
        for p, d in expect.items():
            sha = hashlib.sha256(d).hexdigest()
            blob = git(repo, "rev-parse", f"prereg-v1:{p}")
            check(f"{sha}  {blob}  {p}" in sums, f"{p}: SHA-256 and blob hash in SHA256SUMS.txt")
            check(f"{sha}  {p}" in desc, f"{p}: SHA-256 in the description")
        check(commit in desc and "prereg-v1" in desc, "description names the tag and the commit")
        check("c\n" not in [l[-2:] for l in sums.splitlines()], "comment lines of the list are not files")
        zsha = hashlib.sha256(rd(os.path.join(out, "protocol.zip"), False)).hexdigest()
        with zipfile.ZipFile(os.path.join(out, "protocol.zip")) as z:
            check(sorted(z.namelist()) == sorted(expect), "protocol.zip holds exactly the listed files")
            check(all(z.read(p) == d for p, d in expect.items()), "protocol.zip entries equal the tagged files")
        out2 = os.path.join(tmp, "out2")
        run(["--tag", "prereg-v1", "--repo", repo, "--out", out2, "--today", day])
        zsha2 = hashlib.sha256(rd(os.path.join(out2, "protocol.zip"), False)).hexdigest()
        check(zsha == zsha2, "protocol.zip is the same on a second run")
        check(f"protocol.zip sha256 {zsha}" in sums, "the zip's SHA-256 is in SHA256SUMS.txt")

        code, text = run(["--tag", "prereg-v1", "--repo", repo, "--out", out, "--today", "1999-01-01"])
        check(code == 2 and "WARNING" in text, "a tag date other than today returns 2 with a warning")

        git(repo, "tag", "light")
        code, _ = run(["--tag", "light", "--repo", repo, "--out", os.path.join(tmp, "o3"), "--today", day])
        check(isinstance(code, tuple) and "lightweight" in code[1], "a lightweight tag stops the script")

        write(repo, Z.LIST_PATH, listing + b"scripts/missing.py\n")
        git(repo, "commit", "-q", "-am", "three")
        git(repo, "tag", "-a", "prereg-v1.1", "-m", "v1.1")
        code, _ = run(["--tag", "prereg-v1.1", "--repo", repo, "--out", os.path.join(tmp, "o4"), "--today", day])
        check(isinstance(code, tuple) and "scripts/missing.py" in code[1], "a listed file missing at the tag stops it")

        code, _ = run(["--tag", "nosuchtag", "--repo", repo, "--out", os.path.join(tmp, "o5")])
        check(isinstance(code, tuple) and "no tag" in code[1], "an unknown tag stops the script")

    print("OK" if not FAILS else f"{len(FAILS)} failure(s)")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
