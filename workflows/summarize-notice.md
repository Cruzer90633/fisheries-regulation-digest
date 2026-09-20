# Workflow: Summarize Notice

Turn one raw notice into a plain-English summary.

**Trigger:** a new raw record from `ingest-sources.md`.
**Input:** one raw notice record.
**Output:** one filled `templates/regulation-summary.md` in `drafts/`.

## Steps

1. Read the full notice. If it points to a PDF or Federal Register entry, read that too.
2. Fill the summary template. Every field must trace to the source text.
3. Write the "What changed" section in 2-4 sentences, at roughly an 8th-grade reading
   level. Say what is different now versus before.
4. Tag species and region using only the controlled vocabularies in
   `resources/species-list.md` and `resources/region-list.md`. Do not invent tags.
5. Record the effective date exactly as stated. If the notice does not state one, write
   "Not stated in notice" — never estimate.
6. Mark anything ambiguous with `[UNCLEAR: ...]` for the reviewer. Do not resolve
   ambiguity by guessing.

## Hard rules

- No legal interpretation. Describe the change; do not explain what someone must do.
- No compliance advice.
- No numbers, dates, or species that do not appear in the source.
- If the notice is genuinely unclear, say so in the summary rather than smoothing it over.

## Done when

The template is complete, every claim traces to the source, and the permalink resolves.
