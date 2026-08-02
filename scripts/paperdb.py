#!/usr/bin/env python3
"""Read-only access to the local paper database (ChromaDB SQLite).

The database lives at ~/WorkBuddy/20260408090457/.workbuddy/paper_db/chroma.sqlite3
and indexes 4,269 PDFs from the Paperpile folder. This module is STRICTLY
read-only: connections use mode=ro and nothing here ever writes.

Used by coverage_audit.py and coverage_check.py.
"""
import os
import re
import sqlite3

DB_PATH = "/Users/qlu/WorkBuddy/20260408090457/.workbuddy/paper_db/chroma.sqlite3"
PDF_ROOT = "/Users/qlu/Library/CloudStorage/GoogleDrive-lvqihong1992@gmail.com/My Drive/Paperpile/All Papers"

# Strict DOI regex (no newline joining: wrapped fragments appear once, while a
# paper's own DOI recurs in header + page footers — the repeat rule in
# extract_metadata picks the true DOI and rejects wrap/boilerplate junk).
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,;()\"'<>\u200b]+")
ARXIV_ID_RE = re.compile(r"arXiv:(\d{4}\.\d{4,5})", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def clean_doi(match):
    """Normalize a DOI regex match: strip trailing punctuation (strict regex
    matches contain no newlines)."""
    return match.rstrip(".,")


def connect():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def list_papers(conn=None):
    """All distinct indexed filepaths (sorted)."""
    own = conn is None
    if own:
        conn = connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT string_value FROM embedding_metadata "
            "WHERE key='filepath' AND string_value IS NOT NULL ORDER BY 1"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        if own:
            conn.close()


def get_chunks(conn, filepath):
    """Ordered chunk texts for one paper (by chunk_id)."""
    ids = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM embedding_metadata WHERE key='filepath' AND string_value=?",
            (filepath,),
        ).fetchall()
    ]
    if not ids:
        return []
    ph = ",".join("?" * len(ids))
    cids = {
        i: c
        for i, c in conn.execute(
            f"SELECT id, COALESCE(int_value, CAST(string_value AS INTEGER)) "
            f"FROM embedding_metadata WHERE key='chunk_id' AND id IN ({ph})",
            ids,
        ).fetchall()
    }
    docs = conn.execute(
        f"SELECT id, string_value FROM embedding_metadata "
        f"WHERE key='chroma:document' AND id IN ({ph})",
        ids,
    ).fetchall()
    ordered = sorted(((cids.get(i, 0), t) for i, t in docs), key=lambda x: x[0])
    return [t for _, t in ordered if t]


def _clean_title_from_chunks(chunks):
    """Best-effort title from the first chunk(s): longest plausible line."""
    head = "\n".join(chunks[:2]).split("\n")
    best = None
    for line in head:
        line = line.strip()
        if len(line) < 25:
            continue
        if "http" in line.lower() or "@" in line or "doi" in line.lower():
            continue
        if line.lower().startswith(("received", "accepted", "published")):
            continue
        if best is None or len(line) > len(best):
            best = line
    return best


def extract_metadata(filepath, chunks):
    """Return dict: basename, year, year_source, title, title_source, abstract_window,
    doi_hints, arxiv_ids, needs_ocr."""
    base = os.path.basename(filepath)
    stem = base[:-4] if base.lower().endswith(".pdf") else base

    # --- year ---
    year, year_source = None, None
    m = YEAR_RE.search(stem)
    if m:
        year, year_source = m.group(0), "filename"
    else:
        head = "\n".join(chunks[:2])
        m = YEAR_RE.search(head)
        if m:
            year, year_source = m.group(0), "chunk"

    # --- title ---
    title, title_source = None, None
    clean = re.match(r"^(.+?)\s+(?:(?:19|20)\d{2})\s*[-–—]\s*(.+)$", stem)
    if clean:
        # Author et al. YYYY - Title  => take the part after the year
        title = re.sub(r"^\(\d+\)\s*(?:\(PDF\))?\s*", "", clean.group(2)).strip()
        title_source = "filename"
    if not title:
        t = _clean_title_from_chunks(chunks)
        if t:
            title, title_source = t, "chunk"
    if not title:
        # fallback: last ' - ' segment, or the stem itself
        parts = [p.strip() for p in stem.split(" - ") if p.strip()]
        title, title_source = (parts[-1], "filename-fallback") if parts else (stem, "filename-fallback")

    # --- abstract window (first 3000 chars of ordered chunks) ---
    full = "\n".join(chunks)
    abstract_window = full[:3000]

    # --- identifiers from chunk text (first N chunks; references further in
    #     would pollute with cited DOIs) ---
    N_ID_CHUNKS = 6
    head2 = "\n".join(chunks[:N_ID_CHUNKS])
    dois = [clean_doi(d) for d in DOI_RE.findall(head2) if not d.lower().startswith("10.48550/arxiv")]
    arxiv_ids = ARXIV_ID_RE.findall(head2)
    arxiv_ids += [m2.group(1) for m2 in re.finditer(r"10\.48550/arXiv\.(\d{4}\.\d{4,5})", head2, re.IGNORECASE)]
    dois = list(dict.fromkeys(dois))
    arxiv_ids = list(dict.fromkeys(arxiv_ids))

    # --- identifiers from the FULL text ---
    # A paper's own DOI recurs (header + page footers). Selection: (1) drop
    # matches that are strict prefixes of longer matches (wrap-truncated
    # fragments lose to the unwrapped DOI in references/footers), (2) among
    # the rest pick the most frequent (tie -> earliest). No matches -> None.
    full = "\n".join(chunks)
    all_dois = [clean_doi(m) for m in DOI_RE.findall(full)]
    all_dois = [d for d in all_dois if not d.lower().startswith("10.48550/arxiv")]
    if all_dois:
        from collections import Counter

        uniq = list(dict.fromkeys(all_dois))
        non_prefix = [d for d in uniq if not any(d != o and o.startswith(d) for o in uniq)]
        doi_counts = Counter(all_dois)
        first_doi = max(non_prefix, key=lambda d: (doi_counts[d], -uniq.index(d)))
    else:
        first_doi = None
    m = ARXIV_ID_RE.search(full)
    first_arxiv = m.group(1) if m else None
    if not first_arxiv:
        m = re.search(r"10\.48550/arXiv\.(\d{4}\.\d{4,5})", full, re.IGNORECASE)
        first_arxiv = m.group(1) if m else None

    return {
        "basename": stem,
        "year": year,
        "year_source": year_source,
        "title": title,
        "title_source": title_source,
        "abstract_window": abstract_window,
        "doi_hints": dois,
        "arxiv_ids": arxiv_ids,
        "first_doi_fulltext": first_doi,
        "first_arxiv_fulltext": first_arxiv,
    }


if __name__ == "__main__":
    conn = connect()
    papers = list_papers(conn)
    print("papers:", len(papers))
    for fp in [papers[0], [p for p in papers if "Visual Working Memory Impa" in p][0]]:
        chunks = get_chunks(conn, fp)
        meta = extract_metadata(fp, chunks)
        print("\nFILE:", os.path.basename(fp))
        print("  year:", meta["year"], "|", meta["year_source"])
        print("  title:", meta["title"][:90], "|", meta["title_source"])
        print("  dois:", meta["doi_hints"][:3], "| arxiv:", meta["arxiv_ids"][:3])
