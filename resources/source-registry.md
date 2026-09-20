# Source Registry

Where notices come from. Every entry below was tested live on **2026-09-20**; the
result of each test is recorded. Re-verify before any build work starts.

---

## 1. Federal Register API — the backbone

**URL:** `https://www.federalregister.gov/api/v1/documents.json`
**Format:** JSON API, public, no key required
**Verified working:** 2026-09-20 — returned 200 with structured results
**Covers:** every final rule, proposed rule, and notice NOAA publishes. The pipeline
narrows this to three families: Northeast council actions (GARFO, MAFMC, NEFMC),
Atlantic Highly Migratory Species actions, and Atlantic Coastal Fisheries Cooperative
Management actions.

**Why it matters:** this is the only source that gives a machine-readable effective
date and a permanent document number. Everything else is an announcement *about* a
rule. This is the rule.

**Working queries (tested 2026-09-20).** Two passes, merged on `document_number`.

*Pass 1 — by CFR part.* Catches everything that amends the regulations, which is every
rule and proposed rule. One part per request; a comma-separated list is rejected with
"CFR part must be an integer or a range".

```
https://www.federalregister.gov/api/v1/documents.json
  ?per_page=100
  &order=newest
  &conditions[cfr][title]=50
  &conditions[cfr][part]=648          # repeat for 635 and 697
  &conditions[publication_date][gte]=YYYY-MM-DD
  &fields[]=title&fields[]=type&fields[]=document_number
  &fields[]=publication_date&fields[]=effective_on&fields[]=html_url
  &fields[]=abstract&fields[]=agencies
```

| Part | Covers | All-time count |
| --- | --- | --- |
| 50 CFR 648 | Fisheries of the Northeastern United States (GARFO, MAFMC, NEFMC) | 2,402 |
| 50 CFR 635 | Atlantic Highly Migratory Species (tunas, swordfish, billfish, sharks) | 805 |
| 50 CFR 697 | Atlantic Coastal Fisheries Cooperative Management (ASMFC species, lobster) | 105 |

*Pass 2 — by title phrase, scoped to NOAA.* Catches Notices, which amend nothing and
therefore carry no CFR reference.

```
  &conditions[agencies][]=national-oceanic-and-atmospheric-administration
  &conditions[term]="Fisheries of the Northeastern United States"
```

Repeat for `"Atlantic Highly Migratory Species"` and `"Atlantic Coastal Fisheries
Cooperative Management"`.

**Why both passes.** Measured over 2026-06-22 to 2026-09-20: part 648 returned 11
documents while the title phrase returned 12. The one difference was a Notice —
"Request for Information on Ropeless Fishing" — which amends no CFR part. CFR filtering
is more precise and does not drift with editorial title choices, but it is blind to
notices. Together the two passes returned 23 unique documents where the original
single-phrase filter returned 12.

**Stable ID:** `document_number` (e.g. `2026-18623`)

---

## 2. GARFO bulletins

**Listing URL:** `https://www.fisheries.noaa.gov/news-and-announcements/bulletins`
**Region-filtered:** append `?field_region_vocab_target_id[1000001111]=1000001111`
**Verified working:** 2026-09-20 — filtered listing returned 200 HTML
**Item URL pattern:** `https://www.fisheries.noaa.gov/bulletin/<slug>`
**Format:** HTML only. **No RSS.** Tested and 404'd: `/rss.xml`,
`/rss/bulletins.xml`, `/news-and-announcements/bulletins/feed`.

**Covers:** the plain-language announcements GARFO sends to industry — closures,
quota transfers, permit deadlines, framework implementations.

**Stable ID:** the bulletin slug in the URL.
**Caveat:** scraping HTML is brittle. The page is Drupal; markup can change without
notice. Pair this with the Federal Register API rather than relying on it alone.

**Also seen:** bulletins are mirrored to GovDelivery at
`https://content.govdelivery.com/bulletins/gd/USNOAAFISHERIES-<id>`. Not evaluated as
an ingest path.

**Related pages (not yet evaluated):**
- `https://www.fisheries.noaa.gov/rules-and-announcements/notices-and-rules`
- `https://www.fisheries.noaa.gov/news-and-announcements/news`

---

## 3. MAFMC news feed

**Feed URL:** `https://www.mafmc.org/newsfeed?format=rss`
**Format:** RSS 2.0 (Squarespace-generated)
**Verified working:** 2026-09-20 — returned 200, `application/rss+xml`
**Covers:** Council news, meeting announcements, action updates, notices about
NOAA decisions.

**Stable ID:** item permalink, pattern `https://www.mafmc.org/newsfeed/<year>/<slug>`
**Caveat:** this is Council *news*, not regulation. Many items are meetings, workshops,
and photo contests. Expect to filter hard, and expect meeting notices to be a separate
content type from rule changes.

**Related pages (HTML, no feed found):**
- `https://www.mafmc.org/council-actions` — actions currently in development
- `https://www.mafmc.org/action-archive` — completed actions
- `https://www.mafmc.org/regulations`
- Per-action pages: `https://www.mafmc.org/actions/<slug>`

---

## Recommended ingest strategy

Use the Federal Register API as the source of record for what a rule *is* and when it
takes effect. Use GARFO bulletins and the MAFMC feed to catch announcements early and
to supply plain-language context. Match them to Federal Register documents by document
number where one is cited.

## Before relying on any of this

- Re-run every URL above and update the verified date
- Read each agency's terms of use and robots.txt
- Set a descriptive User-Agent with contact info
- Rate-limit politely; these are public agencies, not a CDN
