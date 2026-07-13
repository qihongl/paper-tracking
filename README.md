# Daily Paper Tracker

Automated daily literature surveillance for computational cognitive neuroscience research on episodic memory. Runs as a WorkBuddy automation, searches multiple sources, filters by relevance, and produces a self-contained HTML briefing.

<p align="center">
  <img src="outputs/bsky-wordcloud.png" alt="Word cloud of paper-sharing topics from @qlu.bsky.social" width="700">
</p>

The tracker's keyword matrix is calibrated against the researcher's actual paper-sharing activity on Bluesky ([@qlu.bsky.social](https://bsky.app/profile/qlu.bsky.social)). The word cloud above — generated from 212 paper-related posts — surfaces the dominant themes: **memory**, **neural** mechanisms, **learning**, the **hippocampus**, **episodic** encoding, **cognitive** models, and **working memory**. These map directly onto the tracker's six relevance categories.

## How It Works

A WorkBuddy automation (`automation-1783133189790`) reads `prompts/daily-paper-tracker.md` and executes it daily. The agent:

1. **Searches** arxiv, bioRxiv, PubMed, and high-impact journals across a 219-keyword matrix spanning six categories.
2. **Deduplicates** against `data/seen_papers.json` — papers are matched by DOI, arxiv ID, or title slug and never reported twice.
3. **Filters** for mechanistic relevance, not just keyword matches. Papers that are purely engineering, clinical case studies without computational relevance, or opinion pieces are excluded.
4. **Generates** a self-contained HTML report at `outputs/YYYY-MM-DD-paper-tracker.html` with papers grouped into six relevance categories, each appearing in exactly one detailed section.
5. **Presents** the HTML via WorkBuddy's `present_files`.

## Keyword Matrix (219 keywords, 6 sections)

| Section | Focus | Example keywords |
|---|---|---|
| A — Episodic Memory | Hippocampus, replay, place/time/grid cells, consolidation, pattern separation, polysemanticity, mixed selectivity | 54 |
| B — Computational Models | TCM, CLS, successor representation, Bayesian efficient coding, planning as inference, simulated experience | 33 |
| C — LLMs & Machine Memory | In-context learning, KV cache, transformer memory, neural modularity, neural geometry, neuroAI alignment | 34 |
| D — Encoding & Retrieval | Reinstatement, oscillations, WM/LTM dissociation, iEEG, schema filling, prior knowledge, individual differences | 33 |
| E — Naturalistic Paradigms | Movie viewing, audiobook listening, conversation, ISC, event segmentation, naturalistic timescales, Sherlock/PIEMAN/Tunnel datasets | 48 |
| F — Methods & Meta-Science | Benchmarks, model validation, reproducibility, neuroAI toolkits, representational geometry, ground truth | 17 |

## Relevance Categories

| Tag | Research Pillar |
|---|---|
| `LLM-Memory` | LLM lingering memory, attention-based episodic memory in transformers |
| `Schema-Episodic` | Schema-guided episodic memory, hippocampal mechanisms |
| `KV-Networks` | Key-value memory networks, serial position effects, temporal context |
| `Encoding-Retrieval` | Encoding/retrieval mechanisms, reinstatement, context effects |
| `Cross-cutting` | Spans multiple pillars or provides theoretical scaffolding |
| `Peripheral` | Adjacent but interesting |

## Bluesky Topic Analysis

The keyword matrix is periodically calibrated against the researcher's actual sharing patterns on Bluesky (`@qlu.bsky.social`). The word cloud and bar chart in `outputs/` — generated from 212 paper-related posts across 30 months — provide a data-driven view of research interests: memory, hippocampus, neural representations, encoding, computational models, and NeuroAI alignment. See `outputs/bsky-paper-posts.html` for the full archive of paper-related posts.

## Project Structure

```
paper-tracking/
├── prompts/
│   └── daily-paper-tracker.md       # The prompt that drives the agent
├── data/
│   └── seen_papers.json             # Deduplication store (DOI → date first seen)
├── outputs/
│   ├── YYYY-MM-DD-paper-tracker.html # Daily reports
│   └── bluesky-topic-analysis.html   # Bluesky repost topic clustering
└── .workbuddy/
    ├── automations/                  # Automation config (not tracked in git)
    └── memory/                       # Workspace memory (not tracked in git)
```

## Modifying

To change search keywords, sources, output format, or quality standards, edit `prompts/daily-paper-tracker.md`. The automation reads this file fresh on each run — no need to update the automation itself.

To reset the deduplication store (e.g., after a bad run), delete `data/seen_papers.json`. It will be recreated on the next run.

## Dependencies

- WorkBuddy with automation support
- Web search and web fetch tools (built into WorkBuddy)
- Optional: MCP connectors for academic search (PubMed, Semantic Scholar)
