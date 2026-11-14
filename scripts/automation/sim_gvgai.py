"""
sim_gvgai.py -- the GVGAI simulator of the search kind gvgaisearch (docs/DESIGN.md, Sections 5 and 6; the
engine decision of docs/design/ENGINE.md).

The engine is GVGAI itself: the Java source vendored under third_party/gvgai/src at commit
e58ff6597319155218759cc178931e05b81b524c, compiled here with javac from a pinned Temurin JDK, and called in-process
through JPype.  Nothing in this file or in the bridge (gvgai_java/core/game/HorizonBridge.java) implements a rule
of a game: every transition is GVGAI's StateObservation.advance on a copy, the forward model GVGAI gives its own
planning agents.

    ensure_jdk      the JDK: Temurin 21.0.13+9, from JAVA_HOME only if its release file names that build, else
                    downloaded into a cache folder and checked by its sha256 (docs/design/engine_evidence.json).
    build           compiles the vendored GVGAI source and the bridge into a folder named by the sha256 of every
                    source file, so a changed file can never run against old classes.
    start_jvm       starts one JVM per process (JPype cannot restart one).
    GVGAISim        the search interface of jobs.run_search: a frontier entry is the action sequence from the level
                    start, as a string of action indices; consecutive entries of a breadth-first layer share
                    prefixes, so the bridge keeps a stack of copies and replays only from the nearest shared state.
    level_paths, with_tick
                    the files of a (game, level) and whether the game tick enters the state key (docs/PREREG.md,
                    Section 6: a Timeout termination, or a sprite with a cooldown, limit or total parameter).

The key of a state is the bridge's canonical serialization (HorizonBridge.key); jobs.h64 hashes it to 64 bits.
Win and loss are GVGAI's: status 1 a win, 2 a loss by a termination, 3 the end GVGAI's own tick limit forces
(CompetitionParameters.MAX_TIMESTEPS = 2000, a compile-time constant).  The search treats 2 and 3 as terminal and
counts 3 apart (states_tick_limit), since the registered search does not include GVGAI's tick limit and that
limit cannot be lifted without changing GVGAI's source.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
GV = os.path.join(REPO, "third_party", "gvgai")
GV_SRC = os.path.join(GV, "src")
BRIDGE_SRC = os.path.join(HERE, "gvgai_java")
GAMES = os.path.join(GV, "examples", "gridphysics")
GVGAI_COMMIT = "e58ff6597319155218759cc178931e05b81b524c"

TEMURIN = {
    "linux": dict(name="OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz",
                  url="https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/"
                      "OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz",
                  sha256="d7f5d5cf865a2902b70ff549b97586a7d3f234e016f041ab447ea740c7d66d1c"),
    "windows": dict(name="OpenJDK21U-jdk_x64_windows_hotspot_21.0.13_9.zip",
                    url="https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/"
                        "OpenJDK21U-jdk_x64_windows_hotspot_21.0.13_9.zip",
                    sha256="a4dbaa05fca4bd89d84584e58c459bd732efebb1722af80ab13c6516832004f9"),
}
JDK_DIR_NAME = "jdk-21.0.13+9"
JDK_RELEASE = ('IMPLEMENTOR="Eclipse Adoptium"', 'IMPLEMENTOR_VERSION="Temurin-21.0.13+9"')
JVM_OPTIONS = ["-Xss16m", "-XX:+UseSerialGC", "-Djava.awt.headless=true"]

STATUS_RUNNING, STATUS_WIN, STATUS_LOSS, STATUS_TICK_LIMIT = 0, 1, 2, 3
TIMED_SPRITE_PARAMS = ("cooldown", "limit", "total")
# the key forms of HorizonBridge: "extended" is the registered state of docs/PREREG.md, Section 6 (decided 14 November
# 2026) and the default; "v0" is the key of PREREG v0 that it replaced, kept only to repeat the check of
# scripts/engine_semantics.py
KEY_FORMS = {"v0": 0, "extended": 1}
DEFAULT_KEY_FORM = "extended"


# ---------------------------------------------------------------- the JDK and the build
def _exe(name):
    return name + (".exe" if os.name == "nt" else "")


def _has_javac(home):
    return bool(home) and os.path.isfile(os.path.join(home, "bin", _exe("javac")))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def is_pinned_jdk(home):
    """True if home holds javac and its release file names the pinned Temurin build (JDK_RELEASE)."""
    if not _has_javac(home):
        return False
    try:
        with open(os.path.join(home, "release"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return False
    return all(line in text for line in JDK_RELEASE)


def ensure_jdk(cache_dir):
    """The JDK home: JAVA_HOME if it is the pinned Temurin, else the pinned Temurin, downloaded into cache_dir once
    and checked by its sha256.  A JDK of another build, such as one an image provides, is never used."""
    home = os.environ.get("JAVA_HOME")
    if is_pinned_jdk(home):
        return home
    home = os.path.join(cache_dir, JDK_DIR_NAME)
    if is_pinned_jdk(home):
        return home
    os.makedirs(cache_dir, exist_ok=True)
    t = TEMURIN["windows" if os.name == "nt" else "linux"]
    archive = os.path.join(cache_dir, t["name"])
    if not os.path.exists(archive) or sha256_file(archive) != t["sha256"]:
        urllib.request.urlretrieve(t["url"], archive + ".part")
        os.replace(archive + ".part", archive)
    got = sha256_file(archive)
    if got != t["sha256"]:
        raise RuntimeError(f"JDK archive sha256 {got} differs from the pinned {t['sha256']}")
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(cache_dir)
    else:
        with tarfile.open(archive) as z:
            z.extractall(cache_dir, filter="tar") if sys.version_info >= (3, 12) else z.extractall(cache_dir)
    if not is_pinned_jdk(home):
        raise RuntimeError(f"no javac of the pinned build under {home} after unpacking {t['name']}")
    return home


def java_sources():
    out = []
    for root in (GV_SRC, BRIDGE_SRC):
        for d, _, files in os.walk(root):
            out += [os.path.join(d, f) for f in files if f.endswith(".java")]
    return sorted(out)


def source_digest(files):
    h = hashlib.sha256()
    for p in files:
        h.update(os.path.relpath(p, REPO).replace(os.sep, "/").encode())
        h.update(b"\0")
        h.update(sha256_file(p).encode())
    return h.hexdigest()


def build(jdk_home, cache_dir):
    """Compiles GVGAI and the bridge into cache_dir/classes-<digest>; returns that folder."""
    files = java_sources()
    out = os.path.join(cache_dir, "classes-" + source_digest(files)[:16])
    if os.path.exists(os.path.join(out, "BUILD_OK")):
        return out
    tmp = out + ".part"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    argfile = os.path.join(cache_dir, "sources.txt")
    with open(argfile, "w", encoding="utf-8") as f:
        f.write("\n".join('"' + p.replace("\\", "/") + '"' for p in files))
    r = subprocess.run([os.path.join(jdk_home, "bin", _exe("javac")), "-nowarn", "-encoding", "UTF-8",
                        "-d", tmp, "@" + argfile], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"javac failed:\n{r.stdout}\n{r.stderr}")
    with open(os.path.join(tmp, "BUILD_OK"), "w", encoding="utf-8") as f:
        f.write(f"{len(files)} files\n")
    shutil.rmtree(out, ignore_errors=True)
    os.replace(tmp, out)
    return out


def _jvm_lib(jdk_home):
    for rel in (("bin", "server", "jvm.dll"), ("lib", "server", "libjvm.so"), ("lib", "server", "libjvm.dylib")):
        p = os.path.join(jdk_home, *rel)
        if os.path.exists(p):
            return p
    raise RuntimeError(f"no JVM library under {jdk_home}")


_BRIDGE = None


def start_jvm(cache_dir, heap="2g"):
    """Starts the JVM of this process once and returns the bridge class."""
    global _BRIDGE
    if _BRIDGE is not None:
        return _BRIDGE
    import jpype  # noqa: PLC0415 -- only on machines that run the GVGAI kinds
    jdk = ensure_jdk(cache_dir)
    classes = build(jdk, cache_dir)
    if not jpype.isJVMStarted():
        jpype.startJVM(_jvm_lib(jdk), f"-Xmx{heap}", *JVM_OPTIONS, classpath=[classes], convertStrings=True)
    bridge = jpype.JClass("core.game.HorizonBridge")
    empty = os.path.join(cache_dir, "no-images")
    os.makedirs(empty, exist_ok=True)
    bridge.noImages(empty.replace("\\", "/") + "/")
    _BRIDGE = bridge
    return bridge


# ---------------------------------------------------------------- a level
def level_paths(game, level, games_dir=None):
    """The description and level file; games_dir replaces the vendored folder (synthetic tests only)."""
    d = GAMES if not games_dir else (games_dir if os.path.isabs(games_dir) else os.path.join(REPO, games_dir))
    return os.path.join(d, f"{game}.txt"), os.path.join(d, f"{game}_lvl{int(level)}.txt")


def with_tick(game, games_dir=None):
    """True where the description has a Timeout termination or a sprite with a cooldown, limit or total
    parameter (docs/PREREG.md, Section 6).  A sprite's parameters include those it inherits."""
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import vgdl_scan  # noqa: PLC0415
    d = vgdl_scan.parse(vgdl_scan.read_text(level_paths(game, 0, games_dir)[0]))
    if any(cls == "Timeout" for cls, _ in d["term"]):
        return True
    return any(k in s["params"] for s in d["sprites"].values() for k in TIMED_SPRITE_PARAMS)


