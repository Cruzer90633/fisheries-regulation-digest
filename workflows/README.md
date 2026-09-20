# Workflows

Workflow instructions, agent definitions, and process documents.

Each workflow is one markdown file describing a repeatable process: what triggers it,
what it takes as input, the steps in order, and what "done" looks like.

## Naming

`<verb>-<object>.md` — lowercase, hyphens, descriptive.
Examples: `ingest-sources.md`, `summarize-notice.md`, `publish-digest.md`.

## Current workflows

- [build-plan.md](build-plan.md) — V1 architecture and the decisions behind it
- [ingest-sources.md](ingest-sources.md) — collect new notices from MAFMC and GARFO
- [summarize-notice.md](summarize-notice.md) — turn one notice into a plain-English summary
- [review-summary.md](review-summary.md) — accuracy check before anything is published
- [publish-digest.md](publish-digest.md) — assemble reviewed summaries into a digest
