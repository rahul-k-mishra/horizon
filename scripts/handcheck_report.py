"""
handcheck_report.py -- writes docs/truth/HANDCHECK_RESULT.md, the result of the hand check of the truth tables and
the reading of gate G4 (docs/PREREG.md, Section 5, as decided on 28 November 2026; Section 8).  Standard library only;
reads committed files only.

NOT RUN ON THE AUTHOR'S ANSWERS.  Tested only on synthetic files (scripts/test_handcheck_report.py,
logs/test_handcheck_report.log; scripts/test_handcheck.py, part 5).  It refuses (exit 3, nothing written) while any of
the 100 rows has no answer or the answers are not marked finished, while a fresh round's rows have no answer, and on
any rows or answers file of the old form, in which the generator's verdict was shown.

Changed 28 November 2026 to the blind form (PREREG Section 5, "The hand check is blind"): the rows carry no verdict
and the author answers holds, fails or unsure from the reading alone; the comparison with the generator is made here,
after his answers are committed.  Until then the rows carried the verdict, the author answered agree, disagree or
unsure, and "the verdict shown" was the verdict in the rows file.  The rules below are otherwise unchanged: "the
verdict compared with" is the generator's verdict in the truth table pinned for the rows; an answer equal to it
counts as agree, a different holds or fails as disagree.

What it reads:
    rows        docs/truth/handcheck_rows.json, schema horizon.handcheck_rows.v2: the 100 rows with no verdict, and
                "truth_blob", the git blob of docs/truth/gvgai.json at the commit the rows were built from (recorded
                when they were built, not read for them; PREREG Section 5, as decided 28 November 2026).
    answers     docs/truth/handcheck_answers.json, schema horizon.handcheck_answers.v2 (scripts/handcheck_app.py):
                holds, fails or unsure per row.
    resolutions docs/truth/handcheck_resolutions.json, schema horizon.handcheck_resolutions.v1: per row id, an entry
                {"resolved": true or false, "source": [{"file", "line"}], "generator_commit", "verdict_after",
                "note"}.  verdict_after is the verdict the GVGAI source determines for the unit, which the generator
                gives after the fix; resolved false means the source does not determine it.  "fresh_truth_blob":
                {round: blob}, the truth table each fresh round is compared with: the git blob of
                docs/truth/gvgai.json after the fixes that precede the round, entered when the round is compared.
                It is required for every round, since a fresh round's rows are built blind and may be built before
                those fixes, and a later fix must not change what an earlier round was compared with.
    truth       docs/truth/gvgai.json at the rows' truth_blob (by git) and now (after the fixes).
    fresh       per round r: docs/truth/handcheck_fresh_<r>.json (scripts/draw_handcheck_fresh.py, the games and
                levels), docs/truth/handcheck_fresh_rows_<r>.json (rows of the same blind form as the 100) and
                docs/truth/handcheck_fresh_answers_<r>.json (answers of the same form).  A fresh row's resolution is
                kept in the same resolutions file under "fresh<r>:<row id>".

The rules applied (PREREG Section 5, decided 28 November 2026):
    a row needs a resolution if it is marked disagree or unsure, or if it is marked agree and the generator's verdict
    for it now differs from the verdict it was compared with (a fix that flips an agreed row is itself a
    disagreement).  A resolution is complete when resolved is false, or when it gives a source line and a
    verdict_after that the generator now gives, with the generator commit wherever verdict_after differs from the
    verdict compared with.  A generator error is a row whose verdict_after differs from the verdict compared with.
    An unsure row resolved from the source counts as answered and stays in the denominator.  The error rate is
    errors over the 100 rows answered.  The rerun's diff is every (unit, predicate) of the 125 confirmatory units
    whose verdict differs before and after.  G4 fails by condition (i), VOID at once and with no repair, if any row
    of the hand check or of a fresh round cannot be resolved from the GVGAI source.  A fresh round shows a
    disagreement only if one of its rows is a generator error after resolution; a disagree mark the source resolves
    in the generator's favour is not one.  Round 1 is required whether or not the 100 rows required a fix.  If it
    shows a disagreement, that is the first failure of G4 by condition (ii): the generator is fixed and rerun and G4
    is read again on round 2; a disagreement in round 2 is the second failure, VOID.  Otherwise G4 passes.
    Anything missing or inconsistent (a resolution, a source line, a commit, a fresh round, a pinned truth table, a
    verdict the fixed generator does not give) stops the reading with no verdict (exit 2).

Exit: 0 G4: PASS; 1 G4: FAIL (the condition named); 2 no verdict, what is missing listed; 3 refused.
Run (working directory D:\\Research\\horizon\\repo), once every answer is in and resolved:
    D:\\Research\\horizon\\.venv\\Scripts\\python.exe scripts\\handcheck_report.py > logs\\handcheck_report.log
Options other than --out are for the tests.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRUTH = os.path.join(REPO, "docs", "truth")
ROWS = os.path.join(TRUTH, "handcheck_rows.json")
ANSWERS = os.path.join(TRUTH, "handcheck_answers.json")
RESOLUTIONS = os.path.join(TRUTH, "handcheck_resolutions.json")
GVGAI = os.path.join(TRUTH, "gvgai.json")
OUT = os.path.join(TRUTH, "HANDCHECK_RESULT.md")
PRED = ("A1", "A2", "A3", "A4", "A5")
ROWS_SCHEMA = "horizon.handcheck_rows.v2"
ANSWERS_SCHEMA = "horizon.handcheck_answers.v2"
ANSWERS_OLD = "horizon.handcheck_answers.v1"
VERDICTS = ("holds", "fails")
GIVEN = VERDICTS + ("unsure",)              # what the author answers
CHOICES = ("agree", "disagree", "unsure")   # his answer compared with the generator, made here
ROUNDS = (1, 2)
READ_ERRORS = (OSError, subprocess.CalledProcessError, ValueError, KeyError)


def rel(path):
    try:
        return os.path.relpath(path, REPO).replace("\\", "/")
    except ValueError:
        return path


def sha256(path):
    """Of the file with Windows line endings read as Unix ones, so that a checkout with either gives the same."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def answered(rows, answers):
    return sum(1 for r in rows if answers.get(r["id"], {}).get("answer") in GIVEN)


