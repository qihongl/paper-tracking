# Daily Paper Tracker

Automated daily literature surveillance for computational cognitive neuroscience research on episodic memory. Runs as a WorkBuddy automation, searches multiple sources, filters by relevance, and produces a self-contained HTML briefing.

## How It Works

A WorkBuddy automation (`automation-1783133189790`) reads `prompts/daily-paper-tracker.md` and executes it daily. The agent:

1. **Searches** arxiv, bioRxiv, PubMed, and high-impact journals across a keyword matrix spanning episodic memory, computational models, LLM memory, and encoding/retrieval mechanisms.
2. **Deduplicates** against `data/seen_papers.json` — papers are matched by DOI, arxiv ID, or title slug and never reported twice.
3. **Filters** for mechanistic relevance, not just keyword matches. Papers that are purely engineering, clinical case studies without computational relevance, or opinion pieces are excluded.
4. **Generates** a self-contained HTML report at `outputs/YYYY-MM-DD-paper-tracker.html` with papers grouped into six relevance categories.
5. **Presents** the HTML via WorkBuddy's `present_files`.

## Relevance Categories

| Tag | Research Pillar |
|---|---|
| `LLM-Memory` | LLM lingering memory, attention-based episodic memory in transformers |
| `Schema-Episodic` | Schema-guided episodic memory, hippocampal mechanisms |
| `KV-Networks` | Key-value memory networks, serial position effects, temporal context |
| `Encoding-Retrieval` | Encoding/retrieval mechanisms, reinstatement, context effects |
| `Cross-cutting` | Spans multiple pillars or provides theoretical scaffolding |
| `Peripheral` | Adjacent but interesting |

## Project Structure

```
paper-tracking/
├── prompts/
│   └── daily-paper-tracker.md    # The prompt that drives the agent
├── data/
│   └── seen_papers.json          # Deduplication store (DOI → date first seen)
├── outputs/
│   └── YYYY-MM-DD-paper-tracker.html  # Daily reports
└── .workbuddy/
    └── memory/                   # Workspace memory (not tracked in git)
```

## Modifying

To change search keywords, sources, output format, or quality standards, edit `prompts/daily-paper-tracker.md`. The automation reads this file fresh on each run — no need to update the automation itself.

To reset the deduplication store (e.g., after a bad run), delete `data/seen_papers.json`. It will be recreated on the next run.

## Dependencies

- WorkBuddy with automation support
- Web search and web fetch tools (built into WorkBuddy)
- Optional: MCP connectors for academic search (PubMed, Semantic Scholar)
