"""Federal Register API client.

Pulls NOAA fishery notices. Collects only — never interprets, never edits source text.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

from . import config

log = logging.getLogger(__name__)


class FetchError(RuntimeError):
    """A source could not be read. Raised rather than swallowed on purpose."""


def get_text(url: str) -> str:
    """GET a plain document (not JSON) with the same retry policy."""
    last_error: Exception | None = None

    for attempt in range(1, config.RETRY_ATTEMPTS + 1):
        request = urllib.request.Request(url, headers={"User-Agent": config.user_agent()})
        try:
            with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            if attempt < config.RETRY_ATTEMPTS:
                wait = config.RETRY_BACKOFF * (2 ** (attempt - 1))
                log.warning("Text fetch attempt %d/%d failed (%s). Retrying in %.0fs.",
                            attempt, config.RETRY_ATTEMPTS, exc, wait)
                time.sleep(wait)

    raise FetchError(f"Could not fetch {url}: {last_error}")


def _build_url(cfr_part: str, since: date, per_page: int) -> str:
    params = [
        ("per_page", str(per_page)),
        ("order", "newest"),
        ("conditions[cfr][title]", config.FR_CFR_TITLE),
        ("conditions[cfr][part]", cfr_part),
        ("conditions[publication_date][gte]", since.isoformat()),
    ]
    params += [("fields[]", f) for f in config.FR_FIELDS]
    return f"{config.FR_API}?{urllib.parse.urlencode(params)}"


def _get_json(url: str) -> dict:
    """GET with retries. Raises FetchError once attempts are exhausted."""
    last_error: Exception | None = None

    for attempt in range(1, config.RETRY_ATTEMPTS + 1):
        request = urllib.request.Request(
            url, headers={"User-Agent": config.user_agent(), "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
            last_error = exc
            if attempt < config.RETRY_ATTEMPTS:
                wait = config.RETRY_BACKOFF * (2 ** (attempt - 1))
                log.warning("Fetch attempt %d/%d failed (%s). Retrying in %.0fs.",
                            attempt, config.RETRY_ATTEMPTS, exc, wait)
                time.sleep(wait)

    raise FetchError(f"Could not fetch {url}: {last_error}")


def _build_term_url(term: str, since: date, per_page: int) -> str:
    """Query by title phrase, scoped to NOAA. Catches Notices, which amend no CFR part."""
    params = [
        ("per_page", str(per_page)),
        ("order", "newest"),
        ("conditions[agencies][]", config.FR_AGENCY),
        ("conditions[term]", term),
        ("conditions[publication_date][gte]", since.isoformat()),
    ]
    params += [("fields[]", f) for f in config.FR_FIELDS]
    return f"{config.FR_API}?{urllib.parse.urlencode(params)}"


def _paginate(url: str, label: str, max_pages: int) -> list[dict]:
    """Follow `next_page_url` up to `max_pages`, collecting results."""
    results: list[dict] = []
    pages = 0

    while url and pages < max_pages:
        payload = _get_json(url)
        results.extend(payload.get("results") or [])
        pages += 1

        url = payload.get("next_page_url")
        if url:
            time.sleep(1)  # rate-limit ourselves

    if pages >= max_pages and url:
        log.warning(
            "%s hit the %d-page cap and more results remain. Narrow --days or "
            "raise max_pages.",
            label,
            max_pages,
        )

    return results


def _fetch_part(cfr_part: str, since: date, max_pages: int) -> list[dict]:
    """Every result for one CFR part."""
    return _paginate(
        _build_url(cfr_part, since, config.FR_PER_PAGE), f"50 CFR {cfr_part}", max_pages
    )


def _fetch_term(term: str, since: date, max_pages: int) -> list[dict]:
    """Every result for one title phrase."""
    return _paginate(
        _build_term_url(term, since, config.FR_PER_PAGE), f"title {term}", max_pages
    )


def fetch_notices(days_back: int = 60, max_pages: int = 10) -> list[dict]:
    """Return notices published in the last `days_back` days, newest first.

    Two passes. First each configured CFR part, which catches everything that
    amends the regulations. Then each title phrase, which catches Notices that
    amend nothing and so carry no CFR reference. The API takes one part and one
    term per request, so each is its own query; results merge on document number,
    and a document found twice is returned once.

    The page cap per query is deliberate — an unbounded crawl of a public agency
    API is rude and usually a bug.
    """
    since = date.today() - timedelta(days=days_back)
    merged: dict[str, dict] = {}
    programs: dict[str, list[str]] = {}
    overlaps = 0

    def absorb(results: list[dict], label: str, query_key: str) -> None:
        """Merge one query's results, recording which program the query represents."""
        nonlocal overlaps
        program = config.PROGRAM_LABELS.get(query_key)
        new_here = 0

        for result in results:
            document_number = result.get("document_number")
            if not document_number:
                continue

            if program:
                seen = programs.setdefault(document_number, [])
                if program not in seen:
                    seen.append(program)

            if document_number in merged:
                overlaps += 1
                continue
            merged[document_number] = result
            new_here += 1

        log.info("%s: %d result(s), %d new.", label, len(results), new_here)

    for cfr_part, description in config.FR_CFR_PARTS.items():
        absorb(_fetch_part(cfr_part, since, max_pages),
               f"50 CFR {cfr_part} — {description}", cfr_part)

    for term in config.FR_TITLE_TERMS:
        absorb(_fetch_term(term, since, max_pages), f"title {term}", term)

    # Attach provenance to each result so normalize() can carry it to the store.
    for document_number, result in merged.items():
        result["_programs"] = sorted(programs.get(document_number, []))

    if overlaps:
        log.info("%d result(s) matched more than one query and were merged.", overlaps)

    notices = sorted(
        merged.values(), key=lambda r: r.get("publication_date") or "", reverse=True
    )
    log.info("Fetched %d unique notice(s) since %s.", len(notices), since)
    return notices


def normalize(raw: dict) -> dict:
    """Flatten one API result into the shape the store expects.

    Nothing is invented. A field the API did not supply stays empty.
    """
    agencies = raw.get("agencies") or []
    agency_names = ", ".join(a.get("name", "") for a in agencies if a.get("name"))

    return {
        "document_number": raw.get("document_number") or "",
        "title": (raw.get("title") or "").strip(),
        "doc_type": raw.get("type") or "",
        "publication_date": raw.get("publication_date") or "",
        "effective_on": raw.get("effective_on") or "",
        "html_url": raw.get("html_url") or "",
        "abstract": (raw.get("abstract") or "").strip(),
        "agency": agency_names,
        "body_html_url": raw.get("body_html_url") or "",
        "programs": raw.get("_programs") or [],
        "raw_json": json.dumps(raw, sort_keys=True),
    }
