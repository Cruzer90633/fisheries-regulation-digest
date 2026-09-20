# Workflow: Ingest Sources

Collect new regulatory notices from MAFMC and GARFO and stage them for summarizing.

**Trigger:** scheduled run (frequency TBD) or manual.
**Input:** the source list in `resources/source-registry.md`.
**Output:** one raw notice record per new item, staged in `drafts/`.

## Steps

1. For each source in the registry, fetch the current list of items.
2. Compare against already-seen items by stable ID (permalink URL, or agency document
   number where one exists). Skip anything already recorded.
3. For each new item, capture:
   - Title, exactly as published
   - Source agency (MAFMC or GARFO)
   - Publication date
   - Permalink to the original notice
   - Full text, or the linked PDF if the text is not on the page
   - Federal Register citation and document number, if referenced
4. Store the raw capture unmodified. Never edit source text during ingest.
5. Log anything that failed to fetch. A silent miss is worse than a visible error.

## Done when

Every new notice has a raw record with a working permalink, and every fetch failure
is logged rather than swallowed.

## Notes

- Ingest never summarizes or interprets. It only collects.
- If a source changes structure and the fetch breaks, stop and flag it. Do not guess
  at replacement content.
