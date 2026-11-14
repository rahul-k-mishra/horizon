"""
test_check_no_aid.py -- tests scripts/check_no_aid.py on git repositories it makes in a temporary folder.
It reads no file of this repository other than the script under test.  The planted text is built at run time
from check_no_aid.patterns(), so this file does not itself match, and the console names patterns by number.

Checks:
    1. a clean repository returns 0 although it holds "General Video Game AI", "GVGAI", "ARC-AGI-3",
       "ARC Prize", a cited title and journal name with "AI" and "AAAI", a docx whose styles part has
       "tblCellMar", Python's re.fullmatch and the GVGAI sprite fullMolarInf;
    2. every one of the patterns, planted in a sentence of a text file, is found, once, in that file, in
       lower case and in capitals, and the check returns 1;
    3. a pattern is found in a directory name, a docx's docProps/app.xml, a PNG tEXt chunk, a PNG zTXt
       chunk, a gzip file, a PDF Info dictionary, a Flate stream of a PDF, a notebook's metadata, a UTF-16
       log and a zip member's name;
    4. a term allowed in one path only is a hit in another path;
    5. a hit under third_party/ is reported apart and does not count;
    6. --rev searches the files as stored at that commit and not the working tree.
Run: D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\test_check_no_aid.py > logs\\test_check_no_aid.log
"""
import gzip
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_no_aid as C  # noqa: E402

FAILS = []
P = C.patterns()


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


def make_repo(tmp, name, files):
    repo = os.path.join(tmp, name)
    os.makedirs(repo)
    git(repo, "init", "-q")
    for path, data in files.items():
        full = os.path.join(repo, *path.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "files")
    return repo


def run(repo, *extra):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = C.main(["--repo", repo, *extra])
    return code, buf.getvalue()


def zip_bytes(members):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in members.items():
            z.writestr(n, d)
    return b.getvalue()


def png_bytes(chunks):
    def chunk(typ, body):
        return struct.pack(">I", len(body)) + typ + body + struct.pack(">I", zlib.crc32(typ + body))
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00")
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
    for typ, body in chunks:
        out += chunk(typ, body)
    return out + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def pdf_bytes(info_producer, stream_text):
    s = zlib.compress(stream_text.encode("latin-1"))
    return (b"%PDF-1.4\n1 0 obj << /Producer (" + info_producer.encode("latin-1") + b") >> endobj\n"
            b"2 0 obj << /Length " + str(len(s)).encode() + b" /Filter /FlateDecode >>\nstream\n" + s +
            b"\nendstream\nendobj\ntrailer << /Info 1 0 R >>\n%%EOF\n")


