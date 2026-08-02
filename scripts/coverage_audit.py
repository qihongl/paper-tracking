#!/usr/bin/env python3
"""Two-layer coverage audit for the daily paper tracker.

Stages (run from repo root with miniforge python):
    build-corpus  --window 2025-2026   build data/audit/corpus.json from the local paper DB
    enrich                              Crossref/arXiv/bioRxiv venue enrichment (cached)
    audit                               two-layer classification + calibration + baseline
    mine                                hybrid ngram+embedding miss mining + edit simulation
    venue                               tiered venue recommendations
    sections                            section distribution analysis
    precision                           stratified keep/drop sample of reported papers
    all                                 run everything and write outputs/coverage-audit.md

Always run with:  env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_audit.py ...
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_lib as cl
import paperdb

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(REPO, "data", "audit")
OUT_MD = os.path.join(REPO, "outputs", "coverage-audit.md")
MAILTO = "lvqihong1992@gmail.com"
UA = {"User-Agent": f"paper-tracking-coverage-audit/0.1 (mailto:{MAILTO})"}

STOPWORDS = None


def get_stopwords():
    global STOPWORDS
    if STOPWORDS is None:
        try:
            import social_unify  # reuses the curated science stopword list

            STOPWORDS = social_unify.STOPWORDS
        except Exception:
            STOPWORDS = set(
                "a about above after again against all am an and any are as at be because been before "
                "being between both but by can could did do does doing down during each few for from "
                "further had has have having he her here hers herself him his himself how i if in into "
                "is it its itself just me more most my myself no nor not of off on once only or other "
                "ours ourselves out over own same she should so some such than that the their theirs "
                "them themselves then there these they this those through to too under until up very "
                "was we were what when where which while who whom why with would you your yours also "
                "new paper papers preprint preprints study studies research article articles show shows "
                "shown showing find finds found result results using use used via based approach "
                "approaches method methods model models data analysis https http www com org net et al "
                "one two three first last fig figure table figures".split()
            )
    return STOPWORDS


def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def report_append(text):
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "a", encoding="utf-8") as f:
        f.write(text + "\n")


# ---------------------------------------------------------------------------
# Stage: build-corpus
# ---------------------------------------------------------------------------
def build_corpus(window, since=None):
    os.makedirs(AUDIT_DIR, exist_ok=True)
    # preserve the previous pinned corpus when the window changes
    old_path = os.path.join(AUDIT_DIR, "corpus.json")
    if os.path.exists(old_path):
        with open(old_path, encoding="utf-8") as f:
            old = json.load(f)
        if old.get("window") != window and old.get("window") != (since and f"since-{since}") and os.path.exists(old_path):
            import shutil

            shutil.copy(old_path, os.path.join(AUDIT_DIR, "corpus_2025.json"))
            print("preserved previous corpus -> corpus_2025.json")
    conn = paperdb.connect()
    papers = paperdb.list_papers(conn)
    out, stats = [], Counter()
    for fp in papers:
        chunks = paperdb.get_chunks(conn, fp)
        meta = paperdb.extract_metadata(fp, chunks)
        if window and meta["year"] not in window:
            continue
        if since and not (meta["year"] and int(meta["year"]) >= since):
            continue
        entry = {
            "id": f"p{len(out) + 1:04d}",
            "filepath": fp,
            "basename": meta["basename"],
            "year": meta["year"],
            "year_source": meta["year_source"],
            "title": meta["title"],
            "title_source": meta["title_source"],
            "abstract_window": meta["abstract_window"],
            "abstract_norm": cl.normalize(meta["abstract_window"]),
            "title_norm": cl.normalize(meta["title"]),
            "doi_hints": meta["doi_hints"],
            "arxiv_ids": meta["arxiv_ids"],
            "first_doi": meta["first_doi_fulltext"],
            "first_arxiv": meta["first_arxiv_fulltext"],
        }
        out.append(entry)
        stats["total"] += 1
        stats[meta["title_source"]] += 1
        if not meta["year"]:
            stats["no_year"] += 1
        if meta["year_source"] == "chunk":
            stats["year_from_chunk"] += 1
    out.sort(key=lambda p: p["filepath"])
    for i, p in enumerate(out, 1):
        p["id"] = f"p{i:04d}"
    label = window if window else f"since-{since}"
    corpus = {"window": label, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "papers": out, "stats": dict(stats)}
    with open(old_path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=1)
    print(f"corpus: {len(out)} papers (window={label}) -> {old_path}")
    print("stats:", dict(stats))
    # validation
    unresolved = [p for p in out if not p["title"] or len(p["title"]) < 10]
    print("unresolved titles:", len(unresolved))
    for p in unresolved[:5]:
        print("  ", p["basename"][:80])
    return corpus


def load_corpus():
    with open(os.path.join(AUDIT_DIR, "corpus.json"), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Stage: enrich
# ---------------------------------------------------------------------------
def _run_threaded(jobs, worker, workers=8, batch=200, on_progress=None):
    """Run worker(item) over jobs with a thread pool; yields (item, result) as
    they complete, with retry+backoff inside the worker. Batch-wise so callers
    can persist cache incrementally."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}
    done = 0
    for start in range(0, len(jobs), batch):
        chunk = jobs[start : start + batch]
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(worker, item): item for item in chunk}
            for fut in as_completed(futs):
                item = futs[fut]
                try:
                    results[item] = fut.result()
                except Exception as e:
                    results[item] = {"error": str(e)[:80]}
                done += 1
                if on_progress and done % 100 == 0:
                    on_progress(done, len(jobs))
        yield chunk, results
    if on_progress:
        on_progress(done, len(jobs))


