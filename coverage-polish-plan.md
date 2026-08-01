# Paper Tracker Coverage Polish — Implementation Plan (v2)

> **Status:** Draft v2 for review · **Owner:** Qihong Lu · **Date:** 2026-08-01
> **Repo:** `~/Documents/GitHub/paper-tracking` (github.com/qihongl/paper-tracking)
> **Companion assets:** local paper database (4,269 PDFs, 769,162 indexed chunks, read-only) — see `paper-db-search` skill for access details.

## Changelog v1 → v2

| # | Change | Why |
|---|---|---|
| 1 | **Two-layer audit** (venue × keyword) instead of keyword-only hit/miss | A paper in an unscanned venue is missed *before* keywords matter; v1 couldn't tell failure modes apart |
| 2 | **Venue enrichment default-ON** (Crossref batch, arXiv category API, bioRxiv section API) | Exact journal names + categories enable the venue layer; ~15–20 min one-time, free APIs |
| 3 | **Embedding-assisted miss mining** (hybrid with ngram mining) | Ngrams can't discover synonyms ("reminiscence bump" vs. "autobiographical memory"); bge-small-en-v1.5 is already in the stack |
| 4 | **Edit simulation with paper-level preview** | Review rescued *papers* (title + abstract snippet), not abstract keywords — faster, higher-quality gate |
| 5 | **Regression harness → proper pytest suite** + golden sets | New code deserves tests; golden sets guard against keyword drift in both directions |
| 6 | **Precision sampling** (keep/drop rating of reported papers) | "High quality" needs a precision number, not just recall |
| 7 | **Run-health diagnostic** (report-gap analysis) | The 2026-07-23 cluster of 5 "no new papers" commits hints at silent failure — reliability issues masquerade as coverage issues |
| 8 | **Phase 8 (optional): library-anchored daily filter** | Ground the daily agent's relevance judgment in the actual library via local `paper_search.py` — the single biggest quality lever, but changes daily behavior |
| 9 | Tiered venue recommendations (add-to-list / promote-to-direct-scan / adjust arXiv categories) | The 47-journal list contains non-direct-scanned venues that may deserve TOC scans |

---

## 1. Goal

**Use the local paper database (4,269 PDFs the researcher actually collects/reads) as the ground-truth signal to measurably improve the daily paper tracker's quality — both recall (coverage: does it find the papers it should?) and precision (does what it reports get read?).**

Deliverables:
1. **Two-layer recall audit** — for each paper in a fair corpus: would the tracker *look at its venue*, and would its *keywords catch its title/abstract*? Failure modes classified separately.
2. **Miss mining** — hybrid ngram + embedding-derived keyword proposals, each backed by the concrete papers it would rescue.
3. **Venue calibration** — exact-journal diff (Crossref), arXiv category gaps, bioRxiv section gaps, with tiered recommendations.
4. **Section rebalancing** — library topic distribution vs. current A–G allocation, informed by embedding-based section assignment.
5. **Regression test suite + run-health diagnostics** — quality is enforced, not hoped for.
6. **Precision estimate** — keep/drop rating on a sample of reported papers.
7. *(Optional, Phase 8)* **Library-anchored relevance filter** in the daily prompt.

## 2. Context: how the tracker works today

| Component | Current state |
|---|---|
| Skill prompt | `prompts/daily-paper-tracker.md` (356 lines) — the *entire* agent logic: sources, 7-section keyword matrix (390 keywords: A=134, B=58, C=47, D=63, E=43, F=17, G=28), dedup rules, HTML template, push steps |
| Dedup store | `data/seen_papers.json` — 179 entries (DOI / arXiv ID / title-slug → first-seen date) |
| Reports | 20 daily reports, 216 papers total (2026-07-04 → 2026-07-31), ~5–15/run |
| Sources | arXiv (cs.CL, cs.AI, cs.LG, q-bio.NC, stat.ML), bioRxiv (neuroscience), PsyArXiv, PubMed, 47 journals (10 direct-scanned), NeurIPS/ICLR/ICML/COSYNE, naturalistic datasets |
| Deployment | git push → GitHub Pages: qihongl.github.io/paper-tracking |
| Social analysis | `scripts/parse_x_archive.py`, `scripts/social_unify.py` → `outputs/keyword-suggestions.md`, `category-breakdown.md` (skew: A=285 posts, B=6, C=7) |
| ⚠ Reliability signal | 2026-07-23: five commits "Run #21–25 — no new papers" in one day — possible silent failure to investigate |

