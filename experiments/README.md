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
- `# ROLE` / `Key concepts`: offline lists raw keyphrases (noisy: `usd`, `tco`,
  `anonymous reporting channel`); online produces clean abstract themes
  (`ESG performance`, `climate emissions`, `governance structure`).
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
online confidence is now grounded correctly (bug fix #1: reverse-verification uses
token-overlap matching, so cleaned concepts still match the corpus).

> Note: online output varies slightly run to run (temperature 0.2), so query-type
> names may differ if you re-run.
