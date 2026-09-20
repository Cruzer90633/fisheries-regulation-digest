"""SQLite storage.

One table. Status moves one way: new -> summarized -> approved.
Nothing renders on the site until it is approved.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

STATUS_NEW = "new"
STATUS_SUMMARIZED = "summarized"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

SCHEMA = """
CREATE TABLE IF NOT EXISTS notices (
    document_number      TEXT PRIMARY KEY,
    title                TEXT NOT NULL,
    doc_type             TEXT,
    publication_date     TEXT,
    effective_on         TEXT,
    html_url             TEXT NOT NULL,
    abstract             TEXT,
    agency               TEXT,
    raw_json             TEXT,
    body_html_url        TEXT,
    programs             TEXT,   -- JSON array: which regulatory programs matched
    full_text            TEXT,
    full_text_truncated  INTEGER DEFAULT 0,

    status               TEXT NOT NULL DEFAULT 'new',
    what_changed         TEXT,
    who_affected         TEXT,
    key_details          TEXT,   -- JSON array
    species              TEXT,   -- JSON array
    regions              TEXT,   -- JSON array
    unclear              TEXT,   -- JSON array
    dropped_tags         TEXT,   -- JSON array, tags Claude proposed that failed validation

    input_tokens         INTEGER,
    output_tokens        INTEGER,

    first_seen_at        TEXT NOT NULL,
    summarized_at        TEXT,
    reviewed_at          TEXT,
    reviewer_note        TEXT
);

CREATE INDEX IF NOT EXISTS idx_notices_status ON notices(status);
CREATE INDEX IF NOT EXISTS idx_notices_pubdate ON notices(publication_date DESC);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(db_path=None):
    """Yield a connection with row access by name. Commits on clean exit."""
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# Columns added after the first release. An existing database gets them on the next
# init rather than needing to be rebuilt — a summary already written is worth more
# than a clean schema.
_ADDED_COLUMNS = {
    "body_html_url": "TEXT",
    "programs": "TEXT",
    "full_text": "TEXT",
    "full_text_truncated": "INTEGER DEFAULT 0",
    "input_tokens": "INTEGER",
    "output_tokens": "INTEGER",
}


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(notices)")}
    for column, column_type in _ADDED_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE notices ADD COLUMN {column} {column_type}")


def init_db(db_path=None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def upsert_notice(conn: sqlite3.Connection, notice: dict) -> bool:
    """Insert a notice if it is new. Returns True only if it was newly inserted.

    A summary already written is never clobbered by a re-fetch. The only fields
    refreshed on an existing row are provenance — which programs matched, and the
    full-text URL if we did not have one. Both are metadata about where the notice
    came from, not claims about what it says.
    """
    if not notice.get("document_number"):
        raise ValueError("notice has no document_number; refusing to store it")

    # rowcount cannot distinguish insert from update once ON CONFLICT is in play,
    # so ask first. Cheap: document_number is the primary key.
    existed = conn.execute(
        "SELECT 1 FROM notices WHERE document_number = ?",
        (notice["document_number"],),
    ).fetchone() is not None

    conn.execute(
        """
        INSERT INTO notices (
            document_number, title, doc_type, publication_date, effective_on,
            html_url, abstract, agency, raw_json, body_html_url, programs,
            status, first_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_number) DO UPDATE SET
            programs      = excluded.programs,
            body_html_url = COALESCE(NULLIF(notices.body_html_url, ''),
                                     excluded.body_html_url)
        """,
        (
            notice["document_number"],
            notice["title"],
            notice.get("doc_type", ""),
            notice.get("publication_date", ""),
            notice.get("effective_on", ""),
            notice.get("html_url", ""),
            notice.get("abstract", ""),
            notice.get("agency", ""),
            notice.get("raw_json", ""),
            notice.get("body_html_url", ""),
            json.dumps(notice.get("programs", [])),
            STATUS_NEW,
            _now(),
        ),
    )
    return not existed


def save_full_text(conn: sqlite3.Connection, document_number: str, text: str,
                   truncated: bool) -> None:
    """Cache the document text so a re-run does not re-fetch it."""
    conn.execute(
        "UPDATE notices SET full_text = ?, full_text_truncated = ? WHERE document_number = ?",
        (text, 1 if truncated else 0, document_number),
    )


def by_status(conn: sqlite3.Connection, status: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM notices WHERE status = ? ORDER BY publication_date DESC",
        (status,),
    ).fetchall()


def get(conn: sqlite3.Connection, document_number: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM notices WHERE document_number = ?", (document_number,)
    ).fetchone()


def save_summary(conn: sqlite3.Connection, document_number: str, summary: dict,
                 usage: dict | None = None) -> None:
    """Store a draft summary and move the notice to 'summarized'.

    Note what is absent: effective_on. That value comes from the Federal Register
    and is never written by the summarizer.
    """
    conn.execute(
        """
        UPDATE notices
           SET what_changed  = ?,
               who_affected  = ?,
               key_details   = ?,
               species       = ?,
               regions       = ?,
               unclear       = ?,
               dropped_tags  = ?,
               input_tokens  = ?,
               output_tokens = ?,
               status        = ?,
               summarized_at = ?
         WHERE document_number = ?
        """,
        (
            summary.get("what_changed", ""),
            summary.get("who_affected", ""),
            json.dumps(summary.get("key_details", [])),
            json.dumps(summary.get("species", [])),
            json.dumps(summary.get("regions", [])),
            json.dumps(summary.get("unclear", [])),
            json.dumps(summary.get("dropped_tags", [])),
            (usage or {}).get("input_tokens"),
            (usage or {}).get("output_tokens"),
            STATUS_SUMMARIZED,
            _now(),
            document_number,
        ),
    )


def set_review(conn: sqlite3.Connection, document_number: str, status: str, note: str = "") -> None:
    if status not in (STATUS_APPROVED, STATUS_REJECTED):
        raise ValueError(f"not a review outcome: {status}")
    conn.execute(
        "UPDATE notices SET status = ?, reviewed_at = ?, reviewer_note = ? WHERE document_number = ?",
        (status, _now(), note, document_number),
    )


def approved(conn: sqlite3.Connection) -> list[dict]:
    """Approved notices, newest first, with JSON columns decoded."""
    rows = conn.execute(
        "SELECT * FROM notices WHERE status = ? ORDER BY publication_date DESC",
        (STATUS_APPROVED,),
    ).fetchall()
    return [to_dict(row) for row in rows]


def to_dict(row: sqlite3.Row) -> dict:
    """Row to plain dict, decoding the JSON array columns."""
    record = dict(row)
    for field in ("key_details", "species", "regions", "unclear", "dropped_tags",
                  "programs"):
        raw = record.get(field)
        try:
            record[field] = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            record[field] = []
    return record


def counts(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM notices GROUP BY status").fetchall()
    return {row["status"]: row["n"] for row in rows}
