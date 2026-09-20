# Workflows

Process documents: how the system works and where human judgement is required.

## Contents

- [pipeline.md](pipeline.md) — what the code does at each stage, and in which module
- [review-summary.md](review-summary.md) — the human review gate, and what to check
- [build-plan.md](build-plan.md) — the V1 architecture and the decisions behind it

## A note on what used to be here

`ingest-sources.md`, `summarize-notice.md` and `publish-digest.md` were written before
the pipeline existed, when the plan was a manual process driven by an agent. They
described collecting from MAFMC and GARFO into `drafts/` — which is not what the code
does, and had not been true for some time. Keeping instructions that misdescribe the
system is worse than having none, so they are replaced by `pipeline.md`.

Git history has them if you want to see the original process design.
