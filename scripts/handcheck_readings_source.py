"""
handcheck_readings_source.py -- the readings shown in the blind hand check (docs/PREREG.md, Section 5, decided
28 November 2026, option B): a transcription of the vendored GVGAI files, not an explanation.  Standard library only.

For every row of the hand check (the 10 games and levels of the draw of 25 October 2026, logs/draw_handcheck.log)
and of fresh round 1 (docs/truth/handcheck_fresh_1.json), the reading quotes verbatim from third_party/gvgai:
    the game's SpriteSet, InteractionSet, TerminationSet and LevelMapping blocks, each from its header line to its
    last line that is not blank;
    the level file of the row's level, whole;
    the avatar's type: the SpriteSet line of each sprite the level character A places (the LevelMapping line for A,
    or the name avatar where the description has no line for A, GVGAI's default mapping) whose nearest class, on its
    own line or a line it sits under, is an avatar class, with every line it sits under; and the class declaration
    of that avatar class, with each class it extends under src/ontology/avatar, and the loadDefaults method of each
    that has one, where GVGAI sets the class's default parameters;
    the avatar's available actions: the postProcess method of each of those classes that has one, where GVGAI adds
    the actions;
    the effects: for each effect the InteractionSet names, in the order of its first appearance, the Java source of
    that effect under src/ontology/effects, from its class declaration to its last line that is not blank (added 28
    November 2026, so that the reading is self-contained where it was not: the effects were otherwise judged from
    memory);
    the physics class the avatar uses, GridPhysics unless a line of the avatar's sprite sets physicstype to CONT
    (none of the games of the row sets does; VGDLSprite's default is GRID), with its activeMovement and
    passiveMovement methods; and Game.killSprite and every Game.addSprite (added 28 November 2026).  The readings
    stop there: beyond these the author judges from documented GVGAI semantics (PREREG Section 5).
Each quote is the exact text of the named lines of the named file as committed at the commit that last changed
third_party/gvgai (read with git show), carriage returns included.  The reading shown is
the quotes in that order, each under a fixed one-line header naming the file and the lines, with the carriage
returns left out for display.  Nothing is derived from the quotes: no count, no line on what would make anything
true or false, no commentary.  The same reading is given for every predicate of a game and level.

Reads only: logs/draw_handcheck.log (the names and levels of the 10 games), docs/truth/handcheck_fresh_1.json (the
names and levels of the 5 fresh games) and the files under third_party/gvgai.  It reads neither the generator, nor
its truth table, nor the readings written for the hand check of 25 October 2026.
Writes docs/truth/handcheck_readings_source.json, schema horizon.handcheck_readings.v2.
Run (working directory D:\\Research\\horizon\\repo):
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\handcheck_readings_source.py > logs\\handcheck_readings_source.log
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GVGAI_DIR = "third_party/gvgai"
GAMES_DIR = f"{GVGAI_DIR}/examples/gridphysics"
AVATAR_SRC = f"{GVGAI_DIR}/src/ontology/avatar"
EFFECTS_SRC = f"{GVGAI_DIR}/src/ontology/effects"
PHYSICS_SRC = f"{GVGAI_DIR}/src/ontology/physics"
GAME_SRC = f"{GVGAI_DIR}/src/core/game/Game.java"
DRAW_LOG = "logs/draw_handcheck.log"
FRESH_DRAWS = ["docs/truth/handcheck_fresh_1.json"]
OUT = "docs/truth/handcheck_readings_source.json"
SCHEMA = "horizon.handcheck_readings.v2"
PRED = ("A1", "A2", "A3", "A4", "A5")
BLOCKS = ("SpriteSet", "InteractionSet", "TerminationSet", "LevelMapping")


_COMMIT = []


def raw_lines(path):
    """The lines of a file as committed at the vendored commit (git show), each with its own line ending.  Read from
    git rather than the working tree, whose line endings git may convert on checkout."""
    if not _COMMIT:
        _COMMIT.append(vendored_commit())
    data = subprocess.run(["git", "show", f"{_COMMIT[0]}:{path}"], cwd=REPO, capture_output=True, check=True).stdout
    return data.decode("utf-8").splitlines(keepends=True)


def quote(label, path, first, last, lines):
    """Lines first to last (1-based, inclusive), exact, without the final line ending."""
    text = "".join(lines[first - 1:last])
    return {"label": label, "file": path, "first": first, "last": last, "text": text.rstrip("\r\n")}


def header(q):
    where = f"line {q['first']}" if q["first"] == q["last"] else f"lines {q['first']} to {q['last']}"
    return f"{q['label']}, {q['file']}, {where}:"


def render(quotes, notes):
    out = []
    for item in quotes:
        if isinstance(item, str):
            out.append(item)
        else:
            out.append(header(item))
            out.append(item["text"].replace("\r", ""))
        out.append("")
    return "\n".join(out + notes).rstrip("\n")


def block_spans(lines):
    """{block name: (first, last)} of the description's blocks, 1-based."""
    heads = [(n, ln.strip()) for n, ln in enumerate(lines, 1) if ln.strip() in BLOCKS]
    spans = {}
    for i, (n, name) in enumerate(heads):
        end = heads[i + 1][0] - 1 if i + 1 < len(heads) else len(lines)
        while end > n and not lines[end - 1].strip():
            end -= 1
        spans[name] = (n, end)
    return spans


