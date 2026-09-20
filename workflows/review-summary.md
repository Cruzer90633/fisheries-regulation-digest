# Workflow: Review a Summary

The human gate. Nothing reaches the public site without passing it.

```
.venv\Scripts\python.exe -m app.cli review
```

One draft at a time: **a**pprove, **r**eject, **s**kip, **q**uit. You can stop
whenever — skipped and undecided drafts stay in the queue.

## What to check

Do not re-read the whole regulation. The drafts are written from the full document
text, so the job is spotting where the summary and the source disagree, not
re-deriving the summary.

- [ ] **The figures match.** Quotas, limits, poundages, percentages. This is where a
      wrong summary does real damage.
- [ ] **The effective date is right.** It comes from the Federal Register field, not
      the model, so it should be — but confirm it against the notice.
- [ ] **Nothing is asserted that the notice does not say.** Watch for confident
      framing the source did not supply: "routine", "minor", "as expected".
- [ ] **No legal interpretation and no compliance advice.** It describes what changed.
      It does not tell anyone what they must do.
- [ ] **Tags look right.** Species and region tags come from the controlled
      vocabularies, so they cannot be invented — but they can be wrong.
- [ ] **Dropped tags are worth a look.** If the review screen reports dropped tags,
      the notice named something outside the vocabulary. Sometimes that means the
      vocabulary needs an entry.

## Open questions do not block approval

Anything the model could not settle appears under **Open questions**, and those
**publish on the card** for readers to see. That is the point: a summary that admits
what it could not determine is more trustworthy than one that quietly smooths the gap.

Approve a draft with open questions when the summary itself is accurate. Reject it
when the summary is wrong.

Run with `--strict` if you want open questions to block approval instead.

## When to reject

Reject on a factual error, an unsupported claim, or interpretation that strays into
advice. Say why — the reason is stored on the record.

Rejection is terminal. To get a corrected summary, reset the row to `new` and re-run
`summarize`.

## After reviewing

```
.venv\Scripts\python.exe -m app.cli build
```

Then commit and push. The live site updates a minute or two later.

> Re-running a summary discards its approval. That is correct — a summary regenerated
> under different rules has not been reviewed under those rules. It does mean
> vocabulary edits cost re-approval work, so batch them before a review session.
