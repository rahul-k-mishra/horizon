"""
The two job kinds of HORIZON (docs/AUTOMATION.md, Sections 3 and 4).  Standard library only.

search  enumerates the first level of a game from its simulator, breadth first, with no agent.  It is
        bounded by three registered caps (nodes expanded, wall-clock seconds summed over sessions,
        resident memory) and spills its frontier to disk past a registered size.  It stops at the
        session deadline with its whole state in a checkpoint and resumes from it in a later session.
        Its result is one horizon.search.v1 row per game and level, complete or capped.
agent   runs one agent on one game and seed.  The seed is the smallest resumable unit: a seed starts
        only if its registered wall-clock cap fits before the session deadline, so no seed is ever cut
        by a session; a seed that exceeds its own cap is recorded as cut_by_cap.

A simulator is reached through a small interface (root_enc, root_info, expand; see DummyGraph): the dry run
uses DummyGraph, a deterministic integer graph slowed down by a sleep per batch, and the dummy agent, a
sleep; stage D's kind devsearch uses sim_minigrid.MiniGridSim.
"""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
import os
import socket
import time
from array import array

from common import now_iso, sha256_file
from schema import AGENT_SCHEMA, SEARCH_SCHEMA, SEARCH_SCHEMA_V2


def rss_bytes():
    """Resident memory of this process (Linux /proc); None where it cannot be read."""
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        return None
    return None


def kaggle_env():
    """Kaggle's own environment variables that are not credentials (names with TOKEN, SECRET, KEY or
    PROXY are left out)."""
    return {k: v for k, v in sorted(os.environ.items()) if k.startswith("KAGGLE_")
            and not any(s in k for s in ("TOKEN", "SECRET", "KEY", "PROXY"))}


def session_entry(nonce, started):
    return dict(run_nonce=nonce, host=socket.gethostname(), started_at=started, ended_at=now_iso(),
                kaggle_env=kaggle_env())


# ---------------------------------------------------------------- simulators
class DummyGraph:
    """Nodes 0..M-1; node n leads to (a*n + b) mod M for each (a, b) in `edges`; the root is 0; the
    goal is `goal`.  `seconds_per_batch` slows the search down so that the dry run can outlast a
    session."""

    def __init__(self, params):
        self.M = int(params["M"])
        self.edges = [tuple(e) for e in params["edges"]]
        self.goal = int(params["goal"])

    def root(self):
        return 0

    def successors(self, n):
        return [(i, (a * n + b) % self.M) for i, (a, b) in enumerate(self.edges)]

    def key(self, n):
        return n.to_bytes(8, "little")

    def is_goal(self, n):
        return n == self.goal

    def encode(self, n):
        return n

    def decode(self, x):
        return int(x)

    # the generic interface used by run_search
    win_is_terminal = False      # the dummy graph keeps expanding through its goal

    def root_enc(self):
        return self.root()

    def root_info(self):
        r = self.root()
        return self.key(r), self.is_goal(r), False

    def expand(self, enc):
        n = self.decode(enc)
        return self.key(n), [(a, self.encode(x), self.key(x), self.is_goal(x), False) for a, x in self.successors(n)]


def make_simulator(p, unit):
    if p["simulator"] == "dummy_graph":
        return DummyGraph(p)
    if p["simulator"] == "minigrid":
        from sim_minigrid import MiniGridSim  # noqa: PLC0415 -- needs gymnasium and minigrid
        return MiniGridSim(p, unit)
    raise ValueError(f"unknown simulator {p['simulator']}")


def h64(b):
    return int.from_bytes(hashlib.blake2b(b, digest_size=8).digest(), "little")


