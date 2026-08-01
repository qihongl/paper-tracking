"""Tests for normalization + matching (coverage_lib)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import coverage_lib as cl


def test_normalize_case_punct_whitespace():
    assert cl.normalize("  Sharp-Wave Ripples! (SWR)  ") == "sharp wave ripples swr"
    assert cl.normalize("Épisodic mémory") == "pisodic m mory"  # accents -> spaces (like hyphens)
    assert cl.normalize("") == ""


def test_match_paper_multiword():
    kws = ["sharp wave ripples", "episodic memory"]
    title = "Sharp-wave ripples during sleep"
    abstract = "we examined episodic memory consolidation"
    hits = cl.match_paper(kws, cl.normalize(title), cl.normalize(abstract))
    assert hits == ["sharp wave ripples", "episodic memory"]


def test_hyphen_keyword_matches_spaced_text():
    # keyword "sharp-wave ripples" normalizes to "sharp wave ripples" -> matches
    kws = [cl.normalize("sharp-wave ripples")]
    assert "sharp wave ripples" in "sharp wave ripples during sleep"
    assert cl.match_paper(kws, "sharp wave ripples during sleep", "") == ["sharp wave ripples"]


def test_no_false_positive_partial_word():
    kws = ["memory"]
    assert cl.match_paper(kws, "memories are formed", "") == []  # "memory" not substring of "memories"
    assert cl.match_paper(kws, "memory formation", "") == ["memory"]


def test_sections_matching():
    sections = {"A": {"keywords": ["hippocampus", "replay"]}, "B": {"keywords": ["transformer"]}}
    out = cl.match_sections(sections, "hippocampal replay is key", "transformers can memorize")
    assert set(out) == {"A", "B"}


def test_specificity_and_ngrams():
    papers = [
        {"title_norm": "hippocampal replay", "abstract_norm": "replay during sleep"},
        {"title_norm": "other topic", "abstract_norm": "nothing here"},
        {"title_norm": "third", "abstract_norm": "more text"},
    ]
    assert cl.specificity("replay", papers) == 1 / 3
    assert cl.ngrams("a b c", 2) == ["a b", "b c"]
    assert cl.ngrams("a b c", 3) == ["a b c"]