def avatar_quotes(desc, lines, spans):
    """The SpriteSet lines of the sprites A places, with the lines they sit under; the avatar class chain."""
    names = ["avatar"]
    if "LevelMapping" in spans:
        a, b = spans["LevelMapping"]
        for n in range(a + 1, b + 1):
            s = lines[n - 1].split("#", 1)[0]
            if ">" in s and s.split(">", 1)[0].strip() == "A":
                names = s.split(">", 1)[1].split()
                break
    a, b = spans["SpriteSet"]
    stack, chain_of = [], {}
    for n in range(a + 1, b + 1):
        s = lines[n - 1].split("#", 1)[0].rstrip()
        if not s.strip() or ">" not in s:
            continue
        ind = len(s) - len(s.lstrip())
        while stack and stack[-1][0] >= ind:
            stack.pop()
        name = s.split(">", 1)[0].strip()
        chain_of[name] = [m for _, m, _ in stack] + [n]
        stack.append((ind, n, name))
    out, classes = [], []
    for name in names:
        if name not in chain_of:
            continue
        nums, found = chain_of[name], None
        for n in reversed(nums):
            right = lines[n - 1].split("#", 1)[0].split(">", 1)[1].split()
            cls = next((t for t in right if "=" not in t), None)
            if cls:
                found = cls if cls.endswith("Avatar") else None
                break
        if found is None:
            continue
        for n in nums:
            out.append(quote("Avatar sprite", desc, n, n, lines))
        if found not in classes:
            classes.append(found)
    return out, classes


def java_file(cls):
    for root, _, files in os.walk(os.path.join(REPO, AVATAR_SRC)):
        if f"{cls}.java" in files:
            return os.path.relpath(os.path.join(root, f"{cls}.java"), REPO).replace("\\", "/")
    return None


def class_quotes(cls):
    """The class declaration of cls and of each avatar class it extends, with their loadDefaults and postProcess."""
    out = []
    while cls:
        path = java_file(cls)
        if path is None:
            break
        lines = raw_lines(path)
        decl = next(n for n, ln in enumerate(lines, 1) if re.search(rf"\bclass {cls}\b", ln))
        out.append(quote(f"Avatar class {cls}", path, decl, decl, lines))
        for method, label in (("loadDefaults", "Defaults of"), ("postProcess", "Actions of")):
            pp = next((n for n, ln in enumerate(lines, 1) if re.search(rf"\bvoid {method}\s*\(", ln)), None)
            if pp is None:
                continue
            depth, seen, end = 0, False, pp
            for n in range(pp, len(lines) + 1):
                depth += lines[n - 1].count("{") - lines[n - 1].count("}")
                seen = seen or "{" in lines[n - 1]
                if seen and depth == 0:
                    end = n
                    break
            out.append(quote(f"{label} {cls}", path, pp, end, lines))
        m = re.search(rf"\bclass {cls}\s+extends\s+(\w+)", "".join(lines[decl - 1:decl + 1]))
        cls = m.group(1) if m else None
    return out