## 3. Key design decisions

**D1 — Fair audit window.** Tracker only reports last-7-days papers. Filename years: 2026=124, 2025=237, 2024=265. **Default corpus: 2025–2026 (361 papers)**; sensitivity: 2024–2026; all-years diagnostic-only.

**D2 — Two-layer pipeline model (v2).** Each corpus paper gets classified on two independent gates:
- **Venue gate:** is the paper's home (journal / arXiv category / bioRxiv section) one the tracker actually scans? (Crossref batch lookup for exact journal; arXiv API `id_list` batch for categories; bioRxiv API by DOI for sections.)
- **Keyword gate:** does any matrix keyword appear in title + abstract window?
- Outcome: `caught` / `venue-gap` / `keyword-gap` / `both-gap`. This makes recommendations surgical: venue-gaps → source-list edits; keyword-gaps → matrix edits; both-gaps → both.
- Known bias: web search can still surface papers outside listed venues (citation graphs, author pages), so a venue-gap is *high-probability miss*, not certain — stated honestly in reports.

**D3 — Corpus source of truth = chunk store, not filenames.** Only 883/4,269 filenames match the clean pattern; 3,386 are messy. Pipeline: filename parse → fallback to first-chunk text → `unresolved` bucket (target <2%). DOI hints + arXiv IDs extracted from chunk text (needed for D2).

**D4 — Hybrid miss mining (v2).** Two complementary miners:
- **Ngram miner** (v1): unigram/bigram/trigram frequency on miss set + specificity filters → explainable, precise.
- **Embedding miner (new):** embed each section's keyword list as a centroid (bge-small-en-v1.5, already in the DB stack); embed missed-paper abstracts; nearest-section + similarity score → catches *synonymy* and improves section assignment. tf-idf terms of the semantic miss-cluster become synonym keyword candidates.
- Union feeds the simulation (D5). Filters: freq ≥2 (ngram), specificity ≤60% corpus, multi-word preferred, cap +30–50 keywords/iteration.

**D5 — Edit simulation before any edit (v2).** Proposed keyword set is applied **in memory** to the corpus; output = list of rescued papers (title + abstract snippet) per proposed keyword. **Qihong reviews papers, not keywords.** Approve/drop per keyword based on the papers it rescues. Only after approval does Phase 7 touch the prompt.

**D6 — Precision measured, not assumed (v2).** Sample ~25 papers from the 216 reported (stratified by tag); agent pre-rates keep/drop per the editor standard (with 1-line rationale); Qihong confirms (~15–20 min his time). Produces a precision estimate and filter-calibration notes. The simulation previews double as a precision check on proposals.

**D7 — Precision budget.** Same as v1 (multi-word preferred, freq/specificity gates, human review) — flooding the matrix remains the top quality risk.

## 4. Approach overview

```
ChromaDB (read-only) ──► corpus.json (titles, abstracts, year, DOI/arXiv hints)
        │                                  │
        ▼                                  ▼
venue enrichment (Crossref/arXiv/bioRxiv)  keyword parser (from prompt, asserts 390)
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
              coverage_audit.py ──► 2-layer classification (caught/venue-gap/keyword-gap/both)
                       │                 │
                       │                 ├──► ngram miner + embedding miner ──► candidate keywords
                       │                 │                                        │
                       │                 └──► venue diff, section distribution     ▼
                       │                                            in-memory edit simulation
                       ▼                                                   │
              outputs/coverage-audit.md  ◄──────────────── rescued-paper preview table
                       │
                       ▼
        Qihong review (papers, not keywords) ──► apply to prompt
                       │
                       ▼
        coverage_check.py + pytest suite (regression vs. baseline)
```

