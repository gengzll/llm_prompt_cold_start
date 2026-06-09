# Experiments

Two corpus groups, each a full 2x2 matrix over the two axes that drive the prompt:

- **inputs**: with `questions` + `domain_knowledge`  vs  none (documents only)
- **mode**: `offline` (deterministic, corpus statistics)  vs  `online` (LLM synthesis)

| Group | Corpus | Folder |
|---|---|---|
| **docs** | `examples/sample_docs` (GreenCo ESG + policy, markdown) | [`docs/`](docs/) |
| **pdf**  | `examples/sample_pdfs` (4 real ESG / annual reports) | [`pdf/`](pdf/) |

Each group folder is self-contained:

```
docs/ (and pdf/)
  questions.txt              # the inputs used by the *_with_inputs variants
  domain_knowledge.txt
  results/
    offline_no_inputs.md     offline_with_inputs.md
    online_no_inputs.md      online_with_inputs.md
  summary.md                 # comparison table for the 4 variants
  summary.json
```

## Reproduce

```bash
# both groups, offline variants only (no key needed; online variants skipped)
python experiments/run_experiments.py

# one group only
python experiments/run_experiments.py docs
python experiments/run_experiments.py pdf

# include the online variants (OpenAI-compatible endpoint)
export OPENAI_API_KEY=...            # online variants read this
export OPENAI_BASE_URL=...           # e.g. https://open.bigmodel.cn/api/paas/v4 (Zhipu)
export COLD_START_MODEL=glm-4-flash
python experiments/run_experiments.py
```

The committed runs used Zhipu **glm-4-flash** for the online variants. See each group's
`summary.md` for its table: [`docs/summary.md`](docs/summary.md),
[`pdf/summary.md`](pdf/summary.md).

## What the experiments show

**Mode (offline vs online) — the biggest difference.**
- `# DOMAIN KNOWLEDGE`: offline lists denoised keyphrases as bare vocabulary; online
  produces a glossary with synonyms (`governance structure (governance model, board
  structure)`) — useful for mapping user phrasing to corpus terms.
- `# QUERY-TYPE PLAYBOOK`: offline picks generic catalog templates (`fact_extraction`,
  `comparison`, ...); online specializes types to the corpus and the questions, and points
  retrieval at the real section names (e.g. `emissions_reduction_target`).

**Inputs (with vs without Q+DK).**
- Offline: `domain_knowledge` is appended verbatim into `# CONTEXT`; `questions` decide
  which catalog query types appear.
- Online: `domain_knowledge` is a signal the LLM folds into the whole pack; `questions`
  make the query types track what users actually ask.

**Confidence ranks the scaffolds as expected.** Six signals — graded grounding, concept
cleanliness, synthesis provenance (LLM vs fallback fields), query-type specificity, corpus
size, section structure. Online clearly outranks offline because the deterministic path
scores 0 on synthesis provenance and query-type specificity. The PDF group shows the widest
gap (offline ~0.5 vs online ~0.9), since offline degrades more on complex real-world layouts.

> Note: online output varies slightly run to run (temperature 0.2), so query-type names and
> aliases may differ if you re-run.
