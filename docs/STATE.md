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
  - The author's own test run: an expectation in the test was wrong (balanced accuracy of an all-false prediction is 0.5 under study 1's function, not undefined); the test was corrected, not the script.
  - requirements.txt now pins numpy 2.4.3 and matplotlib 3.10.9, the versions in D:\python\3.11.9.
- **Not yet run on study-1 data.** No oracle number exists. The author runs the script and pastes the console; docs/oracle/READING.md follows the paste.