def round_units():
    """[(round, game, [levels])]: the 10 games of the draw of 25 October 2026, then each fresh round's games."""
    with open(os.path.join(REPO, DRAW_LOG), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^drawn: (.+)$", text, re.M)
    units = [(0, g, [0, int(k)]) for g, k in re.findall(r"(\w+) \(levels 0 and (\d+)\)", m.group(1))]
    for p in FRESH_DRAWS:
        with open(os.path.join(REPO, p), encoding="utf-8") as f:
            d = json.load(f)
        units += [(d["round"], x["game"], list(x["levels"])) for x in d["games"]]
    return units


def reading_for(game, level):
    desc = f"{GAMES_DIR}/{game}.txt"
    lvl = f"{GAMES_DIR}/{game}_lvl{level}.txt"
    lines = raw_lines(desc)
    spans = block_spans(lines)
    items, notes = [f"Game description: {desc}"], []
    quotes = []
    for b in BLOCKS:
        if b in spans:
            q = quote(b, desc, spans[b][0], spans[b][1], lines)
            quotes.append(q)
            items.append(q)
        else:
            items.append(f"The description has no {b} block.")
    llines = raw_lines(lvl)
    q = quote(f"Level {level} map", lvl, 1, len(llines), llines)
    quotes.append(q)
    items.append(q)
    av, classes = avatar_quotes(desc, lines, spans)
    quotes += av
    items += av
    for cls in classes[:1]:
        cq = class_quotes(cls)
        quotes += cq
        items += cq
    for name in effect_names(lines, spans):
        path = effect_file(name)
        if path is None:
            items.append(f"No source file for the effect {name} under {EFFECTS_SRC}.")
            continue
        elines = raw_lines(path)
        first = next(n for n, ln in enumerate(elines, 1) if re.search(r"\bclass \w+", ln))
        last = len(elines)
        while last > first and not elines[last - 1].strip():
            last -= 1
        q = quote(f"Effect {name}", path, first, last, elines)
        quotes.append(q)
        items.append(q)
    phys = "ContinuousPhysics" if any(re.search(r"\bphysicstype=\S*CONT", q["text"]) for q in av) else "GridPhysics"
    ppath = f"{PHYSICS_SRC}/{phys}.java"
    plines = raw_lines(ppath)
    decl = next(n for n, ln in enumerate(plines, 1) if re.search(rf"\bclass {phys}\b", ln))
    pq = [quote(f"Physics class {phys}", ppath, decl, decl, plines)]
    pq += method_quotes(ppath, plines, "activeMovement", f"Physics {phys}.activeMovement")
    pq += method_quotes(ppath, plines, "passiveMovement", f"Physics {phys}.passiveMovement")
    glines = raw_lines(GAME_SRC)
    pq += method_quotes(GAME_SRC, glines, "killSprite", "Game.killSprite")
    pq += method_quotes(GAME_SRC, glines, "addSprite", "Game.addSprite")
    quotes += pq
    items += pq
    return {"reading": render(items, notes), "quotes": quotes, "lines": {"description": [], "level": []}}


def method_quotes(path, lines, name, label):
    """Every declaration of the method name in the file, each from its declaration line to its closing brace."""
    out = []
    for n, ln in enumerate(lines, 1):
        code = ln.split("//", 1)[0]
        if not re.match(rf"^\s*(public|protected|private)\b[^;=(]*\b{name}\s*\(", code) or code.rstrip().endswith(";"):
            continue
        depth, seen, end = 0, False, n
        for k in range(n, len(lines) + 1):
            depth += lines[k - 1].count("{") - lines[k - 1].count("}")
            seen = seen or "{" in lines[k - 1]
            if seen and depth == 0:
                end = k
                break
        out.append(quote(label, path, n, end, lines))
    return out


def effect_names(lines, spans):
    """The effects the InteractionSet names, in the order of their first appearance."""
    out = []
    if "InteractionSet" not in spans:
        return out
    a, b = spans["InteractionSet"]
    for n in range(a + 1, b + 1):
        s = lines[n - 1].split("#", 1)[0]
        if ">" in s:
            right = s.split(">", 1)[1].split()
            if right and "=" not in right[0] and right[0] not in out:
                out.append(right[0])
    return out


def effect_file(name):
    """The Java file of an effect under src/ontology/effects: the effect's name with its first letter in capitals."""
    target = name[:1].upper() + name[1:] + ".java"
    for root, _, files in os.walk(os.path.join(REPO, EFFECTS_SRC)):
        if target in files:
            return os.path.relpath(os.path.join(root, target), REPO).replace("\\", "/")
    return None


def vendored_commit():
    r = subprocess.run(["git", "log", "-1", "--format=%H", "--", GVGAI_DIR], cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip()


def main():
    units = round_units()
    readings, per_game = {}, {}
    for rnd, game, levels in units:
        for lv in levels:
            r = reading_for(game, lv)
            for p in PRED:
                readings[f"{game}/{p}/{lv}"] = r
            per_game.setdefault((rnd, game), []).append((lv, len(r["quotes"]), len(r["reading"])))
    out = {"schema": SCHEMA, "written_by": "scripts/handcheck_readings_source.py",
           "vendored_commit": vendored_commit(),
           "about": "Transcriptions of the vendored GVGAI files for the blind hand check: verbatim quotes, each with "
                    "its file and lines; nothing derived from them.",
           "readings": readings}
    path = os.path.join(REPO, OUT)
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(path + ".tmp", path)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    print(f"third_party/gvgai as last committed in {out['vendored_commit']}")
    for (rnd, game), v in per_game.items():
        print(f"round {rnd} {game}: " + "; ".join(f"level {lv}: {nq} quotes, {nc} characters shown" for lv, nq, nc in v))
    print(f"readings: {len(readings)} rows, {len(per_game)} games")
    print(f"written {OUT}, sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
