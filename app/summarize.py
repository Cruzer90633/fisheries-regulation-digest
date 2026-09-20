"""Draft a plain-English summary of one notice using Claude.

Design notes:
  * Structured output. The model returns a fixed JSON schema -- no free-form parsing.
  * The effective date is NOT generated. It comes from the Federal Register and is
    passed to the model as context only.
  * Tags are validated against resources/ vocabularies afterwards. Invented tags are
    dropped and recorded, not silently accepted.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import anthropic

from . import config, tagging

log = logging.getLogger(__name__)


class SummarizeError(RuntimeError):
    """The model did not return a usable summary."""


SYSTEM_PROMPT = """You summarize United States fishery regulation notices for a public
audience: students, commercial and recreational fishermen, and interested members of
the public.

Write the way an experienced practitioner would explain the change to a smart person
who does not read the Federal Register. Short sentences. Plain words. Roughly an
8th-grade reading level. Expand every acronym the first time you use it.

Hard rules, in order of importance:

1. Never state a fact that is not in the notice you are given. No numbers, dates,
   species, areas, or limits that do not appear in the source text.
2. Do not interpret the law. Describe what changed. Do not tell anyone what they must
   do, may do, or are prohibited from doing.
3. Do not give compliance advice.
4. If something is genuinely unclear from the text you were given -- and short
   abstracts often are -- put it in the `unclear` array. A reviewer will pull the full
   notice. Do not paper over a gap with a confident sentence.
5. Use only the species and region tags from the lists provided. If the notice names
   something not on a list, leave it out of the tags and note it in `unclear`.
5a. Tag the narrowest area the notice names, plus the broader area containing it. If a
   rule applies to the whole U.S. Atlantic -- an ocean-basin quota, or a gear rule
   spanning the Atlantic Ocean, Gulf of America, and Caribbean Sea -- also tag
   "Greater Atlantic", because such a rule reaches waters from Maine to Cape Hatteras
   and binds readers there. The one exception: if every area the notice names lies
   outside that range, such as a Gulf of America-only closure, use the basin tag alone.
6. Do not include the effective date in your prose. It is recorded separately from an
   authoritative field.

Tone: direct and useful. No filler, no hedging boilerplate, no "it is important to
note". If the change is small, say so briefly rather than padding it."""

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "what_changed": {
            "type": "string",
            "description": (
                "2-4 plain-English sentences saying what is different now compared to "
                "before. No interpretation of obligations."
            ),
        },
        "who_affected": {
            "type": "string",
            "description": (
                "1-2 sentences naming the fisheries, permit holders, or areas the "
                "notice itself names. Only what the source states."
            ),
        },
        "key_details": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Short bullet facts taken straight from the notice: limits, quotas, "
                "areas, sizes. Keep the source's exact figures and units. Empty array "
                "if the source gives no specifics."
            ),
        },
        "species": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Species tags, chosen only from the allowed species list.",
        },
        "regions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Region tags, chosen only from the allowed region list.",
        },
        "unclear": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Anything you could not determine from the text provided. Each entry "
                "is one specific question for the human reviewer. Empty array if the "
                "notice was fully clear."
            ),
        },
    },
    "required": [
        "what_changed",
        "who_affected",
        "key_details",
        "species",
        "regions",
        "unclear",
    ],
    "additionalProperties": False,
}


def _build_user_message(notice: dict) -> str:
    species = ", ".join(tagging.canonical_species()) or "(vocabulary file is empty)"
    regions = ", ".join(tagging.canonical_regions()) or "(vocabulary file is empty)"
    abstract = notice.get("abstract") or "(no abstract supplied by the Federal Register)"
    effective = notice.get("effective_on") or "not stated"
    full_text = notice.get("full_text") or ""

    if full_text:
        warning = ""
        if notice.get("full_text_truncated"):
            warning = (
                "\n\n[NOTE: this document was too long to include in full and has "
                "been cut off. Say so in `unclear` if what you were given looks "
                "incomplete.]"
            )
        body = "FULL DOCUMENT TEXT:\n" + full_text + warning + "\n\n"
        closing = (
            "Base the summary on the full document text. It carries the figures, "
            "dates, and specifics the abstract leaves out. Use `unclear` only for "
            "things the full text genuinely does not settle.\n"
        )
    else:
        body = ""
        closing = (
            "Only the abstract was available, not the full document. Abstracts omit "
            "figures and deadlines. Say what is missing in `unclear` rather than "
            "guessing at the content of the full rule.\n"
        )

    return (
        "Summarize this Federal Register notice.\n\n"
        f"TITLE: {notice.get('title', '')}\n"
        f"DOCUMENT TYPE: {notice.get('doc_type', '')}\n"
        f"AGENCY: {notice.get('agency', '')}\n"
        f"PUBLISHED: {notice.get('publication_date', '')}\n"
        f"EFFECTIVE DATE (recorded separately -- do not repeat it in your prose): {effective}\n"
        f"SOURCE URL: {notice.get('html_url', '')}\n\n"
        f"ABSTRACT:\n{abstract}\n\n"
        f"{body}"
        f"ALLOWED SPECIES TAGS:\n{species}\n\n"
        f"ALLOWED REGION TAGS:\n{regions}\n\n"
        + closing
    )