## 5. New files

| File | Purpose |
|---|---|
| `scripts/paperdb.py` | Shared read-only DB access: enumerate papers, ordered chunks, metadata extraction (year, title, abstract window, DOI/arXiv hints) |
| `scripts/coverage_audit.py` | Two-layer audit, hybrid mining, simulation, venue diff, section analysis → `outputs/coverage-audit.md` |
| `scripts/coverage_check.py` | Fast regression CLI: current matrix vs. pinned baseline; exit 0/1 |
| `scripts/coverage_lib.py` | Pure functions (matrix parsing, matching, mining) — testable, shared by audit/check |
| `tests/test_matrix_parser.py`, `tests/test_matching.py`, `tests/test_mining.py` | pytest suite |
| `data/audit/corpus.json` | Pinned corpus snapshot (deterministic) |
| `data/audit/audit_baseline.json` | Baseline: matrix hash + per-paper two-layer results |
| `data/audit/venue_enrichment.json`, `data/audit/arxiv_categories.json` | Enrichment results (cached — APIs hit once) |
| `data/audit/missed_papers.csv`, `hit_papers.csv` | Per-paper detail |
| `data/audit/precision_sample.json` | Rated keep/drop sample |
| `outputs/coverage-audit.md`, `outputs/run-health.md` | Human-readable reports |

(Decision Q3: commit artifacts to public repo or `.gitignore`.)

---

## 6. Phase 0 — Tooling & smoke test

**Objective:** read-only DB module verified against clean and messy filenames.

1. `scripts/paperdb.py`: `list_papers()`, `get_chunks(filepath)`, `extract_metadata(...)` (year, title via filename→chunk fallback, 3,000-char abstract window, DOI/arXiv regex hints from first chunks).
2. Smoke test (always `env -u PYTHONPATH`; use `/Users/qlu/miniforge3/bin/python3`; DB opened `mode=ro`):

```bash
cd ~/Documents/GitHub/paper-tracking
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 -c "
import sys; sys.path.insert(0, 'scripts')
from paperdb import list_papers, get_chunks
papers = list_papers(); print('papers:', len(papers))
print(get_chunks(papers[0])[0][:200])"
```

3. Verify on two known samples (clean: `Rothschild et al. 2017 - ...`; messy: `(13) (PDF) Visual Working Memory...`) — title extraction must succeed on both.
4. Commit: `feat: read-only paperdb access module`.

## 7. Phase 1 — Corpus construction

**Objective:** validated, deterministic `data/audit/corpus.json`.

1. Flags: `--corpus-window 2025-2026` (default) / `2024-2026` / `all`.
2. Year via regex on filename (flag two-year filenames); exclude yearless from windowed runs.
3. Title extraction: filename parse → chunk-text fallback (first line ≥30 chars) → `unresolved` bucket.
4. Abstract window: first 3,000 chars of ordered concatenated chunks; store normalized + raw.
5. Hints: DOI regex `10.\d{4,9}/[-._;()/:A-Z0-9]+` and arXiv `arXiv:XXXX.XXXXX` from first 2 chunks.
6. **Validation:** stats (per-year, title-source split, unresolved count), eyeball 10 entries, assert non-empty titles. Commit.

## 8. Phase 2 — Two-layer recall audit

**Objective:** classify every corpus paper `caught / venue-gap / keyword-gap / both-gap`.

