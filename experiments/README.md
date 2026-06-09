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

**Confidence ranks the scaffolds as expected.** Online clearly outranks offline; the PDF
group shows the widest gap (offline ~0.5 vs online ~0.9). See
[How confidence is computed](#how-confidence-is-computed) below for the formula.

> Note: online output varies slightly run to run (temperature 0.2), so query-type names and
> aliases may differ if you re-run.

## How confidence is computed

`confidence` (the number in each `summary.md`) is a coarse 0–1 estimate of how much to
trust a generated scaffold before using it. It is a weighted sum of six signals, computed
in `compute_confidence()` in `llm_prompt_cold_start/synthesis.py`:

```
confidence = 0.25·grounding + 0.20·cleanliness + 0.20·synthesis
           + 0.20·specificity + 0.05·corpus_size + 0.10·sections
```

| Signal | Weight | Range | What it measures |
|---|---:|---|---|
| `grounding` | 0.25 | 0–1 | How strongly key concepts are attested in the corpus. Each concept scores `min(1, support / strong)` with `strong = min(3, n_documents)`, then averaged. Graded (not present/absent) so it isn't tautological offline, where concepts *are* the keyphrases. |
| `cleanliness` | 0.20 | 0–1 | Fraction of key concepts that look like real terms (multi-word, or a single word ≥5 letters, no digits) rather than tokenizer noise like `usd`/`tco`. |
| `synthesis` | 0.20 | 0–1 | Fraction of the 8 pack fields the LLM actually produced vs. deterministic fallback. **0 for offline**; a silent fallback (LLM omitting a field) lowers it. |
| `specificity` | 0.20 | 0–1 | Fraction of query types that are corpus-specific (`emissions_reduction_target`) rather than generic catalog names (`fact_extraction`). The always-present `insufficient_evidence` guard is ignored. **0 for offline**. |
| `corpus_size` | 0.05 | 0–1 | `min(1, n_docs/5) · min(1, n_chars/20000)` — more documents / more text is more reliable. |
| `sections` | 0.10 | 0.5–1 | 1.0 if section structure was parsed from the documents, else 0.5. |

**Why online outranks offline.** `synthesis` and `specificity` are 0 by construction for
the deterministic path, so **offline is capped at 0.60** even in the best case. `synthesis`
is an explicit prior (LLM synthesis is treated as more trustworthy here); the other five are
observable quality measures.

**Worked example** (offline, recomputed from the committed runs):

| Term (signal · weight) | docs offline | pdf offline |
|---|---|---|
| grounding · 0.25 | 0.78 → 0.194 | 0.95 → 0.237 |
| cleanliness · 0.20 | 0.85 → 0.170 | 0.80 → 0.160 |
| synthesis · 0.20 | 0.00 → 0.000 | 0.00 → 0.000 |
| specificity · 0.20 | 0.00 → 0.000 | 0.00 → 0.000 |
| corpus_size · 0.05 | 0.044 → 0.002 | 0.800 → 0.040 |
| sections · 0.10 | 1.0 → 0.100 | 1.0 → 0.100 |
| **confidence** | **0.47** | **0.54** |

Going online flips `synthesis` and `specificity` from 0 toward ~1.0, adding up to ~0.40 —
which is why the online variants land near 0.82–0.96.

**Low-confidence flag.** When `confidence < 0.5` the pipeline emits a review note (small
corpus, weak grounding, or deterministic synthesis). The `docs` offline runs sit just under
this line (0.47) and the `pdf` offline runs just above (0.54) — deliberately, since a
deterministic scaffold is a draft that should be reviewed, not trusted blindly.
