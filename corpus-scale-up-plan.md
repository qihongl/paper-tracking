# Corpus Scale-Up Plan: All Papers Since 2000

> **Status:** Draft for review · **Owner:** Qihong Lu · **Date:** 2026-08-01
> **Repo:** `~/Documents/GitHub/paper-tracking` · **Predecessor:** `coverage-polish-plan.md` (2025–2026 window, executed)

## 1. Goal

Re-run the two-layer coverage pipeline on the **full library since 2000** (~3,930 papers, 11× the current 362-paper corpus) to:
1. Surface **legacy-vocabulary keyword gaps** (terms like "paired-associate learning", "trace conditioning" that 2025–26 acquisitions no longer contain but *current* papers still use).
2. Produce a **recency-filtered venue diff** — journals collected across 25 years that the tracker doesn't scan, restricted to venues still active.
3. Show the **historical section drift** (A–G coverage by era) as a diagnostic.
4. Keep the regression guarantees intact (re-pinned baseline + reported-papers golden set).

## 2. Measured ground truth (2026-08-01)

| Era | Papers (filename year) | DOI-hint rate* | arXiv | bioRxiv |
|---|---|---|---|---|
| pre-2000 (excluded) | 270 | 2% | 0% | 0% |
| 2000–2009 | 456 | 15% | 0% | 0% |
| 2010–2019 | 2,108 | 32% | 5% | 3% |
| 2020–2026 | 1,365 | 45% | 0% | 10% |
| yearless (fallback to chunk year) | 70 | — | — | — |
| **Since-2000 corpus** | **≈ 3,930–4,000** | — | — | — |

*DOI/arXiv/bioRxiv hints from first 6 chunks (60-paper stratified sample per era).

**Key implications (why this is not just "the same run × 11"):**

