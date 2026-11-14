# DESIGN, stage E draft: the changes option E would make to docs/DESIGN.md

**Status: adopted 14 November 2026** into docs/DESIGN.md, with the author's answers of that day (docs/DECISIONS_BEFORE_TAG.md); where an answer differed from this draft, the answer was followed. This file is kept unchanged below as the record of the draft. Written 13 November 2026 beside docs/DESIGN.md. If the author adopts option E (docs/design/STAGE_E_OPTIONS.md), docs/DESIGN.md changes in the sections below, by the same text as docs/PREREG_stage_e_draft.md, so that the two documents stay in step. Each change is marked with its date and reason when adopted.

| DESIGN section | change | the text to use |
|---|---|---|
| 1, the question to register | the registered question becomes "among levels of games with the same mechanics score, does a pre-run search measure rank first-level completion above chance"; the v0 contrast becomes a secondary estimate | PREREG draft, Section 1 |
| 2.1, stage D | add what stage D showed, labelled exploratory, and stage E: why it runs (L_C cannot be read from stage D's rows), its manifest (logs/make_stage_e_manifest.log), and that it is development data | PREREG draft, Section 9.1; docs/design/STAGE_E_OPTIONS.md, Sections 1 and 4 |
| 5, the search quantities | the ceiling C, L_C as primary, H_C and b as secondary, the effective-horizon bound dropped, the node cap dropped; the capped-game rule replaced by censoring with the 10% exclusion rule | PREREG draft, Sections 6 and 7.4 |
| 7, the registered tests | AUROC_L over same-mechanics between-game pairs; the verdict per agent; the void rules; the secondary list | PREREG draft, Sections 7.2 to 7.7 |
| 7.1, the smallest detectable difference | d = 0.51 describes the secondary Delta; the answer to "proceed, widen the suite or change the claim" recorded as the author's decision of [date] | PREREG draft, Section 7.8; docs/DECISIONS_BEFORE_TAG.md |
| 8, the pilot gate | G3 checks that every pilot level completes or reaches C within the time cap | PREREG draft, Section 8 |
| 9, the outcome table | the Support and Refute rows | PREREG draft, Section 10 |
| 10, the Kaggle session and the budget | the confirmatory search budget recomputed for the ceiling C (scripts/design_budget.py, rerun with C) | to be printed by the rerun |
| 12, the author's decisions | the decisions of docs/DECISIONS_BEFORE_TAG.md, with their dates | the author's answers |
