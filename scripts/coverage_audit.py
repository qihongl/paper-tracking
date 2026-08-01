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
def build_corpus(window):
    os.makedirs(AUDIT_DIR, exist_ok=True)
    conn = paperdb.connect()
    papers = paperdb.list_papers(conn)
    out, stats = [], Counter()
    for fp in papers:
        chunks = paperdb.get_chunks(conn, fp)
        meta = paperdb.extract_metadata(fp, chunks)
        if window and meta["year"] not in window:
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
    corpus = {"window": window, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "papers": out, "stats": dict(stats)}
    path = os.path.join(AUDIT_DIR, "corpus.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=1)
    print(f"corpus: {len(out)} papers -> {path}")
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
        for d in p["doi_hints"]:
            if d.startswith(("10.1101", "10.64898")):
                biorxiv.add(d)
            elif not d.startswith("10.31234") and not d.startswith("10.48550"):
                dois.add(d)
            has_id = True
        if p["arxiv_ids"]:
            arxiv_ids.update(p["arxiv_ids"])
            has_id = True
        if not has_id and p["title"]:
            title_search.append((p["id"], p["title"]))

    # --- Crossref (by DOI) ---
    todo = [d for d in sorted(dois) if d not in cache["crossref"]]
    print(f"crossref (DOI): {len(todo)} to fetch (of {len(dois)})")
    for i, doi in enumerate(todo, 1):
        try:
            url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="") + f"?mailto={MAILTO}"
            msg = fetch_json(url)["message"]
            journal = None
            for k in ("container-title", "short-container-title"):
                if msg.get(k):
                    journal = msg[k][0]
                    break
            cache["crossref"][doi] = {"journal": journal, "type": msg.get("type")}
        except Exception as e:
            cache["crossref"][doi] = {"journal": None, "error": str(e)[:80]}
        if i % 25 == 0:
            print(f"  crossref {i}/{len(todo)}")
            _save_enrich(path, cache)
        time.sleep(0.25)
    _save_enrich(path, cache)

    # --- Crossref (title search fallback for identifier-less papers) ---
    import difflib

    todo = [(pid, t) for pid, t in title_search if pid not in cache["crossref_title"]]
    print(f"crossref (title search): {len(todo)} to fetch")
    for i, (pid, title) in enumerate(todo, 1):
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
                cache["crossref_title"][pid] = {"doi": best.get("DOI"), "journal": journal,
                                                "score": round(best_score, 3)}
            else:
                cache["crossref_title"][pid] = {"doi": None, "journal": None, "score": round(best_score, 3)}
        except Exception as e:
            cache["crossref_title"][pid] = {"doi": None, "journal": None, "error": str(e)[:80]}
        if i % 25 == 0:
            print(f"  titlesearch {i}/{len(todo)}")
            _save_enrich(path, cache)
        time.sleep(0.25)
    _save_enrich(path, cache)

    # --- arXiv (batches of 50) ---
    todo = [a for a in sorted(arxiv_ids) if a not in cache["arxiv"]]
    print(f"arxiv: {len(todo)} to fetch")
    ns = {"a": "http://www.w3.org/2005/Atom", "ar": "http://arxiv.org/schemas/atom"}
    for i in range(0, len(todo), 50):
        batch = todo[i : i + 50]
        try:
            url = "http://export.arxiv.org/api/query?id_list=" + ",".join(batch) + "&max_results=100"
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                root = ET.fromstring(r.read())
            for entry in root.findall("a:entry", ns):
                eid = (entry.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
                pc = entry.find("ar:primary_category", ns)
                if eid and pc is not None:
                    cache["arxiv"][eid] = pc.get("term")
        except Exception as e:
            print(f"  arxiv batch failed: {e}")
        time.sleep(3)
    _save_enrich(path, cache)

    # --- bioRxiv ---
    todo = [d for d in sorted(biorxiv) if d not in cache["biorxiv"]]
    print(f"biorxiv: {len(todo)} to fetch")
    for doi in todo:
        try:
            url = "https://api.biorxiv.org/details/biorxiv/" + urllib.parse.quote(doi, safe="")
            data = fetch_json(url)
            coll = data.get("collection") or []
            cache["biorxiv"][doi] = coll[0].get("category") if coll else None
        except Exception as e:
            cache["biorxiv"][doi] = {"error": str(e)[:80]}
        time.sleep(0.3)
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
def norm_journal(name):
    if not name:
        return ""
    n = name.lower().strip().rstrip("★").strip()
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    if n.startswith("the "):
        n = n[4:]
    return n


def classify_venue(paper, enrich, sources):
    if paper["arxiv_ids"]:
        cats = [enrich["arxiv"].get(a) for a in paper["arxiv_ids"] if enrich["arxiv"].get(a)]
        if cats:
            covered = cats[0] in sources["arxiv_cats"]
            return covered, f"arXiv:{cats[0]}"
        return True, "arXiv:category-unknown"
    dois = paper["doi_hints"]
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
    return norm in jset


def _journal_tag(j, sources):
    norm = norm_journal(j)
    dset = {norm_journal(x) for x in sources["direct_scan"]}
    jset = {norm_journal(x) for x in sources["journals"]}
    if norm in dset:
        return "direct-scan"
    if norm in jset:
        return "listed"
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

    # calibration: reported papers must be keyword-caught >= 90%
    reported = cl.parse_reported_papers(os.path.join(REPO, "outputs"))
    miss_reported = []
    for t in reported:
        tn = cl.normalize(t)
        hit = any(k in tn for kws in kw_norm.values() for k in kws)
        if not hit:
            miss_reported.append(t)
    cal = 1 - len(miss_reported) / len(reported) if reported else 0
    print(f"calibration: {len(reported)} reported papers, keyword-caught {cal:.1%}")
    for t in miss_reported[:10]:
        print("   NOT caught by matrix:", t[:90])

    # baseline snapshot
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
    }
    with open(os.path.join(AUDIT_DIR, "audit_baseline.json"), "w", encoding="utf-8") as f:
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

    # ---- simulation: rescued papers per candidate ----
    sim = []
    for g, info in ranked[:60]:
        rescued = []
        for p in corpus["papers"]:
            if p["id"] in miss_ids and g in f"{p['title_norm']} {p['abstract_norm']}":
                rescued.append(p)
        sim.append({"keyword": g, "freq": info["freq"], "spec": info["spec"], "source": info["source"],
                    "sections": sorted(info["sections"]), "n_rescued": len(rescued),
                    "rescued": [{"id": p["id"], "year": p["year"], "title": p["title"],
                                 "snippet": p["abstract_window"][:220].replace("\n", " ")} for p in rescued[:3]]})
    with open(os.path.join(AUDIT_DIR, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump({"ngram_n": len(ngram_cands), "embedding_n": len(em_cands), "candidates": sim},
                  f, ensure_ascii=False, indent=1)

    # report section 3
    lines = ["## 3. Miss mining & edit simulation",
             f"Misses: {len(misses)}. Candidates: {len(sim)} shown (freq≥2, specificity≤60%, not already in matrix).",
             "Review = the **rescued papers**, not the keywords: drop any keyword whose rescued papers look off-topic.",
             "", "| Keyword | Source | Freq | Spec | Section(s) | #rescued | Rescued papers (first 3)", "|---|---|---|---|---|---|---|"]
    for c in sim[:50]:
        titles = "; ".join(f"{r['year']} {r['title'][:60]}" for r in c["rescued"])
        lines.append(f"| `{c['keyword']}` | {c['source']} | {c['freq']} | {c['spec']:.2f} | "
                     f"{','.join(c['sections']) or '?'} | {c['n_rescued']} | {titles[:200]} |")
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
             "Papers failing the venue gate (tracker never looks at this venue):", ""]
    for note, c in notes.most_common():
        lines.append(f"- **{note}**: {c} paper(s)")
    # tiered recs
    journal_gaps = Counter()
    arxiv_gaps = Counter()
    for p in corpus["papers"]:
        covered, note = classify_venue(p, enrich_data, sources)
        if covered or not note.startswith(("journal:", "arXiv:")):
            continue
        if note.startswith("journal:"):
            name = note.split("[")[0][len("journal:"):].strip()
            journal_gaps[name] += 1
        elif note.startswith("arXiv:"):
            arxiv_gaps[note[len("arXiv:"):]] += 1
    lines.append("\n**Tier 1 — journals to ADD to the source list:**")
    for name, c in journal_gaps.most_common(10):
        lines.append(f"- {name} ({c})")
    lines.append("\n**Tier 2 — promote to direct-scan?** (in the 47 but not in the 10 direct-scanned; check library weight)")
    for j in sorted(sources["journals"] - sources["direct_scan"]):
        lines.append(f"- {j}")
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
    by_id = {p["id"]: p for p in corpus["papers"]}
    prim = Counter()
    for i, r in baseline["outcomes"].items():
        secs = r["sections"]
        if secs:
            prim[secs[0]] += 1
    lines = ["## 5. Section distribution",
             "| Section | Keywords | Corpus papers (primary) | Social posts (ref) |", "|---|---|---|---|"]
    for s in order:
        lines.append(f"| {s} — {sections[s]['name'][:40]} | {counts[s]} | {prim.get(s, 0)} | — |")
    lines.append("")
    report_append("\n".join(lines))
    print("sections done:", dict(prim))


# ---------------------------------------------------------------------------
# Stage: precision sampling
# ---------------------------------------------------------------------------
def run_precision():
    import glob

    out = []
    for f in sorted(glob.glob(os.path.join(REPO, "outputs", "*-paper-tracker.html"))):
        with open(f, encoding="utf-8") as fh:
            html = fh.read()
        # locate section tags and paper cards by position
        sec_pos = [(m.start(), m.group(1)) for m in re.finditer(r'<div class="section-header tag-(\w+)">', html)]
        for m in re.finditer(r'<div class="paper">', html):
            card = html[m.start() : m.start() + 4000]
            tm = re.search(r'<div class="paper-title">\s*<a href="([^"]*)"[^>]*>(.*?)</a>', card, re.S)
            if not tm:
                continue
            tag = next((t for pos, t in reversed(sec_pos) if pos < m.start()), "?")
            fm = re.search(r"<strong>Finding:</strong>\s*(.*?)</p>", card, re.S)
            out.append({"tag": tag, "url": tm.group(1), "title": cl.html_unescape(tm.group(2)).strip(),
                        "finding": cl.html_unescape(fm.group(1)).strip() if fm else ""})
    groups = defaultdict(list)
    for p in out:
        groups[p["tag"]].append(p)
    # stratified sample, 25 total, proportional
    sample, target = [], 25
    for tag, items in groups.items():
        n = max(1, round(target * len(items) / max(1, len(out))))
        sample += items[:n]
    sample = sample[:target]
    with open(os.path.join(AUDIT_DIR, "precision_sample.json"), "w", encoding="utf-8") as f:
        json.dump({"n_total": len(out), "sample": [
            {"tag": p["tag"], "title": p["title"], "finding": p["finding"][:300], "url": p["url"],
             "rating": None, "rationale": None} for p in sample]}, f, ensure_ascii=False, indent=1)
    print(f"precision sample: {len(sample)} papers (of {len(out)} reported) -> data/audit/precision_sample.json")
    print("tags:", dict((t, len(g)) for t, g in groups.items()))


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["build-corpus", "enrich", "audit", "mine", "venue", "sections", "precision", "all"])
    ap.add_argument("--window", default="2025-2026")
    ap.add_argument("--enrich-only", action="store_true")
    args = ap.parse_args()

    if args.stage in ("build-corpus", "all"):
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
