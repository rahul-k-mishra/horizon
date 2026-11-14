"""
zenodo_deposit.py -- writes the files the author uploads to Zenodo on the day of a registration tag
(docs/PREREG.md, Section 0; the author's steps are docs/registration/ZENODO.md).

The registration of HORIZON is the annotated git tag (prereg-v1, later prereg-v1.1, ...) together with a
Zenodo deposit made the same day that carries the SHA-256 of every tagged protocol file.  This script only
reads the repository: it uploads nothing and changes no file in it.

What it does, for a given tag:
    1. checks that the tag exists and is annotated, and reads its commit, tagger and date;
    2. reads docs/registration/protocol_files.txt as stored at that commit, and takes every listed file as
       stored in git at that commit (git cat-file), never from the working tree; it stops if a listed file is
       missing at the tag;
    2a. runs scripts/check_no_aid.py on every file of the tagged commit and stops if it finds a hit (rule R2,
       docs/RULES.md; added 14 November 2026);
    3. writes, into the output folder (default: a folder named after the tag under the system's temporary
       folder, which is outside the repository):
         protocol/<path>          each listed file, byte for byte as stored in git;
         protocol.zip             the same files in one zip, entries in list order with a fixed date, so that
                                  the zip itself is the same on every run;
         SHA256SUMS.txt           one line per file: SHA-256, git blob hash, path; then the zip's SHA-256;
         description.txt          the text for the deposit's description field, with the tag, the commit,
                                  the tag date and every SHA-256;
         metadata.json            the deposit's form fields, for the author to copy;
    4. prints a summary, and a warning if today (local date) is not the tag's date, since the deposit must be
       made on the day of the tag.
Line endings: git stores the files of this repository with LF.  A checkout on Windows with core.autocrlf=true
gives CRLF and other SHA-256 values; to compare, hash "git show <tag>:<path>" or a checkout without
conversion.  The git blob hash in SHA256SUMS.txt is independent of the checkout.

Run (working directory D:\\Research\\horizon\\repo), on the day of the tag:
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\zenodo_deposit.py --tag prereg-v1
Tested by scripts/test_zenodo_deposit.py on a repository it makes in a temporary folder.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_no_aid  # noqa: E402

REPO =os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST_PATH = "docs/registration/protocol_files.txt"
REPO_URL = "https://github.com/rahul-k-mishra/horizon"
AUTHOR = {"name": "Mishra, Rahul Kumar",
          "affiliation": "Independent Researcher, Ranchi, Jharkhand, India",
          "orcid": "0009-0004-9671-4055"}
ZIP_DATE = (2026, 1, 1, 0, 0, 0)


def git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if binary else r.stdout.decode("utf-8").strip()


def tag_info(repo, tag):
    kind = subprocess.run(["git", "-C", repo, "cat-file", "-t", f"refs/tags/{tag}"], capture_output=True)
    if kind.returncode != 0:
        raise SystemExit(f"no tag {tag}")
    if kind.stdout.decode().strip() != "tag":
        raise SystemExit(f"{tag} is a lightweight tag; the registration needs an annotated tag")
    commit = git(repo, "rev-list", "-n", "1", tag)
    fields = git(repo, "for-each-ref", f"refs/tags/{tag}",
                 "--format=%(taggername)%00%(taggerdate:short)%00%(taggerdate:iso8601-strict)")
    name, day, stamp = fields.split("\0")
    return dict(tag=tag, commit=commit, tagger=name, date=day, timestamp=stamp)


def read_list(repo, commit):
    text = git(repo, "cat-file", "-p", f"{commit}:{LIST_PATH}", binary=True).decode("utf-8")
    paths = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            if line in paths:
                raise SystemExit(f"{LIST_PATH} lists {line} twice")
            paths.append(line)
    if LIST_PATH not in paths:
        paths.insert(0, LIST_PATH)
    return paths


def build(repo, tag, out):
    info = tag_info(repo, tag)
    paths = read_list(repo, info["commit"])
    missing = [p for p in paths
               if subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{info['commit']}:{p}"],
                                 capture_output=True).returncode != 0]
    if missing:
        raise SystemExit("listed files missing at the tag: " + ", ".join(missing))
    hits, _, _ = check_no_aid.scan(repo, info["commit"])
    if hits:
        raise SystemExit(f"scripts/check_no_aid.py finds {len(hits)} hit(s) in the files at the tag "
                         f"(rule R2, docs/RULES.md); first: {hits[0][0]} {hits[0][1]}")
    os.makedirs(out, exist_ok=True)
    rows = []
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            data = git(repo, "cat-file", "-p", f"{info['commit']}:{p}", binary=True)
            blob = git(repo, "rev-parse", f"{info['commit']}:{p}")
            dest = os.path.join(out, "protocol", *p.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            zi = zipfile.ZipInfo(p, date_time=ZIP_DATE)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
            rows.append(dict(path=p, sha256=hashlib.sha256(data).hexdigest(), blob=blob, bytes=len(data)))
    zdata = zbuf.getvalue()
    with open(os.path.join(out, "protocol.zip"), "wb") as f:
        f.write(zdata)
    zsha = hashlib.sha256(zdata).hexdigest()

    sums = [f"# HORIZON registration {tag}, commit {info['commit']}, tag date {info['date']}",
            "# sha256  git-blob  path  (files as stored in git at the tag)"]
    sums += [f"{r['sha256']}  {r['blob']}  {r['path']}" for r in rows]
    sums.append(f"# protocol.zip sha256 {zsha}")
    with open(os.path.join(out, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sums) + "\n")

    desc = [f"The registered protocol of HORIZON, version {tag}, by Rahul Kumar Mishra.",
            "",
            f"This deposit is one half of the registration; the other half is the annotated git tag {tag} "
            f"in {REPO_URL}, on commit {info['commit']}, tagged {info['timestamp']}. The deposit is made on "
            "the day of the tag. Its timestamp and DOI fix the date by which the files below existed; the "
            "repository alone cannot, since its owner can move a tag.",
            "",
            "Each file is given as stored in git at the tag (git show <tag>:<path>), with its SHA-256 and git "
            "blob hash:",
            ""]
    desc += [f"{r['sha256']}  {r['path']}" for r in rows]
    desc += ["", f"protocol.zip holds the same files; its SHA-256 is {zsha}.",
             "The registration and its rules are in docs/PREREG.md, Section 0."]
    with open(os.path.join(out, "description.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(desc) + "\n")

    meta = dict(title=f"HORIZON: registered protocol {tag}",
                creators=[AUTHOR],
                publication_date=info["date"],
                version=tag,
                description_file="description.txt",
                files_to_upload=["protocol.zip", "SHA256SUMS.txt"],
                related_identifiers=[dict(identifier=f"{REPO_URL}/tree/{tag}", note="the git tag")],
                tag=info, files=rows, zip_sha256=zsha,
                left_to_the_author=["resource type", "licence", "keywords", "relation type of the link"])
    with open(os.path.join(out, "metadata.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=1)
        f.write("\n")
    return info, rows, zsha


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", default=None)
    ap.add_argument("--today", default=None, help="for tests: the date to compare with the tag date")
    a = ap.parse_args(argv)
    out = a.out or os.path.join(tempfile.gettempdir(), f"horizon-zenodo-{a.tag}")
    info, rows, zsha = build(a.repo, a.tag, out)
    print(f"tag {info['tag']} (annotated), commit {info['commit']}, tagger {info['tagger']}, date {info['date']}")
    print(f"files {len(rows)}, bytes {sum(r['bytes'] for r in rows)}; protocol.zip sha256 {zsha}")
    print(f"written: protocol/, protocol.zip, SHA256SUMS.txt, description.txt, metadata.json under the folder "
          f"{'given by --out' if a.out else 'horizon-zenodo-' + a.tag + ' in the temporary folder'}")
    today = a.today or datetime.date.today().isoformat()
    if today != info["date"]:
        print(f"WARNING: today is {today} and the tag is dated {info['date']}; the deposit must be made on the "
              f"day of the tag (docs/PREREG.md, Section 0)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
