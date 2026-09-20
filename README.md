# Fisheries Regulation Digest

Plain-English summaries of fishery regulation updates from the Mid-Atlantic Fishery
Management Council (MAFMC) and NOAA Fisheries Greater Atlantic Regional Fisheries
Office (GARFO).

The goal: let students, industry members, and the public find out when a rule affects
a species or region they care about, without reading dense regulatory PDFs or
subscribing to mailing lists.

## V1 scope

- Pull announcements from MAFMC and GARFO
- Summarize each one in plain English (what changed, species/area affected, effective date)
- Filter by species or region
- Link every summary back to its original source
- Archive and search past digests

**Out of scope for V1:** legal interpretation, compliance advice, real-time enforcement data.

## How it works

```
fetch  →  summarize  →  review  →  build
 │          │             │          │
 │          │             │          └─ outputs/site/index.html
 │          │             └─ you approve; nothing publishes without this
 │          └─ Claude drafts against a fixed JSON schema
 └─ Federal Register API
```

Python pipeline, SQLite for state, a generated static site. No server to run.

See [SETUP.md](SETUP.md) to get it running and
[workflows/build-plan.md](workflows/build-plan.md) for the design decisions.

```
python -m app.cli fetch
python -m app.cli summarize --limit 3
python -m app.cli review
python -m app.cli build
```

## Repository layout

| Folder | Contents |
| --- | --- |
| `app/` | The pipeline: fetch, summarize, review, build |
| `tests/` | Unit tests (no network, no API calls) |
| `workflows/` | Workflow instructions, agent definitions, process documents |
| `outputs/` | Completed work and generated deliverables, including `site/` |
| `resources/` | Reference material, source documents, examples, research |
| `drafts/` | Work in progress and temporary files |
| `templates/` | Reusable templates and frameworks |

`CLAUDE.md` holds the project context and working rules for AI agents.

## Accuracy controls

These are the point of the design.

- **Effective dates are never generated.** They are copied from the Federal Register's
  `effective_on` field. The model is not asked for them.
- **Tags are validated.** Anything the model proposes that is not in
  `resources/species-list.md` or `resources/region-list.md` is dropped and logged.
- **Uncertainty is surfaced.** The model fills an `unclear` array; anything in it
  blocks approval until a human checks the original.
- **A human approves every summary** before it can reach the site.
- **Every card links to the original notice.**

## Status

V1 pipeline working. As of 2026-09-20:

- 17/17 tests pass on Python 3.13
- `fetch` runs against the live Federal Register API and stores real notices — 23
  unique documents over a 90-day window, across Northeast, HMS, and ASMFC actions
- The front end renders and filters correctly, verified in a browser
- The species and region vocabularies are verified against the councils' current
  fishery management plans, plus ASMFC and NOAA HMS — 115 species, 32 regions

Not yet exercised: `summarize`, which needs an `ANTHROPIC_API_KEY`. Everything up to
that point runs.

## Disclaimer

This project produces informal summaries for orientation only. It is not legal advice
and is not an official source. Always confirm against the linked original notice and
the Federal Register before acting on a regulation.