# ---------------------------------------------------------------- search
class SearchState:
    """Everything a breadth-first enumeration needs to resume: the frontier in three parts (head,
    spill files, tail; first in, first out across all three), the visited set as 64-bit hashes, the
    counts, and the seconds already spent."""

    def __init__(self):
        self.head = collections.deque()      # (encoded state, depth), next to expand
        self.spills = []                     # file names in work_dir, in order
        self.tail = []                       # newest entries
        self.visited = set()
        self.counts = dict(states_seen=0, states_expanded=0, depth_max=0, frontier_left=0,
                           solution_length=None, successors_total=0, spill_files_max=0)
        self.seconds_spent = 0.0
        self.spill_seq = 0
        self.sessions = []
        self.extra = dict(successors_distinct=0)
        self.graph = None            # transitions for the effective horizon, while the level is small enough
        self.graph_status = None     # None while recording, or why it stopped

    def frontier_size(self, spill_over):
        return len(self.head) + len(self.tail) + len(self.spills) * spill_over

    # -- checkpoint: files in `d`, described by the returned dict
    def save(self, d, work_dir):
        os.makedirs(d, exist_ok=True)
        files = {}
        vis = array("Q", sorted(self.visited))
        with gzip.open(os.path.join(d, "visited.u64.gz"), "wb", compresslevel=6) as f:
            f.write(vis.tobytes())
        files["visited.u64.gz"] = None
        for name, data in (("head.json.gz", list(self.head)), ("tail.json.gz", self.tail)):
            with gzip.open(os.path.join(d, name), "wt", encoding="utf-8") as f:
                json.dump(data, f)
            files[name] = None
        for s in self.spills:
            with open(os.path.join(work_dir, s), "rb") as src, open(os.path.join(d, s), "wb") as dst:
                dst.write(src.read())
            files[s] = None
        graph_meta = None
        if self.graph is not None:
            g = self.graph
            for name, arr in (("graph_hashes.u64.gz", g["hashes"]), ("graph_rows.i32.gz", g["rows"]),
                              ("graph_next.i32.gz", g["next"]), ("graph_win.i32.gz", g["win"]),
                              ("graph_loss.i32.gz", g["loss"])):
                with gzip.open(os.path.join(d, name), "wb", compresslevel=6) as f:
                    f.write(arr.tobytes())
                files[name] = None
            graph_meta = dict(A=g["A"], n=len(g["hashes"]))
        for k in files:
            files[k] = sha256_file(os.path.join(d, k))
        return dict(files=files, spills=list(self.spills), spill_seq=self.spill_seq, counts=dict(self.counts),
                    seconds_spent=self.seconds_spent, sessions=list(self.sessions), visited_n=len(self.visited),
                    extra=dict(self.extra), graph=graph_meta, graph_status=self.graph_status)

    @classmethod
    def load(cls, d, meta, work_dir):
        st = cls()
        for name, sha in meta["files"].items():
            if sha256_file(os.path.join(d, name)) != sha:
                raise ValueError(f"checkpoint file {name}: hash differs from the checkpoint record")
        with gzip.open(os.path.join(d, "visited.u64.gz"), "rb") as f:
            vis = array("Q")
            vis.frombytes(f.read())
        st.visited = set(vis)
        if len(st.visited) != meta["visited_n"]:
            raise ValueError("visited set size differs from the checkpoint record")
        with gzip.open(os.path.join(d, "head.json.gz"), "rt", encoding="utf-8") as f:
            st.head = collections.deque(tuple(x) for x in json.load(f))
        with gzip.open(os.path.join(d, "tail.json.gz"), "rt", encoding="utf-8") as f:
            st.tail = [tuple(x) for x in json.load(f)]
        os.makedirs(work_dir, exist_ok=True)
        for s in meta["spills"]:
            with open(os.path.join(d, s), "rb") as src, open(os.path.join(work_dir, s), "wb") as dst:
                dst.write(src.read())
        st.spills = list(meta["spills"])
        st.spill_seq = meta["spill_seq"]
        st.counts = dict(meta["counts"])
        st.seconds_spent = float(meta["seconds_spent"])
        st.sessions = list(meta["sessions"])
        st.extra = dict(meta.get("extra") or dict(successors_distinct=0))
        st.graph_status = meta.get("graph_status")
        if meta.get("graph"):
            g = dict(A=meta["graph"]["A"])
            for key, name, code in (("hashes", "graph_hashes.u64.gz", "Q"), ("rows", "graph_rows.i32.gz", "i"),
                                    ("next", "graph_next.i32.gz", "i"), ("win", "graph_win.i32.gz", "i"),
                                    ("loss", "graph_loss.i32.gz", "i")):
                arr = array(code)
                with gzip.open(os.path.join(d, name), "rb") as f:
                    arr.frombytes(f.read())
                g[key] = arr
            g["index"] = {h: i for i, h in enumerate(g["hashes"])}
            if len(g["hashes"]) != meta["graph"]["n"]:
                raise ValueError("graph size differs from the checkpoint record")
            st.graph = g
        return st


def _graph_id(g, hk):
    i = g["index"].get(hk)
    if i is None:
        i = len(g["hashes"])
        g["index"][hk] = i
        g["hashes"].append(hk)
    return i


