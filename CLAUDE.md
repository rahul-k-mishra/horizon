# HORIZON

## Rules that never change

R1. Commit messages are one subject line, nothing more; no trailers, no attribution lines, no "Co-Authored-By", no "Generated with", ever. Verify after every commit with git log -1 --format=%B.

R2. No manuscript, figure, caption, letter, README or metadata of this project mentions any writing or coding aid. The author is Rahul Kumar Mishra, single author, Independent Researcher, Ranchi, Jharkhand, India, ORCID 0009-0004-9671-4055.

R3. No number is stated anywhere unless a script in this repository produced it from committed files, and the console of that script is committed as a log. Scripts that run experiments are run by the automation under the author's Kaggle account or by the author himself; you write them and you do not run experiments. Scripts that only read committed files you may run to verify your own work.

R4. Parallel form for every experiment script: a worker pool, resumable, chunked so that any chunk finishes inside 11 hours on 4 CPU cores and 30 GB RAM, with a done-marker per unit of work and a manifest of chunks.

R5. Nothing is claimed before it is registered; nothing registered changes after its tag except by a dated amendment; the outcome table and the venue for each outcome are fixed before any confirmatory run. The author's standing venue rules: no venue with an article charge that cannot be waived, no conference, no workshop; Support goes to IEEE Transactions on Games, with JAIR as the alternative if the result is broad; Refute goes to the repository and a preprint on Zenodo.

R6. Every document that states results separates registered from exploratory, labels exploratory as such in every paragraph, and never proposes a fix as a result. No "future work" section anywhere.

R7. STATE.md is the project record, append-only, dated and lettered amendments as in the old project; it is the first file read at the start of every session and the last file written at the end of every session.

R8. The automation is proven by a dry run that goes round the whole loop with a dummy job before any experiment is launched; no experiment runs until that dry run's log is committed.

R9. Plain English in every document; no AI-sounding phrasing; the forbidden-word list of D:\Research\arc3\repo\docs\manuscript_jagi\BUILD.md (step 8) applies to every document.

## Places

- Project parent folder: D:\Research\horizon. Repository and working directory: D:\Research\horizon\repo (public: https://github.com/rahul-k-mishra/horizon).
- Prompt files: D:\Research\horizon\prompts. Python environment: D:\Research\horizon\.venv, outside the repository, made with D:\python\3.11.9\python.exe.
- The previous project, D:\Research\arc3\repo, is read-only in every phase: read anything there, write nothing there, run nothing there. Its rows under runs/suites and its truth tables are inputs to this project.
- Both of the author's machines run Windows.

## Forbidden words (R9)

From D:\Research\arc3\repo\docs\manuscript_jagi\BUILD.md, step 8, matched without regard to case: assistant, claude, language model, LLM, LLMs, generated, delve, leverag-, robust, comprehensive, novel, showcas-, underscor-, crucial, pivotal, landscape, tapestr-, realm, realms, paradigm, harness, foster, holistic, seamless, cutting-edge, state of the art, it is worth noting, importantly, notably, in this work, in conclusion, furthermore, moreover, additionally. The only exceptions are a word inside the title of a cited work, a word inside a rule of this file that quotes it, and a file name that a citation must give.

## Session start and end

Read docs/STATE.md first. Write docs/STATE.md last, as a new dated, lettered amendment.
