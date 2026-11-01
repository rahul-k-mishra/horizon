#!/usr/bin/env bash
# check_freeze.sh -- does requirements-loop.txt hold everything the kaggle tool needs, with nothing taken
# from outside it?  The halt of 1 November 2026 (docs/STATE.md, amendment n) came from a package the tool
# imports but no pinned package brought in, so a resolve cannot answer this; only an install that adds
# nothing can.
#
#   1. pip download --no-deps of exactly the pinned files into an empty wheelhouse (the only network use
#      besides step 4);
#   2. a virtual environment made with --without-pip, so it holds no pip and no setuptools;
#   3. pip install --no-index --find-links <wheelhouse> --no-deps -r requirements-loop.txt into it,
#      run by a pip outside it (pip --python);
#   4. in it: the package list, an import of the kaggle tool, and one read-only kaggle kernels status;
#   5. the control: steps 2 to 4 with six taken out of the file; the import must fail on six, as every
#      tick from 07:32Z on 1 November 2026 did.
# Reads committed files and the Kaggle API only; changes nothing under jobs/ or runs/.
# Run from the repository, in Git Bash on Windows:
#   bash scripts/automation/check_freeze.sh D:/python/3.11.9/python.exe > logs/check_freeze.log 2>&1
set -u
PY=${1:?usage: check_freeze.sh <python 3.11 interpreter>}
REQ=requirements-loop.txt
KERNEL=${KERNEL:-ericsom/horizon-runner}
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
# the console names the temporary folder <tmp> (on Windows its path holds the user's profile), and leaves out
# venv's notice that the short form of that path was resolved to its long form
exec > >(sed -u -E -e 's#[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/]AppData[\\/]Local[\\/]Temp[\\/]tmp\.[A-Za-z0-9]+#<tmp>#g' \
                   -e '/Actual environment location may have moved|Requested location:|Actual location:/d') 2>&1
say() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
bin() { if [ -d "$1/Scripts" ]; then echo "$1/Scripts"; else echo "$1/bin"; fi; }
exe() { if [ -f "$1.exe" ]; then echo "$1.exe"; else echo "$1"; fi; }   # pip --python needs .exe on Windows

say "interpreter: $("$PY" --version 2>&1); file: $REQ, sha256 $(sha256sum "$REQ" | cut -c1-64)"
say "pins: $(grep -cE '^[A-Za-z0-9_.-]+==' "$REQ")"
"$PY" -m venv "$T/tool"
TP="$(bin "$T/tool")/python"
"$TP" -m pip --version
say "step 1: download the pinned files only"
"$TP" -m pip download --quiet --disable-pip-version-check --no-deps -d "$T/wh" -r "$REQ" || { say "FAIL: download"; exit 1; }
say "wheelhouse: $(ls "$T/wh" | wc -l) files"

install_and_run() {   # $1 requirements file, $2 label
    local env="$T/env-$2"
    "$PY" -m venv --without-pip "$env"
    local P B
    B=$(bin "$env"); P=$(exe "$B/python")
    say "[$2] step 2: empty environment; modules pip and setuptools present: $("$P" -I -c 'import importlib.util as u; print([m for m in ("pip", "setuptools") if u.find_spec(m)])')"
    say "[$2] step 3: offline install, no dependency resolution"
    "$TP" -m pip --disable-pip-version-check --python "$P" install --quiet --no-index --find-links "$T/wh" --no-deps -r "$1" \
        || { say "[$2] FAIL: install"; return 1; }
    say "[$2] installed:"
    "$TP" -m pip --disable-pip-version-check --python "$P" list --format=freeze
    say "[$2] step 4: import and one read-only status"
    "$B/kaggle" --version 2>&1 | grep -v "outdated" || true
    "$B/kaggle" kernels status "$KERNEL" 2>&1 | grep -v "outdated"
    return "${PIPESTATUS[0]}"
}

install_and_run "$REQ" frozen; rc=$?
say "[frozen] exit code $rc"
grep -vE '^six==' "$REQ" > "$T/no-six.txt"
install_and_run "$T/no-six.txt" control-without-six; rc2=$?
say "[control-without-six] exit code $rc2 (must be non-zero)"
if [ "$rc" -eq 0 ] && [ "$rc2" -ne 0 ]; then say "OK"; exit 0; fi
say "FAIL"; exit 1
