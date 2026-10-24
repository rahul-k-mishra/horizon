# AUTOMATION: how HORIZON's runs are made without anyone at the keyboard

Written 24 October 2026 (Phase 2). This file is the design of the machinery that runs HORIZON's jobs. It contains no result. The values marked "registered at the study's tag" are design values: they become binding only when docs/PREREG.md is tagged, and they are copied there unchanged or changed only before the tag.

## 1. The idea in plain words

The work is cut into small pieces. A list in the repository, the manifest, says which pieces exist and which are finished. A free Kaggle computer runs one piece at a time. A small program on GitHub's servers wakes up every 30 minutes, looks at Kaggle, and when a piece has finished, it collects the result, checks it, saves it into the repository, and starts the next piece. The author's laptop is not needed and can be closed. Every result, every log and every half-finished piece is saved in the repository, so nothing lives only on a machine that might disappear.

A piece may be too long for one Kaggle session. It then saves where it got to (a checkpoint), stops cleanly before Kaggle would stop it, and the next session picks up from that point. A piece counts as finished only when all its work is done, never because a session ended.

## 2. The pieces

| file | what it is |
|---|---|
| jobs/manifest.json | the campaign: its settings, one line per chunk (kind, status, attempts, failures, sessions) and one line per unit of work (suite, game, agent, seed, chunk, status) |
| jobs/state.json | the chunk now running on Kaggle, if any (with its run nonce, kernel version and the manifest-entry hash it was dispatched with), and the halt flag |
| jobs/lock.json | exists only while a chunk is dispatched; names the holder and when the lock expires |
| kaggle/runner.ipynb, kaggle/kernel-metadata.json | the Kaggle notebook: CPU, no GPU, internet on, private; the metadata holds the placeholder KAGGLE_USERNAME, filled in at push time |
| kaggle/requirements-runner.txt | pinned packages the notebook installs before a chunk (none for the dry run) |
| scripts/automation/runner.py | what the notebook runs: one chunk, with deadline and checkpoints |
| scripts/automation/jobs.py | the two job kinds, search and agent |
| scripts/automation/schema.py | the two row schemas and the only two loaders an analysis may use |
| scripts/automation/loop.py | one tick of the loop: poll, collect, verify, commit, dispatch |
| .github/workflows/horizon.yml | runs one tick every 30 minutes and on demand |
| logs/automation.log | one line per tick that acted; STATE-ready text when the loop halts |
| logs/kaggle/<chunk>__v<version>.log | the console of every Kaggle session |
| runs/<campaign>/search/, agent/, done/, checkpoints/ | rows, done-markers and the checkpoint of each unfinished chunk |

**Chunks and units.** A unit is the smallest piece of work that produces a row: for a search job, one first level of one game; for an agent job, one agent on one game and one seed. A chunk is a list of units of one kind, sized so that it can finish inside one session; a chunk never mixes the two kinds (common.check_manifest refuses a manifest that does). A chunk's status is pending, running, partial, done or failed.

## 3. The Kaggle session and its deadline

The notebook clones the public repository (branch main, which holds the manifest, the state, the rows and the checkpoints), checks out the code at the tag named in the manifest ("code_tag") into a separate folder, installs the pinned packages, and runs runner.py. The code that runs is therefore fixed by a tag, while the state it reads is the latest commit.

**The deadline.** The notebook records its start time T0 in its first line. The runner stops starting new work at T0 + work_seconds, and must have written and verified its checkpoint by T0 + work_seconds + checkpoint_reserve_seconds. Registered at the study's tag:

| setting | value | meaning |
|---|---|---|
| work_seconds | 37,800 s (10 h 30 min) | no new work after this |
| checkpoint_reserve_seconds | 900 s (15 min) | time kept to write, re-read and hash the checkpoint and pack the output |
| platform limit assumed | 43,200 s (12 h) | Kaggle's session limit for CPU notebooks as commonly stated; Kaggle's own documentation page could not be read when this was written, so the margin below is kept wide |
| margin to the platform limit | 4,500 s (1 h 15 min) | between the latest possible end of the runner (10 h 45 min) and 12 h |

