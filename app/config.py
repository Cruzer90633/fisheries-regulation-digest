"""Configuration. Everything tunable lives here."""

from pathlib import Path

# --- Paths ---------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "digest.db"

RESOURCES_DIR = ROOT / "resources"
SPECIES_LIST = RESOURCES_DIR / "species-list.md"
REGION_LIST = RESOURCES_DIR / "region-list.md"

# GitHub Pages serves from the repository root or a folder named "docs" — those are
# the only two choices it offers. So the generated site goes to docs/ rather than
# under outputs/, even though it is generated output. This folder is committed; it
# is what the public actually reads.
SITE_DIR = ROOT / "docs"

# --- Federal Register API ------------------------------------------------
# Verified working 2026-09-20. See resources/source-registry.md.

FR_API = "https://www.federalregister.gov/api/v1/documents.json"

# Filter by the Code of Federal Regulations part a document affects, not by a
# phrase in its title. A title phrase is editorial and inconsistent; the CFR part
# is what the rule actually amends, so it does not drift.
#
# The API accepts one part per query — a comma-separated list is rejected with
# "CFR part must be an integer or a range" — so the fetcher queries each part in
# turn and merges the results by document number.
FR_CFR_TITLE = "50"

FR_CFR_PARTS = {
    "648": "Fisheries of the Northeastern United States (GARFO, MAFMC, NEFMC)",
    "635": "Atlantic Highly Migratory Species (tunas, swordfish, billfish, sharks)",
    "697": "Atlantic Coastal Fisheries Cooperative Management (ASMFC species, lobster)",
}

# Part 229 (Atlantic Large Whale Take Reduction Plan) is deliberately not here. It
# regulates lobster and gillnet gear, so it is arguably in scope, but it is
# protected-resources work and would pull in a lot of marine mammal content. Add
# it above if you decide you want it.

FR_AGENCY = "national-oceanic-and-atmospheric-administration"

# A CFR-part query catches everything that amends the regulations, which is every
# rule and proposed rule. It does NOT catch Notices, because a notice amends
# nothing — a request for information or a meeting announcement carries no CFR
# reference. Verified 2026-06-22 to 2026-09-20: part 648 returned 11 documents
# while the old title-phrase filter returned 12, and the extra one was a Notice.
#
# So these title phrases run as a second pass, scoped to NOAA, and merge into the
# same result set. Together the two passes are strictly broader than either alone.
# What each query means in plain English. Shown on the card so a reader can tell at
# a glance whether a notice is a Northeast council action, a highly migratory
# species action, or an interstate coastal one. Derived from the query that matched,
# never guessed from the title.
PROGRAM_LABELS = {
    "648": "Greater Atlantic",
    "635": "Highly Migratory Species",
    "697": "Atlantic Coastal",
    '"Fisheries of the Northeastern United States"': "Greater Atlantic",
    '"Atlantic Highly Migratory Species"': "Highly Migratory Species",
    '"Atlantic Coastal Fisheries Cooperative Management"': "Atlantic Coastal",
}

FR_TITLE_TERMS = [
    '"Fisheries of the Northeastern United States"',
    '"Atlantic Highly Migratory Species"',
    '"Atlantic Coastal Fisheries Cooperative Management"',
]

FR_FIELDS = [
    "title",
    "type",
    "document_number",
    "publication_date",
    "effective_on",
    "html_url",
    "abstract",
    "agencies",
    "body_html_url",
]

FR_PER_PAGE = 100

# Be a good citizen. These are public agencies, not a CDN.
#
# Set this to the project's public repository once it exists. Agencies that notice
# unusual traffic can then find out what this is and open an issue. Leave it empty
# rather than filling in a guess: an unreachable URL in a User-Agent is worse than
# no URL, because it wastes the time of whoever tries to follow it.
#
# A contact email would also be acceptable here, but a repository URL keeps a
# personal address out of federal server logs.
PROJECT_URL = "https://github.com/Cruzer90633/fisheries-regulation-digest"


def user_agent() -> str:
    """Identify this client honestly. Never advertise a URL we do not have."""
    base = "FisheriesRegulationDigest/0.1"
    return f"{base} (+{PROJECT_URL})" if PROJECT_URL else base


# Full document text. The abstract alone omits quota figures, fee rates, and
# deadlines, so the summarizer reads the whole document. `raw_text_url` returns 403,
# so `body_html_url` is used and stripped to text.
#
# The cap is a cost guard, not a correctness one. Opus 5 has a 1M context, but a
# 250k-character document is roughly 60k tokens, about 30 cents of input at
# $5/MTok. Over the cap the text is cut AND the model is told it was cut.
MAX_FULL_TEXT_CHARS = 250_000

REQUEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = 2.0  # seconds, doubled each attempt

# --- Claude --------------------------------------------------------------

MODEL = "claude-opus-5"
MAX_TOKENS = 16000
EFFORT = "high"  # accuracy matters more than cost on regulatory text

# Server-side refusal fallbacks. Harmless here, but on by default per Anthropic
# guidance. Set False if your account or gateway rejects the beta flag.
USE_REFUSAL_FALLBACKS = True
REFUSAL_FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Published Claude Opus 5 rates, US dollars per million tokens. Used only to turn
# logged token counts into an estimate — check your Console for actual billing.
PRICE_INPUT_PER_MTOK = 5.00
PRICE_OUTPUT_PER_MTOK = 25.00


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Dollar estimate for one call."""
    return (
        input_tokens / 1_000_000 * PRICE_INPUT_PER_MTOK
        + output_tokens / 1_000_000 * PRICE_OUTPUT_PER_MTOK
    )

# --- Site ----------------------------------------------------------------

SITE_URL = "https://cruzer90633.github.io/fisheries-regulation-digest/"

# Crawlers are asked to stay away. This is a deliberate choice, not an oversight:
# the site is shared by link while it finds its audience, rather than turning up in
# search results for regulatory questions before it has been used in anger.
#
# robots.txt is a request, not a control. It is honoured by the major search engines
# and ignored by anyone who does not care. Nothing here is private — the site is
# public and unauthenticated, and every summary links to a public federal document.
# To reverse this, replace Disallow with Allow and rebuild.
ROBOTS_TXT = """User-agent: *
Disallow: /
"""

SITE_TITLE = "Fisheries Regulation Digest"
SITE_TAGLINE = "Plain-English summaries of Mid-Atlantic and Greater Atlantic fishery rules."
SITE_DISCLAIMER = (
    "Plain-English summaries for orientation only. This is not legal advice and not an "
    "official source. Always confirm against the linked original notice before acting "
    "on a regulation."
)
