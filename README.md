# Fisheries Regulation Digest

**Live at [cruzer90633.github.io/fisheries-regulation-digest](https://cruzer90633.github.io/fisheries-regulation-digest/)**

Plain-English summaries of fishery regulation updates from the Mid-Atlantic Fishery
Management Council (MAFMC) and NOAA Fisheries Greater Atlantic Regional Fisheries
Office (GARFO).

## The weekly rhythm

**Monday 07:00 UTC** — the `Weekly fetch and summarize` Action pulls new Federal
Register notices and drafts summaries. It commits them and stops. It never publishes.

**You, whenever it suits** — `git pull`, then review, build, commit, push. The live
site updates a minute or two later.

```
git pull
.venv\Scripts\python.exe -m app.cli review
.venv\Scripts\python.exe -m app.cli build
git add . && git commit -m "New summaries" && git push
```

Two things that will bite you otherwise:

- **Always `git pull` first.** The Monday Action writes to the same
  `app/data/digest.db`, and Git cannot merge two versions of a SQLite file.
- **Batch any vocabulary edits before a review session.** Changing
  `resources/species-list.md` or `region-list.md` means re-running affected
  summaries, and a re-run drops them back to unapproved.

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
 │          │             │          └─ docs/ — page, data, RSS feed
 │          │             └─ you approve; nothing publishes without this
 │          └─ Claude drafts against a fixed JSON schema
 └─ Federal Register API
```

Python pipeline, SQLite for state, a generated static site. No server to run.

See [SETUP.md](SETUP.md) to get it running, [workflows/pipeline.md](workflows/pipeline.md)
for what each stage does, and [workflows/build-plan.md](workflows/build-plan.md) for the
design decisions.

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
| `workflows/` | How the pipeline works, and the human review gate |
| `docs/` | The generated public site: page, data, RSS feed (GitHub Pages serves this) |
| `outputs/` | Completed work and generated deliverables |
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
- **Uncertainty is published, not hidden.** Anything the model could not settle is
  shown on the card as an open question. A summary that admits its gaps is worth more
  than one that smooths them over.
- **A human approves every summary** before it can reach the site.
- **Provenance is recorded, not inferred.** Which programme a notice belongs to comes
  from the query that matched it, never from reading its title.
- **Every card links to the original notice.**

## Status

Live and running. As of 2026-09-20:

- 24 summaries published, all reviewed and approved by hand
- 37 tests pass on Python 3.13
- Vocabularies verified against the councils' current fishery management plans, plus
  ASMFC and NOAA HMS — 115 species, 32 regions
- Ingest covers 50 CFR parts 648, 635 and 697 plus three title phrases, so Northeast
  council, highly migratory species and interstate coastal actions all arrive
- Cost to produce the whole archive: about $3.40

Crawlers are asked to stay away in `robots.txt` — a deliberate choice while the site
finds its audience, reversible in `app/config.py`.

## Disclaimer

This project produces informal summaries for orientation only. It is not legal advice
and is not an official source. Always confirm against the linked original notice and
the Federal Register before acting on a regulation.
