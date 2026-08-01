#!/usr/bin/env python3
"""Regression check for the daily paper tracker's keyword matrix.

Compares the CURRENT keyword matrix (parsed live from prompts/daily-paper-tracker.md)
against the pinned baseline (data/audit/audit_baseline.json) on the pinned corpus
(data/audit/corpus.json). Also verifies the golden set of actually-reported papers
stays keyword-caught.

Exit codes:
    0  no regression (all baseline keyword hits still hit; recall >= baseline)
    1  regression detected (details printed)

Usage:
    env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/coverage_check.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as ca
import coverage_lib as cl

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(REPO, "data", "audit")


def main():
    with open(os.path.join(AUDIT_DIR, "corpus.json"), encoding="utf-8") as f:
        corpus = json.load(f)
    with open(os.path.join(AUDIT_DIR, "audit_baseline.json"), encoding="utf-8") as f:
        baseline = json.load(f)
    prompt = cl.read_prompt(os.path.join(REPO, cl.PROMPT_PATH))
    sections, order = cl.parse_keyword_matrix(prompt)
    counts, total = cl.matrix_totals(sections)
    assert total == cl.EXPECTED_TOTAL, f"matrix total {total} != {cl.EXPECTED_TOTAL}"
    for s, exp in cl.EXPECTED_SECTION_COUNTS.items():
        assert counts[s] == exp, f"section {s}: {counts[s]} != {exp}"
    sources = cl.parse_sources(prompt)

    kw_norm = {s: [cl.normalize(k) for k in v["keywords"]] for s, v in sections.items()}
    problems = []

    # 1) keyword-gate recomputation on pinned corpus
    now_hits = set()
    for p in corpus["papers"]:
        blob = f"{p['title_norm']} {p['abstract_norm']}"
        if any(k in blob for kws in kw_norm.values() for k in kws):
            now_hits.add(p["id"])

    base_hits = {i for i, r in baseline["outcomes"].items() if r["o"] in ("caught", "venue-gap")}
    lost = sorted(base_hits - now_hits)
    n = len(corpus["papers"])
    recall_now = len(now_hits) / n
    recall_base = baseline["keyword_recall"]

    print(f"matrix hash: current={cl.matrix_hash(sections)} baseline={baseline['matrix_hash']}")
    print(f"keyword-gate recall: baseline {recall_base:.1%} -> now {recall_now:.1%} "
          f"({(recall_now - recall_base):+.1%})")
    print(f"baseline hits: {len(base_hits)} | current hits: {len(now_hits)} | lost: {len(lost)}")

    # 2) golden set: reported papers must stay keyword-caught
    reported = cl.parse_reported_papers(os.path.join(REPO, "outputs"))
    not_caught = []
    for t in reported:
        tn = cl.normalize(t)
        if not any(k in tn for kws in kw_norm.values() for k in kws):
            not_caught.append(t)
    print(f"reported golden set: {len(reported) - len(not_caught)}/{len(reported)} keyword-caught")

    # 3) venue gate on pinned corpus (uses current sources + cached enrichment)
    enrich_data = ca.load_enrich()
    venue_gaps = sum(1 for p in corpus["papers"] if not ca.classify_venue(p, enrich_data, sources)[0])
    venue_base = baseline.get("venue_gaps")
    print(f"venue-gate gaps: {venue_gaps}" + (f" (baseline {venue_base})" if venue_base is not None else ""))

    if lost:
        problems.append(f"{len(lost)} baseline keyword hits lost")
        for i in lost[:10]:
            p = next(p for p in corpus["papers"] if p["id"] == i)
            print(f"  LOST: [{i}] {p['title'][:80]}")
    if recall_now < recall_base - 1e-9:
        problems.append(f"recall regressed: {recall_base:.1%} -> {recall_now:.1%}")
    if not_caught:
        problems.append(f"{len(not_caught)} reported papers not keyword-caught")
        for t in not_caught[:5]:
            print(f"  GOLDEN-FAIL: {t[:90]}")

    # refresh baseline snapshot (keeps venue_gaps field for future diffs)
    baseline["matrix_hash"] = cl.matrix_hash(sections)
    baseline["keyword_recall"] = recall_now
    baseline["venue_gaps"] = venue_gaps
    baseline["checked_at"] = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
    with open(os.path.join(AUDIT_DIR, "audit_baseline.json"), "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=1)

    if problems:
        print("\nREGRESSION:", "; ".join(problems))
        sys.exit(1)
    print("\nOK: no regression.")


if __name__ == "__main__":
    main()