So every chunk ends inside 11 hours, as project rule R4 requires, and the notebook is never stopped by the platform. A unit of the agent kind starts only if its own wall-clock cap still fits before the deadline. A search unit checks the deadline after every batch of expansions.

The dry run uses work_seconds 300 and checkpoint_reserve_seconds 120 (jobs/manifest.json), so that one of its chunks is forced to stop and resume.

**What the notebook leaves.** /kaggle/working/result.json (status, chunk, run nonce, manifest-entry hash, rows with their sha256, checkpoint files with their sha256, units done, the deadline and whether the runner ended before its hard stop), /kaggle/working/bundle.tar.gz (the rows and the checkpoint) and /kaggle/working/console.log. If anything inside the runner fails, it still writes result.json with status "failed" and the traceback, and exits normally, so the evidence reaches the loop.

## 4. Resumability

### 4.1 Level 1: between chunks

The manifest holds each chunk's status. A unit is done when its done-marker exists under runs/<campaign>/done/ and the row it names has the sha256 the marker records (common.unit_done). The loop computes a chunk's completion itself, from the markers, and never takes the notebook's word for it.

### 4.2 Level 2: inside a chunk

Every job writes a checkpoint at a registered interval, in seconds and in work units (whichever comes first), and once more when it stops at the deadline. The checkpoint is runs/<campaign>/checkpoints/<chunk_id>/checkpoint.json with its payload files:

| field | content |
|---|---|
| schema | horizon.checkpoint.v1 |
| campaign, chunk_id, kind | which chunk |
| entry_hash | sha256 of the manifest entry: campaign, code tag, chunk, kind, its units and the parameters of its kind (common.chunk_entry_hash) |
| seq | checkpoint number within the chunk |
| units_done | units of the chunk with a row |
| unit_in_progress | null, or the unit being searched and its search state (below) |
| payload | every payload file with its sha256 and size, and where it is kept: "git" (committed beside checkpoint.json) or "release" (an asset of the GitHub release ckpt-<campaign>, with its URL) |
| run_nonce, written_at | which session wrote it, and when |

**Search job.** The checkpoint holds the whole breadth-first state: the frontier in three parts (head, the spill files in order, tail, which together keep first-in-first-out order), the visited set as sorted 64-bit hashes (visited.u64.gz), the counts so far, the seconds already spent, and the sessions that worked on the unit. Registered interval: every 600 s or every 250,000 expansions. Resume rule: the runner fetches the checkpoint (from git, or from the release URL), checks that its chunk, kind and entry_hash equal the manifest entry and that every payload file has its recorded sha256, rebuilds the frontier and the visited set, and continues expanding; the counts and the seconds spent carry over, so the caps of Section 6 apply to the unit's whole life, not to one session.

**Agent job.** The smallest resumable unit is the seed. The agents of HORIZON hold internal state (graphs, learned step vectors, hash tables) that is not guaranteed to serialize and reload into identical behaviour, so a seed in progress is not checkpointed. Instead a seed starts only if its registered wall-clock cap fits before the session deadline, so no seed is ever cut by a session, and the checkpoint is written after every seed (units_done; unit_in_progress null). Resume rule: seeds with a done-marker are skipped, and the next seed starts from its beginning. A seed that runs past its own cap is recorded with cut_by_cap true, as a fact.

**Ending partial.** When the deadline comes before the chunk is done, the runner writes the checkpoint, re-reads it and checks every hash, marks the result "partial" with the units done and the work done, and exits. The loop commits the checkpoint like any other output and dispatches the same chunk again (a partial chunk comes before any pending chunk). A partial session that made no progress (no new unit done and no search nodes added since the last checkpoint) counts as a failure.