def blind_refusal(data, what):
    """Why a rows file may not be read: not the blind form, or a verdict in it; None if it may."""
    if data.get("schema") != ROWS_SCHEMA:
        return f"{what} is {data.get('schema')}, not {ROWS_SCHEMA} (the old form showed the generator's verdict)"
    if any(k in r for r in data.get("rows", []) for k in ("verdict", "wrong_if", "clauses")):
        return f"{what} carries the generator's verdict or its reading"
    return None


def load_blob(name, blob_dir):
    """The games of docs/truth/gvgai.json as it was in git blob name; with blob_dir (tests), of <blob_dir>/<name>.json."""
    if blob_dir is not None:
        return read_json(os.path.join(blob_dir, f"{name}.json"))["games"]
    text = subprocess.run(["git", "cat-file", "-p", name], cwd=REPO, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout
    return json.loads(text)["games"]


def marked(rows, answers, shown):
    """The rows with the verdict each is compared with, and each answer as agree, disagree or unsure."""
    out_rows, marks = [], {}
    for r in rows:
        v = shown[(r["game"], r["level"], r["predicate"])]
        out_rows.append(dict(r, verdict=v))
        e = answers.get(r["id"], {})
        a = e.get("answer")
        m = "unsure" if a == "unsure" else (("agree" if a == v else "disagree") if a in VERDICTS else None)
        marks[r["id"]] = {"answer": m, "given": a, "note": e.get("note", "")}
    return out_rows, marks


def tally(rows, answers):
    c = {k: 0 for k in CHOICES + ("no answer",)}
    for r in rows:
        a = answers.get(r["id"], {}).get("answer")
        c[a if a in CHOICES else "no answer"] += 1
    return c


def table(title, groups, rows, answers):
    out = [f"| {title} | rows | agree | disagree | unsure | no answer |", "|---|---|---|---|---|---|"]
    for g in groups:
        sub = [r for r in rows if g in (r["predicate"], r["game"])]
        c = tally(sub, answers)
        out.append(f"| {g} | {len(sub)} | {c['agree']} | {c['disagree']} | {c['unsure']} | {c['no answer']} |")
    c = tally(rows, answers)
    out.append(f"| all | {len(rows)} | {c['agree']} | {c['disagree']} | {c['unsure']} | {c['no answer']} |")
    return out


def listing(rows, answers, pick):
    out = []
    for r in rows:
        e = answers.get(r["id"], {})
        if not pick(e):
            continue
        note = (e.get("note") or "").strip() or "(no note)"
        out.append(f"- **{r['game']}, level {r['level']}, {r['predicate']}** ({r['name']}): the author's answer "
                   f"**{e.get('given')}**, the generator's verdict **{r['verdict']}**. Note: {note}")
    return out or ["None."]


def verdicts(truth_games, units):
    """{(game, level, predicate): verdict} over the given (game, level) units; KeyError if one is missing."""
    return {(g, lv, p): truth_games[g]["levels"][str(lv)][p]["verdict"] for g, lv in units for p in PRED}


def judge(rows, answers, resolutions, now, missing, label, check_now=True):
    """Applies the rules to one set of rows.  Returns a list of per-row records; appends gaps to missing.
    check_now False (an earlier fresh round, answered before a later fix): judged on the verdicts it was compared
    with, with no flip and no comparison with the generator now."""
    out = []
    if not check_now:
        now = {(r["game"], r["level"], r["predicate"]): r["verdict"] for r in rows}
    for r in rows:
        rid, shown = r["id"], r["verdict"]
        a = answers.get(rid, {}).get("answer")
        after = now.get((r["game"], r["level"], r["predicate"]))
        if after is None or shown is None:
            missing.append(f"{label} {rid}: no verdict in the truth table")
            continue
        flipped = after != shown
        need = a in ("disagree", "unsure") or (a == "agree" and flipped)
        rec = dict(id=rid, answer=a, shown=shown, now=after, flipped=flipped, need=need, unresolved=False,
                   error=False, res=None)
        if need:
            res = resolutions.get(rid)
            if res is None:
                why = "marked " + a if a != "agree" else "marked agree, and a fix flipped it"
                missing.append(f"{label} {rid}: {why}; no resolution")
            elif res.get("resolved") is False:
                rec["unresolved"], rec["res"] = True, res
            elif res.get("resolved") is not True:
                missing.append(f"{label} {rid}: resolution without resolved true or false")
            else:
                rec["res"] = res
                src = res.get("source") or []
                va = res.get("verdict_after")
                if not src or not all(s.get("file") and s.get("line") for s in src):
                    missing.append(f"{label} {rid}: resolved without a GVGAI source file and line")
                if va not in VERDICTS:
                    missing.append(f"{label} {rid}: verdict_after {va!r}, not holds or fails")
                else:
                    if check_now and va != after:
                        missing.append(f"{label} {rid}: the source gives {va}, the generator now gives {after}")
                    if va != shown:
                        rec["error"] = True
                        if not res.get("generator_commit"):
                            missing.append(f"{label} {rid}: a generator error without the commit of its fix")
        out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--rows", default=ROWS, help="tests only")
    ap.add_argument("--answers", default=ANSWERS, help="tests only")
    ap.add_argument("--resolutions", default=RESOLUTIONS, help="tests only")
    ap.add_argument("--blob-dir", default=None, help="tests only: truth tables by blob name, from this folder")
    ap.add_argument("--truth-after", default=GVGAI, help="tests only")
    ap.add_argument("--fresh-dir", default=TRUTH, help="tests only: the folder of the fresh rounds' files")
    ap.add_argument("--games", default=None, help="tests only: the confirmatory games, game,game,...")
    a = ap.parse_args(argv)

    # refusal: the blind form, and every answer in
    if not os.path.exists(a.answers):
        print(f"refused: no answers file at {rel(a.answers)}; nothing written")
        return 3
    rows_data, ans_data = read_json(a.rows), read_json(a.answers)
    why = blind_refusal(rows_data, rel(a.rows))
    if why:
        print(f"refused: {why}; answers given with the verdict visible were discarded on 28 November 2026 "
              "(PREREG Section 5); nothing written")
        return 3
    if ans_data.get("schema") != ANSWERS_SCHEMA:
        print(f"refused: {rel(a.answers)} is {ans_data.get('schema')}, not {ANSWERS_SCHEMA}"
              + ("; its answers were given with the verdict visible and were discarded on 28 November 2026"
                 if ans_data.get("schema") == ANSWERS_OLD else "") + "; nothing written")
        return 3
    rows, raw = rows_data["rows"], ans_data["answers"]
    done = answered(rows, raw)
    if done < len(rows) or not ans_data.get("finished_at"):
        print(f"refused: the answers are incomplete ({done} of {len(rows)} rows answered, "
              f"finished {ans_data.get('finished_at')}); nothing written")
        return 3
    fresh = {}
    for rnd in ROUNDS:
        rp = os.path.join(a.fresh_dir, f"handcheck_fresh_rows_{rnd}.json")
        if os.path.exists(rp):
            ap_ = os.path.join(a.fresh_dir, f"handcheck_fresh_answers_{rnd}.json")
            draw_p = os.path.join(a.fresh_dir, f"handcheck_fresh_{rnd}.json")
            fdata = read_json(rp)
            why = blind_refusal(fdata, f"fresh round {rnd}'s rows")
            if why:
                print(f"refused: {why}; nothing written")
                return 3
            frows = fdata["rows"]
            fans_data = read_json(ap_) if os.path.exists(ap_) else {"schema": ANSWERS_SCHEMA, "answers": {}}
            fans = fans_data["answers"]
            if answered(frows, fans) < len(frows) or fans_data.get("schema") != ANSWERS_SCHEMA:
                print(f"refused: fresh round {rnd} has rows without an answer, or answers not of {ANSWERS_SCHEMA}; "
                      "nothing written")
                return 3
            fresh[rnd] = dict(rows=frows, answers=fans, draw=read_json(draw_p) if os.path.exists(draw_p) else None)

    missing = []
    rows_sha = sha256(a.rows)
    if ans_data.get("rows_sha256") != rows_sha:
        missing.append("the answers were kept against another version of the rows file")
    resolutions_data = read_json(a.resolutions) if os.path.exists(a.resolutions) else {"resolutions": {}}
    resolutions = resolutions_data.get("resolutions", {})
    after_truth = read_json(a.truth_after)["games"]
    if not rows_data.get("truth_blob"):
        print("stopped, no verdict: the rows file names no truth_blob, the truth table its rows are compared with")
        return 2
    try:
        before_truth = load_blob(rows_data["truth_blob"], a.blob_dir)
    except READ_ERRORS as e:
        print(f"stopped, no verdict: the truth table of blob {rows_data['truth_blob']} cannot be read: {e}")
        return 2
    if a.games is not None:
        conf = [g for g in a.games.split(",") if g]
    else:
        sys.path.insert(0, HERE)
        import suite  # noqa: PLC0415
        conf = suite.confirmatory()
    units = [(g, lv) for g in conf for lv in range(5)]
    try:
        before_v, after_v = verdicts(before_truth, units), verdicts(after_truth, units)
    except KeyError as e:
        print(f"stopped, no verdict: a confirmatory unit is missing from the truth table: {e}")
        return 2
    diff = sorted(k for k in after_v if after_v[k] != before_v[k])
    row_units = {(r["game"], r["level"]) for r in rows}
    for rnd in fresh:
        row_units |= {(r["game"], r["level"]) for r in fresh[rnd]["rows"]}
    now = {}
    for g, lv in row_units:
        for p in PRED:
            try:
                now[(g, lv, p)] = after_truth[g]["levels"][str(lv)][p]["verdict"]
            except KeyError:
                pass

    def shown_by(truth, rws, label):
        out = {}
        for r in rws:
            k = (r["game"], r["level"], r["predicate"])
            try:
                out[k] = truth[r["game"]]["levels"][str(r["level"])][r["predicate"]]["verdict"]
            except KeyError:
                missing.append(f"{label} {r['id']}: not in the truth table it is compared with")
                out[k] = None
        return out

    rows, answers = marked(rows, raw, shown_by(before_truth, rows, "row"))
    c = tally(rows, answers)
    main_recs = judge(rows, answers, resolutions, now, missing, "row")
    fresh_recs = {}
    pinned = resolutions_data.get("fresh_truth_blob", {})
    latest = max(fresh) if fresh else None
    for rnd, f in fresh.items():
        if f["draw"] is None:
            missing.append(f"fresh round {rnd}: no draw file handcheck_fresh_{rnd}.json")
        else:
            want = {f"{d['game']}/{p}/{lv}" for d in f["draw"]["games"] for lv in d["levels"] for p in PRED}
            if {r["id"] for r in f["rows"]} != want:
                missing.append(f"fresh round {rnd}: its rows are not the drawn games, levels and predicates")
        if str(rnd) in pinned:
            try:
                ftruth = load_blob(pinned[str(rnd)], a.blob_dir)
            except READ_ERRORS as e:
                missing.append(f"fresh round {rnd}: its pinned truth table {pinned[str(rnd)]} cannot be read: {e}")
                fresh_recs[rnd] = []
                continue
        else:
            missing.append(f"fresh round {rnd}: no fresh_truth_blob names the truth table it is compared with")
            fresh_recs[rnd] = []
            continue
        f["rows"], f["answers"] = marked(f["rows"], f["answers"], shown_by(ftruth, f["rows"], f"fresh round {rnd}"))
        fres = {k[len(f'fresh{rnd}:'):]: v for k, v in resolutions.items() if k.startswith(f"fresh{rnd}:")}
        fresh_recs[rnd] = judge(f["rows"], f["answers"], fres, now, missing, f"fresh round {rnd}",
                                check_now=rnd == latest)
    if 1 not in fresh:
        missing.append("fresh round 1 has not been checked (handcheck_fresh_rows_1.json and its answers)")

    unresolved = [f"row {r['id']}" for r in main_recs if r["unresolved"]] + \
                 [f"fresh round {k} {r['id']}" for k, v in fresh_recs.items() for r in v if r["unresolved"]]
    fresh_bad = {k: [r["id"] for r in v if r["error"]] for k, v in fresh_recs.items()}
    if 2 in fresh and not fresh_bad.get(1):
        missing.append("fresh round 2 exists, but round 1 showed no disagreement")

    errors = [r for r in main_recs if r["error"]]
    unsure = [r for r in main_recs if r["answer"] == "unsure"]
    flips = [r for r in main_recs if r["flipped"]]
    flipped_agree = [r for r in flips if r["answer"] == "agree"]
    commits = {}
    for r in main_recs + [x for v in fresh_recs.values() for x in v]:
        if r["error"] and r["res"]:
            commits.setdefault(r["res"].get("generator_commit"), []).append(r["id"])

    # the verdict
    if unresolved:
        verdict, cond, code = "FAIL", ("condition (i): a disagreement the GVGAI source does not resolve ("
                                       + ", ".join(unresolved) + "); VOID at once, with no repair"), 1
    elif missing:
        print("stopped, no verdict; missing or inconsistent:")
        for m in missing:
            print(f"  {m}")
        return 2
    elif fresh_bad.get(1) and 2 not in fresh:
        verdict, cond, code = "FAIL", ("condition (ii), first failure: fresh round 1 shows a disagreement ("
                                       + ", ".join(fresh_bad[1]) + "); the generator is fixed and rerun, and G4 is "
                                       "read again on fresh round 2 (seed 20261129)"), 1
    elif fresh_bad.get(1) and fresh_bad.get(2):
        verdict, cond, code = "FAIL", ("condition (ii), second failure: fresh round 2 shows a disagreement ("
                                       + ", ".join(fresh_bad[2]) + "); VOID"), 1
    else:
        verdict, cond, code = "PASS", ("no disagreement left unresolved, and fresh round "
                                       + ("2 agrees, after the first failure on round 1" if fresh_bad.get(1)
                                          else "1 agrees") + " on every predicate"), 0

    n = len(rows)
    rate = f"{len(errors)} of {n} rows answered ({100 * len(errors) / n:.1f}%)"
    games = list(dict.fromkeys(r["game"] for r in rows))
    today = datetime.date.today().isoformat()
    out = ["# Result of the hand check of the truth tables", "",
           f"Written {today} by scripts/handcheck_report.py (console in logs/handcheck_report.log) from "
           f"{rel(a.answers)}, {rel(a.rows)}, {rel(a.resolutions)} and the fresh rounds. The rows are the predicates "
           "of docs/PREREG.md draft v0, Section 5, on the games and levels drawn by scripts/draw_handcheck.py "
           "(logs/draw_handcheck.log). The hand check was blind: the author answered each row from the reading "
           "alone, and his answers were committed before this comparison with the verdicts of "
           f"scripts/truth_vgdl.py in docs/truth/gvgai.json at blob {rows_data['truth_blob']}.", "",
           f"- Answers started {ans_data.get('started_at')}, last changed {ans_data.get('updated_at')}, "
           f"finished {ans_data.get('finished_at')}.",
           f"- Rows file sha256 {rows_sha}.", "",
           f"## G4: {verdict}", "", f"{cond}.", "",
           "## Disagreements, unsure rows and the error rate", "",
           f"- Answers that differ from the generator's verdict: {sum(r['answer'] == 'disagree' for r in main_recs)}. "
           f"Marked unsure: {len(unsure)}, of which the source found the generator right on "
           f"{sum(1 for r in unsure if not r['error'] and r['res'] and not r['unresolved'])}.",
           f"- Generator errors found (the verdict the source determines differs from the generator's verdict before "
           f"the fixes): {rate}. Every unsure row resolved from the source is counted as answered.",
           f"- Rows whose verdict a fix flipped: {len(flips)}, of them agreeing with the author before the fix: "
           f"{len(flipped_agree)}"
           + (" (" + ", ".join(r["id"] for r in flipped_agree) + ", each resolved from the source)" if flipped_agree else "")
           + ".", ""]
    out += ["## Resolutions", ""]
    res_lines = []
    for r in main_recs + [dict(x, id=f"fresh{k}:{x['id']}") for k, v in fresh_recs.items() for x in v]:
        if not r["need"]:
            continue
        res = r["res"] or {}
        src = "; ".join(f"{s.get('file')}:{s.get('line')}" for s in res.get("source") or []) or "none"
        state = "not resolved by the source" if r["unresolved"] else (
            "generator wrong" if r["error"] else "generator right")
        res_lines.append(f"- **{r['id']}** marked {r['answer']}{', flipped by a fix' if r['flipped'] else ''}: "
                         f"generator {r['shown']}, source {res.get('verdict_after')}, now {r['now']}; {state}; source "
                         f"{src}; generator commit {res.get('generator_commit') or 'none'}. {res.get('note') or ''}")
    out += res_lines or ["None needed."]
    out += ["", "## Every generator fix", ""]
    out += [f"- {k}: {', '.join(v)}" for k, v in sorted(commits.items(), key=lambda x: str(x[0]))] or ["None."]
    out += ["", f"## The rerun's diff over the {len(units)} confirmatory units", ""]
    out += [f"- {g}, level {lv}, {p}: {before_v[(g, lv, p)]} before, {after_v[(g, lv, p)]} after"
            for g, lv, p in diff] or ["No verdict changed."]
    out += ["", "## Fresh rounds", ""]
    for rnd in sorted(fresh):
        dr = fresh[rnd]["draw"] or {}
        out.append(f"- Round {rnd} (seed {dr.get('seed')}): " + ", ".join(
            f"{d['game']} (levels {', '.join(map(str, d['levels']))})" for d in dr.get("games", []))
            + f"; {len(fresh[rnd]['rows'])} rows; generator errors {len(fresh_bad.get(rnd, []))}"
            + (": " + ", ".join(fresh_bad[rnd]) if fresh_bad.get(rnd) else "") + ".")
    out += ["", "## Games and levels covered", "", "| game | levels | rows | answered |", "|---|---|---|---|"]
    for g in games:
        sub = [r for r in rows if r["game"] == g]
        lv = ", ".join(str(x) for x in sorted({r["level"] for r in sub}))
        cc = tally(sub, answers)
        out.append(f"| {g} | {lv} | {len(sub)} | {len(sub) - cc['no answer']} |")
    out += ["", "## Per predicate", ""] + table("predicate", PRED, rows, answers)
    out += ["", "## Per game", ""] + table("game", games, rows, answers)
    out += ["", "## Every answer that differs from the generator", ""] + listing(
        rows, answers, lambda e: e.get("answer") == "disagree")
    out += ["", "## Every row marked unsure", ""] + listing(rows, answers, lambda e: e.get("answer") == "unsure")
    out.append("")
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))

    print(f"rows {n} ({rel(a.rows)}, sha256 {rows_sha}); answers finished {ans_data.get('finished_at')}")
    print(f"compared with docs/truth/gvgai.json at blob {rows_data['truth_blob']}")
    print(f"all: agree {c['agree']}, disagree {c['disagree']}, unsure {c['unsure']}, no answer {c['no answer']}")
    print(f"generator errors: {rate}; flipped by a fix {len(flips)}, of them agreeing before {len(flipped_agree)}")
    print(f"rerun diff over {len(units)} confirmatory units: {len(diff)} verdict(s) changed")
    for rnd in sorted(fresh):
        print(f"fresh round {rnd}: {len(fresh[rnd]['rows'])} rows, generator errors {len(fresh_bad.get(rnd, []))}")
    print(f"fixes: {len(commits)} commit(s)")
    print(f"written {rel(a.out)}")
    print(f"G4: {verdict} -- {cond}")
    return code


if __name__ == "__main__":
    sys.exit(main())