def _call_claude(client: anthropic.Anthropic, notice: dict):
    kwargs = {
        "model": config.MODEL,
        "max_tokens": config.MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": config.EFFORT,
            "format": {"type": "json_schema", "schema": SUMMARY_SCHEMA},
        },
        "messages": [{"role": "user", "content": _build_user_message(notice)}],
    }

    if config.USE_REFUSAL_FALLBACKS:
        try:
            return client.beta.messages.create(
                betas=[config.REFUSAL_FALLBACK_BETA],
                fallbacks="default",
                **kwargs,
            )
        except anthropic.BadRequestError as exc:
            # The beta flag is not enabled for this account, or a gateway blocks it.
            # Say so plainly and carry on without it.
            log.warning(
                "Refusal fallbacks rejected (%s). Retrying without them. Set "
                "USE_REFUSAL_FALLBACKS = False in app/config.py to skip this.",
                exc,
            )

    return client.messages.create(**kwargs)


def credential_problem() -> str | None:
    """Return a plain-English reason the Claude API is unreachable, or None.

    Call this before a batch. The SDK raises a bare TypeError when no credential
    can be resolved, which is easy to miss and ugly when it surfaces — better to
    say so once, up front, than to fail per notice.
    """
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return None

    profile = Path.home() / ".config" / "anthropic"
    if profile.exists():
        return None

    return (
        "No Claude credentials found. Set ANTHROPIC_API_KEY, or run `ant auth login`.\n"
        "  Windows:  setx ANTHROPIC_API_KEY \"sk-ant-...\"  (then reopen the terminal)"
    )


def summarize(notice: dict, client: anthropic.Anthropic | None = None) -> dict:
    """Return a validated draft summary for one notice.

    Raises SummarizeError if the model refuses, truncates, or returns bad JSON.
    """
    client = client or anthropic.Anthropic()

    try:
        response = _call_claude(client, notice)
    except anthropic.AuthenticationError as exc:
        raise SummarizeError(
            "Claude rejected the credentials. Set ANTHROPIC_API_KEY or run "
            "`ant auth login`."
        ) from exc
    except anthropic.RateLimitError as exc:
        retry_after = exc.response.headers.get("retry-after", "60")
        raise SummarizeError(f"Rate limited. Retry after {retry_after}s.") from exc
    except anthropic.APIStatusError as exc:
        raise SummarizeError(f"Claude API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise SummarizeError(f"Could not reach the Claude API: {exc}") from exc
    except TypeError as exc:
        # The SDK raises a bare TypeError when it cannot resolve any credential.
        # Translate it rather than letting a traceback reach the user.
        if "authentication method" in str(exc):
            raise SummarizeError(
                credential_problem() or "Claude credentials could not be resolved."
            ) from exc
        raise

    # Check why generation stopped before trusting the content.
    if response.stop_reason == "refusal":
        detail = ""
        if response.stop_details:
            detail = getattr(response.stop_details, "explanation", "") or ""
        raise SummarizeError(f"Model declined to summarize this notice. {detail}".strip())
    if response.stop_reason == "max_tokens":
        raise SummarizeError("Response hit max_tokens and is truncated. Raise MAX_TOKENS.")

    text = next((block.text for block in response.content if block.type == "text"), None)
    if not text:
        raise SummarizeError("Model returned no text block.")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SummarizeError(f"Model returned invalid JSON: {exc}") from exc

    summary = validate_tags(data)
    summary["usage"] = {
        "input_tokens": getattr(response.usage, "input_tokens", 0),
        "output_tokens": getattr(response.usage, "output_tokens", 0),
    }
    return summary


def validate_tags(data: dict) -> dict:
    """Drop any tag outside the controlled vocabulary, and record what was dropped."""
    species, dropped_species = tagging.validate(
        data.get("species", []), tagging.species_vocabulary()
    )
    regions, dropped_regions = tagging.validate(
        data.get("regions", []), tagging.region_vocabulary()
    )

    dropped = dropped_species + dropped_regions
    if dropped:
        log.warning(
            "Dropped %d tag(s) outside the vocabulary: %s", len(dropped), ", ".join(dropped)
        )

    return {
        "what_changed": (data.get("what_changed") or "").strip(),
        "who_affected": (data.get("who_affected") or "").strip(),
        "key_details": [d.strip() for d in data.get("key_details", []) if d and d.strip()],
        "species": species,
        "regions": regions,
        "unclear": [u.strip() for u in data.get("unclear", []) if u and u.strip()],
        "dropped_tags": dropped,
    }
