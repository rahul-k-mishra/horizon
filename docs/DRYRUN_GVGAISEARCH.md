# The dry run of the kind gvgaisearch

This document reports the test of the GVGAI search kind through the whole loop on Kaggle, as rule R8 requires before the pilot search is launched. It states no study result, registered or exploratory. Every figure is printed by scripts/automation/gvgaisearch_report.py from committed files (console in logs/gvgaisearch_dryrun_report.log). The manifest is jobs/gvgaisearch_dryrun/manifest.json, written by scripts/make_gvgai_manifests.py (logs/make_gvgai_manifests.log).

## What ran

One chunk, gd-01, of three GVGAI units on a pool of 4 workers, with the extended state key, the seen cap of 2,000,000 and sessions of 180 seconds of work:
- corridor, level 0, a hand-worked level with a win three moves away;
- corridor, level 1, an avatar boxed in, with one state;
- boxroom, level 0, slowed to 0.5 s per 5 expansions so that it could not finish in one session and had to be checkpointed and resumed.

The games are the synthetic test games under scripts/automation/gvgai_testgames, not GVGAI games of the study.

## The first attempt, under automation-v4: failed

- **Kernel versions 114, 115 and 116** each ended with FileNotFoundError and no unit done. The loop counted three failures and halted at 2026-11-24T00:28:06Z, as it is built to (logs/automation.log). Between versions 114 and 115 the push was refused 12 times for the account's limit of five CPU sessions and deferred, with no failure counted.
- **The cause.** The runner starts each unit in its own worker process, and every worker set up GVGAI in the same cache folder at the same time: each downloaded the JDK to one shared .part file and compiled GVGAI into one shared .part folder, so one worker's rename or removal took the file away from another. The image probe had not met this because it runs in one process.
- **Reproduced on the laptop** by scripts/automation/test_gvgai_setup_race.py: three workers on one empty cache folder without the lock, two of three fail (PermissionError on Windows, the same race); with the lock, three of three succeed and return the same JDK and classes folder (logs/test_gvgai_setup_race.log).
- **The fix** (d776f17): scripts/automation/sim_gvgai.py downloads the JDK and compiles GVGAI under an exclusive lock on a file in the cache folder (setup_lock). Nothing else changed. kaggle/requirements-runner.txt is the same at automation-v4 and automation-v5, so the image probe of kernel version 3 (logs/envprobe_v4.log) and the freeze check (logs/check_runner_freeze.log) hold for both. The code tag **automation-v5** is cut on d776f17; the failed attempt's manifest is kept at jobs/archive/gvgaisearch-dryrun-v4/manifest.json.

## The second attempt, under automation-v5: done

- **Kernel version 117** reached the runner 32 seconds after its own work deadline: cloning and installing took longer than the 180 seconds of work a dry-run session has. It ran no unit; the loop counted one failure ("a partial session made no progress"), as it is built to.
- **Kernel version 118** completed both corridor units and stopped boxroom at the deadline with 784 states expanded; the loop committed the checkpoint (dd502b1).
- **Kernel versions 119, 120 and 121** each resumed boxroom from the committed checkpoint and stopped it again at the deadline, at 1,158, 1,896 and 2,418 expanded (66037e0, a75cad8, 3980966).
- **Kernel version 122** resumed it and completed it; the loop committed the row and removed the checkpoint (4fcb0e4).

## The rows against the laptop

Every row passes the schema horizon.search.v3, and each count equals what the same level gave on the laptop in scripts/automation/test_gvgaisearch.py (logs/test_gvgaisearch.log):

| unit | states seen | expanded | shortest solution | seen at first win | expanded at first win | sessions |
|---|---|---|---|---|---|---|
| corridor, level 0 | 4 | 3 | 3 | 4 | 3 | 1 |
| corridor, level 1 | 1 | 1 | none | none | none | 1 |
| boxroom, level 0 | 2,900 | 2,756 | 2 | 9 | 3 | 5 |

## What this shows

The loop dispatched, pushed, collected and committed the kind gvgaisearch on Kaggle under automation-v5. The runner installed the pinned packages and the pinned JDK, compiled GVGAI, searched with the extended key, checkpointed a unit in progress, resumed it four times from committed checkpoints, and wrote rows equal to the laptop's. The failure of the first attempt was found by this dry run, before any pilot unit ran.
