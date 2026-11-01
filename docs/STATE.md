# STATE: the HORIZON project record

Append-only. Each session adds one dated, lettered amendment at the end; nothing above an amendment is edited. Read this file first in every session and write it last. Every number in this file names the committed file and script it comes from.

## Amendment 24 Oct 2026 (a)

First amendment. The project starts here.

- **Question.** What decides whether a frame-only explorer that relies on built-in assumptions completes the first level of an unseen game: the match between the game's true mechanics and the agent's assumptions (H1), or the size of the search the first level presents (H2) (docs/PROJECT_BRIEF.md, Section 1).
- **Registration status:** not yet registered. No test, threshold, suite or outcome table of HORIZON exists yet.
- **Folders.** Parent D:\Research\horizon; repository and working directory D:\Research\horizon\repo; prompts D:\Research\horizon\prompts; Python environment D:\Research\horizon\.venv (outside the repository, made with D:\python\3.11.9\python.exe). The environment has not been created yet.
- **The earlier project** at D:\Research\arc3\repo is read-only for this project. In this session its files were read and nothing there was written or run.
- **Files written (Phase 0):**
  - CLAUDE.md, with the rules R1 to R9 in the form given by the author, and the forbidden-word list of study 1's docs/manuscript_jagi/BUILD.md step 8 written out;
  - README.md;
  - docs/PROJECT_BRIEF.md;
  - docs/LESSONS_FROM_STUDY1.md, every statement citing a study-1 file;
  - docs/STATE.md (this file);
  - .gitignore; requirements.txt, empty for now;
- **Repository.** git initialised in D:\Research\horizon\repo; public repository rahul-k-mishra/horizon created with gh and pushed. Commit "HORIZON bootstrap".
- **Next:** Phase 1, the oracle test (exploratory, on study-1 data; the pilot for the registration): scripts/oracle_v2.py, run by the author, whose console he pastes; then docs/oracle/READING.md.

## Amendment 24 Oct 2026 (b)

Second amendment. The lines above are unchanged.