- **Enrichment load triples the API volume**: ~1,360 DOI lookups + ~2,200 title searches + ~200 bioRxiv + ~200 arXiv ≈ **~3,950 Crossref-family calls** (vs ~350 now). Pre-2010 papers mostly have **no DOI in text** → title-search becomes the primary identifier.
- **Venue recommendations need a recency filter.** ~70% of the corpus is pre-2020; without a filter, the venue diff will recommend *dead and renamed journals* (e.g., Cognitive Brain Research, JEP: Animal Behavior Processes) for daily scanning. **A journal is only recommendable if it still publishes** — require ≥2 corpus papers AND ≥1 paper from 2020+.
- **Keyword candidates need a recency filter too.** The tracker reports papers from the last 7 days. A keyword that only rescues 2003 papers is worthless for the digest. **Require each candidate to rescue ≥1 paper from 2020+.**
- **Old-scanned-PDF noise** (~5% OCR'd, worse in pre-2010) inflates the miss set with false negatives — audit outputs will flag `needs_ocr` papers so misses can be sanity-checked.
- **Git size**: the since-2000 `corpus.json` ≈ 15–20 MB (abstract windows for 3,930 papers). Fine for GitHub (<100 MB) but a decision point (Q3).

## 3. Design decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Window = `year ≥ 2000`; year from filename, chunk-text fallback for the 70 yearless; report excluded/unresolved counts | "Since 2000" as specified; deterministic |
| D2 | Keep the 362-paper corpus as `corpus_2025.json` + its baseline for continuity; the since-2000 corpus becomes the primary pinned regression substrate | Old results stay reproducible |
| D3 | Enrichment runs **8-threaded** (Crossref polite pool, `mailto` set), cached + resumable (existing cache format) | 50–60 min sequential → ~10 min; zero re-fetch on re-runs |
| D4 | Venue recs recency-filtered: recommend only journals with ≥2 corpus papers **and** ≥1 paper from 2020+; flagged renamed/dead venues listed separately as "historical only" | No dead venues in the daily scan list |
| D5 | Keyword candidates recency-filtered: must rescue ≥1 paper from 2020+; specificity ≤60%; cap +50–80 per iteration; review table shows rescued papers **with years** | Every added keyword must help the *new-paper* digest, not the archive |
| D6 | Calibration (reported-papers golden set) and precision sampling unchanged — they measure the 2026 reports, not the corpus | No scope creep |
| D7 | `needs_ocr` papers flagged in miss lists; excluded from mining corpus by default (configurable) | OCR noise ≠ vocabulary gap |

## 4. Stage-by-stage changes

| Stage | Change vs. current code | Notes |
|---|---|---|
| `build-corpus` | Add `--since 2000` (year ≥ 2000); write `corpus.json` + `corpus_2025.json` copy | ~4–6 min runtime |
| `enrich` | Threaded Crossref (8 workers, polite pool); keep cache/resume; progress every 100 | ~10–14 min (was ~9 min for 350) |
| `audit` | No code change (window comes from corpus); add `needs_ocr` column to miss/hit CSVs | ~1–3 min |
| `mine` | Recency filter (D5); embedding miner only over post-2000-relevant misses; candidates capped | ~5–15 min |
| `venue` | Recency filter (D4); two lists: "active — recommend" vs "historical only — do not add" | ~1 min |
| `sections` | Same table, plus **per-era breakdown** (2000–09 / 2010–19 / 2020–26) | ~1–2 min |
| `coverage_check` | Re-pin to new corpus (baseline regeneration); golden set unchanged | ~1–2 min |
| Apply phase | Same review-gate flow: simulation table → approval → apply → check → commit | per Phase 7 of v2 |

## 5. Compute-time estimate (wall clock, one-time)

| Stage | Sequential | Threaded enrichment |
|---|---|---|
| build-corpus | 4–6 min | 4–6 min |
| enrich (≈3,950 API calls) | 50–65 min | **10–14 min** |
| audit | 1–3 min | 1–3 min |
| mine (ngram + embedding over miss set) | 5–15 min | 5–15 min |
| venue + sections | 2–3 min | 2–3 min |
| coverage_check + tests | 2–3 min | 2–3 min |
| **Total** | **~65–95 min** | **~25–40 min** |

Notes: no GPU; the only model load is bge-small-en-v1.5 for the embedding miner (~2–5 min incl. encoding a few hundred miss abstracts). All runs are cached/resumable — a crash costs at most the current stage.

## 6. Token estimate

The scale-up **reuses all existing scripts** — the new code is ~200–300 lines (flags + threading + two recency filters). Token consumption is dominated by interpretation and review, not computation:

| Activity | Tokens (est.) |
|---|---|
| Script edits (`--since`, threading, filters) + debugging | 30–60k |
| Enrichment/audit run output (progress lines + summaries only) | 5–15k |
| Audit interpretation: miss list, venue diff, era tables, candidates | 40–80k |
| Review artifacts (simulation table with rescued papers + years) | 20–40k |
| Apply approved changes + re-check + README/plan sync | 20–40k |
| **Total (one iteration)** | **~120–250k** |

Compare: the original v2 build cost ~350–550k. The scale-up is **~⅓ the token load of the original**, spread over one focused session (~2–3 h including your review gates). In dollars: trivial on DeepSeek (<$1); modest on premium models.

Cost drivers to avoid (as in v2): never dump `corpus.json` (15–20 MB), CSVs, or enrichment JSON into context — only script-filtered summaries.

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Crossref rate limits on 8-threaded ~4,000 calls | Polite pool + mailto; backoff + retry; resumable cache; degrade to 4 threads if 429s |
| Title-search misidentification for pre-2010 papers | difflib ≥0.85 threshold (existing); flag low-score matches for review |
| OCR noise inflates misses | `needs_ocr` flag; mining exclusion option (D7) |
| Dead/renamed venues pollute recommendations | Recency filter (D4); "historical only" list |
| Keyword candidates that only rescue old papers | Recency filter (D5); rescued-paper years shown in review table |
| Yearless/unresolved papers (70) silently dropped | Chunk-year fallback + explicit count in report |
| Public repo grows ~20 MB | Q3 decision (commit vs gitignore the big JSON) |

## 8. Acceptance criteria

- [ ] Since-2000 corpus built deterministically: ~3,930–4,000 papers; yearless/unresolved counts reported.
- [ ] Enrichment completes (threaded, cached); coverage of identifiers ≥ 95% of corpus (DOI or title-match or arXiv/bioRxiv).
- [ ] **Venue coverage ≥ 90% on the 2020+ subset** after applying approved venue additions; pre-2020 venue gaps reported but not "fixed" (dead venues listed separately).
- [ ] Keyword candidates: every proposed keyword rescues ≥1 paper from 2020+; ≤1/3 single generic tokens; cap respected.
- [ ] Zero regression: reported-papers golden set (200) fully retained; coverage_check exit 0 on the re-pinned baseline; pytest suite green.
- [ ] Per-era section distribution table in `outputs/coverage-audit.md`.
- [ ] No writes to the PDF source; DB read-only; working tree clean after commit.

## 9. Open questions

1. **Venue recency threshold:** 2020+ (recommended) or 2022+?
2. **Keyword recency threshold:** ≥1 rescued paper from 2020+ (recommended) or 2022+?
3. **Corpus.json (~15–20 MB) in the public repo** — commit (recommended; it's the regression substrate) or `.gitignore` it?
4. **Enrichment threading:** 8 parallel Crossref workers OK (polite pool, ~10–14 min), or stay sequential (~1 h)?
5. **Apply changes in one pass** after your review (recommended), or stop at the audit report and defer edits?

## 10. Command quick-reference

```bash
cd ~/Documents/GitHub/paper-tracking
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_audit.py build-corpus --since 2000
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_audit.py enrich        # threaded
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_audit.py audit mine venue sections precision
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_check.py               # gate before commit
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 -m pytest tests/ -q
```

---

## Execution log (2026-08-02)

| Item | Planned (estimate) | Actual |
|---|---|---|
| Corpus | ~3,930–4,000 | **3,950** (chunk-year fallback recovered 20 yearless; 9 unresolved titles flagged) |
| Enrichment | ~3,950 API calls; 10–14 min threaded | **3,890 calls** (1,262 DOI + 2,296 title + 150 arXiv + 182 bioRxiv); **~20 min** incl. one crashed resume (tuple-key bug fixed; cache resume worked) |
| Audit | venue coverage ≥90% (2020+) | **93.9%** (n=1,371); overall 92.3%; keyword recall 99.6% |
| Mining | recency-filtered candidates | 18 misses (mostly off-domain: HDAC6, cardiology, CV methods); recency filter killed all legacy-only vocabulary; **+3 keywords applied** to Section C (`language models`, `in-context learning`, `embeddings`) |
| Venue | recency-filtered adds | **+33 journals** (66→102; Frontiers family ×8, Neural Networks 17, PLoS ONE 22 merged, Phil Trans B 12, Psychological Bulletin 7…); **+10 direct-scan** (16→26; Scientific Reports 34, Nature 23, Cerebral Cortex 17…); NeurIPS/EMNLP/LNCS added to the conference gate (17+9+12 papers reclassified) |
| Calibration | unchanged | **88.0% → 91.5%** (first time ≥90%; the 3 C keywords caught 7 more reported papers) |
| Regression | zero | coverage_check exit 0 (0 lost hits, 0 new golden-fails); 14 pytest tests pass |
| Wall clock | 25–40 min | ~35 min (enrichment ~20, corpus 5, rest ~10) |
| Tokens | 120–250k | ~60–90k (leaner than estimated — script reuse dominated) |
| Git | ~20 MB corpus | committed (corpus.json 25 MB + enrichment cache ~5 MB); repo healthy |