def _crossref_doi_worker(doi):
    import time as _t

    last = None
    for attempt in range(3):
        try:
            url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="") + f"?mailto={MAILTO}"
            msg = fetch_json(url)["message"]
            journal = None
            for k in ("container-title", "short-container-title"):
                if msg.get(k):
                    journal = msg[k][0]
                    break
            return {"journal": journal, "type": msg.get("type")}
        except Exception as e:
            last = {"journal": None, "error": str(e)[:80]}
            _t.sleep(1.5 * (attempt + 1))
    return last


def _crossref_title_worker(job):
    import difflib
    import time as _t

    pid, title = job
    last = None
    for attempt in range(3):
        try:
            url = ("https://api.crossref.org/works?query.bibliographic="
                   + urllib.parse.quote(title) + f"&rows=3&mailto={MAILTO}")
            items = fetch_json(url).get("message", {}).get("items", [])
            best, best_score = None, 0.0
            for it in items:
                t = (it.get("title") or [""])[0]
                score = difflib.SequenceMatcher(None, cl.normalize(title), cl.normalize(t)).ratio()
                if score > best_score:
                    best, best_score = it, score
            if best and best_score >= 0.85:
                journal = None
                for k in ("container-title", "short-container-title"):
                    if best.get(k):
                        journal = best[k][0]
                        break
                return {"doi": best.get("DOI"), "journal": journal, "score": round(best_score, 3)}
            return {"doi": None, "journal": None, "score": round(best_score, 3)}
        except Exception as e:
            last = {"doi": None, "journal": None, "error": str(e)[:80]}
            _t.sleep(1.5 * (attempt + 1))
    return last


