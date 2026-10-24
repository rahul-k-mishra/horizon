# Lessons from study 1

Study 1 is the project at D:\Research\arc3\repo (public at https://github.com/rahul-k-mishra/arc3-frame-only-study). Its registered claim was refuted. It tried to read five mechanics of a game (A1 to A5) from frames and use them to predict where frame-only agents finish level 1.
The census of mechanics failed its own validity test, so the study could not say whether mechanics predict success.
This project, HORIZON, asks that question again, with the mechanics taken from source code and set against the size of the search.
Every statement below names the study-1 file it comes from, as a path relative to D:\Research\arc3\repo.
No number here was computed for this file; each one is quoted from the study-1 file named beside it.
Sections: 1 what study 1 did; 2 its registered result; 3 why its instrument failed; 4 what its automation lacked; 5 what its number pipeline got right; 6 what HORIZON keeps and what it changes.
This file states no result of HORIZON and proposes no fix as a result.

## 1. What study 1 did

- **The claim.** A fixed, cheap, frame-only probe battery, the assumption census, with every parameter frozen on eight ARC-AGI-3 training games, would (i) report the source-code mechanics of unseen games in other suites at a registered accuracy and (ii) predict, before any agent ran, on which unseen games assumption-driven frame-only agents complete level 1. Both halves were required. (docs/PREREG.md v1, Section 1.)
- **The five assumptions.** A1 input coupling, A2 one controlled object, A3 lattice motion, A4 blocking by a fixed obstacle set, A5 place goal. Their truth definitions are written out in docs/PREREG.md v1, Section 7, copied from docs/GROUND_TRUTH_minigrid.md and docs/GROUND_TRUTH_procgen.md.
- **The census.** It was not a separate probe. It was read from the end-of-run report of the planner N (scripts/g_nav.py on scripts/g_agent.py), 20,000 actions per game and seed, by per-seed rules and a seed majority (docs/PREREG.md v1, Sections 5.2 and 5.3; scripts/analyze_common.py, `census_from_report` and `majority`).
- **The agents.** R, the author's hash_state explorer (evidence); N, the author's planner, which uses A1 to A5 by construction (instrument check only); I1, the graph explorer of Rudakov, Shock and Cowley (arXiv:2512.24156), run behind a boundary adapter (evidence) (docs/PREREG.md v1, Section 2; v1.1 D7).
- **The suites.** ARC-AGI-3 (25 public games, development instance, not evidence); suite B, 161 confirmatory MiniGrid and BabyAI environments under two action conditions, raw (turn, forward, pickup, drop, toggle) and macro (north, south, west, east, pickup, toggle); suite C, 14 confirmatory Procgen games, whole-level view (center_off) primary (docs/PREREG.md v1, Sections 3 and 8; v1.1 D1).
- **The tests.** V1 compared each game's seed-majority census with the truth table, per assumption. V2 took the census score S (the number of A1 to A5 that hold) and the conjunctive prediction P (A2, A3, A4 and A5 all hold) and asked whether they predict Y, "the agent completed level 1 in at least half of its 10 seeds", by AUROC with a bootstrap interval, balanced accuracy of P, and a margin over a nuisance baseline B (logistic regression on grid area, action count and colour count) (docs/PREREG.md v1, Section 10; scripts/analyze_v2.py docstring).
- **The runs.** 10 seeds (1000 to 1009), 20,000 actions per game, seed and condition; 9,660 confirmatory rows on suite B and 840 on suite C, 0 errors, 0 cut by the caps (docs/STATE.md, amendments (i) and (j)). Each row is one JSON file, runs/suites/<suite>/<condition>/<mode>/<game>__<seed>.json, holding a one-element list (scripts/run_suite.py docstring; docs/PREREG.md v1, Section 9.3).
- **What one row holds.** The fields used by the analysis are suite, condition, agent, game, seed, level1_completed, level1_actions (the step of the first level end, every step counted, RESET included, null if none), and adapter (grid [h, w], action_list, n_colours). N rows also carry census and the planner report nav. Every R and N row carries level_log, whose first entry gives the actions and the number of distinct hashed states of level 0 and whether it ended "won" (scripts/run_suite.py:131-132; scripts/env_frame.py:174-206; scripts/g_agent.py:356, 523-527, 576, 847-849). I1 rows carry no per-level state count (one I1 row, runs/suites/minigrid/raw/i1/MiniGrid-DoorKey-6x6-v0__1000.json, read for this file).
- **The registration.** prereg-v1 on commit 19f2a9f, OSF https://osf.io/2znhw; prereg-v1.1 on commit 8b2b2b9, OSF https://osf.io/zu5vq; prereg-v1.2 on commit 66e5606 (docs/STATE.md, amendments (d), (h) and (m)).

## 2. Its registered result

- **Outcome REFUTE, by the clause "V1 fails on any suite".** Pre-committed consequence: repository record only, at most an arXiv note (docs/STATE.md, amendment (k)).
- **V1.** On suite B macro, A1 and A2 PASS and A3, A4, A5 FAIL. On suite B raw, A1 PASS and A2 to A5 FAIL. On suite C (all 14), A1 PASS and A2 to A5 FAIL; on the 9 in-range games A1 is "neither" (agreement 0.8889). Cohen's kappa for A5 is negative under macro (-0.4125), raw (-0.3374) and on suite C (-0.7843) (docs/tables/v1.md; docs/STATE.md, amendment (k)).
- **V2.** No agent passed on any suite or subset. On suite B macro primary, R was VOID (101 of 112 games completed, share above 0.90), I1 "neither" (AUROC 0.7187), N "neither" (0.6613). On suite C, all 14 games, I1 FAIL (0.6458) and R "neither" (0.7222) (docs/tables/v2.md).
- **The nuisance baseline B** had a higher AUROC than the census on every primary suite-B line, for example 0.8515 against 0.6985 for R under macro and 0.8413 against 0.7187 for I1 (docs/tables/v2.md; docs/STATE.md, amendment (k)).
- **Defects and deviations recorded, none changing the outcome.** The frozen code computed the ARC V2 lines over all 25 games instead of the 17 held-out ones and printed a verdict with no registered meaning (docs/STATE.md, amendment (k)). Eight deviations in all, among them the ARC development truth table and ARC V1 never done, I1 never run on ARC-AGI-3, and the registered row-field check V3 never computed (docs/STATE.md, amendments (n) and (o); docs/manuscript_jagi/manuscript_jagi.md, Section 3.10).
- **Where it went.** Preprint on Zenodo, DOI 10.5281/zenodo.23375065 (docs/STATE.md, amendment (r)); declined by the Journal of Trial and Error without review (amendment (u)); supplement on Zenodo, DOI 10.5281/zenodo.23614519 (amendment (w)); submitted to the Journal of Artificial General Intelligence on 24 October 2026, manuscript 256, from the tag jagi-submission-v1 on commit 29f1238 (amendment (x)).

## 3. Why its instrument failed

### 3.1 The probes and the truth predicates were different constructs

- The exploratory diagnosis written after the outcome found that for A2 under raw, A3, A4 and A5 the census probe and the truth definition are not the same construct (docs/EXPLORATORY_V1_DIAGNOSIS.md, Section 7; docs/STATE.md, amendment (l)).
- A2 under raw rested on forward alone: on 870 seeds of the 87 disagreeing games, the turn keys were recorded as moving nothing on all 870, because the adapter merges the four facings of the agent tile into one index (docs/EXPLORATORY_V1_DIAGNOSIS.md, Section 5, A2).
- A3 under macro failed through the planner's level-1 fallback "mispredicted" on 755 of 775 failing seeds, while four step vectors were accepted on 850 of 920 seeds. The census read whether the planner's forecast failed; the truth asks whether each move's displacement is constant (docs/EXPLORATORY_V1_DIAGNOSIS.md, Section 5, A3).
- A4 was conditional on A3 by rule, so A3's failures became A4's (docs/PREREG.md v1, Section 5.3; docs/EXPLORATORY_V1_DIAGNOSIS.md, Section 5, A4).
- A5 was silent when no level ended: 620 of 663 undetermined seeds under macro had no recorded goal place at all. Where the level ended beside a target (GoTo families), the census called the neighbouring cell a goal (docs/EXPLORATORY_V1_DIAGNOSIS.md, Section 5, A5).
- The registered kappa mapped "undetermined" to the value opposite the truth, so a silent census and a wrong one were scored alike (docs/PREREG.md v1, Section 10; docs/EXPLORATORY_V1_DIAGNOSIS.md, Section 5, "The negative kappa").
- In each case the census read a by-product of one planner's run, while the truth reads the environment's source (docs/EXPLORATORY_V1_DIAGNOSIS.md, Section 7; docs/manuscript_jagi/manuscript_jagi.md, Section 6.5).

### 3.2 No truth table on the development games

- PREREG v1 provided for docs/GROUND_TRUTH_arc_train.md and for V1 on the eight ARC development games, labelled development. It was never written, so the census was never scored against truth where its parameters were set (docs/PREREG.md v1, preface and Section 10; docs/STATE.md, amendments (o) and (p); docs/manuscript_jagi/manuscript_jagi.md, Section 6.2).

### 3.3 No pilot gate

- The pilot rows held census verdicts for eight games with truth-table entries (six suite-B and two suite-C pilots). A V1 comparison on them before the v1.1 tag would have shown the failure before the confirmatory runs. It was not registered and not done (docs/STATE.md, amendment (k), "A lesson"; docs/manuscript_jagi/manuscript_jagi.md, Section 6.3).

### 3.4 The truth columns had little variance on suite B

- On suite B, A1, A2 and A3-macro hold on every environment, A3-raw fails on every one, and A4 fails only on the Dynamic-Obstacles family (docs/GROUND_TRUTH_minigrid.md, "Limits and findings", item 1). On the 161 confirmatory environments A4 fails on 5 and A5 holds on 36 (docs/PREREG.md v1, Section 8). So on suite B a mechanics vector, even an exact one, can vary only through A4 and A5. This bears directly on HORIZON's first test (Phase 1).

## 4. What its automation lacked

- **Every run was manual.** The rule was "You write scripts; RKM runs them and pastes the console output" (CLAUDE.md, "Rules that bind every task", rule 1). Commands went to the author as PowerShell blocks (CLAUDE.md, "Non-negotiable rules", rule 5).
- **Long blocks on one machine.** The suite-B confirmatory block, 9,660 runs, started on 28 September 2026 and had finished by 13 October 2026, on one machine with 8 workers (docs/STATE.md, amendments (i) and (j)). Blocks had to run one at a time with no other Python job, because the caps were measured on an idle machine (docs/STATE.md, amendment (h)).
- **Console text as the record.** Logs were captured with Tee-Object and are UTF-16. Eight workers shared one console pipe, so 261 "done" lines were merged with BabyAI notices from other workers (docs/STATE.md, amendments (h) and (j)). PowerShell 5.1 wrapped a library's stderr notice in an error record (docs/STATE.md, amendment (h)).
- **Hand moves of output.** The ARC runner wrote its rows into scripts/, and the author moved the file to runs/ (docs/PREREG.md v1, Section 9.2).
- **An unregistered clock.** The ARC runner's 900 s default cut eight rows before the budget, found after the run and re-run under a new cap (docs/STATE.md, amendment (e); docs/PREREG.md v1.1, D12).
- **Kaggle as a lab bench only.** Kaggle CPU sessions (4 vCPUs, 31 GB RAM) were listed as a machine, and notebooks were built by hand-run builder scripts in their own folders (CLAUDE.md, "Machines" and "Non-negotiable rules", rule 7; scripts/build_kaggle_navrun.py exists). Nothing scheduled them, collected their output or committed it.

## 5. What its number pipeline got right

- **Frozen code checked by hash before every block.** The runner compared six frozen files with their registered git blob hashes and refused to start on any difference; every confirmatory log reports "frozen blob hashes: 6 of 6 match" (scripts/run_suite.py docstring; docs/PREREG.md v1, Section 5.4; docs/STATE.md, amendments (i) and (j)).
- **One row per run, written atomically, resumable.** One JSON file per (suite, condition, agent, game, seed); an existing row without error is skipped (scripts/run_suite.py docstring; docs/STATE.md, amendment (j)).
- **Analysis by script, tables written by script.** analyze_v1.py and analyze_v2.py write docs/tables/v1.md, v1.json, v2.md and v2.json; their logs are committed (scripts/analyze_common.py, `write_table`; docs/STATE.md, amendment (k)).
- **Synthetic tests with hand-worked numbers before any real row was read.** 20 of 20 at the v1.1 tag (docs/PREREG.md v1.1, D11; docs/STATE.md, amendment (g)).
- **Identity checks.** E6's hash_state rows were identical to E2's in every field except seconds, 250 of 250 (docs/STATE.md, amendment (e)); the nine-game Procgen determinism check, 270 of 270 pairs identical (amendment (i)).
- **Every manuscript number read from a committed file.** scripts/manuscript_numbers.py reads tables, JSON outputs and prose passages and stops if a passage is missing; scripts/manuscript_check.py checks every numeral, hash, date and URL in the manuscript against that list, and the forbidden words (both docstrings).
- **Withdrawn claims kept in the record.** STATE.md Section 3 lists each claim that fell, why, and where it was corrected (docs/STATE.md, Section 3).
- **Exploratory work labelled and kept apart from the outcome.** The V1 diagnosis was written after gate G3 and changed nothing registered (docs/EXPLORATORY_V1_DIAGNOSIS.md, header).

## 6. What HORIZON keeps and what it changes

Keeps:
- the 175 study-1 games (161 suite-B and 14 suite-C confirmatory), their truth tables and their rows, as development data;
- the truth definitions of A1 to A5, so that HORIZON's mechanics vector means what study 1's truth tables mean;
- the V2 machinery (score, conjunctive prediction, void band, bootstrap, nuisance baseline), imported read-only from the study-1 scripts for the oracle test;
- frozen code checked by blob hash, one row per unit of work, analysis by script, numbers read by script from committed files, the append-only STATE.md.

Changes:
- **The construct question first.** Phase 1 gives the agents' outcomes the exact mechanics (the truth table, "the oracle") in place of the census. If exact mechanics do not predict level-1 completion, no census of them can; if they do, a census is worth building. This test is exploratory and is the pilot for the registration.
- **A rival hypothesis.** H2, the size of the search the first level presents, is set against H1, the match between mechanics and the agent's assumptions. Study 1 had only a nuisance baseline (grid area, action count, colour count), and that baseline beat the census on every primary suite-B line (section 2).
- **Truth on development data and a pilot gate,** both registered before any confirmatory run (sections 3.2 and 3.3).
- **"Undetermined" handled by a registered rule that tells a silent measurement from a wrong one** (section 3.1).
- **Automation in place of pasting.** Runs go through a manifest of chunks on Kaggle, scheduled and committed by a workflow, proven by a dry run before any experiment (project rules R4 and R8).
- **Venues.** Support goes to IEEE Transactions on Games, with JAIR as the alternative if the result is broad; Refute goes to the repository and a preprint on Zenodo (project rule R5).
