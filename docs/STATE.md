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