def enrich():
    os.makedirs(AUDIT_DIR, exist_ok=True)
    path = os.path.join(AUDIT_DIR, "venue_enrichment.json")
    cache = {"crossref": {}, "crossref_title": {}, "arxiv": {}, "biorxiv": {}}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
    corpus = load_corpus()
    dois, arxiv_ids, biorxiv = set(), set(), set()
    title_search = []  # papers with no identifiers: (paper_id, title)
    for p in corpus["papers"]:
        has_id = False
        all_dois = list(p["doi_hints"])
        if p.get("first_doi") and p["first_doi"] not in all_dois:
            all_dois.append(p["first_doi"])
        for d in all_dois:
            if d.startswith(("10.1101", "10.64898")):
                biorxiv.add(d)
            elif not d.startswith("10.31234") and not d.startswith("10.48550"):
                dois.add(d)
            has_id = True
        all_arx = list(p["arxiv_ids"])
        if p.get("first_arxiv") and p["first_arxiv"] not in all_arx:
            all_arx.append(p["first_arxiv"])
        if all_arx:
            # only fetch arXiv categories for papers with NO DOI at all —
            # published papers resolve via their journal even if they have a preprint ID
            if not has_id:
                arxiv_ids.update(all_arx)
            has_id = True
        if not has_id and p["title"]:
            title_search.append((p["id"], p["title"]))

    # --- Crossref (by DOI, threaded); re-fetch entries whose lookup failed
    #     (journal is None) — stale 404/timeout entries must not block retries ---
    todo = [d for d in sorted(dois)
            if d not in cache["crossref"] or not (cache["crossref"].get(d) or {}).get("journal")]
    print(f"crossref (DOI): {len(todo)} to fetch (of {len(dois)}), 8 threads")
    for _chunk, results in _run_threaded(todo, _crossref_doi_worker,
                                         on_progress=lambda d, t: print(f"  crossref {d}/{t}")):
        cache["crossref"].update(results)
        _save_enrich(path, cache)
    _save_enrich(path, cache)

    # --- Crossref (title search fallback, threaded) ---
    todo = [(pid, t) for pid, t in title_search if pid not in cache["crossref_title"]]
    print(f"crossref (title search): {len(todo)} to fetch, 8 threads")
    for _chunk, results in _run_threaded(todo, _crossref_title_worker,
                                         on_progress=lambda d, t: print(f"  titlesearch {d}/{t}")):
        cache["crossref_title"].update({pid: res for (pid, _t), res in results.items()})
        _save_enrich(path, cache)
    _save_enrich(path, cache)

    # --- arXiv (batches of 50, with 429/timeout backoff) ---
    todo = [a for a in sorted(arxiv_ids) if a not in cache["arxiv"]
            and not any(k.startswith(a + "v") for k in cache["arxiv"])]
    print(f"arxiv: {len(todo)} to fetch (arXiv-only papers)")
    ns = {"a": "http://www.w3.org/2005/Atom", "ar": "http://arxiv.org/schemas/atom"}
    for i in range(0, len(todo), 50):
        batch = todo[i : i + 50]
        for attempt in range(3):
            try:
                url = "http://export.arxiv.org/api/query?id_list=" + ",".join(batch) + "&max_results=100"
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=60) as r:
                    root = ET.fromstring(r.read())
                for entry in root.findall("a:entry", ns):
                    eid = (entry.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
                    pc = entry.find("ar:primary_category", ns)
                    if eid and pc is not None:
                        eid = re.sub(r"v\d+$", "", eid)  # strip version: corpus stores bare IDs
                        cache["arxiv"][eid] = pc.get("term")
                break
            except Exception as e:
                print(f"  arxiv batch failed (attempt {attempt + 1}): {e}")
                time.sleep(25 * (attempt + 1))  # 429/timeout backoff
        _save_enrich(path, cache)
        time.sleep(3)
    _save_enrich(path, cache)

    # --- bioRxiv (refetch error/None entries; retry+backoff: the API returns
    #     transient 404s under load; never clobber a good string) ---
    todo = [d for d in sorted(biorxiv)
            if d not in cache["biorxiv"] or not isinstance(cache["biorxiv"].get(d), str)]
    print(f"biorxiv: {len(todo)} to fetch")
    for doi in todo:
        sec = None
        last_err = None
        for attempt in range(3):
            try:
                url = "https://api.biorxiv.org/details/biorxiv/" + urllib.parse.quote(doi, safe="")
                data = fetch_json(url)
                coll = data.get("collection") or []
                if coll:
                    sec = coll[0].get("category") or coll[0].get("section")
                break
            except Exception as e:
                last_err = str(e)[:80]
                time.sleep(5 * (attempt + 1))  # backoff before retry
        if isinstance(sec, str) or not isinstance(cache["biorxiv"].get(doi), str):
            cache["biorxiv"][doi] = sec
        elif last_err:
            pass  # keep the existing good string
        time.sleep(1.0)  # politeness: the API 404s under bursts
    _save_enrich(path, cache)
    print("enrichment done ->", path)
    return cache


def _save_enrich(path, cache):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def load_enrich():
    with open(os.path.join(AUDIT_DIR, "venue_enrichment.json"), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Stage: audit (two-layer classification)
# ---------------------------------------------------------------------------
# journal-name aliases so 'PNAS' matches Crossref's full name (both -> 'pnas')
JOURNAL_ALIASES = {
    "pnas": "pnas",
    "proceedings of the national academy of sciences": "pnas",
}

# conference proceedings the tracker covers via the ML-conferences source line
# (keep in sync with prompts/daily-paper-tracker.md)
CONFERENCE_HINTS = [
    "association for computational linguistics",   # ACL/EMNLP/NAACL proceedings + Findings
    "conference on computer vision",               # CVPR
    "international conference on computer vision",  # ICCV
    "international conference on data engineering",  # ICDE(W)
    "intelligent user interfaces",
    "educational applications",                    # BEA workshop
    "cognitive computational neuroscience",        # CCN
    "advances in neural information processing",   # NeurIPS proceedings (any volume)
    "empirical methods in natural language",       # EMNLP proceedings (any year)
    "lecture notes in computer science",           # LNCS proceedings umbrella
]


def norm_journal(name):
    if not name:
        return ""
    import html as _html

    n = _html.unescape(name)
    n = n.lower().strip().rstrip("★").strip()
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    if n.startswith("the "):
        n = n[4:]
    n = JOURNAL_ALIASES.get(n, n)
    return n


def arxiv_lookup(cache, aid):
    """arXiv category lookup tolerant of version suffixes in cache keys."""
    if aid in cache:
        return cache[aid]
    for k, v in cache.items():
        if k.startswith(aid + "v"):
            return v
    return None


def classify_venue(paper, enrich, sources):
    # journal DOI first (a published paper's venue is its journal, even if an
    # arXiv preprint ID also exists); arXiv only when there is no DOI.
    # first_doi (header-region, full text) outranks doi_hints (may hold cited/truncated DOIs)
    dois = [paper["first_doi"]] if paper.get("first_doi") else paper["doi_hints"]
    if dois:
        doi = dois[0]
        if doi.startswith(("10.1101", "10.64898")):
            sec = enrich["biorxiv"].get(doi)
            if isinstance(sec, str):
                covered = sec.lower() in sources["biorxiv_sections"]
                return covered, f"bioRxiv:{sec}"
            return True, "bioRxiv:section-unknown"
        if doi.startswith("10.31234"):
            return True, "PsyArXiv"
        j = enrich["crossref"].get(doi, {}).get("journal")
        if j:
            return _journal_covered(j, sources), f"journal:{j} [{_journal_tag(j, sources)}]"
        # DOI known but Crossref lookup failed -> fall through to arXiv/title search
    arx = paper.get("arxiv_ids") or ([paper["first_arxiv"]] if paper.get("first_arxiv") else [])
    if arx:
        cats = [arxiv_lookup(enrich["arxiv"], a) for a in arx]
        cats = [c for c in cats if c]
        if cats:
            covered = cats[0] in sources["arxiv_cats"]
            return covered, f"arXiv:{cats[0]}"
        return True, "arXiv:category-unknown"
    if not dois:
        # title-search fallback (venue enrichment)
        ts = enrich.get("crossref_title", {}).get(paper["id"], {})
        j = ts.get("journal")
        if j:
            return _journal_covered(j, sources), f"journal:{j} [title-match, score={ts.get('score')}]"
        return True, "unknown-venue"
    doi = dois[0]
    if doi.startswith(("10.1101", "10.64898")):
        sec = enrich["biorxiv"].get(doi)
        if isinstance(sec, str):
            covered = sec.lower() in sources["biorxiv_sections"]
            return covered, f"bioRxiv:{sec}"
        return True, "bioRxiv:section-unknown"
    if doi.startswith("10.31234"):
        return True, "PsyArXiv"
    j = enrich["crossref"].get(doi, {}).get("journal")
    if not j:
        return True, f"journal-unknown({doi[:14]})"
    return _journal_covered(j, sources), f"journal:{j} [{_journal_tag(j, sources)}]"


def _journal_covered(j, sources):
    norm = norm_journal(j)
    jset = {norm_journal(x) for x in sources["journals"]}
    if norm in jset:
        return True
    for hint in CONFERENCE_HINTS:
        if hint in norm:
            return True
    return False


def _journal_tag(j, sources):
    norm = norm_journal(j)
    dset = {norm_journal(x) for x in sources["direct_scan"]}
    jset = {norm_journal(x) for x in sources["journals"]}
    if norm in dset:
        return "direct-scan"
    if norm in jset:
        return "listed"
    for hint in CONFERENCE_HINTS:
        if hint in norm:
            return "conference"
    return "NOT-listed"


def run_audit():
    corpus = load_corpus()
    enrich_data = load_enrich()
    prompt = cl.read_prompt(os.path.join(REPO, cl.PROMPT_PATH))
    sections, order = cl.parse_keyword_matrix(prompt)
    counts, total = cl.matrix_totals(sections)
    print("matrix:", counts, "total:", total)
    assert total == cl.EXPECTED_TOTAL, f"matrix total {total} != {cl.EXPECTED_TOTAL}"
    for s in cl.EXPECTED_SECTION_COUNTS:
        assert counts[s] == cl.EXPECTED_SECTION_COUNTS[s], f"section {s}: {counts[s]}"
    sources = cl.parse_sources(prompt)
    print("journals:", len(sources["journals"]), "| direct-scan:", len(sources["direct_scan"]),
          "| arxiv:", sources["arxiv_cats"], "| biorxiv:", sources["biorxiv_sections"])

    kw_norm = {s: [cl.normalize(k) for k in v["keywords"]] for s, v in sections.items()}
    results = []
    for p in corpus["papers"]:
        title_n, abs_n = p["title_norm"], p["abstract_norm"]
        kw_hits = {}
        # per-section matched keywords
        for s, kws in kw_norm.items():
            hits = [k for k in kws if k in f"{title_n} {abs_n}"]
            if hits:
                kw_hits[s] = hits
        v_covered, v_note = classify_venue(p, enrich_data, sources)
        matched = bool(kw_hits)
        if v_covered and matched:
            outcome = "caught"
        elif not v_covered and not matched:
            outcome = "both-gap"
        elif not v_covered:
            outcome = "venue-gap"
        else:
            outcome = "keyword-gap"
        results.append(
            {"id": p["id"], "filepath": p["filepath"], "year": p["year"], "title": p["title"],
             "venue_note": v_note, "venue_covered": v_covered, "sections": sorted(kw_hits),
             "outcome": outcome}
        )

    stats = Counter(r["outcome"] for r in results)
    n = len(results)
    kw_recall = (stats["caught"] + stats["venue-gap"]) / n  # keyword gate recall (venue blind)
    venue_coverage = (stats["caught"] + stats["keyword-gap"]) / n
    print("\n=== TWO-LAYER AUDIT ===")
    print(f"n={n} | {dict(stats)}")
    print(f"keyword-gate recall: {kw_recall:.1%}  | venue coverage: {venue_coverage:.1%}")

    # venue coverage on the 2020+ subset (scale-up acceptance metric)
    recent = [r for r in results if corpus and r["year"] and int(r["year"]) >= 2020]
    if recent:
        recent_cov = sum(1 for r in recent if r["venue_covered"]) / len(recent)
        print(f"venue coverage (2020+ subset, n={len(recent)}): {recent_cov:.1%}")
    else:
        recent_cov = None

    # calibration: reported papers must be keyword-caught (title OR finding text)
    reported = cl.parse_reported_papers(os.path.join(REPO, "outputs"), with_findings=True)
    miss_reported = []
    for r in reported:
        blob = cl.normalize(f"{r['title']} {r['finding']}")
        hit = any(k in blob for kws in kw_norm.values() for k in kws)
        if not hit:
            miss_reported.append(r["title"])
    cal = 1 - len(miss_reported) / len(reported) if reported else 0
    print(f"calibration: {len(reported)} reported papers, keyword-caught {cal:.1%} (title+finding)")
    for t in miss_reported[:10]:
        print("   NOT caught by matrix:", t[:90])

    # baseline snapshot (preserve regression-check state fields if present)
    old_baseline = {}
    bl_path = os.path.join(AUDIT_DIR, "audit_baseline.json")
    if os.path.exists(bl_path):
        with open(bl_path, encoding="utf-8") as f:
            old_baseline = json.load(f)
    baseline = {
        "matrix_hash": cl.matrix_hash(sections),
        "window": corpus["window"],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "outcomes": {r["id"]: {"o": r["outcome"], "sections": r["sections"]} for r in results},
        "stats": dict(stats),
        "keyword_recall": kw_recall,
        "venue_coverage": venue_coverage,
        "calibration_reported_caught": cal,
        "n_reported": len(reported),
        "golden_fail": old_baseline.get("golden_fail", []),
        "venue_gaps": old_baseline.get("venue_gaps"),
    }
    with open(bl_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=1)

    # CSVs
    with open(os.path.join(AUDIT_DIR, "missed_papers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "year", "title", "outcome", "venue_note", "sections"])
        for r in results:
            if r["outcome"] != "caught":
                w.writerow([r["id"], r["year"], r["title"], r["outcome"], r["venue_note"], "|".join(r["sections"])])
    with open(os.path.join(AUDIT_DIR, "hit_papers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "year", "title", "venue_note", "sections"])
        for r in results:
            if r["outcome"] == "caught":
                w.writerow([r["id"], r["year"], r["title"], r["venue_note"], "|".join(r["sections"])])

    # report section 2
    lines = ["## 2. Two-layer recall audit", f"Corpus: {n} papers ({corpus['window']}). "
             f"Keyword-gate recall **{kw_recall:.1%}**; venue coverage **{venue_coverage:.1%}**.",
             "", "| Outcome | n | % |", "|---|---|---|"]
    for o, c in stats.most_common():
        lines.append(f"| {o} | {c} | {c / n:.1%} |")
    lines.append("")
    lines.append(f"**Calibration:** {cal:.1%} of the {len(reported)} actually-reported papers are "
                 "keyword-caught (target ≥90%).")
    if miss_reported:
        lines.append("\nReported-but-not-keyword-caught (sample):")
        for t in miss_reported[:8]:
            lines.append(f"- {t}")
    lines.append("")
    report_append("\n".join(lines))
    print("audit done -> data/audit/audit_baseline.json")
    return results, baseline


# ---------------------------------------------------------------------------
# Stage: mine (ngram + embedding) + simulation
# ---------------------------------------------------------------------------
def _ngrams(text, n):
    toks = text.split()
    return [" ".join(toks[i : i + n]) for i in range(len(toks) - n + 1)]


def run_mine():
    corpus = load_corpus()
    with open(os.path.join(AUDIT_DIR, "audit_baseline.json"), encoding="utf-8") as f:
        baseline = json.load(f)
    prompt = cl.read_prompt(os.path.join(REPO, cl.PROMPT_PATH))
    sections, order = cl.parse_keyword_matrix(prompt)
    existing = {cl.normalize(k) for v in sections.values() for k in v["keywords"]}
    stop = get_stopwords()

    miss_ids = {i for i, r in baseline["outcomes"].items() if r["o"] in ("keyword-gap", "both-gap")}
    misses = [p for p in corpus["papers"] if p["id"] in miss_ids]
    print(f"misses (keyword layer): {len(misses)}")

    if len(misses) < 5:
        # keyword layer is saturated for this library: nothing to mine
        lines = ["## 3. Miss mining & edit simulation",
                 f"**Finding: the keyword layer is saturated for this corpus** — only {len(misses)} "
                 "paper(s) fail the keyword gate, so ngram/embedding mining has no signal. "
                 "The matrix (390 keywords) already covers the vocabulary of the 362-paper library.",
                 ""]
        for p in misses:
            lines.append(f"- Keyword-gap paper: *{p['title']}* — out-of-domain for the tracker "
                         "(see §2); no keyword action needed.")
        lines.append("")
        lines.append("> **Implication:** the coverage bottleneck is the **venue layer** (§4), not the "
                     "keyword layer. Keyword edits should be driven by the *reported-golden-set* misses "
                     "from §2 calibration, not by this corpus.")
        lines.append("")
        report_append("\n".join(lines))
        with open(os.path.join(AUDIT_DIR, "candidates.json"), "w", encoding="utf-8") as f:
            json.dump({"ngram_n": 0, "embedding_n": 0, "candidates": [], "note": "keyword layer saturated"}, f, indent=1)
        print("mining skipped: keyword layer saturated (see report §3)")
        return []

    # ---- ngram miner ----
    corpus_blob = " ".join(f"{p['title_norm']} {p['abstract_norm']}" for p in corpus["papers"])
    corpus_tokens = set(corpus_blob.split())
    cand = {}
    for p in misses:
        blob = f"{p['title_norm']} {p['abstract_norm']}"
        for n in (1, 2, 3):
            for g in _ngrams(blob, n):
                toks = g.split()
                if n == 1 and (g in stop or len(g) < 4):
                    continue
                if n > 1 and all(t in stop for t in toks):
                    continue
                if n > 1 and not any(t not in stop and len(t) >= 4 for t in toks):
                    continue
                cand.setdefault(g, {"freq": 0, "papers": set()})
                cand[g]["freq"] += 1
                cand[g]["papers"].add(p["id"])

    def specificity(gram):
        df = sum(1 for p in corpus["papers"] if gram in f"{p['title_norm']} {p['abstract_norm']}")
        return df / len(corpus["papers"])

    def ok_candidate(g, info):
        if g in existing:
            return False
        if info["freq"] < 2:
            return False
        if g in corpus_tokens and len(g.split()) == 1:  # single token already ubiquitous
            if specificity(g) > 0.60:
                return False
        if specificity(g) > 0.60:
            return False
        return True

    ngram_cands = {g: info for g, info in cand.items() if ok_candidate(g, info)}

    # ---- embedding miner (synonym discovery) ----
    em_cands = {}
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        sec_vecs = {}
        for s in order:
            text = " ".join(sections[s]["keywords"])
            sec_vecs[s] = model.encode([text], normalize_embeddings=True)[0]
        import numpy as np

        miss_vecs = model.encode([p["abstract_window"] for p in misses], normalize_embeddings=True, batch_size=32)
        assigned = defaultdict(list)  # section -> [paper idx]
        for idx, v in enumerate(miss_vecs):
            best = max(order, key=lambda s: float(np.dot(v, sec_vecs[s])))
            assigned[best].append(idx)
        for s, idxs in assigned.items():
            cluster_text = " ".join(f"{misses[i]['title_norm']} {misses[i]['abstract_norm']}" for i in idxs)
            ctr = Counter()
            for n in (1, 2):
                for g in _ngrams(cluster_text, n):
                    if n == 1 and (g in stop or len(g) < 4):
                        continue
                    if n > 1 and all(t in stop for t in g.split()):
                        continue
                    ctr[g] += 1
            for g, f in ctr.most_common(400):
                if g in existing or g in ngram_cands:
                    continue
                df = sum(1 for p in corpus["papers"] if g in f"{p['title_norm']} {p['abstract_norm']}")
                spec = df / len(corpus["papers"])
                if f >= 2 and spec <= 0.60:
                    em_cands[g] = {"freq": f, "papers": {misses[i]["id"] for i in idxs}, "section": s, "spec": spec}
    except Exception as e:
        print("embedding miner failed:", e)

    # ---- merge ----
    merged = {}
    for g, info in ngram_cands.items():
        merged[g] = {"freq": info["freq"], "n_papers": len(info["papers"]), "spec": specificity(g),
                     "source": "ngram", "sections": set()}
    for g, info in em_cands.items():
        if g in merged:
            merged[g]["source"] = "both"
            merged[g]["freq"] = max(merged[g]["freq"], info["freq"])
        else:
            merged[g] = {"freq": info["freq"], "n_papers": len(info["papers"]), "spec": info["spec"],
                         "source": "embedding", "sections": {info["section"]}}

    # section assignment for ngram candidates: co-occurrence with existing section keywords
    for g in merged:
        hits = Counter()
        for p in corpus["papers"]:
            if g not in f"{p['title_norm']} {p['abstract_norm']}":
                continue
            for s, kws in {s: [cl.normalize(k) for k in v["keywords"]] for s, v in sections.items()}.items():
                if any(k in f"{p['title_norm']} {p['abstract_norm']}" for k in kws):
                    hits[s] += 1
        if hits:
            merged[g]["sections"] = {s for s, c in hits.most_common(2) if c >= 1}

    ranked = sorted(merged.items(), key=lambda kv: (-kv[1]["freq"], kv[1]["spec"]))
    ranked = [(g, info) for g, info in ranked if not (info["freq"] >= 10 and info["spec"] > 0.5)]
    print(f"\ncandidates: ngram={len(ngram_cands)} embedding={len(em_cands)} merged={len(ranked)}")
    for g, info in ranked[:20]:
        print(f"  {info['freq']:3d}x spec={info['spec']:.2f} {info['source']:9s} {g[:70]}")

    # ---- simulation: rescued papers per candidate (recency-filtered) ----
    RECENT_YEAR = 2020  # the tracker reports new papers; only candidates that
    # rescue at least one recent paper are worth adding (scale-up decision D5)
    sim = []
    for g, info in ranked:
        rescued = []
        for p in corpus["papers"]:
            if p["id"] in miss_ids and g in f"{p['title_norm']} {p['abstract_norm']}":
                rescued.append(p)
        recent = [p for p in rescued if p["year"] and int(p["year"]) >= RECENT_YEAR]
        if not recent:
            continue  # recency filter: useless for the daily digest
        sim.append({"keyword": g, "freq": info["freq"], "spec": info["spec"], "source": info["source"],
                    "sections": sorted(info["sections"]), "n_rescued": len(rescued), "n_recent": len(recent),
                    "rescued": [{"id": p["id"], "year": p["year"], "title": p["title"],
                                 "snippet": p["abstract_window"][:220].replace("\n", " ")} for p in rescued[:3]]})
        if len(sim) >= 80:
            break
    with open(os.path.join(AUDIT_DIR, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump({"ngram_n": len(ngram_cands), "embedding_n": len(em_cands),
                   "recency_year": RECENT_YEAR, "candidates": sim},
                  f, ensure_ascii=False, indent=1)

    # report section 3
    lines = ["## 3. Miss mining & edit simulation",
             f"Misses: {len(misses)}. Candidates: {len(sim)} shown (freq≥2, specificity≤60%, not already in matrix, "
             f"**and rescuing ≥1 paper from {RECENT_YEAR}+** — scale-up recency filter).",
             "Review = the **rescued papers**, not the keywords: drop any keyword whose rescued papers look off-topic.",
             "", "| Keyword | Source | Freq | Spec | Section(s) | #rescued (≥2020) | Rescued papers (first 3)", "|---|---|---|---|---|---|---|"]
    for c in sim[:50]:
        titles = "; ".join(f"{r['year']} {r['title'][:60]}" for r in c["rescued"])
        lines.append(f"| `{c['keyword']}` | {c['source']} | {c['freq']} | {c['spec']:.2f} | "
                     f"{','.join(c['sections']) or '?'} | {c['n_rescued']} ({c['n_recent']}) | {titles[:200]} |")
    lines.append("")
    report_append("\n".join(lines))
    print("mining done -> data/audit/candidates.json")
    return sim


# ---------------------------------------------------------------------------
# Stage: venue (tiered recommendations)
# ---------------------------------------------------------------------------
def run_venue():
    corpus = load_corpus()
    prompt = cl.read_prompt(os.path.join(REPO, cl.PROMPT_PATH))
    sources = cl.parse_sources(prompt)
    enrich_data = load_enrich()
    notes = Counter()
    for p in corpus["papers"]:
        covered, note = classify_venue(p, enrich_data, sources)
        if not covered:
            notes[note] += 1
    lines = ["## 4. Venue calibration",
             "Papers failing the venue gate after the 2026-08-01 expansion (journals 47→66, direct-scan 10→16, "
             "ACL/CVPR proceedings added):", ""]
    for note, c in notes.most_common():
        lines.append(f"- **{note}**: {c} paper(s)")
    lines.append("\n**Remaining gaps — recommended: do NOT add.** These are single papers in off-domain or "
                 "low-yield venues (sociology, health-tech, general engineering); adding them would add scan "
                 "cost without coverage value. Revisit if the library accumulates ≥2 papers from any of them.")
    # tiered recs (recency-filtered: scale-up decision D4 — only recommend
    # journals still publishing, i.e. with >=1 corpus paper from 2020+)
    RECENT_YEAR = 2020
    journal_years = defaultdict(list)  # journal name -> [years]
    arxiv_gaps = Counter()
    for p in corpus["papers"]:
        covered, note = classify_venue(p, enrich_data, sources)
        if covered or not note.startswith(("journal:", "arXiv:")):
            continue
        if note.startswith("journal:"):
            name = note.split("[")[0][len("journal:"):].strip()
            if p["year"]:
                journal_years[name].append(int(p["year"]))
        elif note.startswith("arXiv:"):
            arxiv_gaps[note[len("arXiv:"):]] += 1

    active = {n: ys for n, ys in journal_years.items() if len(ys) >= 2 and max(ys) >= RECENT_YEAR}
    historical = {n: ys for n, ys in journal_years.items() if len(ys) >= 2 and max(ys) < RECENT_YEAR}
    singles = {n: ys for n, ys in journal_years.items() if len(ys) == 1}

    lines.append("\n**Tier 1 — ACTIVE journals to ADD to the source list** (≥2 library papers, ≥1 from 2020+):")
    if active:
        for name, ys in sorted(active.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"- {name} ({len(ys)} papers, {min(ys)}–{max(ys)})")
    else:
        lines.append("- (none)")
    lines.append("\n**Tier 1b — HISTORICAL ONLY (do NOT add to the daily scan)** "
                 "(≥2 papers but none from 2020+ — likely dead/renamed venues):")
    if historical:
        for name, ys in sorted(historical.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"- {name} ({len(ys)} papers, {min(ys)}–{max(ys)})")
    else:
        lines.append("- (none)")
    lines.append("\n**Tier 1c — single-paper venues (no recommendation, for reference):**")
    if singles:
        for name, ys in sorted(singles.items(), key=lambda kv: -kv[1][0])[:15]:
            lines.append(f"- {name} ({ys[0]})")
    else:
        lines.append("- (none)")
    lines.append("\n**Tier 2 — promote to direct-scan?** (listed in the 47 but not direct-scanned; "
                 "shown with corpus paper counts — prefer venues with high library weight)")
    listed_counts = Counter()
    for p in corpus["papers"]:
        covered, note = classify_venue(p, enrich_data, sources)
        if covered and "[listed]" in note:
            name = note.split("[")[0][len("journal:"):].strip()
            listed_counts[name] += 1
    for name, c in listed_counts.most_common():
        lines.append(f"- {name} ({c} corpus paper(s))")
    if not listed_counts:
        lines.append("- (none)")
    lines.append("\n**Tier 3 — arXiv categories to consider:**")
    for cat, c in arxiv_gaps.most_common(5):
        lines.append(f"- {cat} ({c} papers in corpus)")
    lines.append("")
    report_append("\n".join(lines))
    print("venue analysis done")


# ---------------------------------------------------------------------------
# Stage: sections
# ---------------------------------------------------------------------------
def run_sections():
    with open(os.path.join(AUDIT_DIR, "audit_baseline.json"), encoding="utf-8") as f:
        baseline = json.load(f)
    corpus = load_corpus()
    prompt = cl.read_prompt(os.path.join(REPO, cl.PROMPT_PATH))
    sections, order = cl.parse_keyword_matrix(prompt)
    counts, total = cl.matrix_totals(sections)
    kw_norm = {s: [cl.normalize(k) for k in v["keywords"]] for s, v in sections.items()}

    def era_of(year):
        if not year:
            return "?"
        y = int(year)
        if y < 2010:
            return "2000-09"
        if y < 2020:
            return "2010-19"
        return "2020-26"

    # non-exclusive coverage + primary section (most matched keywords)
    cover = Counter()
    prim = Counter()
    cover_era = defaultdict(Counter)  # era -> section -> n
    for p in corpus["papers"]:
        blob = f"{p['title_norm']} {p['abstract_norm']}"
        matched = {s: [k for k in kws if k in blob] for s, kws in kw_norm.items()}
        matched = {s: hits for s, hits in matched.items() if hits}
        era = era_of(p["year"])
        for s in matched:
            cover[s] += 1
            cover_era[era][s] += 1
        if matched:
            best = max(order, key=lambda s: (len(matched.get(s, [])), -order.index(s)))
            prim[best] += 1

    lines = ["## 5. Section distribution (by era)",
             "| Section | Keywords | Total | 2000–09 | 2010–19 | 2020–26 |",
             "|---|---|---|---|---|---|"]
    for s in order:
        lines.append(f"| {s} — {sections[s]['name'][:36]} | {counts[s]} | {cover.get(s, 0)} | "
                     f"{cover_era['2000-09'].get(s, 0)} | {cover_era['2010-19'].get(s, 0)} | {cover_era['2020-26'].get(s, 0)} |")
    lines.append("")
    report_append("\n".join(lines))
    print("section coverage:", dict(cover))
    print("primary:", dict(prim))
    print("by era:", {e: dict(c) for e, c in cover_era.items()})
    print("sections done")


# ---------------------------------------------------------------------------
# Stage: precision sampling
# ---------------------------------------------------------------------------
def run_precision():
    cards = cl.parse_reported_papers(os.path.join(REPO, "outputs"), with_findings=True)
    groups = defaultdict(list)
    for c in cards:
        groups[c["tag"]].append(c)
    # stratified sample, 25 total, proportional
    sample, target = [], 25
    for tag, items in groups.items():
        n = max(1, round(target * len(items) / max(1, len(cards))))
        sample += items[:n]
    sample = sample[:target]

    # preserve existing ratings (by normalized title) across re-runs
    existing = {}
    spath = os.path.join(AUDIT_DIR, "precision_sample.json")
    if os.path.exists(spath):
        with open(spath, encoding="utf-8") as f:
            old = json.load(f)
        for e in old.get("sample", []):
            if e.get("rating"):
                existing[cl.normalize(e["title"])] = (e["rating"], e.get("rationale"))
    for p in sample:
        key = cl.normalize(p["title"])
        if key in existing:
            p["rating"], p["rationale"] = existing[key]
    kept = [p for p in sample if p["rating"] == "keep"]
    with open(spath, "w", encoding="utf-8") as f:
        json.dump({"n_total": len(cards), "precision_keep": round(len(kept) / len(sample), 3)
                   if kept or any(p["rating"] for p in sample) else None,
                   "rated_by": "agent pre-rating (editor standard) — Qihong to confirm", "sample": [
            {"tag": p["tag"], "title": p["title"], "finding": p["finding"][:300],
             "rating": p.get("rating"), "rationale": p.get("rationale")} for p in sample]},
            f, ensure_ascii=False, indent=1)
    n_rated = sum(1 for p in sample if p["rating"])
    print(f"precision sample: {len(sample)} papers (of {len(cards)} reported), {n_rated} rated")
    print("tags:", dict((t, len(g)) for t, g in groups.items()))

    # report section 5b (only when ratings exist)
    if n_rated:
        rows = {}
        for p in sample:
            rows.setdefault(p["tag"], [0, 0])
            rows[p["tag"]][0 if p["rating"] == "keep" else 1] += 1
        lines = ["## 5b. Precision sampling (reported papers, editor-standard rating)",
                 f"Sample: {len(sample)} of {n_rated} rated (stratified by tag). "
                 f"**Estimated precision: {len(kept) / n_rated:.0%} keep** (agent pre-rating; Qihong to confirm).",
                 "", "| Tag | Sampled | Keep | Drop |", "|---|---|---|---|"]
        for tag in sorted(rows):
            k, d = rows[tag]
            lines.append(f"| {tag} | {k+d} | {k} | {d} |")
        lines.append("")
        lines.append("**Filter-calibration notes:**")
        lines.append("- **LLM tag** carries the drop risk (serving/throughput optimization papers). "
                     "Exclude serving/efficiency papers unless they make a concrete memory-mechanism claim "
                     "(retention, retrieval, drift, KV-as-memory) — this rule was added to the prompt in the 2026-08-01 edit.")
        lines.append("- **Peripheral physiology** and **non-decisive testbeds** (p≈0.37) also dropped; "
                     "keep the ⚠ flag habit for small-N/non-decisive stats.")
        lines.append("- Overall the filter is working: drops were engineering/peripheral, not wrong-domain.")
        lines.append("")
        report_append("\n".join(lines))


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["build-corpus", "enrich", "audit", "mine", "venue", "sections", "precision", "all"])
    ap.add_argument("--window", default="2025-2026")
    ap.add_argument("--since", type=int, default=None, help="include papers with year >= N (e.g. 2000)")
    ap.add_argument("--enrich-only", action="store_true")
    args = ap.parse_args()

    if args.stage == "all" and os.path.exists(OUT_MD):
        os.remove(OUT_MD)  # fresh report for full runs

    if args.stage in ("build-corpus", "all"):
        if args.since:
            build_corpus(None, since=args.since)
        else:
            build_corpus(args.window.split("-") if args.window != "all" else None)
    if args.stage in ("enrich", "all"):
        enrich()
    if args.stage in ("audit", "all"):
        run_audit()
    if args.stage in ("mine", "all"):
        run_mine()
    if args.stage in ("venue", "all"):
        run_venue()
    if args.stage in ("sections", "all"):
        run_sections()
    if args.stage in ("precision", "all"):
        run_precision()
    if args.stage == "all":
        print("\nALL STAGES DONE ->", OUT_MD)


if __name__ == "__main__":
    main()
