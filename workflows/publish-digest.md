# Workflow: Publish Digest

Assemble approved summaries into a digest issue.

**Trigger:** scheduled digest window (cadence TBD).
**Input:** approved summaries in `outputs/` not yet included in a digest.
**Output:** one filled `templates/digest-issue.md`.

## Steps

1. Gather every approved summary since the last digest.
2. Group by agency, then by species where grouping helps the reader.
3. Write a 2-3 sentence issue intro naming the most significant change in the period.
4. Order items by likely reader impact, not by date.
5. Confirm every source link resolves. Broken links block publication.
6. Include the standard disclaimer.

## Done when

The issue is complete, every link resolves, and it is saved to `outputs/` as
`YYYY-MM-DD-digest.md`.
