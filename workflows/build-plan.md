# Build Plan — V1

Decisions made 2026-09-20.

## Shape

Python ingest pipeline → SQLite → generated static site. No server, no database to
operate, free hosting. Filtering and search run in the browser.

## Decisions and why

| Decision | Choice | Why |
| --- | --- | --- |
| App type | Static site from a pipeline | One person can keep it alive. No uptime risk. |
| Summaries | AI draft, human approves | Nothing public until a person signs off. |
| Sources | Federal Register API only | Verified working, structured, has real effective dates. |
| Language | Python | Matches the user's existing work. |
| Model | `claude-opus-5` | Accuracy matters more than cost here. |
| Storage | SQLite | One file, no server, easy to back up and inspect. |

## Pipeline

```
fetch  →  summarize  →  review  →  build
 │           │            │          │
 │           │            │          └─ writes outputs/site/
 │           │            └─ human approves, status: approved
 │           └─ Claude drafts, status: summarized
 └─ Federal Register API, status: new
```

Status moves one way. Nothing reaches the site without `approved`.

## Modules

| File | Job |
| --- | --- |
| `app/config.py` | Paths, model, API query, feature flags |
| `app/fetch.py` | Federal Register API client, pagination, retries |
| `app/store.py` | SQLite schema and all queries |
| `app/tagging.py` | Species/region tags from the controlled vocabularies |
| `app/summarize.py` | Claude call with a strict JSON schema |
| `app/build_site.py` | Static HTML generation |
| `app/cli.py` | `fetch`, `summarize`, `review`, `build`, `status`, `run` |

## Accuracy controls

These are the point of the design, not decoration.

1. **Structured output.** Claude returns a fixed JSON schema. No free-form parsing.
2. **Effective date is never generated.** It is copied from the API's `effective_on`
   field. The model is not asked for it and cannot change it.
3. **Tags are validated against the vocabulary.** Anything Claude proposes that is not
   in `resources/species-list.md` or `resources/region-list.md` is dropped and logged.
4. **Unclear items are surfaced, not smoothed.** The schema has an `unclear` array.
   Anything in it blocks approval until a human resolves it.
5. **Human gate.** `status` must be `approved` before a notice renders.
6. **Every card links to the Federal Register original.**

## Deliberately not in V1

Email alerts, user accounts, saved filters, MAFMC and GARFO scraping, full PDF text
extraction. Each is a real feature; none is needed to prove the format works.

## Risks

- **Abstracts are thin.** The API's `abstract` is short. Some notices will need full
  text before a summary is trustworthy. Mitigation: the `unclear` array catches these
  and the reviewer pulls the original.
- **Resolved 2026-09-20: the ingest filter now matches the vocabulary.** It was a
  single title phrase, which reached only the Northeast series. It is now two passes —
  50 CFR parts 648, 635, and 697, then the three matching title phrases. Over a 90-day
  window that took coverage from 12 documents to 23, and all 115 species are now
  reachable. Details below.

- **Notice volume is up, and some of it is low value.** The widened filter pulls in
  "Agency Information Collection Activities" paperwork notices alongside real rules.
  They are in-domain but rarely interesting. If summarization cost becomes a concern,
  filtering those out by title is the cheapest lever.
- **Model cost.** At Opus 5 rates ($5/M input, $25/M output) a summary runs roughly 3-6
  cents, most of it thinking tokens. At 20-40 notices a month that is a couple of
  dollars. Measure it rather than trusting this estimate.
