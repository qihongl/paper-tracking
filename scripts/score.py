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
]


def norm(s):
    return (s or "").lower()


def score(p):
    text = norm(p.get("title", "")) + " " + norm(p.get("abstract", ""))
    ti = norm(p.get("title", ""))
    s = 0.0
    hits = []
    for k, w in CORE.items():
        if k in text:
            # title hits count double
            mult = 2 if k in ti else 1
            s += w * mult
            hits.append(k)
    if re.search(r"\bkv\b", text) and "cache" in text:
        s += 5
    for e in ENGINEERING:
        if e in text:
            s -= 2
    # gate: must contain at least 2 distinct gate terms
    ghits = sum(1 for g in GATE if g in text)
    gated = ghits >= 2
    return s, hits, gated, ghits


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
        s, hits, gated, ghits = score(p)
        if not gated:
            continue
        p["_score"] = round(s, 1)
        p["_hits"] = hits
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
        print(f"HITS: {', '.join(sorted(set(p['_hits']))[:18])}")
        print(f"ABS: {(p.get('abstract','') or '')[:700]}")
        print(f"URL: {p.get('url') or p.get('doi') or p.get('id')}")


if __name__ == "__main__":
    main()