def run_search(unit, p, work_dir, state, deadline, on_checkpoint, nonce, started, schema=SEARCH_SCHEMA):
    """Expand until the frontier is empty (complete), a cap is hit (capped), or the session deadline
    (stopped, state returned for the checkpoint).  Returns (status, row_or_None, state).

    Win and loss states are counted and, where the simulator says so (win_is_terminal), not expanded.
    With params eh_state_limit, the transitions are recorded while the level has at most that many states,
    and a complete search computes the effective-horizon bound (eh.py) with horizon eh_horizon; such rows
    use the schema horizon.search.v2, whose "measures" hold the branching and the bound."""
    sim = make_simulator(p, unit)
    terminal_on_win = getattr(sim, "win_is_terminal", False)
    spill_over = int(p["spill_frontier_over"])
    node_cap, time_cap, mem_cap = int(p["node_cap"]), float(p["time_cap_seconds"]), int(p["memory_cap_bytes"])
    batch, pause = int(p.get("batch", 1000)), float(p.get("seconds_per_batch", 0.0))
    every_s, every_n = float(p["checkpoint_every_seconds"]), int(p["checkpoint_every_nodes"])
    eh_limit = int(p.get("eh_state_limit", 0))
    os.makedirs(work_dir, exist_ok=True)
    if state is None:
        state = SearchState()
        rkey, rwin, rloss = sim.root_info()
        hk = h64(rkey)
        state.visited.add(hk)
        state.counts["states_seen"] = 1
        if rwin:
            state.counts["solution_length"] = 0
        if eh_limit:
            state.graph = dict(A=None, hashes=array("Q"), rows=array("i"), next=array("i"), win=array("i"),
                               loss=array("i"), index={})
            _graph_id(state.graph, hk)
        if not ((rwin and terminal_on_win) or rloss):
            state.head.append((sim.root_enc(), 0))
    c = state.counts
    t_mark = time.time()
    last_ck_t, last_ck_n = time.time(), c["states_expanded"]
    cap_hit = None

    def spend():
        nonlocal t_mark
        t = time.time()
        state.seconds_spent += t - t_mark
        t_mark = t

    while True:
        if not state.head:                                   # refill the head, first in first out
            if state.spills:
                name = state.spills.pop(0)
                with gzip.open(os.path.join(work_dir, name), "rt", encoding="utf-8") as f:
                    state.head = collections.deque(tuple(x) for x in json.load(f))
                os.remove(os.path.join(work_dir, name))
            elif state.tail:
                state.head, state.tail = collections.deque(state.tail), []
            else:
                break                                        # frontier empty: complete
        for _ in range(batch):
            if not state.head or c["states_expanded"] >= node_cap:
                break
            enc, depth = state.head.popleft()
            pkey, kids = sim.expand(enc)
            phk = h64(pkey)
            c["states_expanded"] += 1
            g = state.graph
            if g is not None:
                g["A"] = len(kids)
                g["rows"].append(_graph_id(g, phk))
            distinct = set()
            for _a, enc2, key2, win, loss in kids:
                c["successors_total"] += 1
                hk = h64(key2)
                if hk != phk:
                    distinct.add(hk)
                if g is not None:
                    cid = _graph_id(g, hk)
                    g["next"].append(cid)
                    if win:
                        g["win"].append(cid)
                    if loss:
                        g["loss"].append(cid)
                if hk in state.visited:
                    continue
                state.visited.add(hk)
                c["states_seen"] += 1
                c["depth_max"] = max(c["depth_max"], depth + 1)
                if c["solution_length"] is None and win:
                    c["solution_length"] = depth + 1
                if (win and terminal_on_win) or loss:
                    continue
                state.tail.append((enc2, depth + 1))
                if len(state.tail) >= spill_over:            # spill the newest entries to disk
                    state.spill_seq += 1
                    name = f"spill_{state.spill_seq:06d}.json.gz"
                    with gzip.open(os.path.join(work_dir, name), "wt", encoding="utf-8") as f:
                        json.dump(state.tail, f)
                    state.spills.append(name)
                    state.tail = []
                    c["spill_files_max"] = max(c["spill_files_max"], len(state.spills))
            state.extra["successors_distinct"] += len(distinct)
            if g is not None and len(g["hashes"]) > eh_limit:
                state.graph, state.graph_status = None, f"more than {eh_limit} states"
        if pause:
            time.sleep(pause)
        spend()
        rss = rss_bytes()
        if c["states_expanded"] >= node_cap:
            cap_hit = "node"
        elif state.seconds_spent >= time_cap:
            cap_hit = "time"
        elif rss is not None and rss >= mem_cap:
            cap_hit = "memory"
        if cap_hit:
            break
        if time.time() >= deadline:
            c["frontier_left"] = state.frontier_size(spill_over)
            return "stopped", None, state
        if time.time() - last_ck_t >= every_s or c["states_expanded"] - last_ck_n >= every_n:
            c["frontier_left"] = state.frontier_size(spill_over)
            on_checkpoint(state)
            last_ck_t, last_ck_n = time.time(), c["states_expanded"]
    spend()
    c["frontier_left"] = state.frontier_size(spill_over)
    sessions = state.sessions + [session_entry(nonce, started)]
    row = dict(schema=schema, campaign=unit["campaign"], unit_id=unit["unit_id"], chunk_id=unit["chunk_id"],
               suite=unit["suite"], game=unit["game"], level=unit["level"],
               complete=cap_hit is None, capped=cap_hit is not None, cap_hit=cap_hit, counts=dict(c),
               caps=dict(node_cap=node_cap, time_cap_seconds=time_cap, memory_cap_bytes=mem_cap,
                         spill_frontier_over=spill_over),
               seconds_spent=round(state.seconds_spent, 3), sessions=sessions, written_at=now_iso())
    if schema == SEARCH_SCHEMA_V2:
        row["measures"] = measures(state, cap_hit, p)
    return ("capped" if cap_hit else "complete"), row, state