**Checkpoints that are too large for git.** A payload file larger than payload_commit_limit_bytes (registered at the study's tag: 50,000,000 bytes, under GitHub's 100 MB file limit) is uploaded by the loop as an asset of the release ckpt-<campaign>, and checkpoint.json records its URL and sha256. The repository is public, so the notebook downloads it without a credential. When the chunk is done, its checkpoint folder is removed from the repository and its release assets are deleted; the rows and markers are what remain. The dry run sets the limit to 65,536 bytes so that this path is exercised.

## 5. Two job kinds, two schemas

**search** enumerates the first level of a game from the simulator, with state cloning, breadth first, and runs no agent. It writes one row per game and level, schema horizon.search.v1, under runs/<campaign>/search/. The row holds the counts (states seen, states expanded, depth reached, frontier left, shortest solution length if the goal was reached, successors produced, the largest number of spill files), the caps in force, whether the search is complete or capped and by which cap, the seconds spent, and the sessions that worked on it.

**agent** runs one agent on one game and seed. It writes one row per unit, schema horizon.agent.v1, under runs/<campaign>/agent/. The row holds the outcome (level 1 completed, levels) and, apart, agent_stats: what the agent itself did.

**No feature may be computable only after an agent runs.** The two schemas share only identity fields (schema, campaign, unit, chunk, suite, game, sessions, time written); every other field belongs to exactly one schema, and a row with any field outside its schema fails validation (schema.validate_search_row, validate_agent_row), so the loop refuses to commit it. An analysis reads features only through schema.load_features, which accepts search rows only, and outcomes only through schema.load_outcomes, which returns the two outcome fields of an agent row and nothing else. agent_stats is never returned by any loader. This rule exists because the oracle test found that measures read out of an agent's own runs (its states and its actions to the first level end) separate completing from non-completing games largely through the censoring of runs that never ended level 1 (docs/oracle/saturation.md); such measures are not available before an agent runs and are not features.

## 6. The search job: caps, spill and the capped-game rule

Registered at the study's tag (values per unit, summed over all sessions that work on it):

| cap | value | why |
|---|---|---|
| node cap | 5,000,000 states expanded | the visited set then needs 40 MB as 64-bit hashes; a checkpoint stays small enough to commit or to upload |
| wall-clock cap per game | 14,400 s (4 h), summed over sessions | at most a little over one third of a session's work time per game |
| memory ceiling | 24 GiB resident memory (25,769,803,776 bytes), read from /proc/self/status after every batch | leaves room under a Kaggle CPU session's memory (about 30 GB) for the interpreter and the simulator |
| frontier spill | the in-memory frontier tail is written to a compressed file on disk when it reaches 1,000,000 entries | the frontier then never holds more than about two such blocks in memory |

**What is written when a cap is hit.** A row, not a gap: complete false, capped true, cap_hit "node", "time" or "memory", and the partial counts at that moment (states seen and expanded, depth reached, frontier left, the solution length if the goal had been reached). A capped game is a recorded fact. The node cap is checked after every expansion, so a node-capped row has exactly the cap's number of expansions.

**How a capped game enters an analysis.** The registration decides it, before any confirmatory run, and nothing afterwards changes it. The registration must state: which counts of a capped game are used, and as what (for example, as a lower bound that ranks the game above every uncapped game on that count, or not at all); whether capped games are excluded from a test or kept in it; and a share of capped games above which a search measure is declared void for a suite. Whatever is registered, every analysis reports the number and share of capped games per suite and per cap, next to its result.

**The frontier format for real simulators.** The dry run's dummy graph stores frontier entries as integers. For the suites of Phase 3 the frontier entry is either the simulator's serialized state, where cloning yields compact bytes, or the action sequence from the level start, replayed on resume; the choice is made per suite in Phase 3 and registered with its size per entry, so that the spill files and checkpoints stay within the limits of Section 4.

## 7. The loop (GitHub Actions)

