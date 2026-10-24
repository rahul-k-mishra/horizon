# The dry run of the kind devsearch

This document reports the test of stage D's job kind (docs/AUTOMATION.md, Section 5.1) through the whole loop on Kaggle, before the stage itself is launched. It states no study result, registered or exploratory. Every figure is printed by scripts/automation/devsearch_report.py from committed files (console in logs/devsearch_dryrun_report.log). The code the sessions ran is the tag automation-v2 (commit afa984c); the manifest was committed in 238b4aa.

## What ran

One chunk, ds-01, of three MiniGrid units on a pool of 4 workers, with stage D's registered caps:
- MiniGrid-Empty-5x5-v0, seed 1000;
- BabyAI-UnlockLocal-v0, seed 1002, large enough for the effective-horizon bound to do real work;
- MiniGrid-DoorKey-5x5-v0, seed 1000, slowed (10 s per batch of 5 expansions) so that it could not finish within the 180-second session and had to be checkpointed and resumed.

## What happened

- **Kernel version 6** (run devsearch-dryrun-ds-01-20261024T181711Z-cd7c15): Empty-5x5 and UnlockLocal completed; DoorKey stopped at the session deadline with 70 states expanded. The session ended partial. The loop committed the checkpoint in d64ad89: it lists the two units done and DoorKey in progress, in 8 payload files, all in git.
- **Kernel version 7** (run devsearch-dryrun-ds-01-20261024T182531Z-36bf43), on another machine, resumed DoorKey from that checkpoint and completed it. The loop committed the row and removed the checkpoint in 4f88211.
- No failure was counted. The loop's successor runs started each other with no hand-started run after the first.

## The rows against the laptop

Every row passes the schema horizon.search.v2, and each count equals what the same level gave on the laptop in scripts/automation/test_devsearch.py (logs/test_devsearch.log):

| unit | states seen | expanded | shortest solution | effective-horizon bound | sessions |
|---|---|---|---|---|---|
| Empty-5x5, seed 1000 | 23 | 21 | 4 | 14.2242 (k 2) | 1 |
| UnlockLocal, seed 1002 | 4,273 | 4,272 | 11 | 22.5755 (k 1) | 1 |
| DoorKey-5x5, seed 1000 | 112 | 109 | 9 | 12.0923 (k 3) | 2 |

The resumed unit's counts and bound equal those of an uninterrupted search on the laptop, so the multi-unit checkpoint carried the whole search state across machines.

## What it shows

On Kaggle, through the loop, the kind devsearch:
- installed its pinned packages;
- ran units in parallel on a worker pool;
- wrote rows of the new schema with the branching and the effective-horizon bound;
- checkpointed an unfinished unit in a chunk checkpoint with others done;
- resumed it on another machine, and finished with the same counts as the laptop.

The full stage's manifest, jobs/stage_d/manifest.json, is ready and not launched.