def measures(state, cap_hit, p):
    """Branching and the effective-horizon bound for a horizon.search.v2 row."""
    c = state.counts
    b = state.extra["successors_distinct"] / c["states_expanded"] if c["states_expanded"] else None
    out = dict(branching=b, eh=None, eh_k=None, eh_status=None, eh_horizon=int(p.get("eh_horizon", 0)) or None)
    if cap_hit:
        out["eh_status"] = f"not computed: capped by {cap_hit}"
    elif state.graph is None:
        out["eh_status"] = f"not computed: {state.graph_status or 'not recorded'}"
    else:
        import numpy as np  # noqa: PLC0415
        from eh import effective_horizon  # noqa: PLC0415
        g = state.graph
        n = len(g["hashes"])
        A = g["A"] or 1
        win = np.zeros(n, bool)
        win[np.frombuffer(g["win"].tobytes(), dtype=np.int32)] = True
        loss = np.zeros(n, bool)
        loss[np.frombuffer(g["loss"].tobytes(), dtype=np.int32)] = True
        rows = np.frombuffer(g["rows"].tobytes(), dtype=np.int32)
        if not len(rows):
            out["eh_status"] = "not computed: the start is terminal"
            return out
        nxt = np.frombuffer(g["next"].tobytes(), dtype=np.int32).reshape(len(rows), A)
        r = effective_horizon(nxt, rows, win, loss, start=0, T=int(p["eh_horizon"]), A=A)
        out.update(eh=r["eh"], eh_k=r["k"], eh_status=r["status"])
    return out


# ---------------------------------------------------------------- agent
def run_agent(unit, p, nonce, started):
    """The dry run's dummy agent: it sleeps for params.sleep_seconds and records a row.  Real agents
    plug in here (Phase 3); each gets params.unit_seconds_cap as its own wall-clock cap."""
    t0 = time.time()
    if p.get("agent_impl", "dummy_sleep") != "dummy_sleep":
        raise NotImplementedError(f"agent implementation {p.get('agent_impl')} is not written yet")
    sleep = float(p["sleep_seconds"])
    cap = float(p["unit_seconds_cap"])
    cut = sleep > cap
    time.sleep(min(sleep, cap))
    return dict(schema=AGENT_SCHEMA, campaign=unit["campaign"], unit_id=unit["unit_id"], chunk_id=unit["chunk_id"],
                suite=unit["suite"], game=unit["game"], agent=unit["agent"], seed=unit["seed"],
                budget=p.get("budget"), outcome=dict(level1_completed=False, levels=0),
                agent_stats=dict(slept_seconds=round(time.time() - t0, 3)), cut_by_cap=cut,
                seconds=round(time.time() - t0, 3), sessions=[session_entry(nonce, started)], written_at=now_iso())
