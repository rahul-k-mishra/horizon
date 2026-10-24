"""
Row schemas of HORIZON (docs/AUTOMATION.md, Section 5).  Standard library only.

Two kinds of row, in two folders, with two schemas whose fields are disjoint apart from the identity
fields.  The rule they enforce: no feature may be computable only after an agent runs.
    horizon.search.v1   runs/<campaign>/search/<unit_id>.json   written by a search job, which plays
                        no agent; it holds the only fields an analysis may use as features
    horizon.search.v2   the same, plus "measures" (branching and the effective-horizon bound); written by
                        the kind devsearch under runs/<campaign>/devsearch/ (stage D, docs/DESIGN.md 2.1)
    horizon.agent.v1    runs/<campaign>/agent/<unit_id>.json    written by an agent job; its "outcome"
                        is the only part an analysis may read, and only as the outcome; "agent_stats"
                        (what the agent did, how many states it saw, how many actions it took) is kept
                        for the record and no loader in this file returns it
A row that carries a field of the other schema, or any field not listed here, fails validation, and
the loop refuses to commit it (scripts/automation/loop.py, integrate).
"""
from __future__ import annotations

import json

SEARCH_SCHEMA = "horizon.search.v1"
SEARCH_SCHEMA_V2 = "horizon.search.v2"
SEARCH_KINDS = ("search", "devsearch")
MEASURE_KEYS = {"branching", "eh", "eh_k", "eh_status", "eh_horizon"}
AGENT_SCHEMA = "horizon.agent.v1"
IDENTITY = {"schema", "campaign", "unit_id", "chunk_id", "suite", "game", "sessions", "written_at"}
SEARCH_KEYS = IDENTITY | {"level", "complete", "capped", "cap_hit", "counts", "caps", "seconds_spent"}
SEARCH_COUNTS = {"states_seen", "states_expanded", "depth_max", "frontier_left", "solution_length",
                 "successors_total", "spill_files_max"}
SEARCH_CAPS = {"node_cap", "time_cap_seconds", "memory_cap_bytes", "spill_frontier_over"}
CAP_KINDS = ("node", "time", "memory")
AGENT_KEYS = IDENTITY | {"agent", "seed", "budget", "outcome", "agent_stats", "cut_by_cap", "seconds"}
OUTCOME_KEYS = {"level1_completed", "levels"}
SESSION_KEYS = {"run_nonce", "host", "started_at", "ended_at", "kaggle_env"}
SEARCH_KEYS_V2 = SEARCH_KEYS | {"measures"}
assert not (SEARCH_KEYS_V2 - IDENTITY) & (AGENT_KEYS - IDENTITY), "the two schemas must stay disjoint"


def _sessions(row, errs):
    s = row.get("sessions")
    if not isinstance(s, list) or not s:
        errs.append("sessions must be a non-empty list")
        return
    for x in s:
        if not isinstance(x, dict) or set(x) != SESSION_KEYS:
            errs.append(f"session entry has keys {sorted(x) if isinstance(x, dict) else x}, expected {sorted(SESSION_KEYS)}")


def validate_search_row(row):
    errs = []
    keys = {SEARCH_SCHEMA: SEARCH_KEYS, SEARCH_SCHEMA_V2: SEARCH_KEYS_V2}.get(row.get("schema"))
    if keys is None:
        return [f"schema is {row.get('schema')!r}, expected {SEARCH_SCHEMA} or {SEARCH_SCHEMA_V2}"]
    if set(row) != keys:
        errs.append(f"keys differ from {row['schema']}: extra {sorted(set(row) - keys)}, "
                    f"missing {sorted(keys - set(row))}")
        return errs
    if "measures" in row and (not isinstance(row["measures"], dict) or set(row["measures"]) != MEASURE_KEYS):
        errs.append(f"measures keys must be {sorted(MEASURE_KEYS)}")
    if set(row["counts"]) != SEARCH_COUNTS:
        errs.append(f"counts keys {sorted(row['counts'])}, expected {sorted(SEARCH_COUNTS)}")
    if set(row["caps"]) != SEARCH_CAPS:
        errs.append(f"caps keys {sorted(row['caps'])}, expected {sorted(SEARCH_CAPS)}")
    if not isinstance(row["complete"], bool) or not isinstance(row["capped"], bool):
        errs.append("complete and capped must be booleans")
    if row["capped"]:
        if row["cap_hit"] not in CAP_KINDS:
            errs.append(f"a capped row needs cap_hit in {CAP_KINDS}")
        if row["complete"]:
            errs.append("a capped row cannot be complete")
    elif row["cap_hit"] is not None:
        errs.append("cap_hit must be null on an uncapped row")
    if not row["capped"] and not row["complete"]:
        errs.append("a row is either complete or capped; an unfinished search is a checkpoint, not a row")
    _sessions(row, errs)
    return errs


def validate_agent_row(row):
    errs = []
    if row.get("schema") != AGENT_SCHEMA:
        return [f"schema is {row.get('schema')!r}, expected {AGENT_SCHEMA}"]
    if set(row) != AGENT_KEYS:
        errs.append(f"keys differ from {AGENT_SCHEMA}: extra {sorted(set(row) - AGENT_KEYS)}, "
                    f"missing {sorted(AGENT_KEYS - set(row))}")
        return errs
    if set(row["outcome"]) != OUTCOME_KEYS:
        errs.append(f"outcome keys {sorted(row['outcome'])}, expected {sorted(OUTCOME_KEYS)}")
    elif not isinstance(row["outcome"]["level1_completed"], bool):
        errs.append("outcome.level1_completed must be a boolean")
    if not isinstance(row["agent_stats"], dict):
        errs.append("agent_stats must be an object")
    _sessions(row, errs)
    return errs


def validate_row(row, kind):
    return validate_search_row(row) if kind in SEARCH_KINDS else validate_agent_row(row)


# ---------------------------------------------------------------- the only two loaders an analysis may use
def load_features(paths):
    """{(suite, game, level): {counts..., complete, capped, cap_hit}} from search rows only.  A file of
    any other schema stops the load."""
    out = {}
    for p in paths:
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        e = validate_search_row(r)
        if e:
            raise ValueError(f"{p}: not a valid {SEARCH_SCHEMA} row: {e}")
        out[(r["suite"], r["game"], r["level"])] = dict(r["counts"], complete=r["complete"], capped=r["capped"],
                                                      cap_hit=r["cap_hit"], measures=r.get("measures"))
    return out


def load_outcomes(paths):
    """{(suite, game, agent, seed): {level1_completed, levels}} from agent rows only; nothing else of an
    agent row leaves this function."""
    out = {}
    for p in paths:
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        e = validate_agent_row(r)
        if e:
            raise ValueError(f"{p}: not a valid {AGENT_SCHEMA} row: {e}")
        out[(r["suite"], r["game"], r["agent"], r["seed"])] = {k: r["outcome"][k] for k in OUTCOME_KEYS}
    return out
