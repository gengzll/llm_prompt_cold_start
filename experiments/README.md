# Experiments

A 2x2 matrix showing how the two axes affect the generated system prompt:

- **inputs**: with `questions` + `domain_knowledge`  vs  none (documents only)
- **mode**: `offline` (deterministic, corpus statistics)  vs  `online` (LLM synthesis)

Reproduce:

```bash
# offline groups only (no key needed)
python experiments/run_experiments.py

# include the online groups (OpenAI-compatible endpoint)
export OPENAI_API_KEY=...            # online groups read this
export OPENAI_BASE_URL=...           # e.g. https://open.bigmodel.cn/api/paas/v4 (Zhipu)
export COLD_START_MODEL=glm-4-flash
python experiments/run_experiments.py
```

Outputs: the four prompts in [`results/`](results/), plus [`summary.md`](summary.md)
and `summary.json`. The run below used Zhipu **glm-4-flash** for the online groups.

## What the four prompts show

See [`summary.md`](summary.md) for the table. Qualitative findings:

**Mode (offline vs online) — the biggest difference.**
- `# DOMAIN KNOWLEDGE`: offline lists denoised keyphrases as bare vocabulary;
  online produces a glossary with aliases (`governance structure (aka governance
  model, board structure)`) — useful for mapping user phrasing to corpus terms.
- `# QUERY-TYPE PLAYBOOK`: offline picks generic catalog templates
  (`fact_extraction`, `comparison`, ...); online specializes types to the corpus
  and the questions, and points retrieval at the real section names
  (e.g. `emissions_reduction_target` → "Climate Targets and Emissions").

**Inputs (with vs without Q+DK).**
- Offline: `domain_knowledge` is appended verbatim into `# CONTEXT`; `questions`
  decide which catalog query types appear.
- Online: `domain_knowledge` is a signal the LLM folds into the whole pack;
  `questions` make the query types track what users actually ask.

**Both online groups keep the `insufficient_evidence` guard** (bug fix #2), and the
reverse-verification matches cleaned concepts against the corpus by token overlap
(bug fix #1).

**Confidence now ranks the scaffolds the way you'd expect.** It used to return the same
value (~0.71) for every group: two of its three terms were corpus constants and the third
(binary coverage) was tautological offline. It is now six signals — graded grounding,
concept cleanliness, **synthesis provenance** (fraction of pack fields the LLM actually
produced vs. silent fallback), **query-type specificity** (corpus-specific vs. generic
catalog templates), corpus size, and section structure. Result on this corpus:

- online (0.83–0.89) clearly outranks offline (0.46), because the deterministic path
  scores 0 on both synthesis provenance and query-type specificity;
- a silent fallback (the LLM omitting `key_concepts`) now lowers `synthesis` instead of
  passing noisy keyphrases off as if they were clean LLM output.

The `synthesis` signal encodes a prior (LLM synthesis is more trustworthy here); the
others are observable quality measures.

> Note: online output varies slightly run to run (temperature 0.2), so query-type
> names may differ if you re-run.
