"""A record of the last automated run.

The weekly job commits this file whether or not it found anything, and that is
the whole point. Without it, three very different outcomes all look the same
from the outside — nothing new was published this week, the job broke, or the
schedule stopped firing and nobody noticed. A commit every Monday makes the
quiet weeks legible and makes a missing week obvious.

It also keeps the schedule alive. GitHub documents that in a public repository,
scheduled workflows are automatically disabled after 60 days with no repository
activity. A weekly commit is activity, so the cron cannot quietly lapse during a
slow stretch.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config, store

PATH = config.DATA_DIR / "last-run.json"


def record(days_back, fetched, added, drafted, failed, blocked, tally) -> dict:
    """Build the run record. Pure — writing is a separate step."""
    return {
        "ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days_back": days_back,
        "fetched": fetched,
        "new": added,
        "drafted": drafted,
        "failed": failed,
        "blocked": blocked or "",
        "awaiting_review": tally.get(store.STATUS_SUMMARIZED, 0),
        "published": tally.get(store.STATUS_APPROVED, 0),
    }


def headline(run: dict) -> str:
    """One line, readable as a commit subject or a notification.

    Written so that the thing you most need to know comes first. A run that
    could not draft anything must not read like a quiet week.
    """
    if run.get("blocked"):
        return f"Weekly run: could not draft — {run['blocked']}"
    failed = run.get("failed", 0)
    drafted = run.get("drafted", 0)
    if failed and drafted:
        return f"Weekly run: {drafted} drafted, {failed} failed — check the log"
    if failed:
        return f"Weekly run: {failed} notice(s) failed to draft — check the log"
    if drafted:
        return f"Weekly run: {drafted} new summary(ies) awaiting review"
    if run.get("new"):
        return f"Weekly run: {run['new']} new notice(s) fetched, none drafted"
    return "Weekly run: nothing new"


def lines(run: dict) -> list[str]:
    """The record as a short human report."""
    out = [
        headline(run),
        "",
        f"Ran at        {run['ran_at']} (looked back {run['days_back']} days)",
        f"Fetched       {run['fetched']} notice(s), {run['new']} not seen before",
        f"Drafted       {run['drafted']}, failed {run['failed']}",
        f"Awaiting you  {run['awaiting_review']} draft(s) to review",
        f"Published     {run['published']} approved summary(ies)",
    ]
    if run.get("blocked"):
        out.append(f"Blocked       {run['blocked']}")
    return out


def write(run: dict, path: Path | None = None) -> Path:
    target = Path(path) if path else PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    return target


def read(path: Path | None = None) -> dict | None:
    """The last recorded run, or None if the job has never run here."""
    target = Path(path) if path else PATH
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
