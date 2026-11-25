# The dry run of the kind gvgaiagent

This document reports the test of the GVGAI agent kind through the whole loop on Kaggle, as rule R8 requires before any pilot or confirmatory agent run. It states no study result, registered or exploratory. Every figure is printed by scripts/automation/gvgaiagent_report.py from committed files (console in logs/gvgaiagent_dryrun_report.log). The manifest is jobs/gvgaiagent_dryrun/manifest.json, written by scripts/make_gvgaiagent_dryrun_manifest.py (logs/make_gvgaiagent_dryrun_manifest.log) and copied unchanged to jobs/manifest.json (8e75dee).

## What ran

One chunk, a-01, of 36 units on a pool of 4 workers, with sessions of 600 seconds of work, under the code of commit e608f7577820569fef94bb40b89db19839a8cda3 (no tag is cut in this session; the runner checks out the commit the manifest names). The games are the synthetic test games under scripts/automation/gvgai_testgames, not GVGAI games of the study:
- 12 units of 300 actions, N, R, I1 and Rand with seed 1000, on allwin level 0 (every action wins), corridor level 1 (no action can win) and corridor level 0;
- 24 units with a budget of 10,000,000 actions and a cap of 120 seconds, N, R, I1 and Rand with seeds 1000 to 1005 on corridor level 1, more than one session's work, so that the chunk had to end partial, be checkpointed and be resumed.

kaggle/kernel-metadata.json named stage D's image (docker_image), so this dry run was also the runner's first session under that pin.

## The sessions

- The push was refused twice for the account's limit of five CPU sessions and deferred, with no failure counted.
- **Kernel version 125** (2026-11-25, 11:22Z pushed) ran 24 units: the 12 short units and the first three seeds of the capped units. Then it stopped at its deadline, because "12 agent units do not fit before it", and wrote checkpoint 1. The loop committed the rows, the done-markers and the checkpoint (57cfdd4).
- The second push was refused three times and deferred, with no failure counted.
- **Kernel version 126** (13:11Z pushed) resumed from checkpoint 1 with 24 units done and ran the other 12. The loop committed the rows and removed the checkpoint (b8604a4). The chunk is done after 2 attempts and 0 failures.

## The rows against what is known without Kaggle

All 36 rows pass the schema horizon.agent.v2. Every session entry of every row names the image asked for, gcr.io/kaggle-images/python@sha256:17b2fc7f27c25c6c2fd4230ec8e66097ab2b89fc88e1e4d6f338b72e1ee0bc3e.

| units | expected | rows as expected |
|---|---|---|
| allwin level 0, N, R, I1, Rand | by hand: 300 actions, 300 level ends, first at action 1 | 4 of 4 |
| corridor level 1, N, R, I1, Rand | by hand: 300 actions, no level end | 4 of 4 |
| corridor level 0, N, R, I1, Rand | the laptop's rows (logs/test_gvgaiagent.log, part 2): levels 80, 28, 28 and 15, first level end 22, 14, 14 and 15 | 4 of 4 |
| corridor level 1, 10,000,000 actions, 120 s cap | cut by the cap, 0 levels, at most 123 s | 23 of 24 |

**The one capped unit not as expected** is I1 on seed 1003. It was cut by its cap with 0 levels, but the row's seconds are 135.165. I1's own play clock, study 1's timer, which the cap stops, read 120.0 s, so 15.165 s of the unit lay outside the timed play. The same happened to the first I1 unit of the first session (allwin level 0, 12.62 s outside a play of 8.14 s). Every other I1 unit had at most 1.576 s outside its play. N, R and Rand were at most 0.285 s over the cap. Both units ran in the first minutes of their session (the session consoles, as the report prints them). The cap stops I1's play when it should. The unit's wall time can exceed the cap by the setup that comes before study 1's timer starts. The runner's checkpoint reserve of 300 s covers such an overrun in a session.

The capped units also show how much the speed of a Kaggle session varies. In 120 s, I1 played 8,551 to 8,675 actions in the first session and 4,994 to 5,076 in the second. N, R and Rand were slower by a similar factor in the second session (the rows' actions in the report).

## The pins after the dry run

The image probe of e608f75 (logs/envprobe_agents.log) played N, R, I1 and Rand on corridor level 0 on stage D's image and got the laptop's rows. It found the 15 frozen files of study 1 with their registered blob hashes. It also found that the agents' process imports four packages the pins did not name: brotli, chardet, PySocks and simplejson, which requests and urllib3 load when installed. The image holds them, so the dry run used the image's versions. Commit a1d370b pins the four at those versions, and nothing else changes in the code. The probe of a1d370b (logs/envprobe_agents_v2.log) gets the same four rows, and scripts/automation/check_runner_freeze.py ends OK on it (logs/check_runner_freeze.log): 31 pins equal the image's versions and every distribution the agents import is pinned.

## What this shows

The loop dispatched, pushed, collected and committed the kind gvgaiagent on Kaggle. The runner checked study 1's frozen files before every unit, played N, R, I1 and Rand, and wrote horizon.agent.v2 rows equal to the hand-worked and laptop rows. It stopped the capped units by their cap, ended a session partial with a checkpoint, and resumed and completed the chunk in the next session. One capped I1 unit ran 12.165 s past the report's 3 s allowance; the cause is time outside I1's own play clock, as above.
