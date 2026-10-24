# The dry run of the HORIZON loop

This document reports the test of the automation with dummy work that project rule R8 requires before any experiment. It states no study result, registered or exploratory. Every figure below is printed by one of two scripts, from committed files and GitHub's own run records: scripts/automation/dryrun_report.py (console in logs/dryrun_report.log) and scripts/automation/actions_minutes.py (console in logs/actions_minutes.log, raw records in runs/dryrun/actions_runs.json). The design is docs/AUTOMATION.md; the code the Kaggle sessions ran is the tag automation-v1 (commit 59ddd88).

## 1. What ran, and where

The manifest jobs/manifest.json holds three chunks (AUTOMATION.md, Section 12). All three ended done, on 24 October 2026, each session on a different Kaggle machine (host names in the log):

| Chunk | Kind | Kaggle kernel version | Run nonce | Outcome | Session ended (UTC) |
|---|---|---|---|---|---|
| dry-01 | agent | 2 | dryrun-dry-01-20261024T153044Z-9b86d2 | done | 15:33:01 |
| dry-02 | search | 3 | dryrun-dry-02-20261024T162730Z-a1675a | partial | 16:32:47 |
| dry-02 | search | 4 | dryrun-dry-02-20261024T163347Z-620106 | done | 16:36:28 |
| dry-03 | agent | 5 | dryrun-dry-03-20261024T163736Z-9ff09c | done | 16:39:53 |

Kernel version 1 was the registration push made by hand (AUTOMATION.md, Section 12, step 3). Its session found no dispatch and wrote nothing, as designed. It also showed that the notebook has internet and can clone the repository and check out the tag.

The console of every session is committed in logs/kaggle/ under the chunk and kernel version. Every row passed its schema check, and each done-marker names the kernel version that wrote it.

## 2. The forced checkpoint: dry-02

dry-02's first unit needs about seven minutes of work against a five-minute session, so the session had to stop, checkpoint, end partial and be resumed.

- **Kernel version 3** (run dryrun-dry-02-20261024T162730Z-a1675a) took checkpoints 1 to 7 during the session. It stopped at its deadline inside the search unit dry-02-graph-a and ended partial with no unit done.
- **Checkpoint commit dc4bcde** "Loop: dry-02 partial (kernel version 3)", made by the loop at 16:33:46Z, holds checkpoint 7. It has the frontier head and tail and five spill files, each a few hundred bytes, committed to git. It also has the visited set, visited.u64.gz, 156,459 bytes. That is over the dry run's commit limit of 64 KB, so it was kept as an asset of the release ckpt-dryrun, and the checkpoint records its sha256 and address.
- **Kernel version 4** (run dryrun-dry-02-20261024T163347Z-620106) resumed from checkpoint 7 of the earlier run, as its console shows. It took checkpoints 8 and 9, completed graph-a, then ran graph-b, and ended done.
- **Commit 6c79930** "Loop: dry-02 done (kernel version 4)" wrote the two rows and their markers and removed the checkpoint. The release now holds no asset.

The row of graph-a lists both sessions. It counts 28,000 states seen with the goal at depth 48, the same as an uninterrupted enumeration of the same graph computed by the report script. graph-b stopped at its node cap: 500 expansions against a cap of 500. It is recorded as capped by "node", with 615 states seen and 115 left on the frontier.

## 3. Failures

One failure was counted, and the loop handled it as designed. At 15:27:26Z the first tick on GitHub failed to push the notebook: "Authentication required to call the Kaggle API". That counted as failure 1 of 3 for dry-01. The cause was the credential form (AUTOMATION.md, Section 8). It was fixed in commit c696ea6, and dry-01 then ran on attempt 2. No other failure was logged.

## 4. The loop's commits

The loop made 14 commits under the name horizon-loop, from aa86001 "Loop: dispatch dry-01 (attempt 1)" to 7bf137e "Loop: dry-03 done (kernel version 5)". Each is listed in logs/dryrun_report.log. No commit in the repository has a message of more than one line.

## 5. The two triggers

The cron of the workflow never fired during the dry run. GitHub's run records hold 7 runs of the workflow, all started by workflow_dispatch and none by the schedule. Six were started by hand from the author's account. As a result dry-01, finished on Kaggle at 15:33:01Z, was collected only at 16:27:28Z (commit badc990), by a manual run.

The second trigger, a successor started by the workflow itself (AUTOMATION.md, Section 7), was committed in db58d22 and started once by hand, as run 40112453074, at 16:37:57Z. That run ticked, found dry-03 running on kernel version 5, and slept until that session was due to end. Its step "Start the next tick" lasted 389 s by GitHub's records, an upper bound (Section 7). It then started run 40112968801, which GitHub records as started by github-actions[bot]. That run collected dry-03 and found the manifest complete. It printed "no successor: the loop has nothing left to do" and started nothing more, so the loop stopped by itself.

## 6. Elapsed time

From the first dispatch (15:27:24Z) to the collection that left every chunk done (16:44:55Z): 1 h 17 min 31 s. From the first notebook push that reached Kaggle (15:30:48Z): 1 h 14 min 07 s. Most of it was the wait for a cron run that never came (Section 5).

## 7. GitHub Actions minutes

From logs/actions_minutes.log:
- **A tick** (the step Tick): median 6.5 s, largest 12 s, over 6 runs.
- **A run that does not wait:** median job 18.5 s, which is 1 minute when rounded up to whole minutes. The run that found the manifest complete took 15 s.
- **A month with nothing to do** (manifest complete or loop halted): the cron's 1,440 runs would use 1,440 minutes.
- **A month of a campaign in flight:** the one link of the chain that waited used 7 minutes, rounded up, over 6.7 wall-clock minutes, which is 1.050 billed minutes per minute. Over 30 days that is 45,360 minutes. This rests on a single link and is an estimate.

The repository is public, so GitHub charges none of these minutes. On a private repository with the Free plan's 2,000 minutes a month, the chain could not run a campaign, and the laptop fallback of AUTOMATION.md, Section 11 would be needed.

GitHub's step records were incomplete for the two runs of Section 5: the sleeping step had a start but no end, and the last run had no step records at all. The script handles this as its docstring states; job times, which were complete, are used for every total.

## 8. What the dry run shows

The loop went round the whole cycle with dummy work. It dispatched each chunk, pushed the notebook under the author's Kaggle account, and collected and checked each session's output. It committed rows, markers, checkpoints and consoles, resumed a chunk across two sessions from a checkpoint kept partly in git and partly in a release, recorded a capped search, counted a failure and recovered from it, started its own successor, and stopped when the manifest was complete. The halt after three failures was shown only in the local test (scripts/automation/test_loop.py), not on GitHub.
