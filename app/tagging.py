"""Species and region tagging against the controlled vocabularies.

Two jobs:
  1. Parse the vocabulary files in resources/ into canonical term lists.
  2. Validate tags — anything not in the vocabulary is dropped, never invented.
"""

from __future__ import annotations

import functools
import re

from . import config

# Bullet lines in the vocabulary files, e.g. "- Summer flounder (fluke)".
_BULLET = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
# A parenthetical alternate name: "Summer flounder (fluke)" -> "fluke".
_ALTERNATE = re.compile(r"^(?P<canonical>[^(]+?)\s*\((?P<alternate>[^)]+)\)\s*$")


def _parse_vocabulary(path) -> dict[str, str]:
    """Return {lowercase searchable term: canonical term}.

    Both the canonical name and any parenthetical alternate map to the canonical
    name, so "fluke" and "Summer flounder" both tag as "Summer flounder".
    """
    terms: dict[str, str] = {}
    if not path.exists():
        return terms

    for line in path.read_text(encoding="utf-8").splitlines():
        # Skip the blockquote status notices and headings.
        if line.lstrip().startswith((">", "#")):
            continue
        match = _BULLET.match(line)
        if not match:
            continue

        entry = match.group(1).strip()
        # Ignore prose bullets from the "Rules" sections. The word cap is the loose
        # filter and the trailing period is the reliable one — every prose bullet in
        # these files is a sentence. Eight words, because the real entries run long:
        # "Mid-Atlantic Bottom Longline Gear Restricted Area" is already six.
        if len(entry.split()) > 8 or entry.endswith("."):
            continue

        alternate_match = _ALTERNATE.match(entry)
        if alternate_match:
            canonical = alternate_match.group("canonical").strip()
            terms[alternate_match.group("alternate").strip().lower()] = canonical
        else:
            canonical = entry
        terms[canonical.lower()] = canonical

    return terms


@functools.lru_cache(maxsize=None)
def species_vocabulary() -> dict[str, str]:
    return _parse_vocabulary(config.SPECIES_LIST)


@functools.lru_cache(maxsize=None)
def region_vocabulary() -> dict[str, str]:
    return _parse_vocabulary(config.REGION_LIST)


def canonical_species() -> list[str]:
    return sorted(set(species_vocabulary().values()))


def canonical_regions() -> list[str]:
    return sorted(set(region_vocabulary().values()))


def validate(proposed: list[str], vocabulary: dict[str, str]) -> tuple[list[str], list[str]]:
    """Split proposed tags into (accepted canonical tags, dropped tags).

    A tag that is not in the vocabulary is dropped and reported. It is never
    silently kept and never guessed at.
    """
    accepted: list[str] = []
    dropped: list[str] = []

    for tag in proposed:
        key = (tag or "").strip().lower()
        if not key:
            continue
        if key in vocabulary:
            canonical = vocabulary[key]
            if canonical not in accepted:
                accepted.append(canonical)
        else:
            dropped.append(tag)

    return accepted, dropped


def find_in_text(text: str, vocabulary: dict[str, str]) -> list[str]:
    """Deterministic keyword pass over raw text.

    Matches on word boundaries so "scup" does not match inside another word.

    Not wired into the pipeline, and deliberately so. Word boundaries do not stop
    one vocabulary term matching inside a longer one: "Gulf of Maine" contains
    "Maine", so this would tag the state on a notice that only named the stock
    area. Use it as a reviewer's aid for spotting what a summary may have missed,
    not as a source of published tags.
    """
    found: list[str] = []
    lowered = (text or "").lower()

    for term, canonical in vocabulary.items():
        pattern = r"\b" + re.escape(term) + r"\b"
        if re.search(pattern, lowered) and canonical not in found:
            found.append(canonical)

    return sorted(found)
