"""Tests for the parts that do not call the network or the model.

Run:  python -m unittest discover tests
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import build_site, fetch, fulltext, store, summarize, tagging  # noqa: E402


class TestTagging(unittest.TestCase):
    def test_vocabulary_parses_canonical_names(self):
        vocabulary = tagging.species_vocabulary()
        self.assertIn("summer flounder", vocabulary)
        self.assertEqual(vocabulary["summer flounder"], "Summer flounder")

    def test_parenthetical_alternate_maps_to_canonical(self):
        vocabulary = tagging.species_vocabulary()
        # "Summer flounder (fluke)" should make "fluke" resolve to the canonical name.
        self.assertEqual(vocabulary.get("fluke"), "Summer flounder")

    def test_validate_accepts_known_and_drops_unknown(self):
        vocabulary = {"scup": "Scup", "bluefish": "Bluefish"}
        accepted, dropped = tagging.validate(["Scup", "Unicorn fish", "bluefish"], vocabulary)
        self.assertEqual(accepted, ["Scup", "Bluefish"])
        self.assertEqual(dropped, ["Unicorn fish"])

    def test_validate_deduplicates(self):
        vocabulary = {"scup": "Scup", "porgy": "Scup"}
        accepted, dropped = tagging.validate(["Scup", "porgy"], vocabulary)
        self.assertEqual(accepted, ["Scup"])
        self.assertEqual(dropped, [])

    def test_long_hms_area_names_survive_the_prose_filter(self):
        # These run to six words. The parser drops bullets over eight as prose, so
        # they sit close to the cap — this test is the tripwire if it moves.
        regions = tagging.canonical_regions()
        for area in (
            "Mid-Atlantic Bottom Longline Gear Restricted Area",
            "East Florida Coast Gear Restricted Area",
            "Charleston Bump Gear Restricted Area",
            "DeSoto Canyon Gear Restricted Area",
            "Northeast Distant Gear Restricted Area",
            "Charleston Bump Monitoring Area",
            "East Florida Coast Monitoring Area",
            "Gulf of America",
            "Caribbean Sea",
            "Atlantic Ocean",
        ):
            self.assertIn(area, regions)

    def test_gulf_of_mexico_resolves_to_gulf_of_america(self):
        vocabulary = tagging.region_vocabulary()
        self.assertEqual(vocabulary.get("gulf of mexico"), "Gulf of America")
        self.assertEqual(vocabulary.get("ned"), "Northeast Distant Gear Restricted Area")

    def test_prose_bullets_do_not_leak_into_the_vocabulary(self):
        # Every prose bullet in the resource files is a sentence ending in a period.
        for term in tagging.canonical_regions() + tagging.canonical_species():
            self.assertFalse(term.endswith("."), f"prose leaked in as a tag: {term!r}")
            self.assertLessEqual(len(term.split()), 8, f"suspiciously long tag: {term!r}")

    def test_undefined_reporting_areas_are_not_tags(self):
        # NEC, NCA and SAR appear in proposed-rule discussion but are not defined in
        # 50 CFR 635, so they must not be taggable.
        vocabulary = tagging.region_vocabulary()
        for absent in ("nec", "nca", "sar", "sargasso sea"):
            self.assertNotIn(absent, vocabulary)

    def test_find_in_text_respects_word_boundaries(self):
        vocabulary = {"scup": "Scup"}
        self.assertEqual(tagging.find_in_text("Scup quota transfer", vocabulary), ["Scup"])
        self.assertEqual(tagging.find_in_text("scuppernong grapes", vocabulary), [])


class TestNormalize(unittest.TestCase):
    def test_normalize_keeps_only_what_the_api_gave(self):
        raw = {
            "document_number": "2026-18623",
            "title": "  Fisheries of the Northeastern United States; Bluefish  ",
            "type": "Rule",
            "publication_date": "2026-09-11",
            "html_url": "https://example.gov/doc",
            "agencies": [{"name": "National Oceanic and Atmospheric Administration"}],
        }
        notice = fetch.normalize(raw)

        self.assertEqual(notice["document_number"], "2026-18623")
        self.assertEqual(notice["title"], "Fisheries of the Northeastern United States; Bluefish")
        # effective_on was absent — it stays empty rather than being invented.
        self.assertEqual(notice["effective_on"], "")
        self.assertEqual(notice["abstract"], "")


class TestFetchFilter(unittest.TestCase):
    def test_url_filters_on_cfr_part_not_a_title_phrase(self):
        from datetime import date

        url = fetch._build_url("635", date(2026, 1, 1), 100)
        self.assertIn("conditions%5Bcfr%5D%5Btitle%5D=50", url)
        self.assertIn("conditions%5Bcfr%5D%5Bpart%5D=635", url)
        self.assertIn("conditions%5Bpublication_date%5D%5Bgte%5D=2026-01-01", url)

    def test_term_url_scopes_to_noaa(self):
        from datetime import date

        url = fetch._build_term_url('"Atlantic Highly Migratory Species"', date(2026, 1, 1), 100)
        self.assertIn("conditions%5Bterm%5D=", url)
        self.assertIn("national-oceanic-and-atmospheric-administration", url)
        self.assertNotIn("cfr", url)

    def test_both_passes_run_and_results_merge(self):
        from app import config

        parts_called, terms_called = [], []

        def fake_fetch_part(cfr_part, since, max_pages):
            parts_called.append(cfr_part)
            # 648 and 635 both return the same document — it must appear once.
            shared = {"document_number": "2026-SHARED", "publication_date": "2026-05-01"}
            if cfr_part == "648":
                return [shared, {"document_number": "2026-A", "publication_date": "2026-06-01"}]
            if cfr_part == "635":
                return [shared, {"document_number": "2026-B", "publication_date": "2026-04-01"}]
            return []

        def fake_fetch_term(term, since, max_pages):
            terms_called.append(term)
            # The title pass finds a Notice the CFR pass cannot see, plus a
            # duplicate of something the CFR pass already had.
            return [
                {"document_number": "2026-NOTICE", "publication_date": "2026-07-01"},
                {"document_number": "2026-A", "publication_date": "2026-06-01"},
            ]

        original_part, original_term = fetch._fetch_part, fetch._fetch_term
        fetch._fetch_part, fetch._fetch_term = fake_fetch_part, fake_fetch_term
        try:
            notices = fetch.fetch_notices(days_back=30)
        finally:
            fetch._fetch_part, fetch._fetch_term = original_part, original_term

        self.assertEqual(parts_called, list(config.FR_CFR_PARTS.keys()))
        self.assertEqual(terms_called, list(config.FR_TITLE_TERMS))

        numbers = [n["document_number"] for n in notices]
        self.assertEqual(len(numbers), len(set(numbers)), "a shared document was duplicated")
        self.assertIn("2026-NOTICE", numbers, "the title pass must add notices the CFR pass misses")
        self.assertIn("2026-SHARED", numbers)
        # Newest first.
        self.assertEqual(numbers[0], "2026-NOTICE")

    def test_results_without_a_document_number_are_dropped(self):
        original_part, original_term = fetch._fetch_part, fetch._fetch_term
        fetch._fetch_part = lambda p, s, m: [{"publication_date": "2026-06-01"}]
        fetch._fetch_term = lambda t, s, m: []
        try:
            self.assertEqual(fetch.fetch_notices(days_back=30), [])
        finally:
            fetch._fetch_part, fetch._fetch_term = original_part, original_term


class TestFullText(unittest.TestCase):
    def test_html_is_stripped_to_readable_text(self):
        html = (
            "<html><head><style>p{color:red}</style><script>x=1</script></head>"
            "<body><div>Department of Commerce</div>"
            "<p>AGENCY:</p><p>National Marine Fisheries Service</p>"
            "<p>Transfer of  250,000   pounds.</p></body></html>"
        )
        text = fulltext.html_to_text(html)

        self.assertIn("Transfer of 250,000 pounds.", text, "whitespace should collapse")
        self.assertNotIn("color:red", text, "style contents must be dropped")
        self.assertNotIn("x=1", text, "script contents must be dropped")

    def test_page_furniture_before_the_document_is_trimmed(self):
        html = (
            "<div>Document headings vary by document type but may contain the "
            "following: the agency or agencies that issued and signed a document.</div>"
            "<div>Department of Commerce</div><p>AGENCY:</p><p>NMFS</p>"
        )
        text = fulltext.html_to_text(html)

        self.assertTrue(text.startswith("Department of Commerce"))
        self.assertNotIn("Document headings vary", text)

    def test_unexpected_layout_keeps_everything(self):
        # No "Department of" and no "AGENCY:" — cut nothing rather than guess.
        text = fulltext.html_to_text("<p>Some other document entirely.</p>")
        self.assertIn("Some other document entirely.", text)

    def test_oversized_text_is_truncated_and_reported(self):
        from app import config, fetch as fetch_module

        original_get, original_limit = fetch_module.get_text, config.MAX_FULL_TEXT_CHARS
        fetch_module.get_text = lambda url: "<p>Department of Commerce</p><p>" + ("x" * 500) + "</p>"
        config.MAX_FULL_TEXT_CHARS = 100
        try:
            text, truncated = fulltext.fetch_text("https://example.gov/doc.html")
        finally:
            fetch_module.get_text, config.MAX_FULL_TEXT_CHARS = original_get, original_limit

        self.assertTrue(truncated, "over-limit text must report truncation, not hide it")
        self.assertEqual(len(text), 100)

    def test_no_url_returns_nothing_rather_than_failing(self):
        self.assertEqual(fulltext.fetch_text(""), ("", False))


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.db"
        store.init_db(self.db)
        self.notice = {
            "document_number": "2026-00001",
            "title": "Test Notice",
            "doc_type": "Rule",
            "publication_date": "2026-09-01",
            "effective_on": "2026-09-15",
            "html_url": "https://example.gov/doc",
            "abstract": "An abstract.",
            "agency": "NOAA",
            "raw_json": "{}",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_insert_is_idempotent(self):
        with store.connect(self.db) as conn:
            self.assertTrue(store.upsert_notice(conn, self.notice))
            self.assertFalse(store.upsert_notice(conn, self.notice))

    def test_refetch_does_not_clobber_a_summary(self):
        with store.connect(self.db) as conn:
            store.upsert_notice(conn, self.notice)
            store.save_summary(conn, "2026-00001", {
                "what_changed": "Something changed.",
                "who_affected": "Someone.",
                "key_details": ["A detail."],
                "species": ["Bluefish"],
                "regions": ["Mid-Atlantic"],
                "unclear": [],
                "dropped_tags": [],
            })
            # A later fetch sees the same document again.
            store.upsert_notice(conn, self.notice)
            row = store.to_dict(store.get(conn, "2026-00001"))

        self.assertEqual(row["what_changed"], "Something changed.")
        self.assertEqual(row["status"], store.STATUS_SUMMARIZED)

    def test_only_approved_notices_are_published(self):
        with store.connect(self.db) as conn:
            store.upsert_notice(conn, self.notice)
            store.save_summary(conn, "2026-00001", {
                "what_changed": "x", "who_affected": "y", "key_details": [],
                "species": [], "regions": [], "unclear": [], "dropped_tags": [],
            })
            self.assertEqual(store.approved(conn), [])

            store.set_review(conn, "2026-00001", store.STATUS_APPROVED, "checked")
            self.assertEqual(len(store.approved(conn)), 1)

    def test_notice_without_document_number_is_refused(self):
        with store.connect(self.db) as conn:
            with self.assertRaises(ValueError):
                store.upsert_notice(conn, dict(self.notice, document_number=""))


class TestPromptRules(unittest.TestCase):
    """The resource files document the tagging rules; the prompt is what enforces
    them. Only the canonical names are sent to the model, never the Rules sections,
    so a rule written in markdown alone changes nothing. These guard the coupling."""

    def test_basin_wide_rule_reaches_the_model(self):
        prompt = summarize.SYSTEM_PROMPT
        self.assertIn("Greater Atlantic", prompt)
        self.assertIn("Cape Hatteras", prompt)

    def test_core_accuracy_rules_are_in_the_prompt(self):
        prompt = summarize.SYSTEM_PROMPT.lower()
        self.assertIn("unclear", prompt)
        self.assertIn("do not interpret the law", prompt)
        self.assertIn("effective date", prompt)

    def test_vocabulary_is_what_gets_sent(self):
        message = summarize._build_user_message({
            "title": "Test", "doc_type": "Rule", "agency": "NOAA",
            "publication_date": "2026-01-01", "effective_on": "2026-01-02",
            "html_url": "https://example.gov", "abstract": "An abstract.",
        })
        self.assertIn("Greater Atlantic", message)
        self.assertIn("Northeast Distant Gear Restricted Area", message)
        self.assertIn("Bluefin tuna", message)
        # No full text supplied, so the model must be told to lean on `unclear`.
        self.assertIn("Only the abstract was available", message)


class TestSummaryValidation(unittest.TestCase):
    def test_invented_tags_are_dropped_and_recorded(self):
        result = summarize.validate_tags({
            "what_changed": " Changed. ",
            "who_affected": "Everyone.",
            "key_details": ["One", "  ", "Two"],
            "species": ["Bluefish", "Space whale"],
            "regions": ["Mid-Atlantic", "Atlantis"],
            "unclear": [],
        })

        self.assertEqual(result["what_changed"], "Changed.")
        self.assertEqual(result["key_details"], ["One", "Two"])
        self.assertIn("Bluefish", result["species"])
        self.assertNotIn("Space whale", result["species"])
        self.assertIn("Space whale", result["dropped_tags"])
        self.assertIn("Atlantis", result["dropped_tags"])


class TestBuildSite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.db"
        self.out = Path(self.tmp.name) / "site"
        store.init_db(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_builds_an_empty_site_without_failing(self):
        result = build_site.build(db_path=self.db, out_dir=self.out)
        self.assertEqual(result["count"], 0)
        self.assertTrue((self.out / "index.html").exists())

    def test_approved_notice_reaches_the_page_and_data_file(self):
        with store.connect(self.db) as conn:
            store.upsert_notice(conn, {
                "document_number": "2026-00002",
                "title": "Bluefish Quota Transfer",
                "doc_type": "Rule",
                "publication_date": "2026-09-11",
                "effective_on": "2026-09-10",
                "html_url": "https://example.gov/doc",
                "abstract": "",
                "agency": "NOAA",
                "raw_json": "{}",
            })
            store.save_summary(conn, "2026-00002", {
                "what_changed": "Quota moved between two states.",
                "who_affected": "Commercial bluefish permit holders.",
                "key_details": ["Transfer of 100,000 lb."],
                "species": ["Bluefish"],
                "regions": ["Mid-Atlantic"],
                "unclear": [],
                "dropped_tags": [],
            })
            store.set_review(conn, "2026-00002", store.STATUS_APPROVED)

        build_site.build(db_path=self.db, out_dir=self.out)

        data = json.loads((self.out / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["species"], ["Bluefish"])

        page = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn("Bluefish Quota Transfer", page)
        self.assertIn("https://example.gov/doc", page)


if __name__ == "__main__":
    unittest.main()
