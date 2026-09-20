# Workflow: Review Summary

Accuracy check. Nothing reaches `outputs/` without passing this.

**Trigger:** a draft summary from `summarize-notice.md`.
**Input:** the draft plus its raw source record.
**Output:** an approved summary, or the draft returned with specific corrections.

## Checklist

- [ ] Every factual claim appears in the source notice
- [ ] Effective date matches the source exactly, or is marked "Not stated in notice"
- [ ] Species tags come from `resources/species-list.md`
- [ ] Region tags come from `resources/region-list.md`
- [ ] Permalink resolves to the correct original notice
- [ ] Summary contains no legal interpretation or compliance advice
- [ ] No `[UNCLEAR: ...]` markers remain unresolved
- [ ] Plain English: no undefined jargon, no acronyms without expansion on first use
- [ ] The disclaimer is present

## Failure handling

If any item fails, return the draft with the specific problem named. Do not fix a
factual error by rewording — go back to the source.

## Done when

All boxes are checked and the summary is moved to `outputs/`.