1. Keyword parser (in `coverage_lib.py`): extract 7 sections from prompt; assert totals (390 = A134+B58+C47+D63+E43+F17+G28).
2. **Venue enrichment (default ON):**
   - Crossref batch: DOI → journal name for all corpus DOIs (~361 requests, polite pool with `mailto`, ~10 min, cached to `venue_enrichment.json`).
   - arXiv API `id_list` batches (≤100 IDs/request): category per arXiv paper → covered set? (cs.CL, cs.AI, cs.LG, q-bio.NC, stat.ML)
   - bioRxiv API by DOI: section per bioRxiv paper → "neuroscience"?
   - PsyArXiv DOIs (10.31234) → covered by default.
3. Keyword gate: normalized substring match on title+abstract window; record catching section(s).
4. Outputs: 4-way classification table; recall by gate; recall by section; recall by year. `missed_papers.csv` / `hit_papers.csv` with gap type.
5. **Proxy calibration:** parse titles from the 20 existing HTML reports (the 216 reported papers) → keyword-gate catch rate should be ≥90% (they were found via search). If much lower, recalibrate the proxy before trusting misses. Also note any reported paper that fails the *venue* gate (evidence search exceeds listed venues — expected, quantify it).
6. Write `outputs/coverage-audit.md` §2 + snapshot `audit_baseline.json`. Commit.

## 9. Phase 3 — Hybrid miss mining + edit simulation

**Objective:** keyword proposals backed by the papers they rescue.

