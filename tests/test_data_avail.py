"""Availability regressions: public claims require independent, local evidence."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import data_avail as da


def publisher_page(sections):
    # Real publisher pages exceed the detector's bot-stub cutoff.
    return "<html><body>" + sections + "<!--" + " " * 21000 + "--></body></html>"


def pmc_page(sections):
    return "<article>" + sections + "<!--" + " " * 6000 + "--></article>"


class ClassifierTests(unittest.TestCase):
    def test_restricted_overrides_open_repository(self):
        statement = "Data are in UK Biobank under a data-use agreement; see https://osf.io/example."
        self.assertEqual(da.classify_data(statement, []), "restricted")

    def test_request_overrides_supplementary_information(self):
        statement = ("Data are available upon reasonable request. "
                     "Source data are provided in Supplementary Information files.")
        self.assertEqual(da.classify_data(statement, []), "on_request")

    def test_public_supplementary_data(self):
        statement = "The data are provided in the Supporting Information Excel files."
        self.assertEqual(da.classify_data(statement, []), "open_data")

    def test_bare_code_claim_is_unknown(self):
        self.assertEqual(da.classify_code("Code is available.", []), "unknown")

    def test_relative_reference_does_not_prove_code_release(self):
        self.assertEqual(da.classify_code("Code is available.", ["#ref1", "/policy"]),
                         "unknown")

    def test_request_only_code_is_not_open(self):
        self.assertEqual(da.classify_code("Code is available upon reasonable request.", []),
                         "on_request")

    def test_request_location_is_not_an_open_data_release(self):
        statement = "Data are available upon reasonable request at https://osf.io/request."
        self.assertEqual(da.classify_data(statement, []), "on_request")

    def test_bare_ambiguous_hyperlink_is_not_open_data(self):
        self.assertEqual(da.classify_data("See the repository for this study.",
                                         ["https://zenodo.org/records/123"]), "unknown")

    def test_ambiguous_link_beyond_proximity_window_is_not_evidence(self):
        statement = "Data " + "x " * 200 + "https://github.com/lab/project"
        self.assertEqual(da.classify_data(statement, []), "unknown")

    def test_combined_statement_request_data_and_public_code(self):
        statement = ("The data are available upon reasonable request. "
                     "Code is available at https://github.com/lab/project.")
        self.assertEqual(da.classify_data(statement, []), "on_request")
        self.assertEqual(da.classify_code("", [], statement, []), "open_code")

    def test_combined_statement_public_data_and_request_code(self):
        statement = ("The data are available at https://osf.io/example. "
                     "Code is available upon reasonable request.")
        self.assertEqual(da.classify_data(statement, []), "open_data")
        self.assertEqual(da.classify_code("", [], statement, []), "on_request")

    def test_data_url_cannot_prove_code_available(self):
        statement = "The data are available at https://example.org/dataset."
        self.assertEqual(da.classify_code("", [], statement, []), "unknown")

    def test_first_domain_in_statement_wins_over_href_order(self):
        statement = "Data: https://zenodo.org/records/123, mirrored at https://osf.io/example."
        hrefs = ["https://osf.io/example", "https://zenodo.org/records/123"]
        self.assertEqual(da.pick_url(statement, hrefs), "https://zenodo.org/records/123")


class ExtractionTests(unittest.TestCase):
    def test_heading_fallback_retains_body_and_hidden_href(self):
        document = ('<h2>Data availability</h2><p>The dataset is available at '
                    '<a href="https://zenodo.org/records/123">this repository</a>.</p>'
                    '<h2>References</h2><p>Unrelated references.</p>')
        data, hrefs, _, _ = da.extract(document)
        self.assertIn("dataset", data)
        self.assertIn("https://zenodo.org/records/123", hrefs)
        self.assertNotIn("Unrelated references", data)
        self.assertEqual(da.classify_data(data, hrefs), "open_data")

    def test_xml_hidden_repository_keeps_its_proximity_context(self):
        document = ('<sec sec-type="data-availability"><title>Data availability</title>'
                    '<p>The dataset is publicly available at '
                    '<ext-link xlink:href="https://zenodo.org/records/123">Zenodo</ext-link>.'
                    '</p></sec>')
        data, hrefs, _, _ = da.extract(document)
        self.assertEqual(da.classify_data(data, hrefs), "open_data")

    def test_code_heading_fallback_retains_body(self):
        document = ('<h2>Code availability</h2><p>Analysis code is available at '
                    '<a href="https://github.com/lab/project">GitHub</a>.</p>'
                    '<h2>References</h2><p>Unrelated references.</p>')
        _, _, code, hrefs = da.extract(document)
        self.assertIn("Analysis code", code)
        self.assertIn("https://github.com/lab/project", hrefs)
        self.assertNotIn("Unrelated references", code)
        self.assertEqual(da.classify_code(code, hrefs), "open_code")

    def test_xml_sections_do_not_leak_code_into_request_data(self):
        document = ('<sec sec-type="data-availability"><title>Data availability</title>'
                    '<p>Data available from the corresponding author upon reasonable request.</p>'
                    '</sec><sec sec-type="code-availability"><title>Code availability</title>'
                    '<p>Code is available at https://github.com/lab/project.</p></sec>')
        data, data_hrefs, code, code_hrefs = da.extract(document)
        self.assertNotIn("github.com", data)
        self.assertEqual(da.classify_data(data, data_hrefs), "on_request")
        self.assertEqual(da.classify_code(code, code_hrefs), "open_code")

    def test_bold_leadin_preserves_public_supplementary_data(self):
        document = ('<p><strong>Data Availability:</strong> The data are provided in '
                    'Supporting Information Excel files.</p>')
        data, hrefs, _, _ = da.extract(document)
        self.assertEqual(da.classify_data(data, hrefs), "open_data")

    def test_xml_title_cannot_turn_code_only_release_into_open_data(self):
        document = ('<sec sec-type="data-availability"><title>Data availability</title>'
                    '<p>Only analysis code is available at https://github.com/lab/project.</p></sec>')
        data, hrefs, _, _ = da.extract(document)
        self.assertEqual(da.classify_data(data, hrefs), "unknown")

    def test_bold_title_cannot_turn_code_only_release_into_open_data(self):
        document = ('<p><strong>Data Availability:</strong> Only analysis code is available '
                    'at https://github.com/lab/project.</p>')
        data, hrefs, _, _ = da.extract(document)
        self.assertEqual(da.classify_data(data, hrefs), "unknown")

    def test_navigation_chrome_is_rejected(self):
        document = ('<section id="data-availability"><p>Data Availability: ethical publishing '
                    'practice; expressions of concern; available at '
                    '<a href="https://osf.io/example">OSF</a>.</p></section>')
        data, hrefs, _, _ = da.extract(document)
        self.assertEqual(da.classify_data(data, hrefs), "unknown")
        self.assertTrue(da.looks_like_chrome(
            "ethical publishing practice and expressions of concern"))


class LookupTests(unittest.TestCase):
    def lookup_with_pages(self, publisher, pmc, doi="10.1234/example", abstract=""):
        with patch.object(da, "fetch", return_value=publisher), \
                patch.object(da, "europepmc_fulltext", return_value=pmc):
            return da.lookup(doi, abstract)

    def test_pmc_completes_unknown_code_independently(self):
        publisher = publisher_page(
            '<section id="data-availability"><p>Data are available at '
            'https://osf.io/example.</p></section>')
        pmc = pmc_page('<sec sec-type="code-availability"><title>Code availability</title>'
                       '<p>Code is available at https://github.com/lab/project.</p></sec>')
        result = self.lookup_with_pages(publisher, pmc)
        self.assertEqual(result["data_avail"], "open_data")
        self.assertEqual(result["code_avail"], "open_code")

    def test_pmc_completes_unknown_data_independently(self):
        publisher = publisher_page(
            '<section id="code-availability"><p>Code is available at '
            'https://github.com/lab/project.</p></section>')
        pmc = pmc_page('<sec sec-type="data-availability"><title>Data availability</title>'
                       '<p>Data are available upon reasonable request.</p></sec>')
        result = self.lookup_with_pages(publisher, pmc)
        self.assertEqual(result["data_avail"], "on_request")
        self.assertEqual(result["code_avail"], "open_code")

    def test_publisher_verdict_is_preserved_during_fallback(self):
        publisher = publisher_page(
            '<section id="data-availability"><p>Data are available upon reasonable '
            'request.</p></section>')
        pmc = pmc_page('<sec sec-type="data-availability"><title>Data availability</title>'
                       '<p>Data are available at https://osf.io/example.</p></sec>'
                       '<sec sec-type="code-availability"><title>Code availability</title>'
                       '<p>Code is available at https://github.com/lab/project.</p></sec>')
        result = self.lookup_with_pages(publisher, pmc)
        self.assertEqual(result["data_avail"], "on_request")
        self.assertEqual(result["code_avail"], "open_code")

    def test_failed_lookup_is_unknown_and_silent(self):
        result = self.lookup_with_pages("Bot challenge", "")
        for channel in ("data", "code"):
            self.assertEqual(result[f"{channel}_avail"], "unknown")
            self.assertEqual(result[f"{channel}_avail_url"], "")

    def test_journal_abstract_cannot_replace_availability_statement(self):
        result = self.lookup_with_pages("Bot challenge", "", abstract=
                                        "Data are available at https://osf.io/example.")
        self.assertEqual(result["data_avail"], "unknown")
        self.assertEqual(result["code_avail"], "unknown")

    def test_preprint_abstract_requires_channel_words(self):
        data_hit, code_hit = da.scan_text(
            "The data are openly available at https://osf.io/example.")
        self.assertTrue(data_hit)
        self.assertFalse(code_hit)
        self.assertEqual(da.scan_text("See https://github.com/lab/project."), (None, None))


if __name__ == "__main__":
    unittest.main()
