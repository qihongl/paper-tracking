## 2. Two-layer recall audit
Corpus: 362 papers (['2025', '2026']). Keyword-gate recall **99.7%**; venue coverage **96.7%**.

| Outcome | n | % |
|---|---|---|
| caught | 349 | 96.4% |
| venue-gap | 12 | 3.3% |
| keyword-gap | 1 | 0.3% |

**Calibration:** 88.0% of the 200 actually-reported papers are keyword-caught (target ≥90%).

Reported-but-not-keyword-caught (sample):
- Auditing Forgetting in Limited Memory Language Models
- LongCrafter: Towards Diverse Long-Context Understanding via Evidence-Graph-Guided Instruction Synthesis
- Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents
- Creativity, honesty and designed forgetting emerge in small hyperbolic language models
- Scoped Verification for Reliable Long-Horizon Agentic Context Evolution under Distribution Shift (GRACE)
- MLPs are Hebbians: Constructing Efficient Fact-Storing MLPs for Transformers
- One Mechanism for Many Mental Spaces: A Shared Router over a Value Slot in Language Models
- Remembering Distinct Items, Not Tokens: A Learnable Dirichlet-Process Cache Between State-Space Models and Attention

## 4. Venue calibration
Papers failing the venue gate (tracker never looks at this venue):

- **journal:Theory and Society [NOT-listed]**: 1 paper(s)
- **journal:Journal of Dementia and Alzheimer's Disease [title-match, score=1.0]**: 1 paper(s)
- **journal:Royal Society Open Science [NOT-listed]**: 1 paper(s)
- **journal:Age and Ageing [NOT-listed]**: 1 paper(s)
- **journal:Developmental Science [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of Medical Internet Research [title-match, score=1.0]**: 1 paper(s)
- **journal:Journal of Neuropsychology [NOT-listed]**: 1 paper(s)
- **journal:The Clinical Neuropsychologist [NOT-listed]**: 1 paper(s)
- **journal:Philosophical Transactions of the Royal Society A: Mathematical, Physical and Engineering Sciences [NOT-listed]**: 1 paper(s)
- **journal:Eng [NOT-listed]**: 1 paper(s)
- **journal:Advances in Science, Technology &amp; Innovation [title-match, score=1.0]**: 1 paper(s)
- **journal:DIGITAL HEALTH [title-match, score=1.0]**: 1 paper(s)

**Tier 1 — journals to ADD to the source list:**
- Theory and Society (1)
- Journal of Dementia and Alzheimer's Disease (1)
- Royal Society Open Science (1)
- Age and Ageing (1)
- Developmental Science (1)
- Journal of Medical Internet Research (1)
- Journal of Neuropsychology (1)
- The Clinical Neuropsychologist (1)
- Philosophical Transactions of the Royal Society A: Mathematical, Physical and Engineering Sciences (1)
- Eng (1)

**Tier 2 — promote to direct-scan?** (listed in the 47 but not direct-scanned; shown with corpus paper counts — prefer venues with high library weight)
- Communications Biology (8 corpus paper(s))
- Scientific Data (7 corpus paper(s))
- Nature Medicine (2 corpus paper(s))
- Cell Reports (2 corpus paper(s))
- PLOS Biology (2 corpus paper(s))
- Nature Reviews Psychology (2 corpus paper(s))
- npj Science of Learning (2 corpus paper(s))
- Memory (1 corpus paper(s))
- Nature Computational Science (1 corpus paper(s))
- Journal of Experimental Psychology: Learning, Memory, and Cognition (1 corpus paper(s))
- The Neuroscientist (1 corpus paper(s))
- iScience (1 corpus paper(s))
- Nature Protocols (1 corpus paper(s))
- Imaging Neuroscience (1 corpus paper(s))
- Nature Methods (1 corpus paper(s))
- Perspectives on Psychological Science (1 corpus paper(s))
- Psychophysiology (1 corpus paper(s))
- Current Opinion in Neurobiology (1 corpus paper(s))

**Tier 3 — arXiv categories to consider:**

## 5. Section distribution
| Section | Keywords | Corpus papers matched (any kw) | Primary (most kws) |
|---|---|---|---|
| A — Human/Animal Systems & Cognitive Neuroscie | 134 | 355 | 315 |
| B — Computational Models of Memory | 58 | 222 | 12 |
| C — LLMs and Machine Memory | 47 | 7 | 0 |
| D — Encoding, Working Memory & Retrieval Mecha | 63 | 108 | 1 |
| E — Naturalistic Paradigms & Neuroimaging | 43 | 142 | 3 |
| F — Methods, Benchmarks & Meta-Science | 17 | 0 | 0 |
| G — Reinforcement Learning, Decision-Making &  | 28 | 238 | 30 |

## 3. Miss mining & edit simulation
**Finding: the keyword layer is saturated for this corpus** — only 1 paper(s) fail the keyword gate, so ngram/embedding mining has no signal. The matrix (390 keywords) already covers the vocabulary of the 362-paper library.

- Keyword-gap paper: *Human HDAC6 senses valine abundancy to regulate DNA damage* — out-of-domain for the tracker (see §2); no keyword action needed.

> **Implication:** the coverage bottleneck is the **venue layer** (§4), not the keyword layer. Keyword edits should be driven by the *reported-golden-set* misses from §2 calibration, not by this corpus.

