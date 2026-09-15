#!/usr/bin/env python3
"""Score harvested candidates for relevance; emit ranked shortlist after dedup."""
import json
import re
import sys

CAND = sys.argv[1]
SEEN = sys.argv[2]
OUT = sys.argv[3]
TOPN = int(sys.argv[4]) if len(sys.argv) > 4 else 60

# ---- weighted keyword groups -------------------------------------------------
# Core pillar terms (high weight) — these are what the researcher actually works on
CORE = {
    # Pillar 1: LLM memory / transformers
    "kv cache": 6, "kv-cache": 6, "key-value cache": 6, "kv eviction": 8, "kv retention": 8,
    "in-context learning": 7, "in context learning": 7, "induction head": 8,
    "attention sink": 6, "long-context": 6, "long context": 6, "context window": 5,
    "transformer memory": 8, "associative memory": 7, "memory augmentation": 7,
    "episodic memory in language model": 12, "continual learning": 5, "catastrophic forgetting": 6,
    "memory-augmented": 7, "external memory": 6, "hopfield": 6, "memory network": 7,
    # Pillar 2: schema / episodic / hippocampal
    "episodic memory": 9, "episodic": 5, "hippocamp": 8, "entorhinal": 6,
    "sharp-wave ripple": 9, "sharp wave ripple": 9, "hippocampal replay": 10, "replay": 7,
    "schema": 8, "schema-guided": 12, "pattern separation": 9, "pattern completion": 9,
    "systems consolidation": 8, "memory consolidation": 8, "place cell": 6, "grid cell": 6,
    "time cell": 6, "cognitive map": 7, "temporal context": 10, "temporal context model": 14,
    "mental time travel": 7, "episodic future thinking": 7, "autobiographical memory": 6,
    "recollection": 5, "source memory": 6, "relational memory": 6,
    # Pillar 3: KV / serial order / temporal context
    "serial recall": 10, "free recall": 9, "serial position": 10, "primacy": 6, "recency": 6,
    "contiguity": 6, "lag effect": 7, "spacing effect": 7, "testing effect": 6,
    "key-value": 5, "successor representation": 7, "complementary learning systems": 8,
    "context maintenance and retrieval": 12, "cmr model": 10, "retrieving effectively from memory": 12,
    "global matching": 7, "attractor network": 6, "positional encoding": 4,
    # Encoding / retrieval
    "encoding-retrieval": 8, "encoding specificity": 8, "reinstatement": 8,
    "retrieval practice": 7, "subsequent memory": 8, "pattern reinstatement": 9,
    "retrieval mode": 6, "reactivation": 6, "targeted memory reactivation": 8,
    "working memory": 5, "event segmentation": 7, "event boundary": 7, "event model": 6,
    # Naturalistic
    "naturalistic": 8, "inter-subject correlation": 9, "intersubject": 9,
    "shared response model": 9, "movie viewing": 7, "story listening": 7, "audiobook": 7,
    "sherlock": 8, "pieman": 10, "ds005658": 12, "openneuro": 4,
    "narrative comprehension": 7, "movie-watching": 7, "film viewing": 7,
    "neural alignment": 6, "representational similarity": 5,
    # Computational
    "recurrent neural network": 4, "rnn": 3, "computational model": 4,
    "reinforcement learning": 3, "predictive coding": 4, "active inference": 4,
    "neural manifold": 5, "representational drift": 7, "mixed selectivity": 6,
    "population coding": 4, "neural geometry": 6, "sparse autoencoder": 4,
    "mechanistic interpretability": 5,
    # --- Added 2026-09-05 / 09-15: title-phrase gaps that caused confirmed misses ---
    # (MEC strategy learning; human hippocampal abstraction; Bayesian-connectionist;
    #  emergent symbolic structure.) Keep in sync with the prompt's keyword matrix.
    "medial entorhinal cortex": 7, "strategy learning": 6, "strategy switching": 6,
    "neural dynamics": 5, "geometric alignment": 7, "neuronal selectivity": 6,
    "abstract generalization": 8, "human hippocampus": 7, "human hippocampal": 7,
    "connectionist": 5, "bayesian-connectionist": 7, "hybrid model": 5,
    "behavioral prediction": 6, "predicting human behavior": 6, "inductive bias": 5,
    "cognitive modeling": 5, "behavioral modeling": 5,
    "symbolic structure": 7, "symbolic representation": 7, "symbolic reasoning": 6,
    "emergent structure": 6, "compositionality": 7, "systematicity": 7,
    "neurosymbolic": 5, "vector representation": 5,
}

# Terms that attract but are usually engineering-only (penalise unless core memory present)
ENGINEERING = [
    "throughput", "serving", "latency", "tokens per second", "gpu memory", "pagedattention",
    "batching", "offloading", "speculative decoding", "quantization", "distillation serving",
    "inference cost", "memory footprint", "accelerat", "benchmark suite",
]

