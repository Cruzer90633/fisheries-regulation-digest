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

`.github/workflows/weekly-digest.yml` runs `app.cli run` — fetch then summarize —
every Monday at 07:17 UTC, commits what it found, and stops. It never publishes.
Review stays human.

07:17 rather than 07:00 because GitHub documents that scheduled runs can be delayed,
and sometimes dropped, when Actions is under load, and load peaks at the top of the
hour.

### The run record

Every run writes `app/data/last-run.json` and commits it, whether or not it found
anything. Nothing about the record is clever; it exists because silence is
ambiguous. A week with no new rules, a job that broke, and a schedule GitHub quietly
disabled all produce the same nothing. A commit every Monday separates them, and the
commit subject says which one you got:

```
Weekly run: 3 new summary(ies) awaiting review
Weekly run: nothing new
Weekly run: 2 drafted, 1 failed — check the log
Weekly run: could not draft — No Claude credentials found.
```

Read it locally with `app.cli heartbeat`, or `app.cli status`, which ends with the
same line.

Three supporting choices, all in service of the same thing:

- **A partial failure fails the job.** `run` exits non-zero if any notice failed to
  draft, not only if every one did. Four good drafts and a fifth that broke used to
  report success.
- **The drafts are committed first, the job fails after.** Losing four good drafts
  because the fifth failed would be a poor trade, so the commit step runs either way
  and the job is failed deliberately at the end. A red run emails you.
- **A weekly commit keeps the schedule alive.** GitHub disables scheduled workflows
  in a public repository after 60 days with no repository activity. A quiet stretch
  could have killed the cron silently. Now it cannot.