- **Phase 0 done.** Commit 69adf28 "HORIZON bootstrap", pushed to https://github.com/rahul-k-mishra/horizon; its message checked with git log -1 --format=%B: one subject line.
- **Phase 1, the oracle test (EXPLORATORY), written and not yet run.**
  - scripts/oracle_v2.py recomputes study 1's V2 on study 1's rows (minigrid raw and macro, procgen center_off) with the truth table's A1 to A5 in place of the census, through study 1's analyze_common.py and analyze_v2.py imported read-only by path, and adds five search features that need no simulator: grid area, action count, colour count, N's distinct states in level 0, N's actions to its first level end. Outputs docs/oracle/oracle_v2.md, .json and two figures; its console also goes to logs/oracle_v2.log.
  - The script checks itself three ways: its census lines must equal study 1's docs/tables/v2.json, its bootstrap loop must reproduce study 1's intervals, and its logistic refit must reproduce study 1's baseline.
  - scripts/test_oracle_v2.py, a synthetic test on fabricated rows and truth tables in a temporary folder (two study-1 analysis files copied there unchanged): OK, run in this session with D:\python\3.11.9\python.exe. It read no study-1 row or truth table. No study-1 file was written; the study-1 scripts/__pycache__ folder gained no file.
  - In the first test run an expectation in the test was wrong (balanced accuracy of an all-false prediction is 0.5 under study 1's function, not undefined); the test was corrected, not the script.
  - requirements.txt now pins numpy 2.4.3 and matplotlib 3.10.9, the versions in D:\python\3.11.9.
- **Not yet run on study-1 data.** No oracle number exists. The author runs the script and pastes the console; docs/oracle/READING.md follows the paste.

## Amendment 24 Oct 2026 (c)

Third amendment. The lines above are unchanged. Everything in this amendment about the oracle test is EXPLORATORY.

- **The oracle run.** The author ran scripts/oracle_v2.py on 24 October 2026 with 8 workers and pasted the console. The console, written by the script, is logs/oracle_v2.log; the outputs are docs/oracle/oracle_v2.md, oracle_v2.json, fig_oracle_vs_census.png and fig_search_features.png. All are committed in ff85628.
  - Inputs as the log reports them: 10,500 row files, 10,080 confirmatory rows kept, 420 pilot rows skipped; 0 rows with an error field, 0 short of their budget; both imported study-1 analysis files match their blob hashes registered at study 1's prereg-v1.1.
- **The three reproduction checks**, from the log: reproduction of study-1 census lines 20 of 20 identical to docs/tables/v2.json; the bootstrap loop reproduces bootstrap_auroc_ci on 20 of 20 lines; the logistic refit reproduces logistic_fit_predict for B on 20 of 20 lines.
- **The finding, in one sentence (exploratory):** with exact mechanics in place of the census, first-level completion is ranked at AUROC 0.5477 to 0.6967 on MiniGrid/BabyAI, with leave-one-game-out fits of the mechanics vector below 0.5 on all 14 MiniGrid/BabyAI lines, while grid area alone ranks the games better on five of the six primary lines and measures read out of N's runs better still, post hoc.
- **docs/oracle/READING.md** (ff85628) gives the reading per suite and condition, the limits, and, as a reading and not a plan, that the registered study must be built around H2 (search size) with H1 (mechanics match) as the rival.
- **scripts/oracle_sat.py** (ff85628), written and not yet run on study-1 data: how each AUROC of 1.0000 arises (values per class, overlap, whether the censoring flag alone separates the classes) and the pre-run number per line (area, action count, colour count, alone and together, in-sample and leave-one-out). It was exercised once on the fabricated data of scripts/test_oracle_v2.py in the session scratchpad, not on study-1 rows. Command, working directory D:\Research\horizon\repo: D:\Research\horizon\.venv\Scripts\python.exe scripts\oracle_sat.py --workers 4. Outputs docs/oracle/saturation.md, saturation.json and logs/oracle_sat.log.
- **Next:** the author runs scripts/oracle_sat.py; then Phase 2, the automation, built and proven by a dry run before any study code.

## Amendment 24 Oct 2026 (d)

Fourth amendment. The lines above are unchanged. Everything in this amendment about the oracle test is EXPLORATORY; nothing about the automation is a study result.

- **The saturation run (EXPLORATORY).** The author ran scripts/oracle_sat.py; its console is logs/oracle_sat.log, its outputs docs/oracle/saturation.md and saturation.json, committed in a19ae3b. From the log: its inputs agree with oracle_v2.json on 2017 of 2017 games on 20 of 20 lines; there are 41 saturated items on 11 lines, and on 8 of those lines the majority censoring flag alone separates the classes. The automation keeps every agent statistic out of the features for this reason (docs/AUTOMATION.md, Section 5).
- **Phase 2, the automation, built.** docs/AUTOMATION.md; scripts/automation/ (common.py, schema.py, jobs.py, runner.py, loop.py, fake_kaggle.py, test_loop.py, actions_minutes.py, dryrun_report.py); kaggle/ (runner.ipynb, kernel-metadata.json, requirements-runner.txt); requirements-loop.txt; jobs/manifest.json for the dry run; .github/workflows/horizon.yml. Two job kinds, search and agent, never mixed in a chunk, with separate row files and schemas; the bounded search job with node, time and memory caps and a frontier spill; resumability by done-markers between chunks and by checkpoints inside a chunk; a session deadline computed at start. The code the Kaggle sessions run is the annotated tag **automation-v1** (commit 59ddd88). The loop code that runs on GitHub was changed after the tag, as listed below; the runner code was not.
- **The credential.** The username-and-key form does not authenticate the Kaggle tool 2.2.4; the author's existing KGAT_ API token does, given as KAGGLE_API_TOKEN. The repository secret KAGGLE_KEY holds that existing token, and the workflow passes it to the tool as KAGGLE_API_TOKEN (c696ea6). No new token was created. The first tick on GitHub had failed its push for this reason, which counted as failure 1 of 3 for dry-01 (docs/AUTOMATION.md, Section 8).
- **The second trigger.** The cron never fired during the dry run (7 runs on GitHub, all workflow_dispatch). On 24 October 2026 the workflow was changed to start its own successor with workflow_dispatch after a bounded sleep (loop.py next-wake: 5 to 30 minutes; none when the manifest is complete or the loop halted), the cron kept, in db58d22. An external cron service and a push trigger were weighed and rejected (docs/AUTOMATION.md, Section 7). The report scripts were then corrected (933c5e9 and the commit after it).
- **The dry run (R8), done.** Report docs/DRYRUN.md with logs/dryrun_report.log, logs/actions_minutes.log and runs/dryrun/actions_runs.json, committed in 7103bc3. All three chunks done: dry-01 on Kaggle kernel version 2, dry-02 partial on version 3 and done on version 4 after a resume from the checkpoint committed in dc4bcde (its visited set kept as a release asset), dry-03 on version 5; graph-a's count equal to an uninterrupted enumeration, graph-b capped at its node cap. The chain started its successor once by itself (run 40112968801, started by github-actions[bot]), which found the manifest complete and stopped the loop. Elapsed from the first dispatch: 1 h 17 min 31 s. Actions: a tick median 6.5 s; a run that does not wait 1 minute rounded up; 1,440 minutes for a month with nothing to do; 45,360 minutes for a month of a campaign in flight, estimated from one link; free, the repository being public.
- **The dry run's log is committed**, so under R8 experiments may now be launched through the loop, once registered.
- **Next:** Phase 3, as the bootstrap prompt sets it out; nothing of it is begun.

## Amendment 24 Oct 2026 (e)

Fifth amendment. The lines above are unchanged. Nothing in this amendment is registered; the scan of the GVGAI descriptions is EXPLORATORY.

- **Forbidden-word exception approved.** On 24 October 2026 the author approved the exception in CLAUDE.md to the forbidden-word list of rule R9 for a file name that a citation must give (with the exceptions for a word inside a cited title and inside a rule that quotes it).
- **Consecutive-crash counter** (243c363). A tick that ends with an error, or a workflow run whose earlier step fails before the tick, adds 1 to "consecutive_crashes" in jobs/state.json; a tick that reaches a chunk sets it to 0; at 12 the loop halts with STATE-ready text in logs/automation.log, as a failing chunk halts it. 12 because at the chain's shortest spacing of 5 minutes it is an hour of continuous failure. scripts/automation/test_loop.py has a third scenario for it, and all three scenarios pass (OK, run in this session on the local stand-in for Kaggle).
- **The Kaggle session limit is recorded as an assumption** (docs/AUTOMATION.md, Section 3). Kaggle's documentation page returns no text to a plain fetch, so the 12-hour limit was not verified. The study's session is set to stay correct at 9 hours: work 28,800 s, checkpoint reserve 900 s, start-up allowance 900 s and one search batch of at most 60 s end at most 30,660 s after the notebook starts, 29 minutes inside 9 hours and 3 h 29 min inside 12 (logs/design_budget.log). A shorter real limit shows up as failures and a halt, not as silent loss. The search memory ceiling becomes 6 GiB per worker, four workers to a session.
- **Phase 3 written** (dc3de2e): docs/DESIGN.md and docs/PREREG.md draft v0, not registered and not tagged.
  - Suites weighed with evidence fetched and saved by scripts/suite_evidence.py (logs/suite_evidence.log): Griddly, py-vgdl and MinAtar are not used; the confirmatory suite is GVGAI's deterministic grid-physics games, vendored under third_party/gvgai at commit e58ff6597319155218759cc178931e05b81b524c.
  - *Exploratory:* scripts/vgdl_scan.py found 110 grid-physics games that parse with a level-0 file, 30 of them deterministic by a rule read from the GVGAI source, with 5 levels each; its simplified reading of A1 to A5 gives the score S every value from 1 to 5 on those 30 games (logs/vgdl_scan.log).
  - Pilot games drawn with seed 20261024 (logs/draw_pilot.log): bait, labyrinthdual, rivers, watergame; 26 confirmatory games, 130 (game, level) units.
  - The capped-game rule is decided (docs/DESIGN.md, Section 5; docs/PREREG.md, Section 7.4).
  - Budget, upper bounds: 43 to 111 Kaggle chunks, 16.2 to 41.7 days, depending on the agent cap the pilot sets (logs/design_budget.log).
- **Next:** the author's review of docs/DESIGN.md Section 12 and the five items at the head of docs/PREREG.md; then the truth-table generator with its hand check, the GVGAI adapter and search job, the agent copies and the analysis script, before the tag prereg-v1. No experiment of the study has run.

## Amendment 24 Oct 2026 (f)

Sixth amendment. The lines above are unchanged. Nothing is registered or tagged; generator outputs not yet hand-checked are EXPLORATORY.

- **Review before the decisions** (09a6dcd): docs/design/DECISION_REVIEW.md gives a view on each of the author's five decisions with its evidence, and a sixth consideration. It changes no file; a point adopted from it enters by a dated change.
- **The author's five decisions written in** (fd375cf), each with its reason, in docs/DESIGN.md (Sections 2.1, 3.3, 4, 7, 7.1, 12) and docs/PREREG.md draft v0 (Sections 4, 5, 7.4 to 7.8, 9.1, 10):
  1. the level is the unit, games the clusters; the mechanics score is constant within a game, so H1 is tested on 26 effective points;
  2. A2 fails for a shooting avatar; study 1's census had no such clause and disagreed with the Procgen truth on six games, five of them by firing or throwing and one by pushing;
  3. the thresholds stand and are registered: AUROC floor 0.70, 98.33% Bonferroni family, void band 10% to 90%, capped shares 25% and 10%;
  4. stage D, the development search on study 1's MiniGrid/BabyAI levels, runs before the tag as the kind devsearch; it may not be used as evidence for the registered claim;
  5. the smallest detectable difference is registered before the tag, and a Refute outcome reads "no difference of at least d".
- **Budget** with stage D as 1,610 (game, seed) units at a 900 s cap: 50 to 118 chunks at most, 18.8 to 44.3 days (logs/design_budget.log).
- **Truth-table generator** (75ab7cd): scripts/truth_vgdl.py reads only the vendored GVGAI files and writes docs/truth/gvgai.json with every deciding clause and line. Its synthetic tests pass with warnings as errors (OK, run in this session). While writing it, A4 was clarified in the design: stationary producers count as classes that stay in place, and a blocker removed through a sprite only the avatar pushes counts as removed by the avatar. *Exploratory, not yet hand-checked:* on the 30 deterministic games, 150 units, A1 holds on 150, A2 on 50, A3 on 110, A4 on 145, A5 on 65; no game's vector differs between its levels (logs/truth_vgdl.log).
- **Hand check prepared:** scripts/draw_handcheck.py, seed 20261025 (logs/draw_handcheck.log), drew clusters, colourescape, glow, labyrinthdual, lasers, painter, racebet, rivers, sokoban and wrapsokoban; the sheet docs/truth/HANDCHECK.md lists 100 rows, none filled in.
- **Smallest detectable difference:** scripts/sdd.py and its tests (OK) are written; it waits on stage D's rows.
- **Next:** the author's hand check; stage D's job (kind devsearch) written, dry-run tested and run through the loop; then scripts/sdd.py; then the author's two reserved decisions (Sections 2.1 and 7.1 of docs/DESIGN.md) before the tag.

## Amendment 25 Oct 2026 (g)

Seventh amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created.

- **Four changes adopted by the author on 25 October 2026** from docs/design/DECISION_REVIEW.md, written into docs/DESIGN.md and docs/PREREG.md draft v0 with date and reason (2aa8d93):
  1. both AUROCs over between-game pairs only; at most 156 within-game pairs are removed, at most 10.3% of all pairs at an edge of the void band (logs/design_budget.log); the bootstrap over 26 games is unchanged;
  2. a registered limit in PREREG Section 1: A4 fails on 100 of 550 units over all games against 5 of 150 in the deterministic suite (logs/truth_vgdl.log), and A1 and A4 hold on all 26 confirmatory games (logs/sdd.log), so H1 is tested mainly through A2, A3 and A5; scripts/sdd.py reports the mechanics score's variation beside its number;
  3. two of three evidence agents void makes the study Void, and no agent is added, removed or re-weighted afterwards; the single-primary-agent alternative is recorded in DECISION_REVIEW.md as considered and not adopted;
  4. scripts/sdd.py has a second estimate on the confirmatory structure (26 clusters of 5 levels with the actual S_M), and the registration states both.
- **Kind devsearch written and tested** (17c04da; code tag automation-v2 on afa984c): the MiniGrid search with snapshots instead of deep copies, the effective-horizon bound by exact dynamic programming (scripts/automation/eh.py), schema horizon.search.v2, and a worker pool in the runner with a multi-unit chunk checkpoint. Tests, run in this session: scripts/automation/test_devsearch.py OK (the bound equals a hand-worked value and an independent implementation on 40 random MDPs; the search equals a deep-copy search on six levels; a resumed search equals an uninterrupted one; logs/test_devsearch.log); scripts/automation/test_loop.py OK with a fourth scenario for the kind (logs/test_loop.log); scripts/test_sdd.py OK. A .gitattributes now keeps runs/ and jobs/ byte-exact on Windows, found because the fourth scenario failed on CRLF line endings.
- **Dry run of the kind** through the loop on Kaggle (docs/DRYRUN_DEVSEARCH.md, 2fd4f21): kernel version 6 partial, checkpoint committed in d64ad89, kernel version 7 resumed on another machine and done in 4f88211; the three rows equal the laptop's counts. The dummy dry-run manifest is archived at jobs/archive/dryrun/manifest.json.
- **Stage D's manifest** (afa984c): jobs/stage_d/manifest.json, 156 games (5 Dynamic-Obstacles games left out), 1,560 units, 39 chunks, registered caps; between 39 and 195 sessions (logs/make_stage_d_manifest.log). Not launched.
- **Next:** the author decides whether to launch stage D (copy jobs/stage_d/manifest.json to jobs/manifest.json and start the workflow); the author's hand check; then scripts/sdd.py on stage D's rows.

## Amendment 25 Oct 2026 (h)

Eighth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. No file under jobs/ or runs/ was changed.

- **A window for the hand check** (3590100 to 7c5981a, and a fix to how it hashes files): scripts/handcheck_app.py, standard library only, shows one row at a time: a predicate on one drawn level, with the description and level file beside it, the deciding line highlighted, the generator's verdict, a plain reading of the line and what would make the verdict wrong. It keeps the answers in docs/truth/handcheck_answers.json after every click and resumes where it stopped.
- **docs/truth/HANDCHECK_GUIDE.md**: how a VGDL description and a level file are written, and for each of A1 to A5 its question, the words that decide it, an example and a counter-example. The per-row readings are in docs/truth/handcheck_readings.json.
- **docs/truth/handcheck_rows.json**: the 100 rows of the 10 drawn games (logs/handcheck_rows.log), built from docs/truth/gvgai.json, docs/truth/HANDCHECK.md, the guide and the readings.
- **scripts/handcheck_report.py** writes docs/truth/HANDCHECK_RESULT.md from the answers: counts per predicate and per game, every disagreement and unsure row with its note, games, levels and dates; it resolves nothing. scripts/test_handcheck.py, run in this session, OK (logs/test_handcheck.log).
- Not yet decided by the author, and not written into docs/DESIGN.md or docs/PREREG.md: whether the hand check is made by the author or the automated cross-checks stand alone. No answers exist yet.
- **Next:** the author tries the tool and decides; stage D as in amendment (g).

## Amendment 25 Oct 2026 (i)

Ninth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. No row of stage D has been read and no analysis has run.

- **State before the launch.** jobs/manifest.json was the campaign devsearch-dryrun, its one chunk ds-01 done; no dispatch in flight; the loop not halted; the tag automation-v2, which jobs/stage_d/manifest.json names, on the remote at afa984c.
- **Stage D launched** (2ce262c): the devsearch dry-run manifest moved to jobs/archive/devsearch-dryrun/manifest.json; jobs/stage_d/manifest.json copied unchanged to jobs/manifest.json (campaign dev-minigrid, 39 chunks, 1,560 units); jobs/state.json reset to no dispatch, not halted, 0 consecutive crashes.
- **First chunk.** The loop was started with gh workflow run horizon.yml (run 40141855308). logs/automation.log: chunk d-001 dispatched at 2026-10-24T23:13:58Z and pushed to Kaggle as kernel version 8 at 23:14:04Z.
- **Next:** wait until every chunk of dev-minigrid is done; then the campaign check, scripts/sdd.py on the stage D rows, and the development reading, in that order. docs/DESIGN.md and docs/PREREG.md are not changed before the author decides.

## Amendment 25 Oct 2026 (j)

Tenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. No file under jobs/ or runs/ was changed by this session's work; stage D is running. docs/DESIGN.md and docs/PREREG.md are unchanged.

- **eggomania's A1, settled.** GVGAI maps w to wall and A to avatar when a LevelMapping leaves them out (src/core/game/BasicGame.java:51-56, at the vendored commit, not vendored), with default sprites wall Immovable and avatar MovingAvatar (src/core/game/Game.java:359-367). scripts/truth_vgdl.py ignored these defaults and has been fixed. scripts/test_truth_vgdl.py has a new game, nomap: OK (logs/test_truth_vgdl.log). The generator was rerun (logs/truth_vgdl.log). scripts/truth_diff.py against b0091c7 (logs/truth_diff.log): the only verdicts that change are eggomania's A1 on 5 units, fails to holds, in a game that is not deterministic. Clauses change with the same verdict in chopper, circuit, eggomania and islands. The 30 deterministic games, the pilot draw and the hand-check draw are the same. docs/truth/handcheck_rows.json was written again for the new hash, with its 100 rows unchanged (logs/handcheck_rows.log). Record: docs/truth/DEFAULT_MAPPING.md.
- **Four questions for the author** (docs/truth/PREDICATE_QUESTIONS.md): Q1 painter A2 (a sprite created by walking), Q2 rivers A4 (a blocker transformed into another blocker in place), Q3 labyrinthdual A4 (blockers that differ by avatar subtype), Q4 colourescape A4 (undoAll with the avatar not named first). For each the file sets out what the description says, what the predicate says, and whether the verdict follows. *Exploratory:* scripts/predicate_readings.py (logs/predicate_readings.log) counts the confirmatory games that would change under the other reading: Q1 2 (painter, zenpuzzle), Q2 0, Q3 2 (modality, tercio), Q4 1 (colourescape), or 0 if the generator counted a parent name by its placeable types. That last change alters no present verdict. No predicate was changed.
- **Next:** the author decides Q1 to Q4 and records the decisions by dated changes before the tag; the hand check; stage D runs on, and its reading comes after every chunk is done.

## Amendment 25 Oct 2026 (k)

Eleventh amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. No file under jobs/ or runs/ was changed by this session's work; stage D is running.

- **The four predicate questions, decided by the author on 25 October 2026,** before the tag and before any confirmatory run, with the exploratory counts of logs/predicate_readings.log known. They are recorded in docs/truth/PREDICATE_QUESTIONS.md (last section) and, dated, in docs/DESIGN.md (Sections 4 and 7.1) and docs/PREREG.md draft v0 (header, Sections 1, 5, 7.8 and 13).
  - Q1: A2 widened. It fails where an interaction that names an avatar type creates a sprite of a non-avatar type.
  - Q2: rivers' A4 unchanged.
  - Q3: labyrinthdual's A4 unchanged, and the other reading rejected before the tag.
  - Q4: the predicate unchanged, and the generator now counts a name by the types it can place, in both places it tests for agent-driven sprites.
- **Generator changes and their effect.**
  - Q4 fix: no verdict or clause changes on 550 units, 2,750 verdicts compared (logs/truth_diff_q4.log).
  - Q1 change: 90 verdicts change on 18 games, all A2, holds to fails. In the deterministic suite only painter and zenpuzzle change, both confirmatory (logs/truth_diff_q1.log).
  - Tests: two new games, parentbox and walkspawn. OK, and each fails without its change (logs/test_truth_vgdl.log).
- **After the decisions.** S_M on the 26 confirmatory games was 2: 3, 3: 11, 4: 9, 5: 3 and is now 2: 3, 3: 13, 4: 7, 5: 3. A2 holds on 7 of 26 instead of 9. A1 and A4 hold on all 26, so the registered limit stands (logs/sdd.log, rerun on committed files; it stops at "waiting", since stage D has no rows yet).
- **What stayed the same.** The deterministic suite, the pilot draw (logs/draw_pilot.log) and the hand-check draw (logs/draw_handcheck.log).
- **Hand check.** docs/truth/HANDCHECK.md changed in its A2 rows: painter's two from holds to fails, and the clauses of labyrinthdual's and racebet's. The painter, labyrinthdual and racebet A2 readings and the guide's A2 section were rewritten. The rows file was written again (logs/handcheck_rows.log), and scripts/test_handcheck.py is OK (logs/test_handcheck.log). No answers existed.
- **A new registered limit** (PREREG Section 1). A4's first clause is not checked by the generator. scripts/a4_unchecked.py (logs/a4_unchecked.log) finds undoAll lines without the avatar first in 14 of the 26 confirmatory games where A4 holds.
- **Next:** the hand check by the author; stage D runs on, and its reading comes after every chunk is done.

## Amendment 25 Oct 2026 (l)

Twelfth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. No file under jobs/ or runs/ was changed by this session's work; stage D is running.

- **A4's first clause is now checked by the generator,** at the author's request before the tag. scripts/truth_vgdl.py (cancelling_lines, obstacle_fails) takes every undoAll line without the avatar first, which still cancels the avatar's move (UndoAll.java:40-57). Every sprite such a line names must be agent-driven or pass the tests on a blocker.
- **The author's decision on the check.** A first version failed A4 on thecitadel (a crate pushed along by a crate, line 34) and wrapsokoban (a pushed box wrapping at the edge, line 23), both confirmatory. On 25 October 2026 the author decided both count as moved only through the avatar, with that known. agent_driven is now the largest set consistent with itself, and a move whose only partner is the edge does not count against a sprite. Recorded in docs/truth/PREDICATE_QUESTIONS.md, docs/DESIGN.md (Section 4) and docs/PREREG.md draft v0 (Sections 1 and 5). The limit recorded in amendment (k) is replaced by what remains of it.
- **Effect** (scripts/truth_diff.py against 923d046, logs/truth_diff_a4clause.log): 5 verdicts change, all A4 holds to fails on enemycitadel, which is not deterministic; its cancelling line names a RandomNPC. No verdict changes in the 30 deterministic games, and 105 entries change their clauses only.
- **Coverage** (scripts/a4_unchecked.py, rewritten to report the check, logs/a4_unchecked.log). Every cancelling line is cited in the 14 confirmatory and 2 pilot games that have one. In the deterministic games, no effect applied to the avatar other than stepBack and undoAll cancels a move, and no undoAll line has a notStype.
- **Tests:** four new games, boxwall, boxbat, chainpush and wrapbox, all OK (logs/test_truth_vgdl.log). boxwall and boxbat fail on the generator before the check.
- **Reruns.** S_M on the 26 is unchanged at 2: 3, 3: 13, 4: 7, 5: 3; A1 and A4 hold on all 26, so the registered limit stands (logs/sdd.log). The deterministic suite, the pilot draw and the hand-check draw are unchanged. docs/truth/HANDCHECK.md changed in A4 clauses only. The A4 readings of clusters, colourescape, lasers and wrapsokoban and the guide's A4 section were rewritten. The rows were written again (logs/handcheck_rows.log), and scripts/test_handcheck.py is OK.
- **Next:** the hand check by the author; stage D runs on, and its reading comes after every chunk is done.

## Amendment 30 Oct 2026 (m)

Thirteenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. No file under jobs/ or runs/ was changed by this session's work; stage D is running, chunk d-010 on its second session (kernel version 30). docs/DESIGN.md and docs/PREREG.md are unchanged. This is a progress count of the automation, not a reading of stage D; no search result other than seconds, caps and state was read.

- **Progress report** (217e57e): scripts/stage_d_progress.py reads runs/dev-minigrid/devsearch/*.json, jobs/manifest.json and logs/automation.log and writes logs/stage_d_progress.log. Run in this session on committed files only.
- **From the log.** 378 rows; 140 units capped, 81 by the node cap and 59 by the time cap of 14400 s; 238 complete. 15 of 38 games have a capped unit, 12 have every unit capped, and those 15 games hold 0.9365 of all worker seconds; the slowest 10 units hold 0.0829. Finished chunks needed 1 session (2 chunks), 2 (3), 3 (3) and 4 (1); wall per chunk from first dispatch to last collect 2.04 h to 32.37 h, median 14.68 h, mean 14.13 h. d-010 has 18 of 40 units done after one session.
- **Estimate for the 29 pending chunks, on that basis:** 17.07 days at the mean, 17.74 at the median, 2.46 to 39.12 days at the finished extremes; at most 5 sessions a chunk under the registered caps, 49.15 days if every pending unit hit the time cap. The finished chunks hold the first games in name order, not a random draw.
- **Next:** stage D runs on; its reading comes after every chunk is done.

## Amendment 1 Nov 2026 (n)

Fourteenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. docs/DESIGN.md and docs/PREREG.md are unchanged. No search result other than unit counts and state was read.

- **The halt.** Twelve ticks in a row crashed, from run 41285176094 (07:32Z) to run 41309961307 (13:11Z) on 1 November 2026, and the loop halted at 13:11:37Z (logs/automation.log, CRASH 1 to 12 and HALT). Each tick failed at its first Kaggle call, kaggle kernels status, before reaching a chunk.
- **The cause.** The kaggle tool could not import: kaggle/models/upload_file.py line 22 imports six, and six was not installed (ModuleNotFoundError: No module named 'six'; the halt reason in jobs/state.json was cut before this line). kaggle 2.2.4 imports six without declaring it, and six used to come only through python-dateutil 3.0.0, which requires it. python-dateutil 4.0.0 was uploaded to PyPI at 2026-11-01T07:02:40Z and requires only tzdata. The kaggle release was not the cause: requirements-loop.txt has pinned kaggle==2.2.4 since 59ddd88.
- **The evidence.** The last good tick (run 41283126638, 07:01Z) and the first failing one (run 41285176094, 07:32Z) ran on the same commit, cf2e503, the same runner image (ubuntu-24.04 20261025.353.1) and the same CPython 3.11.17, so only the dependencies resolved at install time differ. The good tick installed its packages at about 07:02:10Z, before 4.0.0 existed. A fresh install of kaggle==2.2.4 on the laptop resolves python-dateutil 4.0.0 and fails with the same ModuleNotFoundError.
- **The pin** (013ee76): requirements-loop.txt keeps kaggle==2.2.4 and adds python-dateutil==3.0.0 and six==1.17.0, with a comment naming the broken release and the date. Checked on the laptop before the restart: a fresh install of the file imports (Kaggle CLI 2.2.4), and a read-only kaggle kernels status answered COMPLETE for the runner notebook, with its last run at 06:00:53Z, kernel version 36. No tick was run from the laptop, because a tick commits, pushes and may start a session on Kaggle.
- **scripts/automation/test_loop.py cannot run on the present manifest.** It copies jobs/manifest.json, which since 2ce262c is stage D's and has no agent kind, and stops with KeyError: 'agent'. It also uses a fake kaggle tool, so it would not have tested the import. Not changed in this session.
- **The restart** (013ee76): jobs/state.json halted false, consecutive_crashes 0, halted_at and halt_reason null, the dispatch of d-013 kept. Run 41318682726 reached the chunk: COLLECT d-013 kernel version 36, partial, at 14:57:24Z (304fec5); DISPATCH d-013 attempt 2 and PUSHED as kernel version 37 at 14:57:44Z (2edd2c4). Chunks: done 12, partial 1, pending 26 at the collect.
- **No result was lost.** The session of kernel version 36 was not cut short by the halt. It ran on Kaggle while the ticks crashed, stopped at its deadline at 14:01:59Z with 10 of 40 units done (logs/kaggle/d-013__v36.log), ended COMPLETE, and its output stayed on Kaggle until the collect. That collect committed 10 finished units of d-013 with their done markers and 15 checkpoint files, with 0 failures. Attempt 2 resumes from them. The halt cost about 55 minutes of idle time, from the end of that session to the new push, and no rows.
- **Next:** stage D runs on; its reading comes after every chunk is done.

## Amendment 1 Nov 2026 (o)

Fifteenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. docs/DESIGN.md and docs/PREREG.md are unchanged. No file under jobs/ or runs/ was changed by this session's work; stage D is running, chunk d-013 on kernel version 37.

- **Every loop dependency pinned** (5eafa48), at the author's request after amendment (n). requirements-loop.txt now holds the full freeze of a fresh install of kaggle==2.2.4 with python-dateutil==3.0.0 and six==1.17.0: 35 packages, each with an exact version. Nothing is left to the resolver. colorama, which tqdm needs on Windows only, carries the marker sys_platform == "win32".
- **Checked on the laptop before the push.** A fresh install from the file gives the same 35 packages as the set checked in amendment (n), and pip check finds no broken requirement. A read-only kaggle kernels status answered RUNNING for the runner notebook. pip download for manylinux2014_x86_64, CPython 3.11, binary wheels only, found a wheel for every pin, so the runner can install the file. The first tick to install it is the next one after 5eafa48.
- **Next:** stage D runs on; its reading comes after every chunk is done.

## Amendment 1 Nov 2026 (p)

Sixteenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. docs/DESIGN.md and docs/PREREG.md are unchanged. No file under jobs/ or runs/ was changed by this session's work; stage D is running, chunk d-013 on kernel version 37.

- **The loop test no longer reads the live campaign** (70e8b66). scripts/automation/test_loop.py copied jobs/ into each scenario, and so could not run since stage D was installed (amendment n). It now builds its own manifest (fixture_manifest: the dummy dry run of the kinds agent and search, the same chunks and units as jobs/archive/dryrun/manifest.json, with fast settings) and copies only the automation code. jobs/ is written from nothing in each scenario. The devsearch scenario already built its own manifest and now uses the same helper.
- **Session budgets of the test.** With its own manifest, the test failed on the laptop. Each fake session spends part of its work time cloning and running pip before the runner starts, and 6 s did not always leave the 2 s an agent unit needs, so dry-01 failed three times and halted the loop. The devsearch scenario had the same thin margin at 8 s. The fixture now gives 12 s of work, and the devsearch scenario 16 s, with DoorKey slowed to 1.0 s a batch so that its first session still ends partial. All four scenarios pass: main, halt, crash and devsearch (logs/test_loop.log, OK). In that log dry-02 and d-01 each end partial and are resumed, as the test requires. A later commit (dd270ab) changes a comment only.
- **The freeze checked by an install that adds nothing** (c9e9eb1). scripts/automation/check_freeze.sh downloads exactly the pinned files without dependencies and makes a virtual environment with no pip and no setuptools. It installs the file offline with --no-index --no-deps, then runs kaggle --version and one read-only kaggle kernels status in it. The control does the same with six taken out of the file. logs/check_freeze.log: 35 pins, 35 files in the wheelhouse, 35 packages installed; Kaggle CLI 2.2.4; the status answered RUNNING. The control fails with ModuleNotFoundError: No module named 'six' (from python-dateutil 3.0.0's relativedelta, reached at kaggle_api_extended.py line 39). The check would therefore have caught the halt of amendment (n). The script hides the temporary folder's path, which on Windows holds the user's profile. .gitattributes now keeps shell scripts at LF (98d7a0b).
- **What is still not pinned, and why.**
  - Nothing the kaggle tool imports: the empty environment ran it with the 35 pinned packages and nothing else. pip and setuptools are not needed at run time; the runner's pip is the one actions/setup-python ships, used only to install.
  - The Python patch release: the workflow asks for "3.11", which gave 3.11.17 on 1 November 2026.
  - File hashes: the file pins versions, not hashes; PyPI does not let a released file be replaced.
  - On Kaggle: kaggle/requirements-runner.txt pins gymnasium 1.3.0 and minigrid 3.1.0 only. Their dependencies (cloudpickle, farama-notifications, numpy, typing-extensions, pygame-ce) are resolved against Kaggle's image in each session. That file belongs to the code tag automation-v2, which stage D's manifest names, so it is not changed while stage D runs.
- **Next:** stage D runs on; its reading comes after every chunk is done.

## Amendment 1 Nov 2026 (q)

Seventeenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. docs/DESIGN.md and docs/PREREG.md are unchanged. No file under jobs/ or runs/ was changed by this session's work; stage D is running.

- **kaggle/requirements-runner.txt stays as it is for the rest of stage D, by decision of the author on 1 November 2026.** It pins gymnasium 1.3.0 and minigrid 3.1.0 and nothing else. Their dependencies (cloudpickle, farama-notifications, numpy, typing-extensions, pygame-ce) are resolved against Kaggle's image in each session. The file belongs to the code tag automation-v2, which jobs/manifest.json names as the code stage D runs. Changing it now would compute the units of one campaign under two sets of dependencies.
- **This is the same exposure that caused the halt of amendment (n), now on the Kaggle side.** A new release of a dependency that is not pinned can break a session on install or on import.
- **What happens if it does.** The notebook stops when its pip install fails (kaggle/runner.ipynb, sh), and a session that breaks on import writes no valid result. Either way the collect finds no usable result.json and counts a failure of the chunk (scripts/automation/loop.py, collect and failure). Nothing from that session is integrated. The chunk's committed rows, done-markers and checkpoint are left as they were, and the chunk goes back to partial or pending. The loop halts when one chunk reaches max_failures, 3 in jobs/manifest.json, with STATE-ready text in logs/automation.log. The count is per chunk, across its sessions, and not reset by a session that succeeds. No committed row is lost. Only the work of the broken session itself is lost, which is none if it broke before the runner started.
- **To do before the prereg tag:** freeze kaggle/requirements-runner.txt in the same way as requirements-loop.txt (amendments o and p), with every package at an exact version. Check it with an install that adds nothing, as scripts/automation/check_freeze.sh does for requirements-loop.txt, and include it in the code tag of the confirmatory campaign.
- **Next:** stage D runs on; its reading comes after every chunk is done. The freeze of kaggle/requirements-runner.txt comes before the tag.

## Amendment 1 Nov 2026 (r)

Eighteenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag is not created. No file under jobs/ or runs/ was changed by this session's work; stage D is running, chunk d-013 on its second session (kernel version 37). docs/DESIGN.md and docs/PREREG.md are unchanged. This is a progress count of the automation, as in amendment (m), not a reading of stage D; no search result other than seconds, caps and state was read.

- **Progress report** (34a05df): scripts/stage_d_progress.py run on committed files only; logs/stage_d_progress.log.
- **From the log.** Chunks: 12 done, 1 running (d-013), 26 pending, of 39. 490 rows of 1,560 units; 1,070 units not done. 189 units capped, 120 by the node cap and 69 by the time cap; 301 complete. 21 of 49 games with rows have a capped unit, 15 have every unit capped, and the games with a capped unit hold 0.9467 of all worker seconds. Finished chunks needed 1 session (2 chunks), 2 (5), 3 (4) and 4 (1); wall per chunk from first dispatch to last collect 2.04 h to 32.37 h, median 14.75 h, mean 14.56 h. d-013 has 10 of 40 units done after one session, 8 of them capped.
- **Estimate for the 26 pending chunks, on that basis:** 15.78 days at the mean, 15.98 at the median, 2.21 to 35.07 days at the finished extremes; 44.38 days if every pending unit hit the time cap. The finished chunks hold the first games in name order, not a random draw. The halt of amendment (n) falls in d-013, which is not yet among the finished chunks.
- **Next:** stage D runs on; its reading comes after every chunk is done.

## Amendment 1 Nov 2026 (s)

Nineteenth amendment. The lines above are unchanged. Nothing is registered; the prereg tag and the confirmatory code tag are not created. docs/DESIGN.md and docs/PREREG.md are unchanged. No file under jobs/ or runs/ was changed by this session's work. Stage D runs on, chunk d-013 on kernel version 37, with the file of the code tag automation-v2, which is unchanged (two pins); the notebook installs kaggle/requirements-runner.txt from the tag's worktree, never from main.

- **What stage D's sessions ran on.** No committed file recorded the versions the image supplies. All 550 session entries in stage D's rows name one image, gcr.io/kaggle-images/python@sha256:17b2fc7f27c25c6c2fd4230ec8e66097ab2b89fc88e1e4d6f338b72e1ee0bc3e.
- **The environment probe** (d5777d4), at the author's choice of 1 November 2026: kaggle/envprobe/probe.ipynb, a private notebook of its own, ericsom/horizon-envprobe, apart from the runner and the campaign. It was pushed once from the laptop by scripts/automation/envprobe.py (kernel version 1). It records the image and Python, installs the tag's kaggle/requirements-runner.txt with the runner's own command, records every package the file needs as installed, and imports gymnasium and minigrid. It runs no search.
- **What it found** (logs/envprobe.log, e4ce0f1):
  - the same image as every stage D session;
  - CPython 3.13.15;
  - cloudpickle 3.1.2, farama-notifications 0.0.6, gymnasium 1.3.0, minigrid 3.1.0, numpy 2.1.3, pygame-ce 2.5.8 and typing-extensions 4.16.0;
  - the install changed three packages only: gymnasium (1.2.0 in the image), minigrid and pygame-ce (absent).
  pygame-ce, the one package pip chose, has had 2.5.8 as its latest release since 9 August 2026 (PyPI), before stage D began, so stage D's sessions had the same set.
- **The freeze** (e8210da): kaggle/requirements-runner.txt now pins those 7 packages, with the image and Python named in its header. scripts/automation/check_runner_freeze.py checks, from committed files and PyPI:
  - every line is an exact pin;
  - every pin has a wheel for CPython 3.13 manylinux x86_64;
  - every requirement each wheel declares is pinned at a version it allows;
  - every module outside the standard library that scripts/automation imports (numpy, gymnasium, minigrid) comes from a pinned package;
  - the pins equal the probe's versions.
  OK (logs/check_runner_freeze.log). The control, the same check on the file before the freeze, fails 8 times: the five packages pip chose and numpy imported directly (logs/check_runner_freeze_control.log). The empty install of check_freeze.sh does not apply, because the runner installs into the image and the laptop has no Python 3.13.
- **The loop test** (e8c62b2): its fake sessions run the notebook with the project's interpreter, so the new pins would have put numpy 2.1.3 over the 2.4.3 of requirements.txt. Each scenario now gets a requirements-runner.txt with comments only, which the notebook skips. OK (logs/test_loop.log), with the project environment unchanged.
- **What the freeze does not cover.** The image itself and its Python: if the confirmatory campaign runs on a different image, the pins hold but the rest of the image does not. Whether that image can be pinned through the notebook's metadata has not been checked.
- **Next:** stage D runs on; its reading comes after every chunk is done. The confirmatory code tag, when it is cut from main, carries this file. The item of amendment (q) is done.

## Amendment 1 Nov 2026 (t)

Twentieth amendment. The lines above are unchanged. Nothing is registered; the prereg tag and the confirmatory code tag are not created. docs/DESIGN.md and docs/PREREG.md are unchanged. No file under jobs/ or runs/ was changed by this session's work, and kaggle/kernel-metadata.json is unchanged; stage D runs on, chunk d-013 on kernel version 37.

- **The question** (amendment s): can the notebook's metadata pin the Kaggle image?
- **What the pinned kaggle tool sends.** kaggle 2.2.4 (kaggle/api/kaggle_api_extended.py, kernels_push) reads two keys of kernel-metadata.json and sends them with every push. docker_image_pinning_type must be "original" or "latest". docker_image, in kagglesdk's words, is "Which docker image to run with. This must be one of the Kaggle-provided, known images", given as gcr.io/kaggle-images/python@sha256:<digest>, the form in which stage D's rows record the image.
- **What the server holds now.** A read-only kernels pull gives docker_image gcr.io/kaggle-images/python@sha256:17b2fc7f27c25c6c2fd4230ec8e66097ab2b89fc88e1e4d6f338b72e1ee0bc3e for the runner and for the probe's first version. That is the only digest in the committed rows. Other notebooks on the account report two older public images, 81b1e7c4... and dafd4ce5....
- **The test** (scripts/automation/envprobe.py --docker-image, 01f72eb; log d105aaf). The probe was pushed as kernel version 2 with docker_image set to gcr.io/kaggle-images/python@sha256:81b1e7c4b4f0f2a7e0a33943c95754b1b7af6b30d65221633a284b6b601cd84a. The session ran on that image and not on the default (logs/envprobe_pin.log: "the session ran on the image asked for: yes"). The metadata can therefore pin the image, and that older image was still runnable on 1 November 2026. It holds the same CPython 3.13.15, and after the runner's install the same 7 versions as kaggle/requirements-runner.txt, with 859 packages before the install against 860 on stage D's image.
- **Seen, not checked.** A notebook on the account last run at 2026-11-01T01:44Z ran on 81b1e7c4..., while others had run on 17b2fc7f... since at least 2026-10-22. This fits Kaggle keeping a notebook on the image it first ran on. kernels pull does not report the pinning type, so this is not known.
- **Not known:** how long Kaggle keeps an image runnable, and what a later push without docker_image does after a pinned one.
- **What is not changed, and why.** The loop builds the runner's metadata from kaggle/kernel-metadata.json on main at every dispatch (scripts/automation/loop.py, prepare_kernel), not from the code tag. Adding docker_image there would pin stage D's own sessions from the next dispatch on. That would hold stage D on the image of all its sessions so far, but it changes the running campaign, so it is the author's decision. The probe's last version, private and apart from the campaign, is left on 81b1e7c4....
- **Next:** stage D runs on; its reading comes after every chunk is done. For the confirmatory campaign, docker_image in the runner's metadata can name the image. Whether it does, and which image, is for the author before the tag.

## Amendment 1 Nov 2026 (u)

Twenty-first amendment. The lines above are unchanged. Nothing is registered; the prereg tag and the confirmatory code tag are not created. docs/DESIGN.md and docs/PREREG.md are unchanged. No file under jobs/ or runs/ was changed by this session's work.

- **Stage D's image is not pinned, by decision of the author on 1 November 2026.** kaggle/kernel-metadata.json stays as it is, with no docker_image key. git diff shows it unchanged against the code tag automation-v2 and against 01858fa, the halt of this morning; its last change is 59ddd88. Reasons:
  1. All 550 session entries in stage D's rows name one image, gcr.io/kaggle-images/python@sha256:17b2fc7f27c25c6c2fd4230ec8e66097ab2b89fc88e1e4d6f338b72e1ee0bc3e.
  2. The evidence of amendment (t) suggests that Kaggle keeps a notebook on the image it first ran on.
  3. Changing the metadata of a running campaign adds a risk larger than the one it removes.
- **The loop after the decision.** jobs/state.json: not halted, 0 consecutive crashes, d-013 dispatched as kernel version 37 (pushed 2026-11-01T14:57:44Z). kaggle kernels status at 17:49Z: RUNNING. The workflow's ticks at 16:29Z and 16:59Z succeeded, and the one of 17:30Z was running.
- **A change of image during stage D would be visible.** Every session entry of a row records Kaggle's own environment variables (kaggle_env, scripts/automation/jobs.py at automation-v2), the image digest KAGGLE_DOCKER_IMAGE among them. The row schema requires kaggle_env (scripts/automation/schema.py); the digest is there because Kaggle sets it, and all 550 session entries so far carry it. If stage D's rows name more than one image when every chunk is done, that is stated as a limit of the development data, with the chunks and units each image ran.
- **Before the confirmatory code tag is cut**, docker_image is set in the runner's metadata, kaggle/kernel-metadata.json, with the image chosen at that point.
- **Next:** stage D runs on; its reading comes after every chunk is done, and it counts the images the rows name.