CLEAN = {
    "README.md": ("Games of the General Video Game AI framework (GVGAI); the benchmark ARC-AGI-3 and the ARC Prize.\n"
                  "Perez-Liebana, D. et al. General Video Game AI: Competition, Challenges and Opportunities. "
                  "AAAI 2016.\nSchaul, T. A video game description language for model-based or interactive "
                  "learning. IEEE Trans. Comput. Intell. AI Games 2013.\n"),
    "docs/paper.docx": zip_bytes({"word/styles.xml": "<w:style><w:tblPr><w:tblCellMar/></w:tblPr></w:style>",
                                  "docProps/app.xml": "<Application>Word processor</Application>"}),
    "scripts/x.py": "import re\nm = re.fullmatch(r'a', 'a')\n",
    "docs/truth.json": '{"text": "deadMolarInf avatar > transformTo stype=fullMolarInf"}\n',
    "docs/fig.png": png_bytes([(b"tEXt", b"Software\x00Matplotlib version3.10.9")]),
}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        # 1. clean
        repo = make_repo(tmp, "clean", CLEAN)
        code, out = run(repo)
        check(code == 0 and "hits: 0" in out and "clean" in out,
              "clean repository with GVGAI, ARC-AGI-3, cited titles with AI, AAAI, tblCellMar, fullmatch, fullMolar returns 0")
        hits, skipped, files = C.scan(repo)
        check(files == len(CLEAN) and not hits and not skipped, f"clean repository: {files} files read, no hit")

        # 2. every pattern in a text file, lower case and capitals
        for case in ("lower", "upper"):
            files = dict(CLEAN)
            for i, p in enumerate(P):
                files[f"docs/note{i:02d}.md"] = f"First line.\nThis text was made {p.upper() if case == 'upper' else p} the end.\n"
            repo = make_repo(tmp, f"each-{case}", files)
            hits, _, _ = C.scan(repo)
            per = {}
            for h in hits:
                per.setdefault(h[0], []).append(h)
            for i, p in enumerate(P):
                got = per.get(f"docs/note{i:02d}.md", [])
                # a longer pattern may contain a shorter one; the longer one is reported, once
                check(len(got) == 1 and got[0][1] == "line 2", f"pattern #{i:02d} ({case} case) found once, on line 2")
            check(len(hits) == len(P), f"{case} case: {len(hits)} hits for {len(P)} planted patterns, none elsewhere")
            code, _ = run(repo)
            check(code == 1, f"{case} case: the check returns 1")

        # 3. other places
        word, tool = P[12], P[16]          # a single name, and a second one
        places = {
            f"docs/{word}-notes/a.txt": "plain text\n",
            "docs/report.docx": zip_bytes({"word/document.xml": "<w:t>Body</w:t>",
                                           "docProps/app.xml": f"<Application>{tool} writer</Application>"}),
            "docs/plot_text.png": png_bytes([(b"tEXt", ("Comment\x00made by " + word).encode())]),
            "docs/plot_ztxt.png": png_bytes([(b"zTXt", b"Comment\x00\x00" + zlib.compress(("by " + word).encode()))]),
            "runs/rows.json.gz": gzip.compress(f'{{"note": "{tool}"}}\n'.encode()),
            "docs/info.pdf": pdf_bytes(f"{word} 1.0", "BT (Hello) Tj ET"),
            "docs/stream.pdf": pdf_bytes("TeX", f"BT ({tool} text) Tj ET"),
            "kaggle/nb.ipynb": json.dumps({"cells": [], "metadata": {"kernelspec": {"display_name": word}}}),
            "logs/utf16.log": ("line one\r\nrun by " + word + "\r\n").encode("utf-16"),
            "docs/bundle.zip": zip_bytes({f"{word}.txt": "plain"}),
        }
        repo = make_repo(tmp, "places", places)
        hits, _, _ = C.scan(repo)
        for path in places:
            check(any(h[0] == path for h in hits), f"hit found in {path.replace(word, '<pattern #12>')}")
        where = {h[1].split(":")[0] for h in hits}
        check("path" in where, "a directory name is searched")
        check(any("docProps/app.xml" in h[1] for h in hits), "docx docProps/app.xml is searched")
        check(any("png zTXt" in h[1] for h in hits), "a PNG zTXt chunk is decompressed and searched")
        check(any("pdf stream" in h[1] for h in hits), "a PDF Flate stream is decompressed and searched")
        check(any("gzip content" in h[1] for h in hits), "a gzip file is decompressed and searched")
        check(any(h[1] == "zip member name" for h in hits), "a zip member's name is searched")

        # 4. a term allowed by path, in another path
        allowed_line = "    " + tool + "==2.54.0\n"
        repo = make_repo(tmp, "bypath", {"logs/envprobe.log": allowed_line, "logs/other.log": allowed_line})
        hits, _, _ = C.scan(repo)
        check([h[0] for h in hits] == ["logs/other.log"], "a term allowed in logs/envprobe.log is a hit in logs/other.log")

        # 5. third_party
        repo = make_repo(tmp, "vendored", {"third_party/lib/a.txt": f"by {word}\n", "README.md": "plain\n"})
        code, out = run(repo)
        hits, skipped, _ = C.scan(repo)
        check(code == 0 and not hits and len(skipped) == 1 and "1 hit(s) in 1 file(s)" in out,
              "a hit under third_party/ is reported apart and does not count")

        # 6. --rev
        repo = make_repo(tmp, "rev", {"docs/a.md": f"made {P[3]} someone\n"})
        first = git(repo, "rev-parse", "HEAD")
        with open(os.path.join(repo, "docs", "a.md"), "w", encoding="utf-8") as f:
            f.write("plain\n")
        git(repo, "commit", "-q", "-am", "two")
        code_tree, _ = run(repo)
        code_first, _ = run(repo, "--rev", first)
        code_head, _ = run(repo, "--rev", "HEAD")
        check(code_tree == 0 and code_head == 0 and code_first == 1,
              f"--rev reads the commit: working tree {code_tree}, HEAD {code_head}, first commit {code_first}")

    print("OK" if not FAILS else f"{len(FAILS)} failure(s)")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