.github/workflows/horizon.yml runs on a cron every 30 minutes, on manual trigger, and on its own successor (below). It checks out the repository, installs the Kaggle command-line tool (pinned in requirements-loop.txt), and runs one tick, scripts/automation/loop.py tick. The runner does no computation: everything it does is poll, download, check, copy, commit, push and wait.

**Two triggers, and why.** GitHub may delay or drop scheduled events, and on 24 October 2026 it did: after the workflow was pushed with its cron, no scheduled run appeared for over an hour, and the loop moved only on manual runs. The cron is kept, and a second trigger that does not depend on it was added on the same day. Three were weighed:
- (a) *A workflow that starts its own successor.* After the tick, a last step asks loop.py next-wake how long to wait, sleeps that long inside the job, and starts the workflow again with workflow_dispatch, using the workflow's own GITHUB_TOKEN (permission actions: write). GitHub's documentation on GITHUB_TOKEN states that events it triggers "will not create a new workflow run", and that "workflow_dispatch and repository_dispatch events always create workflow runs". It needs no new credential and nothing outside GitHub.
- (b) *A free external cron service calling a dispatch webhook.* It needs a token stored at that service. GitHub's table of permissions for fine-grained tokens puts POST /repos/{owner}/{repo}/dispatches under the repository permission Contents (write), the same permission that creates, changes and deletes files, commits and tags. A token limited to that one action does not exist (the workflow-dispatch endpoint needs Actions (write), which also covers cancelling, re-running and deleting runs). It would also be a new credential held by a third party. Not used.
- (c) *The workflow waking on push*, each tick's commit starting the next. The loop pushes with GITHUB_TOKEN, and by the sentence quoted under (a) such a push starts no run. Making it start one would need a personal token or deploy key, a new credential. Also, a tick that finds the kernel still running commits nothing, so the chain would stop exactly while it is needed. Not used.

(a) was chosen. Of its two forms, the bounded sleep followed by a dispatch was chosen over one long job that loops: each job lasts at most the sleep plus a tick (timeout 45 minutes, well inside the 6-hour job limit), so a lost runner costs at most one link of the chain, which the cron or the next manual run starts again, and every link runs the latest committed loop code.

**How long the chain sleeps** (loop.py next-wake, from the committed files only). Halted loop, or every chunk done with nothing in flight: "none", so no successor is started and the loop stops. With a session in flight: until the session's deadline plus its checkpoint reserve, counted from the kernel push, but no less than 5 minutes and no more than 30. Work left and nothing in flight (for example after a failed push): 5 minutes. The step runs even when the tick step fails, so a passing fault (Kaggle or GitHub unreachable) does not break the chain; a fault inside a chunk's session is counted by the retry rule below and halts the loop at the maximum, but a tick that crashes before it reaches a chunk is not counted, and keeps the chain going at 5-minute intervals until someone looks (the run list shows each failed tick).

**One tick at a time.** All runs, whatever started them, share the concurrency group horizon-loop without cancelling the one in progress. GitHub keeps at most one run waiting in a group: a newer waiting run replaces the older one, which ends as cancelled without using a runner. A successor started during a sleep therefore waits for the current job to end, and a cron run that arrives while a link of the chain sleeps either replaces the waiting successor or is replaced by it. There is never more than one chain.

**Costs.** A tick that finds nothing to do (the manifest complete or the loop halted) costs only the job's setup and the tick, seconds, and starts no successor; the cron's later runs cost the same. While a campaign is in flight the chain keeps a runner busy for most of the wall-clock time, mostly asleep; Section 10 gives the measured figures.

