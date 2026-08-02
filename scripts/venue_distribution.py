#!/usr/bin/env python3
"""Venue distribution for the since-2000 corpus — scope/cost decision support.

For every corpus paper, resolve its publication venue (Crossref journal, arXiv
category, bioRxiv section, or unknown) and classify coverage status against the
current prompt source list. Produces:

  outputs/venue-distribution.png    two-panel figure (top venues + cumulative curve)
  outputs/venue-distribution.csv    full per-venue table

Run:  env -u PYTHONPATH /Users/qlu/miniforge3/bin/python3 scripts/venue_distribution.py
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverage_audit as ca
import coverage_lib as cl

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(REPO, "data", "audit")
OUT_PNG = os.path.join(REPO, "outputs", "venue-distribution.png")
OUT_CSV = os.path.join(REPO, "outputs", "venue-distribution.csv")
RECENT = 2020


def resolve_venue(p, enrich, sources):
    """Return (group_key, display_name, status, covered)."""
    dois = p["doi_hints"]
    if not dois and p.get("first_doi"):
        dois = [p["first_doi"]]
    if dois:
        doi = dois[0]
        if doi.startswith(("10.1101", "10.64898")):
            sec = enrich["biorxiv"].get(doi)
            s = sec if isinstance(sec, str) else "section unknown"
            covered = isinstance(sec, str) and sec.lower() in sources["biorxiv_sections"]
            label = "bioRxiv" if s == "neuroscience" else "bioRxiv/medRxiv"
            return label, f"{label} ({s})", "biorxiv-covered" if covered else "biorxiv-gap", covered
        if doi.startswith("10.31234"):
            return "PsyArXiv", "PsyArXiv", "listed", True
        j = enrich["crossref"].get(doi, {}).get("journal")
        if j:
            norm = ca.norm_journal(j)
            jset = {ca.norm_journal(x) for x in sources["journals"]}
            dset = {ca.norm_journal(x) for x in sources["direct_scan"]}
            if norm in dset:
                return norm, j, "direct-scan", True
            if norm in jset:
                return norm, j, "listed", True
            for hint in ca.CONFERENCE_HINTS:
                if hint in norm:
                    return norm, j, "conference", True
            return norm, j, "not-listed", False
    arx = p.get("arxiv_ids") or ([p["first_arxiv"]] if p.get("first_arxiv") else [])
    if arx:
        cats = [ca.arxiv_lookup(enrich["arxiv"], a) for a in arx]
        cats = [c for c in cats if c]
        cat = cats[0] if cats else "unknown"
        covered = cat in sources["arxiv_cats"]
        return "arXiv", f"arXiv ({cat})", "arxiv-covered" if covered else "arxiv-gap", covered
    if not dois:
        ts = enrich.get("crossref_title", {}).get(p["id"], {})
        j = ts.get("journal")
        if not j:
            return "Unknown", "Unknown / no identifier", "unknown", True
        norm = ca.norm_journal(j)
        jset = {ca.norm_journal(x) for x in sources["journals"]}
        dset = {ca.norm_journal(x) for x in sources["direct_scan"]}
        if norm in dset:
            return norm, j, "direct-scan", True
        if norm in jset:
            return norm, j, "listed", True
        for hint in ca.CONFERENCE_HINTS:
            if hint in norm:
                return norm, j, "conference", True
        return norm, j, "not-listed", False
    doi = dois[0]
    if doi.startswith(("10.1101", "10.64898")):
        sec = enrich["biorxiv"].get(doi)
        s = sec if isinstance(sec, str) else "unknown"
        covered = isinstance(sec, str) and sec.lower() in sources["biorxiv_sections"]
        return "bioRxiv", f"bioRxiv ({s})", "biorxiv-covered" if covered else "biorxiv-gap", covered
    if doi.startswith("10.31234"):
        return "PsyArXiv", "PsyArXiv", "listed", True
    j = enrich["crossref"].get(doi, {}).get("journal")
    if not j:
        return "Unknown", f"journal-unknown ({doi[:12]}…)", "unknown", True
    norm = ca.norm_journal(j)
    jset = {ca.norm_journal(x) for x in sources["journals"]}
    dset = {ca.norm_journal(x) for x in sources["direct_scan"]}
    if norm in dset:
        return norm, j, "direct-scan", True
    if norm in jset:
        return norm, j, "listed", True
    for hint in ca.CONFERENCE_HINTS:
        if hint in norm:
            return norm, j, "conference", True
    return norm, j, "not-listed", False


def main():
    corpus = json.load(open(os.path.join(AUDIT, "corpus.json"), encoding="utf-8"))
    enrich = json.load(open(os.path.join(AUDIT, "venue_enrichment.json"), encoding="utf-8"))
    sources = cl.parse_sources(cl.read_prompt(os.path.join(REPO, cl.PROMPT_PATH)))

    # per-venue aggregation (group by family+category so arXiv/bioRxiv rows are homogeneous)
    venues = defaultdict(lambda: {"name": None, "n": 0, "n_recent": 0, "status": None,
                                  "years": [], "covered": None})
    for p in corpus["papers"]:
        key, disp, status, covered = resolve_venue(p, enrich, sources)
        # for arXiv/bioRxiv, the display name (incl. category) is the group key
        if key in ("arXiv", "bioRxiv", "PsyArXiv"):
            key = disp
        v = venues[key]
        v["name"] = disp
        v["n"] += 1
        if p["year"] and int(p["year"]) >= RECENT:
            v["n_recent"] += 1
        if p["year"]:
            v["years"].append(int(p["year"]))
        v["status"] = status
        v["covered"] = covered

    rows = sorted(venues.values(), key=lambda v: -v["n"])
    n_all = len(corpus["papers"])
    n_recent = sum(1 for p in corpus["papers"] if p["year"] and int(p["year"]) >= RECENT)

    # cumulative shares
    cum_all, cum_recent = 0, 0
    for i, v in enumerate(rows, 1):
        v["rank"] = i
        cum_all += v["n"]
        v["cum_all"] = cum_all / n_all
        v["cum_recent"] = None

    # cumulative over 2020+ ordering
    recent_rows = sorted(venues.values(), key=lambda v: -v["n_recent"])
    cum = 0
    for v in recent_rows:
        cum += v["n_recent"]
        v["cum_recent"] = cum / n_recent

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "venue", "status", "n_papers", "n_2020plus", "year_range",
                    "cum_share_all", "cum_share_2020plus"])
        for v in rows:
            w.writerow([v["rank"], v["name"], v["status"], v["n"], v["n_recent"],
                        f"{min(v['years'])}–{max(v['years'])}" if v["years"] else "-",
                        f"{v['cum_all']:.3f}", f"{v['cum_recent']:.3f}" if v["cum_recent"] is not None else "-"])
    print(f"CSV -> {OUT_CSV}")

    # ---- figure ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import numpy as np
    try:
        import seaborn as sns

        sns.set_context("talk")
        sns.set_style("whitegrid")
    except Exception:
        pass

    STATUS_COLOR = {
        "direct-scan": "#2e8b57",   # green — agent reads TOC every run (high cost)
        "listed": "#3b6ea5",        # blue — web-search covered (low cost)
        "conference": "#8d99ae",    # gray — proceedings
        "not-listed": "#e07a3f",    # orange — active-ish gap (decision set)
        "arxiv-covered": "#6a4c93",
        "arxiv-gap": "#d1495b",
        "biorxiv-covered": "#6a4c93",
        "biorxiv-gap": "#d1495b",
        "unknown": "#c9c9c9",
    }
    STATUS_LABEL = {
        "direct-scan": "direct-scan (TOC read)",
        "listed": "listed (web search)",
        "conference": "conference proc.",
        "not-listed": "NOT listed",
        "arxiv-covered": "arXiv (covered)",
        "arxiv-gap": "arXiv (gap)",
        "biorxiv-covered": "bioRxiv (covered)",
        "biorxiv-gap": "bioRxiv (gap)",
        "unknown": "unknown / no ID",
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(19, 9), gridspec_kw={"width_ratios": [1.25, 1]})

    # Panel A: top 35 venues
    top = rows[:35]
    names = [f"{v['name'][:42]}" for v in top][::-1]
    counts = [v["n"] for v in top][::-1]
    colors = [STATUS_COLOR[v["status"]] for v in top][::-1]
    ax1.barh(names, counts, color=colors, edgecolor="white", linewidth=0.5)
    for i, (n, v) in enumerate(zip(counts, top[::-1])):
        ax1.text(n + 0.4, i, str(n), va="center", fontsize=11, color="#333")
    ax1.set_xlabel(f"Papers in library (since 2000, n={n_all})")
    ax1.set_title("Top 35 venues by library weight", fontsize=16)
    handles = []
    for st in ["direct-scan", "listed", "conference", "not-listed", "unknown"]:
        if st in STATUS_COLOR:
            handles.append(Rectangle((0, 0), 1, 1, color=STATUS_COLOR[st], label=STATUS_LABEL[st]))
    ax1.legend(handles=handles, loc="lower right", fontsize=10, framealpha=0.95)

    # Panel B: cumulative coverage curves (all rows vs resolved venues only)
    xs = list(range(1, len(rows) + 1))
    cum_a = [rows[i - 1]["cum_all"] for i in xs]
    resolved = [v for v in rows if v["status"] != "unknown"]
    xs_r = list(range(1, len(resolved) + 1))
    cum_r_all = []
    acc = 0
    for v in resolved:
        acc += v["n"]
        cum_r_all.append(acc / (n_all - sum(v2["n"] for v2 in rows if v2["status"] == "unknown")))
    # 2020+ ordering cumulative
    order_recent = sorted(rows, key=lambda v: -v["n_recent"])
    cum_r = []
    acc = 0
    for v in order_recent:
        acc += v["n_recent"]
        cum_r.append(acc / n_recent)

    n_unknown = sum(v["n"] for v in rows if v["status"] == "unknown")
    resolved_n = n_all - n_unknown
    ax2.plot(xs, np.array(cum_a) * 100, color="#8d99ae", lw=2, ls="--",
             label=f"All rows incl. unresolved (n={n_all})")
    ax2.plot(xs_r, np.array(cum_r_all) * 100, color="#3b6ea5", lw=2.5,
             label=f"Resolved venues only (n={resolved_n})")
    ax2.plot(xs, np.array(cum_r) * 100, color="#e07a3f", lw=2.5,
             label=f"2020+ papers (n={n_recent})")
    ax2.fill_between(xs_r, 0, np.array(cum_r_all) * 100, color="#3b6ea5", alpha=0.12)
    ax2.fill_between(xs, 0, np.array(cum_r) * 100, color="#e07a3f", alpha=0.10)
    for k in (26, 66, 102):
        ax2.axvline(k, color="#555", ls="--", lw=1.2, alpha=0.6)
        ax2.text(k + 0.8, 8, f"K={k}", rotation=90, fontsize=10, color="#555")
    # Pareto annotations on resolved-only curve
    k90 = next(i for i, c in enumerate(cum_r_all) if c >= 0.90)
    k95 = next(i for i, c in enumerate(cum_r_all) if c >= 0.95)
    ax2.annotate(f"top {k90} venues = 90% of resolved", xy=(k90, 90), xytext=(k90 * 0.55, 40),
                 arrowprops=dict(arrowstyle="->", color="#333"), fontsize=11)
    ax2.annotate(f"top {k95} venues = 95%", xy=(k95, 95), xytext=(k95 * 0.5, 70),
                 arrowprops=dict(arrowstyle="->", color="#333"), fontsize=11)
    ax2.set_xlabel("Venues scanned (sorted by library weight)")
    ax2.set_ylabel("Cumulative % of library covered")
    ax2.set_title("Coverage vs. scan cost (Pareto)", fontsize=16)
    ax2.set_ylim(0, 102)
    ax2.legend(loc="lower right", fontsize=10, framealpha=0.95)

    fig.suptitle(f"Publication venue distribution — library since 2000 ({n_all} papers, {len(rows)} venues)",
                 fontsize=17, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    print(f"PNG -> {OUT_PNG}")

    # ---- decision stats ----
    long_tail = [v for v in rows if v["n"] <= 2]
    tail_papers = sum(v["n"] for v in long_tail)
    n_2020gap = sum(1 for v in rows if v["status"] == "not-listed" and v["n_recent"] >= 1)
    print(f"\nvenues total: {len(rows)} | papers: {n_all} (2020+: {n_recent})")
    print(f"top-{k90} venues cover 90% | top-{k95} cover 95% | long tail (n<=2): {len(long_tail)} venues, {tail_papers} papers ({tail_papers/n_all:.1%})")
    print(f"NOT-listed venues with >=1 paper from 2020+: {n_2020gap}")
    print("\ntop 15:")
    for v in rows[:15]:
        print(f"  {v['rank']:3d}. {v['name'][:48]:50s} {v['n']:4d} (2020+: {v['n_recent']:3d}) {v['status']}")


if __name__ == "__main__":
    main()
