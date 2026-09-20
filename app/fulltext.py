"""Fetch the full text of a Federal Register document.

The abstract is too thin to summarize from — it routinely omits the quota figures,
fee rates, and deadlines that make a notice worth reading. The full document has
them.

Two URLs are offered per document. `raw_text_url` returns 403 (verified 2026-09-20),
so this uses `body_html_url` and strips the markup with the standard library. No new
dependency for one small job.
"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser

from . import config, fetch

log = logging.getLogger(__name__)

# Tags whose contents are never body text.
_SKIP = {"script", "style", "head", "meta", "link", "noscript"}
# Tags that imply a line break when they close.
_BLOCK = {
    "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "section", "article", "blockquote",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self._skip_depth += 1
        elif tag in _BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._skip_depth == 0:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        # Collapse runs of spaces, then runs of blank lines, keeping paragraphs.
        raw = re.sub(r"[ \t ]+", " ", raw)
        raw = re.sub(r" *\n *", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


# Every Federal Register page opens with the same "Document headings vary by
# document type..." explainer. It is page furniture, identical on every document,
# and only dilutes the prompt. The real document starts at the AGENCY: heading.
#
# Cut at the issuing department line, which sits just above it and starts the real
# document. Falls back to the AGENCY: heading, then to keeping everything — an
# unexpected layout should cost context, never content.
_DOCUMENT_STARTS = (
    re.compile(r"^Department of\b", re.MULTILINE),
    re.compile(r"^AGENCY:", re.MULTILINE),
)


def _trim_boilerplate(text: str) -> str:
    for pattern in _DOCUMENT_STARTS:
        match = pattern.search(text)
        if match:
            return text[match.start():].strip()
    return text


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return _trim_boilerplate(parser.text())


def fetch_text(body_html_url: str) -> tuple[str, bool]:
    """Return (text, truncated) for one document.

    Truncation is reported, never silent — the caller tells the model the text was
    cut so it can say so rather than summarizing a document it only half saw.
    """
    if not body_html_url:
        return "", False

    html = fetch.get_text(body_html_url)
    text = html_to_text(html)

    limit = config.MAX_FULL_TEXT_CHARS
    if len(text) > limit:
        log.warning(
            "Full text is %d chars, over the %d limit. Truncating and flagging it.",
            len(text),
            limit,
        )
        return text[:limit], True

    return text, False