# Strong "this is a memory-science paper" gate
GATE = [
    "memory", "hippocamp", "replay", "recall", "episodic", "schema", "consolidation",
    "forgetting", "retrieval", "encoding", "kv cache", "in-context", "transformer",
    "attention", "narrative", "event segmentation", "remember", "recognition",
    "context", "working memory", "reactivation", "ripple", "place cell", "grid cell",
    "reinstatement", "serial",
    # Added 2026-09-15: abstraction / symbolic / decision-adjacent work was being
    # gated out of the pool even when the abstract was squarely on-topic.
    "generalization", "abstraction", "compositional", "symbolic", "entorhinal",
    "navigation", "decision-making", "concept learning", "neural network", "language model",
]


def norm(s):
    return (s or "").lower()


def score(p):
    ti = norm(p.get("title", ""))
    ab = norm(p.get("abstract", ""))
    text = ti + " " + ab
    s = 0.0
    hits, title_hits, abs_hits = [], [], []
    for k, w in CORE.items():
        if k in text:
            # title hits count double
            if k in ti:
                s += w * 2
                title_hits.append(k)
            else:
                s += w
                abs_hits.append(k)
            hits.append(k)
    if re.search(r"\bkv\b", text) and "cache" in text:
        s += 5
    for e in ENGINEERING:
        if e in text:
            s -= 2
    # gate: >=2 distinct gate terms, OR strong abstract-level relevance.
    # The rescue exists because abstract-only matches are precisely the papers
    # whose titles are opaque — the failure mode behind the 2026-09 misses.
    ghits = sum(1 for g in GATE if g in text)
    gated = ghits >= 2 or s >= 12
    return s, hits, title_hits, abs_hits, gated, ghits


def slug(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    t = re.sub(r"\s+", "-", t.strip())
    return t[:60]


def ids_of(p):
    out = set()
    if p.get("doi"):
        out.add(p["doi"].lower().strip())
    i = p.get("id", "")
    if i:
        out.add(i.lower().strip())
    out.add(slug(p.get("title", "")))
    return out


def evidence(p, terms, width=200):
    """Abstract snippets around each matched term — the evidence a reviewer needs.

    Abstract-only hits are the cases where the title was uninformative, so showing
    the matched context is what makes the include/exclude call defensible.
    """
    ab = p.get("abstract", "") or ""
    low = norm(ab)
    out, seen = [], []
    for t in terms:
        i = low.find(t)
        if i < 0:
            continue
        lo = max(0, i - width // 2)
        hi = min(len(ab), i + len(t) + width // 2)
        if any(lo < e and s2 < hi for s2, e in seen):
            continue
        seen.append((lo, hi))
        out.append(("\u2026" if lo else "") + ab[lo:hi].strip() + "\u2026")
    return out


def main():
    cands = json.load(open(CAND))
    seen = json.load(open(SEEN))
    seenkeys = set(k.lower().strip() for k in seen.keys())

    rows = []
    ndup = 0
    for p in cands:
        keys = ids_of(p)
        if keys & seenkeys:
            ndup += 1
            continue
        s, hits, title_hits, abs_hits, gated, ghits = score(p)
        if not gated:
            continue
        p["_score"] = round(s, 1)
        p["_hits"] = hits
        p["_title_hits"] = title_hits
        p["_abs_hits"] = abs_hits
        p["_ghits"] = ghits
        rows.append(p)

    # dedup within batch by doi/id/slug
    outrows = []
    used = set()
    for p in sorted(rows, key=lambda x: -x["_score"]):
        keys = ids_of(p)
        if keys & used:
            continue
        used |= keys
        outrows.append(p)

    print(f"candidates={len(cands)} already-seen-removed={ndup} gated={len(rows)} after-internal-dedup={len(outrows)}")
    json.dump(outrows, open(OUT, "w"))
    for p in outrows[:TOPN]:
        print("=" * 100)
        print(f"[{p['_score']}] {p['src']:9s} | {p.get('date','')} | {p.get('venue','')[:45]}")
        print(f"T: {p.get('title','')}")
        print(f"A: {', '.join(p.get('authors',[])[:3])}{' et al.' if len(p.get('authors',[]))>3 else ''}")
        th = sorted(set(p.get("_title_hits", [])))
        ah = sorted(set(p.get("_abs_hits", [])))
        print(f"TITLE-HITS:    {', '.join(th[:18]) or '(none)'}")
        print(f"ABS-ONLY-HITS: {', '.join(ah[:18]) or '(none)'}"
              + ("   <-- abstract-only: review, do not auto-drop" if ah and not th else ""))
        for sn in evidence(p, ah[:3] or th[:2]):
            print(f"  ~ {sn}")
        print(f"ABS: {(p.get('abstract','') or '')[:700]}")
        print(f"URL: {p.get('url') or p.get('doi') or p.get('id')}")


if __name__ == "__main__":
    main()
