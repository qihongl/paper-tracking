#!/usr/bin/env python3
"""Pure functions shared by coverage_audit.py and coverage_check.py.

Everything here is deterministic and side-effect free, so it can be unit
tested (tests/test_*.py) and reused across stages.
"""
import hashlib
import html
import re

PROMPT_PATH = "prompts/daily-paper-tracker.md"

# expected matrix totals (integrity check) — updated 2026-08-02 (scale-up: +3 to C)
EXPECTED_SECTION_COUNTS = {"A": 134, "B": 58, "C": 50, "D": 63, "E": 43, "F": 17, "G": 28}
EXPECTED_TOTAL = 393

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
        if line.startswith("##"):
            cur = None  # any other header ends the current section
            continue
        if cur and line.strip():
            stripped = line.strip()
            if re.match(r"^-{3,}$", stripped) or stripped.startswith("```"):
                continue
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
    # --- 47-journal list (single bullet; bold span ends with ':**') ---
    m = re.search(r"\*\*High-impact journals[^*]*:\*\*\s*([^\n]+)", prompt_text)
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
            item = item.strip().lower()
            item = item.replace(" section", "").replace(" sections", "").strip()
            if item:
                biorxiv_sections.add(item)
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


def ngrams(text, n):
    """Character-split n-grams of a normalized (space-separated) string."""
    toks = text.split()
    return [" ".join(toks[i : i + n]) for i in range(len(toks) - n + 1)]


def specificity(gram, papers):
    """Fraction of corpus papers whose title+abstract contain gram."""
    n = max(1, len(papers))
    df = sum(1 for p in papers if gram in f"{p['title_norm']} {p['abstract_norm']}")
    return df / n


html_unescape = html.unescape  # alias kept for callers


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


CARD_RE = re.compile(r'<div class="paper">(.*?)(?=<div class="paper">|</div>\s*</div>|<div class="excluded">)', re.S)


def parse_reported_cards(html_text):
    """(tag, title, finding) for each paper card in one report.

    The tag is read from the closest preceding section header.
    """
    sec_pos = [(m.start(), m.group(1)) for m in re.finditer(r'<div class="section-header tag-(\w+)">', html_text)]
    out = []
    for m in re.finditer(r'<div class="paper">', html_text):
        card = html_text[m.start() : m.start() + 6000]
        tm = re.search(r'<div class="paper-title">\s*<a href="[^"]*"[^>]*>(.*?)</a>', card, re.S)
        if not tm:
            continue
        tag = next((t for pos, t in reversed(sec_pos) if pos < m.start()), "?")
        fm = re.search(r"<strong>Finding:</strong>\s*(.*?)</p>", card, re.S)
        out.append({
            "tag": tag,
            "title": html.unescape(tm.group(1)).strip(),
            "finding": html.unescape(fm.group(1)).strip() if fm else "",
        })
    return out


def parse_reported_papers(outputs_dir="outputs", with_findings=False):
    """All reported papers across reports, deduped by normalized title.

    with_findings=True returns list of dicts {title, finding, tag}.
    """
    import glob

    out, seen = [], set()
    for f in sorted(glob.glob(f"{outputs_dir}/*-paper-tracker.html")):
        with open(f, encoding="utf-8") as fh:
            for card in parse_reported_cards(fh.read()):
                key = normalize(card["title"])
                if key and key not in seen:
                    seen.add(key)
                    out.append(card)
    if with_findings:
        return out
    return [c["title"] for c in out]
