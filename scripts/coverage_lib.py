#!/usr/bin/env python3
"""Pure functions shared by coverage_audit.py and coverage_check.py.

Everything here is deterministic and side-effect free, so it can be unit
tested (tests/test_*.py) and reused across stages.
"""
import hashlib
import html
import re

PROMPT_PATH = "prompts/daily-paper-tracker.md"

# Expected matrix totals (integrity check)
EXPECTED_SECTION_COUNTS = {"A": 134, "B": 58, "C": 47, "D": 63, "E": 43, "F": 17, "G": 28}
EXPECTED_TOTAL = 390

ARXIV_COVERED = {"cs.CL", "cs.AI", "cs.LG", "q-bio.NC", "stat.ML"}
BIORXIV_COVERED_SECTIONS = {"neuroscience"}


def read_prompt(path=PROMPT_PATH):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_keyword_matrix(prompt_text):
    """Extract sections A-G with their keyword lists.

    Returns (sections, order) where sections maps 'A' -> {'name': ..., 'keywords': [...]}.
    """
    sections, order = {}, []
    cur = None
    for line in prompt_text.splitlines():
        m = re.match(r"^###\s+([A-G])\s*[—–\-:]\s*(.+)$", line)
        if m:
            cur = m.group(1)
            order.append(cur)
            sections[cur] = {"name": m.group(2).strip(), "keywords": []}
            continue
        if cur and line.strip() and not line.startswith("##"):
            for kw in line.split(","):
                kw = kw.strip()
                if kw:
                    sections[cur]["keywords"].append(kw)
    return sections, order


def matrix_totals(sections):
    """Return {section: count} and grand total."""
    counts = {s: len(v["keywords"]) for s, v in sections.items()}
    return counts, sum(counts.values())


def matrix_hash(sections):
    """Stable hash of the keyword matrix (for baseline comparison)."""
    blob = json_dumps_sorted({s: v["keywords"] for s, v in sections.items()})
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def json_dumps_sorted(obj):
    import json

    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def parse_sources(prompt_text):
    """Parse the venue-related source lists from the prompt.

    Returns dict with keys: journals (set), direct_scan (set), arxiv_cats (set),
    biorxiv_sections (set).
    """
    journals, direct_scan = set(), set()
    # --- direct scan table ---
    in_table = False
    for line in prompt_text.splitlines():
        if line.startswith("| Journal | URL to scan |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and "---" not in cells[0]:
                direct_scan.add(cells[0])
    # --- 47-journal list (single bullet) ---
    m = re.search(r"\*\*High-impact journals[^*]*\*\*:\s*([^\n]+)", prompt_text)
    if m:
        for item in m.group(1).split(","):
            item = item.strip().rstrip("★").strip()
            if item:
                journals.add(item)
    # --- arxiv categories ---
    m = re.search(r"- \*\*arxiv:\*\*\s*([^\n]+)", prompt_text)
    arxiv_cats = set()
    if m:
        for item in m.group(1).split(","):
            item = item.strip()
            if item:
                arxiv_cats.add(item)
    # --- bioRxiv section ---
    m = re.search(r"- \*\*bioRxiv:\*\*\s*([^\n]+)", prompt_text)
    biorxiv_sections = set()
    if m:
        for item in m.group(1).split(","):
            item = item.strip()
            if item and item.lower() not in ("section", "sections"):
                biorxiv_sections.add(item.lower())
    return {
        "journals": journals,
        "direct_scan": direct_scan,
        "arxiv_cats": arxiv_cats,
        "biorxiv_sections": biorxiv_sections,
    }


def normalize(text):
    """Lowercase, strip non-alphanumerics, collapse whitespace."""
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


html_unescape = html.unescape


def match_paper(keywords, title_norm, abstract_norm):
    """Return the list of (normalized) keywords found in title+abstract."""
    blob = f"{title_norm} {abstract_norm}"
    return [k for k in keywords if k in blob]


def match_sections(sections, title_norm, abstract_norm):
    """Return {section: [matched keywords]} for all sections."""
    out = {}
    for s, v in sections.items():
        hits = match_paper([normalize(k) for k in v["keywords"]], title_norm, abstract_norm)
        if hits:
            out[s] = hits
    return out


# --- reported-papers parsing (calibration golden set) ---
REPORT_GLOB = "outputs/*-paper-tracker.html"
PAPER_TITLE_RE = re.compile(r'<div class="paper-title">\s*<a href="[^"]*"[^>]*>(.*?)</a>', re.S)


def parse_reported_titles(html_text):
    """Titles from one tracker HTML report."""
    return [html.unescape(t.strip()) for t in PAPER_TITLE_RE.findall(html_text)]


def parse_reported_papers(outputs_dir="outputs"):
    """All reported titles across reports, deduped, order preserved."""
    import glob

    titles, seen = [], set()
    for f in sorted(glob.glob(f"{outputs_dir}/*-paper-tracker.html")):
        with open(f, encoding="utf-8") as fh:
            for t in parse_reported_titles(fh.read()):
                key = normalize(t)
                if key and key not in seen:
                    seen.add(key)
                    titles.append(t)
    return titles
