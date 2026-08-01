"""Tests for reported-paper parsing (calibration golden set)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import coverage_lib as cl

SAMPLE_HTML = """
<html><body>
<div class="summary-table">...</div>
<div class="section">
  <div class="section-header tag-llm">LLM-Memory</div>
  <div class="paper">
    <div class="paper-title"><a href="https://doi.org/10.1/abc" target="_blank">Attention &amp; Memory in Transformers</a></div>
    <div class="paper-meta">A. Author et al. (B. Author) &middot; Journal, 2026</div>
    <div class="paper-body"><p><strong>Approach:</strong> x</p><p><strong>Finding:</strong> y</p></div>
  </div>
  <div class="paper">
    <div class="paper-title"><a href="https://arxiv.org/abs/2607.1" target="_blank">Hippocampal Replay: A Review</a></div>
    <div class="paper-meta">C. Author et al. &middot; arXiv, 2026</div>
  </div>
</div>
<div class="excluded"><h2>Papers Scanned but Not Included</h2><ul><li>Foo — reason</li></ul></div>
</body></html>
"""


def test_parse_reported_titles_html_unescape():
    titles = cl.parse_reported_titles(SAMPLE_HTML)
    assert titles == ["Attention & Memory in Transformers", "Hippocampal Replay: A Review"]
    assert "&amp;" not in titles[0]


def test_parse_reported_papers_glob_dedup(tmp_path):
    # write two reports with an overlapping title; expect dedup
    import glob

    out = tmp_path / "outputs"
    out.mkdir()
    (out / "2026-07-01-paper-tracker.html").write_text(SAMPLE_HTML, encoding="utf-8")
    (out / "2026-07-02-paper-tracker.html").write_text(
        SAMPLE_HTML.replace("Attention &amp; Memory in Transformers", "Attention & Memory in Transformers"),
        encoding="utf-8",
    )
    titles = cl.parse_reported_papers(str(out))
    assert titles.count("Attention & Memory in Transformers") == 1
    assert len(titles) == 2  # the other paper appears once


def test_parse_reported_cards_tags_and_findings():
    cards = cl.parse_reported_cards(SAMPLE_HTML)
    assert len(cards) == 2
    assert cards[0]["tag"] == "llm"
    assert cards[0]["title"] == "Attention & Memory in Transformers"
    assert cards[0]["finding"] == "y"
    assert cards[1]["tag"] == "llm"
    assert cards[1]["finding"] == ""  # card without Finding block


def test_keyword_gate_on_reported_title():
    # a reported title must be caught by a matching keyword
    sections = {"A": {"keywords": ["hippocampal replay"]}}
    title_n = cl.normalize("Hippocampal Replay: A Review")
    hits = cl.match_paper([cl.normalize(k) for k in sections["A"]["keywords"]], title_n, "")
    assert hits == ["hippocampal replay"]
