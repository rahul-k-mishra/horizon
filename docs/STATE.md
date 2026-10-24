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