def unpack_expand(buf):
    """The bridge's expand result: (parent key, [(status, key) per action])."""
    mv = memoryview(buf)
    n, plen = struct.unpack_from(">ii", mv, 0)
    off = 8
    pkey = bytes(mv[off:off + plen])
    off += plen
    kids = []
    for _ in range(n):
        st, klen = struct.unpack_from(">ii", mv, off)
        off += 8
        kids.append((st, bytes(mv[off:off + klen])))
        off += klen
    return pkey, kids


ACTION_CHARS = "0123456789"


class GVGAISim:
    """The search interface of jobs.run_search for one GVGAI level."""
    win_is_terminal = True

    def __init__(self, p, unit):
        self.cache = p.get("gvgai_cache") or os.environ.get("HORIZON_GVGAI_CACHE") or \
            os.path.join(os.environ.get("HORIZON_TMP", "/tmp"), "horizon-gvgai")
        self.bridge = start_jvm(self.cache, p.get("jvm_heap", "2g"))
        game_file, level_file = level_paths(unit["game"], unit["level"], p.get("games_dir"))
        self.tick = bool(p["with_tick"][unit["game"]]) if "with_tick" in p else with_tick(unit["game"], p.get("games_dir"))
        self.root = self.bridge.load(game_file.replace("\\", "/"), level_file.replace("\\", "/"), 0)
        self.form = KEY_FORMS[p.get("key_form", DEFAULT_KEY_FORM)]
        self.expander = self.bridge.Expander(self.root, self.tick, self.form)
        self.actions = [str(a) for a in self.bridge.actionNames(self.root)]
        if len(self.actions) > len(ACTION_CHARS):
            raise ValueError("more actions than the frontier encoding holds")
        self.tick_limit_states = 0

    def root_enc(self):
        return ""

    def root_info(self):
        st = int(self.bridge.status(self.root))
        return bytes(self.bridge.key(self.root, self.tick, self.form)), st == STATUS_WIN, st in (STATUS_LOSS, STATUS_TICK_LIMIT)

    def expand(self, enc):
        seq = bytes(int(c) for c in enc)
        buf = bytes(self.expander.expand(seq))
        pkey, kids = unpack_expand(buf)
        out = []
        for a, (st, key) in enumerate(kids):
            if st == STATUS_TICK_LIMIT:
                self.tick_limit_states += 1
            out.append((a, enc + ACTION_CHARS[a], key, st == STATUS_WIN, st in (STATUS_LOSS, STATUS_TICK_LIMIT)))
        return pkey, out
