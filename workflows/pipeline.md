# The Pipeline

What the code actually does, and where. Four stages, each a command.

```
fetch  →  summarize  →  review  →  build
 │          │             │          │
 │          │             │          └─ writes docs/ (the public site)
 │          │             └─ a person approves; nothing publishes without this
 │          └─ Claude drafts against a fixed JSON schema
 └─ Federal Register API
```

Status moves one direction only: `new` → `summarized` → `approved`. A notice can also
be `rejected`, which is terminal. The site renders `approved` rows and nothing else.

## fetch — `app/fetch.py`

Queries the Federal Register API in two passes and merges on document number.

1. **By CFR part** — 50 CFR 648, 635 and 697. Catches everything that amends the
   regulations, which is every rule and proposed rule. One part per request; the API
   rejects a comma-separated list.
2. **By title phrase**, scoped to NOAA. Catches Notices, which amend nothing and so
   carry no CFR reference.

Which query matched is recorded as the notice's `programs`, so the site can say a rule
came from the Greater Atlantic, Highly Migratory Species, or Atlantic Coastal
programme without guessing from its title.

Collects only. Never interprets, never edits source text. A fetch failure is logged
and raised, not swallowed.

## summarize — `app/summarize.py`

Fetches the full document text (`app/fulltext.py`) and asks Claude for a fixed JSON
schema: what changed, who it affects, key details, species, regions, open questions.

Four things keep it honest:

- **Structured output.** A JSON schema, not free-form parsing.
- **The effective date is never generated.** It is copied from the API's
  `effective_on` field and the prompt tells the model not to repeat it in prose.
- **Tags are validated** against `resources/species-list.md` and `region-list.md`.
  Anything outside the vocabulary is dropped and recorded in `dropped_tags`.
- **Uncertainty is surfaced.** Anything the text does not settle goes in `unclear`.

Token usage and cost are recorded per notice.

> The tagging rules live in the prompt, not in the resource files. Only the canonical
> names are sent to the model — the Rules sections in those markdown files are
> documentation for humans. A rule added there alone changes nothing.

## review — the human gate

See [review-summary.md](review-summary.md). This is the only stage a person must do.

## build — `app/build_site.py`

Renders approved notices into `docs/index.html`, plus `docs/data.json` and
`docs/feed.xml`. The page is self-contained: the data is embedded, filtering and
search run in the browser, and it works from any static host or straight off disk.

`docs/` rather than `outputs/` because GitHub Pages will only serve the repository
root or a folder named `docs`.

## Automation

`.github/workflows/weekly-digest.yml` runs fetch and summarize every Monday at 07:00
UTC, commits the drafts, and stops. It never publishes. Review stays human.
