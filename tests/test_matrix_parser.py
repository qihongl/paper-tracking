"""Tests for the keyword-matrix parser (coverage_lib.parse_keyword_matrix)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import coverage_lib as cl

MINI_PROMPT = """## Sources to Search
### Primary search: keyword-based (WebSearch)

### A — Human/Animal Systems
episodic memory, hippocampus, memory replay, sharp-wave ripples
### B — Computational Models
temporal context model, TCM, successor representation
## Output
"""


def test_parse_sections_and_order():
    sections, order = cl.parse_keyword_matrix(MINI_PROMPT)
    assert order == ["A", "B"]
    assert sections["A"]["keywords"] == ["episodic memory", "hippocampus", "memory replay", "sharp-wave ripples"]
    assert sections["B"]["keywords"] == ["temporal context model", "TCM", "successor representation"]


def test_real_prompt_totals():
    prompt = cl.read_prompt(os.path.join(os.path.dirname(__file__), "..", cl.PROMPT_PATH))
    sections, order = cl.parse_keyword_matrix(prompt)
    assert order == ["A", "B", "C", "D", "E", "F", "G"]
    counts, total = cl.matrix_totals(sections)
    assert total == cl.EXPECTED_TOTAL, f"total {total}"
    for s, expected in cl.EXPECTED_SECTION_COUNTS.items():
        assert counts[s] == expected, f"section {s}: {counts[s]} != {expected}"


def test_matrix_hash_deterministic():
    prompt = cl.read_prompt(os.path.join(os.path.dirname(__file__), "..", cl.PROMPT_PATH))
    sections, _ = cl.parse_keyword_matrix(prompt)
    assert cl.matrix_hash(sections) == cl.matrix_hash(sections)
    assert len(cl.matrix_hash(sections)) == 16


def test_parse_sources_real_prompt():
    prompt = cl.read_prompt(os.path.join(os.path.dirname(__file__), "..", cl.PROMPT_PATH))
    sources = cl.parse_sources(prompt)
    assert len(sources["journals"]) == 102  # 66 + 33 scale-up additions + 3 from 2026-08-01
    assert "Nature Neuroscience" in sources["journals"]
    assert "Communications Biology" in sources["journals"]
    assert "Frontiers in Psychology" in sources["journals"]  # scale-up addition
    assert len(sources["direct_scan"]) == 26  # 16 + 10 scale-up promotions
    assert "Communications Psychology" in sources["direct_scan"]
    assert "Scientific Reports" in sources["direct_scan"]
    assert sources["arxiv_cats"] == {"cs.CL", "cs.AI", "cs.LG", "q-bio.NC", "stat.ML"}
