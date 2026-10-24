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
