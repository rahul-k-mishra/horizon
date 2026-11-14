# The Zenodo deposit of a registration: the author's steps

Written 14 November 2026. The registration of HORIZON is the annotated git tag `prereg-v1` together with a Zenodo deposit of the protocol, made on the same day and carrying the SHA-256 of every tagged protocol file (docs/PREREG.md, Section 0). OSF is no longer available to the author; study 1 had a tag and two OSF registrations. Nothing here has been deposited; the author makes the deposit himself.

## On the day of the tag, in this order

1. Check that every file in docs/registration/protocol_files.txt that is still under "to be added" has been committed and moved into the list, and that the list is committed.
1a. (added 14 November 2026) Check that no tracked file names a writing or coding aid (rule R2, docs/RULES.md):
   `D:\Research\horizon\.venv\Scripts\python.exe scripts\check_no_aid.py > logs\check_no_aid.log`
   It must end with "clean" and return 0. If it does not, remove the mention, commit, and run it again before the tag. scripts/zenodo_deposit.py in step 3 runs the same check on the tagged commit and stops if it finds a hit.
2. Create the annotated tag and push it:
   `git tag -a prereg-v1 -m "HORIZON registration v1"` and `git push origin prereg-v1`.
3. Write the deposit files from the tag (working directory D:\Research\horizon\repo):
   `D:\Research\horizon\.venv\Scripts\python.exe scripts\zenodo_deposit.py --tag prereg-v1 --out D:\Research\horizon\zenodo\prereg-v1 > logs\zenodo_deposit_prereg-v1.log`
   The folder is outside the repository. The script reads the files as stored in git at the tag, not the working tree. It returns 2 with a warning if the tag is not dated today; in that case do not deposit, and record why in docs/STATE.md.
4. On Zenodo, make a new upload:
   - files: `protocol.zip` and `SHA256SUMS.txt` from that folder;
   - title, creator (name, affiliation, ORCID), publication date and version: as in `metadata.json`;
   - description: the text of `description.txt`, unchanged; it names the tag, the commit and every SHA-256;
   - related identifier: the tag's address on GitHub, given in `metadata.json`;
   - resource type, licence and keywords: the author's choice; the repository has no licence file at the time of writing.
   Publish it the same day.
5. Record the DOI, the Zenodo record's date and the SHA-256 of `protocol.zip` in docs/STATE.md as a new amendment, and commit `logs/zenodo_deposit_prereg-v1.log` (the script's console) with it. This commit comes after the tag and is not part of the tagged files.

Each later version (prereg-v1.1, ...) repeats the same steps on the day of its tag, as a new version of the Zenodo record or a new record.

## What a reader can check

- Hash the tagged files (`git show prereg-v1:<path>`, or a clone without line-ending conversion) and compare with the SHA-256 in the Zenodo description; the git blob hashes in SHA256SUMS.txt can be compared with `git rev-parse prereg-v1:<path>` on any clone.
- Compare the Zenodo record's date with the first confirmatory dispatch in logs/automation.log and with the times GitHub Actions records for those workflow runs: every confirmatory dispatch must come after the deposit.

## What this does not show

A tag alone does not prove that the protocol was fixed before the data arrived: the author controls the repository and can move a tag, and a commit carries the date its machine gives it. The Zenodo record's timestamp and DOI cannot be altered by the author, and its SHA-256 values tie the tagged files to that date. Zenodo does not check what is deposited, and its date says nothing about when the confirmatory runs began; that rests on the loop's record on GitHub and on the Kaggle kernel versions.
