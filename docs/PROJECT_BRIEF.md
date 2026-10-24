# HORIZON: project brief

Written 24 October 2026 for a reader who has never seen the earlier project. Registration status: not yet registered. Nothing in this file is a result.

## 1. The question

Some game-playing agents see only the screen. They are told when a level or the game ends, and nothing else: no score, no list of objects, no text, no access to the game's code. Many such agents also carry built-in assumptions about how games work, for example that one object on the screen is the player, that each arrow key moves it one cell, that walls are fixed, and that a level ends when the player reaches a particular place.

HORIZON asks what decides whether such an agent completes the first level of a game it has not seen:

- **H1, mechanics match.** The agent completes the first level where the game's true mechanics agree with the agent's assumptions, and fails where they do not.
- **H2, search size.** The agent completes the first level where the search the level presents is small (few reachable states, short solutions, little branching), whatever the mechanics.

The two can be told apart because they make different predictions on games whose mechanics fit the agent's assumptions but whose first level is large, and on games whose mechanics do not fit but whose first level is small.

## 2. Where the question comes from

The earlier project (study 1) built an instrument, the assumption census, that tried to read five mechanical assumptions of a game (A1 to A5) from frames, and registered a test of whether the census score predicts first-level completion. The census failed its registered validity test against truth tables read from each game's source code, so study 1 could not say whether mechanics predict success at all. docs/LESSONS_FROM_STUDY1.md gives the full account, with a citation to a study-1 file for every statement.

The five assumptions, as study 1 defined them against source code:
- A1, input coupling: the actions change the picture, and different actions change it differently.
- A2, one controlled object: exactly one object's displacement is a fixed function of the action.
- A3, lattice motion: each movement action shifts that object by a constant step whenever it is not blocked.
- A4, blocking by a fixed obstacle set: every move with no effect is explained by a fixed set of obstacles that changes only through the agent's own actions.
- A5, place goal: a level ends when the controlled object enters a particular place, with no other condition at that moment.

## 3. The plan

- **Phase 0.** Read study 1 and write down its lessons (docs/LESSONS_FROM_STUDY1.md); set up this repository.
- **Phase 1, the oracle test (exploratory; the pilot for the registration).** Recompute study 1's prediction test on its own rows, with one change: each game's mechanics vector is the truth table's A1 to A5, exact mechanics, in place of the census. Add the first search features that need no simulator. The result decides which hypothesis the registered study is built to test against the other.
- **Phase 2, automation.** A manifest of chunks, a Kaggle CPU notebook that runs the next chunk, and a scheduled GitHub workflow that collects and commits each chunk's rows, proven by a dry run with a dummy job before any experiment.
- **Phase 3, the study design and registration draft.** Confirmatory suites whose mechanics are written as declarative descriptions (so truth tables come from the description) and whose simulators can clone states (so search quantities can be computed): Griddly, py-vgdl or the GVGAI framework, and MinAtar are to be evaluated for cost on Kaggle CPU. The registered test compares, per agent and suite, how well the mechanics vector and the search quantities predict first-level completion, with thresholds, a pilot gate and an outcome table fixed before any confirmatory run.

Venues, fixed in advance by outcome (project rule R5): Support goes to IEEE Transactions on Games, with the Journal of Artificial Intelligence Research as the alternative if the result is broad; Refute goes to this repository and a preprint on Zenodo.

## 4. The earlier project

- Repository: https://github.com/rahul-k-mishra/arc3-frame-only-study (local copy D:\Research\arc3\repo, read-only for this project).
- Tags, with the commit each points to (study 1 docs/STATE.md, amendments (d), (h), (m), (r), (s) and (x)):

| tag | commit | what it marks |
|---|---|---|
| prereg-v1 | 19f2a9f | the registered protocol v1 |
| prereg-v1.1 | 8b2b2b9 | v1.1, after the pilot; the confirmatory runs ran under it |
| prereg-v1.2 | 66e5606 | v1.2, written after the outcome |
| manuscript-v1 | 895f3ac | the preprint |
| jote-submission-v1 | 8f99b24 | the Journal of Trial and Error submission |
| jagi-submission-v1 | 29f1238 | the Journal of Artificial General Intelligence submission |

- Registrations: https://osf.io/2znhw (v1) and https://osf.io/zu5vq (v1.1).
- Zenodo: the preprint, DOI 10.5281/zenodo.23375065 (https://doi.org/10.5281/zenodo.23375065); the supplement, version 2 of the same record, DOI 10.5281/zenodo.23614519 (https://doi.org/10.5281/zenodo.23614519).
- Journal of Artificial General Intelligence: submission 256, made on 24 October 2026 (http://jagi.mindmakers.org/index.php/jagi/author/submission/256).

## 5. The author

Rahul Kumar Mishra, single author, Independent Researcher, Ranchi, Jharkhand, India, ORCID 0009-0004-9671-4055.
