"""Command line interface.

    python -m app.cli fetch       pull new notices from the Federal Register
    python -m app.cli summarize   draft summaries for new notices
    python -m app.cli review      approve or reject drafts, one at a time
    python -m app.cli build       generate the static site
    python -m app.cli status      show where everything stands
    python -m app.cli run         fetch + summarize (no publishing)
    python -m app.cli heartbeat   what the last automated run found
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import textwrap

from . import build_site, config, fetch, fulltext, heartbeat, store


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s  %(message)s",
    )


def _wrap(text: str, indent: str = "  ") -> str:
    return textwrap.fill(text, width=88, initial_indent=indent, subsequent_indent=indent)


# --- commands ------------------------------------------------------------


def _fetch(days: int) -> dict:
    """Pull notices into the database. Returns a tally for the run record."""
    store.init_db()
    raw_notices = fetch.fetch_notices(days_back=days)

    added = 0
    skipped = 0
    with store.connect() as conn:
        for raw in raw_notices:
            notice = fetch.normalize(raw)
            if not notice["document_number"]:
                skipped += 1
                logging.warning("Skipping a result with no document number: %r", notice["title"])
                continue
            if store.upsert_notice(conn, notice):
                added += 1

    return {"fetched": len(raw_notices), "added": added, "skipped": skipped}


def cmd_fetch(args) -> int:
    _report_fetch(_fetch(args.days))
    return 0


def _ensure_full_text(notice: dict) -> dict:
    """Fetch and cache the document's full text if we do not already have it.

    A failure here is not fatal. The summarizer falls back to the abstract and
    says so — a thin summary beats no summary, as long as it admits what it is.
    """
    if notice.get("full_text"):
        return notice

    url = notice.get("body_html_url")
    if not url:
        print("  no full-text URL — summarizing from the abstract alone")
        return notice

    try:
        text, truncated = fulltext.fetch_text(url)
    except fetch.FetchError as exc:
        print(f"  full text unavailable ({exc}) — falling back to the abstract")
        return notice

    if not text:
        return notice

    with store.connect() as conn:
        store.save_full_text(conn, notice["document_number"], text, truncated)

    notice = dict(notice, full_text=text, full_text_truncated=1 if truncated else 0)
    print(f"  full text: {len(text):,} chars{' (truncated)' if truncated else ''}")
    return notice


def _summarize(limit: int) -> dict:
    """Draft summaries for everything new. Returns a tally for the run record.

    A missing credential comes back as `blocked` rather than being raised. The
    caller still wants to record that the run happened and why it drafted
    nothing — an unexplained quiet week is the exact failure this reporting
    exists to prevent.
    """
    # Imported here so fetch/review/build work before the Claude SDK is installed.
    from . import summarize as summarizer

    stats = {"drafted": 0, "failed": 0, "blocked": "",
             "input_tokens": 0, "output_tokens": 0}

    problem = summarizer.credential_problem()
    if problem:
        print(problem)
        stats["blocked"] = problem.splitlines()[0]
        return stats

    store.init_db()

    with store.connect() as conn:
        pending = [store.to_dict(row) for row in store.by_status(conn, store.STATUS_NEW)]

    if not pending:
        print("Nothing to summarize.")
        return stats

    if limit:
        pending = pending[:limit]

    print(f"Summarizing {len(pending)} notice(s) with {config.MODEL}.\n")

    for index, notice in enumerate(pending, start=1):
        print(f"[{index}/{len(pending)}] {notice['title'][:78]}")

        notice = _ensure_full_text(notice)

        try:
            summary = summarizer.summarize(notice)
        except summarizer.SummarizeError as exc:
            stats["failed"] += 1
            print(f"  FAILED: {exc}\n")
            continue

        usage = summary.pop("usage", {})
        with store.connect() as conn:
            store.save_summary(conn, notice["document_number"], summary, usage)

        stats["drafted"] += 1
        tokens_in = usage.get("input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)
        stats["input_tokens"] += tokens_in
        stats["output_tokens"] += tokens_out

        flags = []
        if summary["unclear"]:
            flags.append(f"{len(summary['unclear'])} unclear")
        if summary["dropped_tags"]:
            flags.append(f"{len(summary['dropped_tags'])} tag(s) dropped")

        print(f"  drafted{' — ' + ', '.join(flags) if flags else ''}")
        print(f"  {tokens_in:,} in / {tokens_out:,} out — "
              f"${config.estimate_cost(tokens_in, tokens_out):.4f}\n")

    return stats


def _report_fetch(stats: dict) -> None:
    known = stats["fetched"] - stats["added"] - stats["skipped"]
    print(f"Fetched {stats['fetched']} notice(s). {stats['added']} new, {known} already known.")
    if stats["skipped"]:
        print(f"{stats['skipped']} skipped — no document number.")


def _report_summarize(stats: dict) -> None:
    done = stats["drafted"]
    failed = stats["failed"]
    if not done:
        if failed:
            print(f"Nothing drafted. {failed} failed.")
        return
    cost = config.estimate_cost(stats["input_tokens"], stats["output_tokens"])
    print(f"Drafted {done}. Failed {failed}.")
    print(f"Tokens: {stats['input_tokens']:,} in / {stats['output_tokens']:,} out. "
          f"Estimated cost ${cost:.2f} (${cost / done:.4f} per notice).")
    print("Estimate only — check the Console for actual billing.")
    print("Run `review` next — nothing publishes without it.")


def cmd_summarize(args) -> int:
    stats = _summarize(args.limit)
    _report_summarize(stats)
    if stats["blocked"]:
        return 1
    return 1 if stats["failed"] and not stats["drafted"] else 0


def cmd_review(args) -> int:
    store.init_db()

    with store.connect() as conn:
        drafts = [store.to_dict(row) for row in store.by_status(conn, store.STATUS_SUMMARIZED)]

    if not drafts:
        print("No drafts waiting for review.")
        return 0

    print(f"{len(drafts)} draft(s) to review. [a]pprove  [r]eject  [s]kip  [q]uit")
    if args.strict:
        print("--strict is on: open questions will block approval.\n")
    else:
        print("Open questions publish alongside the summary.\n")

    for index, draft in enumerate(drafts, start=1):
        print("=" * 88)
        print(f"[{index}/{len(drafts)}] {draft['title']}")
        print(f"  {draft['doc_type']} · published {draft['publication_date']} · "
              f"effective {draft['effective_on'] or 'not stated in notice'}")
        print(f"  {draft['html_url']}")
        print()
        print("WHAT CHANGED")
        print(_wrap(draft["what_changed"] or "(empty)"))
        print()
        print("WHO IT AFFECTS")
        print(_wrap(draft["who_affected"] or "(empty)"))

        if draft["key_details"]:
            print("\nKEY DETAILS")
            for detail in draft["key_details"]:
                print(_wrap(f"- {detail}"))

        print(f"\nSPECIES  {', '.join(draft['species']) or '(none)'}")
        print(f"REGIONS  {', '.join(draft['regions']) or '(none)'}")

        if draft["unclear"]:
            print("\nOPEN QUESTIONS — these publish on the card")
            for item in draft["unclear"]:
                print(_wrap(f"- {item}"))

        if draft["dropped_tags"]:
            print(f"\n!! TAGS DROPPED (not in the vocabulary): {', '.join(draft['dropped_tags'])}")

        print()
        choice = input("  [a]pprove / [r]eject / [s]kip / [q]uit > ").strip().lower()

        if choice == "q":
            print("Stopped. Remaining drafts stay pending.")
            return 0
        if choice == "a":
            # Open questions are published on the card, so they no longer block
            # approval — hiding a known gap was the bigger risk. --strict restores
            # the old behaviour for anyone who wants only airtight summaries.
            if draft["unclear"] and args.strict:
                print("  Blocked by --strict: unresolved open questions.\n")
                continue
            if draft["unclear"]:
                print(f"  note: {len(draft['unclear'])} open question(s) will publish "
                      "with this summary.")
            note = input("  note (optional) > ").strip()
            with store.connect() as conn:
                store.set_review(conn, draft["document_number"], store.STATUS_APPROVED, note)
            print("  approved\n")
        elif choice == "r":
            note = input("  why? > ").strip()
            with store.connect() as conn:
                store.set_review(conn, draft["document_number"], store.STATUS_REJECTED, note)
            print("  rejected\n")
        else:
            print("  skipped\n")

    return 0


def cmd_build(args) -> int:
    store.init_db()
    result = build_site.build()

    if result["count"] == 0:
        print("No approved summaries yet — the site will be empty. Run `review` first.")
    print(f"Wrote {result['count']} summaries to {result['path']}")
    print(f"  {result['species']} species and {result['regions']} regions available as filters.")
    print(f"  Feed: {result['feed_items']} items in feed.xml")
    print(f"  Page: {result['page_bytes'] / 1024:.0f} KB raw, roughly "
          f"{result['wire_bytes'] / 1024:.0f} KB compressed on the wire.")
    if result["size_warning"]:
        print(f"  ! {result['size_warning']}")
    print(f"  Open: {result['path'] / 'index.html'}")
    return 0


def cmd_status(args) -> int:
    store.init_db()
    with store.connect() as conn:
        tally = store.counts(conn)

    if not tally:
        print("Nothing in the database yet. Start with `fetch`.")
        return 0

    labels = {
        store.STATUS_NEW: "new, awaiting summary",
        store.STATUS_SUMMARIZED: "drafted, awaiting review",
        store.STATUS_APPROVED: "approved and publishable",
        store.STATUS_REJECTED: "rejected",
    }
    print(f"Database: {config.DB_PATH}")
    print()
    for status, label in labels.items():
        print(f"  {tally.get(status, 0):>4}  {label}")

    print()
    run = heartbeat.read()
    if run:
        print(f"Last automated run: {run['ran_at']}")
        print(f"  {heartbeat.headline(run)}")
    else:
        print("No automated run recorded here yet.")
        print("  The weekly job writes one every time it runs, even a quiet one.")
    return 0


def _write_step_summary(run: dict) -> None:
    """Put the outcome on the GitHub Actions run page, when we are in one.

    Costs nothing locally and saves opening the log just to find out whether a
    run did anything.
    """
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    fence = chr(96) * 3
    try:
        with open(path, "a", encoding="utf-8") as handle:
            print(f"### {heartbeat.headline(run)}", file=handle)
            print(file=handle)
            print(fence, file=handle)
            for line in heartbeat.lines(run)[2:]:
                print(line, file=handle)
            print(fence, file=handle)
    except OSError as exc:
        logging.warning("Could not write the step summary: %s", exc)


def cmd_run(args) -> int:
    """Fetch, then draft, then record that it happened.

    This is what the weekly job calls. It always writes a run record — after a
    busy week, a quiet one, or a failure — because otherwise all three look
    identical from the outside. It exits non-zero if anything went wrong at
    all, including a partial failure, so a run that half-worked cannot report
    success.
    """
    blocked = ""
    try:
        fetch_stats = _fetch(args.days)
        _report_fetch(fetch_stats)
    except fetch.FetchError as exc:
        logging.error("%s", exc)
        fetch_stats = {"fetched": 0, "added": 0, "skipped": 0}
        blocked = f"fetch failed: {exc}"

    print()
    if blocked:
        sum_stats = {"drafted": 0, "failed": 0, "blocked": blocked,
                     "input_tokens": 0, "output_tokens": 0}
        print("Skipping the draft step — the fetch did not complete.")
    else:
        sum_stats = _summarize(args.limit)
        _report_summarize(sum_stats)

    store.init_db()
    with store.connect() as conn:
        tally = store.counts(conn)

    run = heartbeat.record(
        days_back=args.days,
        fetched=fetch_stats["fetched"],
        added=fetch_stats["added"],
        drafted=sum_stats["drafted"],
        failed=sum_stats["failed"],
        blocked=sum_stats["blocked"],
        tally=tally,
    )
    path = heartbeat.write(run)

    print()
    for line in heartbeat.lines(run):
        print(line)
    print()
    print(f"Run record: {path}")
    _write_step_summary(run)

    return 1 if (sum_stats["blocked"] or sum_stats["failed"]) else 0


def cmd_heartbeat(args) -> int:
    """Report the last automated run. The workflow uses it for its commit message."""
    run = heartbeat.read()
    if not run:
        print("No run recorded yet.")
        return 1
    if args.headline:
        print(heartbeat.headline(run))
    else:
        for line in heartbeat.lines(run):
            print(line)
    return 0


# --- entry point ---------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="app.cli",
        description="Fisheries Regulation Digest pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_fetch = subparsers.add_parser("fetch", help="pull new notices")
    p_fetch.add_argument("--days", type=int, default=60, help="how far back to look (default 60)")
    p_fetch.set_defaults(func=cmd_fetch)

    p_sum = subparsers.add_parser("summarize", help="draft summaries for new notices")
    p_sum.add_argument("--limit", type=int, default=0, help="stop after N notices")
    p_sum.set_defaults(func=cmd_summarize)

    p_review = subparsers.add_parser("review", help="approve or reject drafts")
    p_review.add_argument("--strict", action="store_true",
                          help="refuse to approve a draft that still has open questions")
    p_review.set_defaults(func=cmd_review)

    p_build = subparsers.add_parser("build", help="generate the static site")
    p_build.set_defaults(func=cmd_build)

    p_status = subparsers.add_parser("status", help="show pipeline counts")
    p_status.set_defaults(func=cmd_status)

    p_run = subparsers.add_parser("run", help="fetch then summarize")
    p_run.add_argument("--days", type=int, default=60)
    p_run.add_argument("--limit", type=int, default=0)
    p_run.set_defaults(func=cmd_run)

    p_beat = subparsers.add_parser("heartbeat", help="what the last automated run found")
    p_beat.add_argument("--headline", action="store_true",
                        help="one line only, for a commit message")
    p_beat.set_defaults(func=cmd_heartbeat)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    try:
        return args.func(args)
    except fetch.FetchError as exc:
        logging.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
