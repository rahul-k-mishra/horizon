"""
Shared helpers of the HORIZON automation (docs/AUTOMATION.md).  Standard library only, so that the
same file runs on a Kaggle CPU session, on a GitHub Actions runner and on the author's laptop.

Files of the loop, relative to the repository root:
    jobs/manifest.json   the campaign: settings, one line per chunk, one line per unit of work
    jobs/state.json      the dispatch in flight (if any), the halt flag, the history of sessions
    jobs/lock.json       present only while a dispatch holds the loop
    logs/automation.log  one line per acting tick; STATE-ready text when the loop halts
    runs/<campaign>/search/<unit_id>.json    search rows   (schema horizon.search.v1)
    runs/<campaign>/agent/<unit_id>.json     agent rows    (schema horizon.agent.v1)
    runs/<campaign>/done/<unit_id>.json      done-markers
    runs/<campaign>/checkpoints/<chunk_id>/  the latest checkpoint of an unfinished chunk
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os

MANIFEST = "jobs/manifest.json"
STATE = "jobs/state.json"
LOCK = "jobs/lock.json"
AUTOLOG = "logs/automation.log"
KINDS = ("search", "agent")
CHUNK_STATUS = ("pending", "running", "partial", "done", "failed")


def now_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    """Atomic write: a temporary file in the same folder, then a rename."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- manifest
def load_manifest(repo):
    return read_json(os.path.join(repo, MANIFEST))


def save_manifest(repo, m):
    """One line per chunk and one line per unit, so that a diff shows each change on its own line."""
    head = {k: v for k, v in m.items() if k not in ("chunks", "units")}
    lines = ["{"]
    for k in sorted(head):
        lines.append(f' {json.dumps(k)}: {json.dumps(head[k], sort_keys=True)},')
    lines.append(' "chunks": [')
    lines += ["  " + json.dumps(c, sort_keys=True) + ("," if i < len(m["chunks"]) - 1 else "")
              for i, c in enumerate(m["chunks"])]
    lines.append(" ],")
    lines.append(' "units": [')
    lines += ["  " + json.dumps(u, sort_keys=True) + ("," if i < len(m["units"]) - 1 else "")
              for i, u in enumerate(m["units"])]
    lines.append(" ]")
    lines.append("}")
    path = os.path.join(repo, MANIFEST)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)


def check_manifest(m):
    """Structural rules: every chunk has one kind, every unit belongs to one chunk of the same kind,
    a chunk never mixes kinds, ids are unique."""
    errs = []
    ids = [c["chunk_id"] for c in m["chunks"]]
    if len(ids) != len(set(ids)):
        errs.append("duplicate chunk_id")
    uids = [u["unit_id"] for u in m["units"]]
    if len(uids) != len(set(uids)):
        errs.append("duplicate unit_id")
    kind_of = {c["chunk_id"]: c["kind"] for c in m["chunks"]}
    for c in m["chunks"]:
        if c["kind"] not in KINDS:
            errs.append(f"chunk {c['chunk_id']}: unknown kind {c['kind']}")
        if c["status"] not in CHUNK_STATUS:
            errs.append(f"chunk {c['chunk_id']}: unknown status {c['status']}")
    for u in m["units"]:
        if u["chunk_id"] not in kind_of:
            errs.append(f"unit {u['unit_id']}: unknown chunk {u['chunk_id']}")
        elif u["kind"] != kind_of[u["chunk_id"]]:
            errs.append(f"unit {u['unit_id']}: kind {u['kind']} in a {kind_of[u['chunk_id']]} chunk")
    for c in m["chunks"]:
        if not chunk_units(m, c["chunk_id"]):
            errs.append(f"chunk {c['chunk_id']}: no units")
    return errs


def get_chunk(m, chunk_id):
    for c in m["chunks"]:
        if c["chunk_id"] == chunk_id:
            return c
    raise KeyError(chunk_id)


def chunk_units(m, chunk_id):
    return [u for u in m["units"] if u["chunk_id"] == chunk_id]


def kind_params(m, kind):
    return dict(m["kinds"][kind])


def unit_params(m, unit):
    """The kind's registered parameters, overridden by the unit's own."""
    p = kind_params(m, unit["kind"])
    p.update(unit.get("params") or {})
    return p


def chunk_entry_hash(m, chunk_id):
    """What a checkpoint and a dispatch are verified against: the campaign, the code tag, the chunk's
    kind, its units (without their status) and the parameters of its kind and of its units."""
    c = get_chunk(m, chunk_id)
    units = [{k: v for k, v in u.items() if k != "status"} for u in chunk_units(m, chunk_id)]
    return sha256_bytes(canonical(dict(campaign=m["campaign"], code_tag=m["code_tag"], chunk_id=chunk_id,
                                       kind=c["kind"], units=units, kind_params=m["kinds"][c["kind"]])))


def select_next(m):
    """The next chunk to run: a partial chunk first (in manifest order), then a pending one; never one
    whose failures reached the registered maximum."""
    eligible = [c for c in m["chunks"] if c["failures"] < m["max_failures"]]
    for status in ("partial", "pending"):
        for c in eligible:
            if c["status"] == status:
                return c
    return None


# ---------------------------------------------------------------- paths
def campaign_dir(m):
    return f"runs/{m['campaign']}"


def row_relpath(m, unit):
    return f"{campaign_dir(m)}/{unit['kind']}/{unit['unit_id']}.json"


def marker_relpath(m, unit):
    return f"{campaign_dir(m)}/done/{unit['unit_id']}.json"


def checkpoint_reldir(m, chunk_id):
    return f"{campaign_dir(m)}/checkpoints/{chunk_id}"


def unit_done(repo, m, unit):
    """A unit is done when its marker exists and the row it names has the recorded hash."""
    mp = os.path.join(repo, marker_relpath(m, unit))
    if not os.path.exists(mp):
        return False
    mk = read_json(mp)
    rp = os.path.join(repo, mk["row_path"])
    return os.path.exists(rp) and sha256_file(rp) == mk["row_sha256"]