1. **Ngram miner:** unigrams/bigrams/trigrams on miss set (stopwords from `social_unify.py`); filters: freq ≥2, specificity ≤60% of corpus, not already in matrix, multi-word preferred.
2. **Embedding miner (v2):** bge-small-en-v1.5 (reuse the DB stack's model): section centroids from each section's keyword list; missed abstracts → nearest section + cosine; tf-idf terms of each semantic miss-cluster → synonym candidates ("reminiscence bump" → autobiographical memory, etc.). Also upgrades section assignment for all proposals.
3. **Merge + dedupe** candidates; cap +30–50; assign sections (embedding assignment + ngram co-occurrence vote).
4. **In-memory simulation:** apply candidate set to the matrix, recompute keyword-gate → **rescued-paper list per keyword** (title + ~20-word abstract snippet, max 3 papers each). Also compute projected per-section recall gain, and flag any proposed keyword whose rescued papers look off-topic (precision warning).
5. Output `outputs/coverage-audit.md` §3: **review table = keyword | section | specificity | rescued papers (clickable) | precision warning**. This is the artifact Qihong reviews — papers, not keywords.
6. Commit (candidates + simulation, no prompt change yet).

## 10. Phase 4 — Venue calibration (tiered)

**Objective:** source-list edits from the venue-gap analysis.

1. From Phase 2 enrichment: group venue-gap papers by journal/category/section.
2. Three-tier recommendations:
   - **Add to source list:** journals present in library, absent from the 47.
   - **Promote to direct-scan:** library-heavy journals currently in the 47 but *not* in the 10 direct-scanned (e.g., Hippocampus, Learning & Memory, J Neurosci, NeuroImage if they show up strongly) — TOC scans beat search for coverage.
   - **Extend arXiv categories:** if ≥5 arXiv-gap papers cluster in one uncovered category (e.g., cs.NE, q-bio.QM), add it.
3. Output `outputs/coverage-audit.md` §4 with the diff tables. No prompt edits yet — merged into Phase 7 approval.

## 11. Phase 5 — Section rebalancing + precision sampling

**Objective:** realign A–G with the library; get a precision number.

1. Section distribution of the *library* (embedding-assigned) vs. social-posts distribution (A=285, D=34, E=31, F=12, C=7, B=6) vs. current keyword counts. If miss clusters form a coherent topic with no home → new-section proposal with projected gains per option.
2. **Precision sampling (v2, ~15–20 min Qihong time):** sample ~25 of the 216 reported papers (stratified by tag); agent pre-rates keep/drop per editor standard with rationale; Qihong confirms → precision estimate + filter-calibration notes (e.g., "Peripheral tag has 60% drop-rate → tighten criterion").
3. Output `outputs/coverage-audit.md` §5 + `precision_sample.json`.

## 12. Phase 6 — Regression suite + run-health

**Objective:** quality enforced by tests; reliability diagnosed.

1. `coverage_lib.py` pure functions + pytest:
   - `test_matrix_parser.py`: totals, section counts, format drift.
   - `test_matching.py`: normalization, multi-word phrases, edge cases (hyphens, unicode).
   - `test_mining.py`: filters (freq, specificity), embedding-assignment determinism.
2. Golden sets in `coverage_check.py`:
   - Pinned corpus (baseline per-paper results).
   - **The 216 reported papers** (new golden set — any matrix edit that would have "un-found" a paper the tracker actually reported fails the check).
3. `coverage_check.py` CLI: exit 0 (no regression + recall ≥ baseline) / exit 1 (diff report). Documented as **required pre-commit step** for matrix edits.
4. **Run-health diagnostic** (`outputs/run-health.md`): git-log report dates vs. seen_papers first-seen dates → gap days; investigate the 2026-07-23 five-commit "no new papers" cluster (dedup-store corruption? failed searches? repeated empty runs?) — fix recommendation (e.g., a last-run marker file + a "0 papers found" guard in the prompt).
5. Commit.

## 13. Phase 7 — Apply & validate

1. Apply Qihong-approved changes to `prompts/daily-paper-tracker.md`: approved keywords, source-list tiers, section reweights, (if approved) new section.
2. Run `coverage_check.py` → zero regression on both golden sets + recall gain ≥ target.
3. Run pytest suite → all green.
4. Sync `README.md` (journal count, keyword count).
5. Commit + push. Optional: seed `seen_papers.json` with owned papers (Q3).

## 14. Phase 8 — (OPTIONAL) Library-anchored daily filter

**Objective:** the daily agent's relevance judgment gets grounded in the library.

1. Add a step to `prompts/daily-paper-tracker.md`: for each borderline candidate, run the local `paper_search.py "TITLE ABSTRACT"` query; if top-3 cosine similarity ≥ threshold, add a `📚 matches-library` badge + include; borderline-with-low-similarity → excluded with note.
2. Threshold calibration from Phase 5 precision sample (what do library-similar papers look like vs. drop-rated ones?).
3. Report template: optional `library-affinity` column.
4. **Dependency to confirm:** the daily harness must be able to execute local Python on this machine (README already requires code execution; `paper_search.py` must be reachable). Zero API cost (local model), ~2–5 s per candidate.
5. Acceptance: run 7 days; report quality (Qihong daily read) maintained or improved; precision ≥ baseline; no run-time failures.

## 15. Acceptance criteria

- [ ] Two-layer recall on 2025–2026 corpus: keyword-gate recall improves **≥10 pp**; after Phase 4 source edits, **≥90% of corpus papers pass the venue gate**.
- [ ] **Zero regression** on both golden sets (corpus baseline + the 216 reported papers).
- [ ] Precision estimate reported (target: ≥60% keep-rate; final target set after baseline measurement); filter-calibration notes applied where flagged.
- [ ] pytest suite green; `coverage_check.py` exit-0 on approved edit.
- [ ] Run-health report produced; the 07-23 anomaly explained with a fix applied if warranted.
- [ ] Determinism: same window → identical output. No writes to PDF source; DB read-only throughout.
- [ ] ≤1/3 of added keywords are single generic tokens; every added keyword backed by ≥1 rescued paper in the review table.
- [ ] (Phase 8, if opted) 7-day trial clean, precision ≥ baseline.

## 16. Risks & tradeoffs

| Risk | Mitigation |
|---|---|
| Keyword gate is a lower-bound proxy for search | Calibration vs. the 216 reported papers (§8.5); stated bias in every report |
| Date-filter bias | Fair window (D1) + sensitivity runs |
| Messy filenames → title errors | Chunk fallback + validation + unresolved bucket |
| Precision/recall tension | Specificity filters, multi-word preference, cap, paper-level review gate (D4/D5/D7) |
| Enrichment API flakiness (Crossref/arXiv/bioRxiv) | Cached artifacts; retries; skip-and-report degraded mode (venue layer marked partial) |
| Embedding miner proposes synonyms that are too broad | Specificity gate applies to embedding candidates too; precision warnings in review table |
| Phase 8 changes daily behavior | Optional, opt-in, 7-day trial with explicit rollback |
| Audit artifacts bloat public repo | Q3 decision (.gitignore vs commit) |

## 17. Open questions (before execution)

1. **Scope package** — core v2 (Phases 0–7) vs. full v2 including Phase 8 (library-anchored daily filter)? Phase 8 is the biggest quality lever but changes daily behavior and needs the daily harness to run local Python.
2. **Corpus window:** 2025–2026 (361, default) or 2024–2026 (626)?
3. **Seed `seen_papers.json`** with owned papers so the tracker never re-recommends library papers?
4. **Audit artifacts in public repo** (default commit) or `.gitignore`?
5. **Precision sampling:** OK to take ~15–20 min of Qihong time to rate 25 papers?
6. **Enrichment default-ON** (Crossref/arXiv/bioRxiv, ~15–20 min one-time, free APIs) — OK?

## 18. Command quick-reference

```bash
cd ~/Documents/GitHub/paper-tracking
# Audit (Phases 1–5)
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_audit.py --corpus-window 2025-2026
# Regression (after any matrix edit)
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_check.py
# Tests
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 -m pytest tests/ -q
# Enrichment (cached; re-runs are no-ops)
env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_audit.py --enrich-only
```

**Runtime:** audit <2 min (embedding mining adds ~5–6 min); enrichment one-time ~15–20 min (network); tests <10 s. No GPU, no model-loading beyond bge-small (already used by the DB pipeline).

**Environment:** always `env -u PYTHONPATH` (Hermes terminal pollutes it, breaking miniforge numpy); `/Users/qlu/miniforge3/bin/python3`; DB via `file:...?mode=ro`; PDF source untouched.

---

## Execution log (2026-08-01)

| Phase | Status | Result |
|---|---|---|
| 0 — paperdb.py | ✅ | Read-only DB module; smoke-tested on clean + messy filenames |
| 1 — Corpus | ✅ | 362 papers (2025–2026), 0 unresolved titles, deterministic |
| 2 — Two-layer audit | ✅ | Keyword recall 99.7%; venue coverage 79.6% → **96.7%** after Phase 7 edits; calibration 88% (title+finding) |
| 3 — Mining | ✅ (adapted) | Keyword layer saturated (1 out-of-domain miss, HDAC6 bio paper) → mining correctly short-circuits; bottleneck is venues, not words |
| 4 — Venue | ✅ | 19 journals added (47→66), 6 promoted to direct-scan (10→16), ACL/EMNLP/NAACL/CVPR/ICCV added; PNAS alias + `&amp;` unescape fixes |
| 5 — Sections + precision | ✅ | A 98%, G 66%, B 61%, E 39%, D 30%, C 2%, F 0% coverage; precision **84% keep** (21/25, agent pre-rating) |
| 6 — Regression suite | ✅ | 14 pytest tests; `coverage_check.py` exit 0 (zero regression, golden set stateful); run-health report clean (07-23 cluster = retries, not corruption) |
| 7 — Apply & validate | ✅ | Prompt edited (journals, direct-scan, conferences, precision filter, run guard); README synced; committed + pushed |
| 8 — Library-anchored filter | ✅ (deployed) | Daily prompt now queries `paper_search.py` for borderline candidates + `📚 matches-library` badge; 7-day trial starts with next daily run |