A tick:
1. Restores jobs/, runs/ and logs/ to the last commit (a crashed tick leaves nothing behind) and fast-forwards to the remote. If the loop is halted, it says so and stops.
2. If a chunk is in flight, it asks Kaggle for the kernel's status. Queued or running: it stops. A session still running 30 minutes past the platform limit counts as a failure.
3. A finished session's output is downloaded and verified: the run nonce and chunk must match the dispatch; the manifest-entry hash must match; bundle.tar.gz must have the sha256 in result.json; every row must sit at its unit's path, have its recorded sha256, pass its schema and name its own unit and chunk; a partial session must leave a checkpoint whose files all have their recorded sha256. Then rows, done-markers, the checkpoint and the session's console are committed with the updated manifest, in one commit with a one-line message, and the lock is released.
4. With nothing in flight, the next chunk is chosen (partial before pending), the lock is taken (below), the notebook is pushed with the Kaggle tool, and the kernel version is committed. If every chunk is done, the tick says "manifest complete" and does nothing.

**The lock.** A tick takes the lock by committing jobs/lock.json and the dispatch, and pushing that commit, before it pushes the notebook. If the push is rejected, another runner moved main first, and this tick stops without starting anything. Two runners therefore never dispatch at once, whether both are Actions runs (also prevented by the workflow's concurrency group) or one is the laptop fallback. A lock expires one hour after the platform limit; an expired lock is removed and the removal is logged.

**Retries and the halt.** Each failure of a chunk (a kernel error, missing or invalid output, a partial session without progress, an overdue session, a push that fails) adds one to the chunk's failures and is logged. At the registered maximum, 3, the chunk becomes "failed", the loop halts, and logs/automation.log receives a paragraph that can be pasted into docs/STATE.md as it stands: the time, the chunk, the number of failures, the last reason with its kernel version and run nonce, and the count of chunks by status. A halted loop does nothing until the cause is found and the halt flag in jobs/state.json is cleared by hand.

**Commits made by the loop** carry the name horizon-loop and the GitHub Actions noreply address, and one-line messages: "Loop: dispatch <chunk> (attempt n)", "Loop: <chunk> pushed as kernel version n", "Loop: <chunk> done|partial|failed (kernel version n)".

## 8. Credentials, and why none is kept on Kaggle

The loop needs the Kaggle credentials to push the notebook and read its output; the notebook needs none, because it only clones a public repository and downloads public release files. The credentials therefore live only in two GitHub repository secrets: KAGGLE_USERNAME, the account name, used to name the notebook (account/horizon-runner), and KAGGLE_KEY, the author's existing Kaggle API token, which the workflow step hands to the Kaggle tool as the environment variable KAGGLE_API_TOKEN. Nothing secret is stored on Kaggle, in the notebook, in the repository or in any log; the notebook records only Kaggle's own environment variables whose names contain none of TOKEN, SECRET, KEY or PROXY. A notebook that could push to GitHub would need a GitHub token inside Kaggle, where anyone who gained access to the notebook could read it; this design avoids that.

Which credential works was found by testing the Kaggle tool 2.2.4 on 24 October 2026 in an empty home folder, with no Kaggle variable inherited from the laptop. The laptop has no kaggle.json. It has the environment variable KAGGLE_API_TOKEN, holding an API token (prefix KGAT_), and the file %USERPROFILE%\.kaggle\access_token, holding a token of another kind (prefix KGRT_). Only KAGGLE_API_TOKEN set to the KGAT_ token authenticated. KAGGLE_USERNAME with KAGGLE_KEY failed with either token, as with a made-up key, and the file's token did not authenticate. A first test, which did not clear the inherited KAGGLE_API_TOKEN, had wrongly shown the username-and-key form working; the first tick on GitHub, the only place without that variable, then failed its push (docs/DRYRUN.md). So the secret KAGGLE_KEY holds the existing KGAT_ token, no new token is created, and the secret names stay as specified.

## 9. Kaggle limits checked against the design

- **Concurrent sessions.** The loop runs one session at a time, so a limit on concurrent CPU sessions does not bind. More throughput, if needed, would come from several notebooks with their own slugs and their own locks; that is not built.
- **Output size.** A session's output is result.json, console.log and one compressed bundle of rows and one checkpoint; with the node cap of Section 6 the bundle stays far below the size of the working folder Kaggle keeps.
- **Internet.** The notebook needs internet to clone the repository and fetch release files. Kaggle allows internet in a notebook only for accounts with a verified phone number; the registration push (Section 12) shows whether it is on.
- **Session length.** Section 3.
- **Output of a session that fails.** Whether Kaggle keeps /kaggle/working of a session that errors is not relied on: the runner catches every error itself and ends normally. If a session is lost all the same, the work since the last committed checkpoint is done again; jobs are deterministic given their parameters, so the rows are the same.

## 10. GitHub Actions minutes

The repository is public. GitHub's billing documentation states that "the use of standard GitHub-hosted runners is free" in public repositories, so the loop uses none of the author's included minutes, which matter only for private repositories (2,000 minutes a month on the Free plan). scripts/automation/actions_minutes.py measures every run of the workflow from GitHub's own job and step times and writes logs/actions_minutes.log; docs/DRYRUN.md gives its figures: the seconds of a tick, the minutes of a run that does not wait, the monthly total of the cron with nothing to do (48 runs a day for 30 days, each rounded up to whole minutes), and the monthly total while a campaign is in flight (the measured billed minutes per wall-clock minute of the chain, times the 43,200 minutes of 30 days). The second total is far above the 2,000 minutes of a private repository on the Free plan, because the chain sleeps on a runner; that is free only because the repository is public.

## 11. Fallback: the same loop from the laptop

If the Actions minutes ever ran out (for example if the repository were made private), the same tick runs from a Windows scheduled task on the laptop every 30 minutes, in a separate clone of the repository used for nothing else: the task, with KAGGLE_USERNAME set to the account name and the laptop's own KAGGLE_API_TOKEN, runs D:\Research\horizon\.venv\Scripts\python.exe scripts\automation\loop.py tick in that clone. The lock of Section 7 keeps it from ever acting at the same time as an Actions run, so the workflow need not be switched off first; this fallback is used only if the minutes run out, and it needs the laptop on.

## 12. The dry run

Before any experiment, the whole loop is proven with dummy work (project rule R8); docs/DRYRUN.md reports it. The dry-run manifest has three chunks: dry-01 (agent kind, one seed, a two-minute sleep that writes a row with the host name, the run nonce and the time), dry-02 (search kind: a slowed breadth-first enumeration of a 28,000-node dummy graph that needs about seven minutes of work against a five-minute session, so it must checkpoint, end partial and be resumed by a later session; and a second graph with a node cap of 500, which must end capped), and dry-03 (agent kind, like dry-01). The row of a Kaggle session names the run by its nonce; the loop records the nonce together with the Kaggle kernel version in the manifest and in each done-marker.

The same loop was first run on this machine with a stand-in for the Kaggle tool and a local git remote (scripts/automation/test_loop.py): every chunk completed, the search resumed across sessions with the same count as an uninterrupted enumeration, the large checkpoint file went the release path, and a second scenario showed the halt after three failures.

**One-time commands for the author** (PowerShell, working directory D:\Research\horizon\repo):

```powershell
cd D:\Research\horizon\repo
# 1. the Python environment, outside the repository (once; skip if it exists)
D:\python\3.11.9\python.exe -m venv D:\Research\horizon\.venv
D:\Research\horizon\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-loop.txt
# 2. the two repository secrets: the account name, and this laptop's existing Kaggle API token (no new token)
gh secret set KAGGLE_USERNAME --body "ericsom"
gh secret set KAGGLE_KEY --body $env:KAGGLE_API_TOKEN
# 3. register the notebook by pushing it once by hand (its run finds no dispatch and does nothing)
$env:KAGGLE_USERNAME = "ericsom"
D:\Research\horizon\.venv\Scripts\python.exe scripts\automation\loop.py prepare-kernel --dir "$env:TEMP\horizon-kernel"
D:\Research\horizon\.venv\Scripts\kaggle.exe kernels push -p "$env:TEMP\horizon-kernel"
# 4. start the loop; each run then starts its own successor until the manifest is complete or the loop halts
gh workflow run horizon.yml
```
