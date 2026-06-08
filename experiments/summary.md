# Experiment results: inputs x mode (2x2)

Corpus: `examples/sample_docs` (GreenCo ESG + policy). Inputs: `examples/questions.txt` + `examples/domain_knowledge.txt`.

| Group | Mode | Inputs | Confidence | #Types | Query types | Prompt |
|---|---|---|---:|---:|---|---|
| offline_no_inputs | offline (-) | none | 0.72 | 6 | fact_extraction, comparison, policy_interpretation, summary, evidence_lookup, insufficient_evidence | [results/offline_no_inputs.md](results/offline_no_inputs.md) |
| offline_with_inputs | offline (-) | Q+DK | 0.72 | 5 | fact_extraction, comparison, evidence_lookup, policy_interpretation, insufficient_evidence | [results/offline_with_inputs.md](results/offline_with_inputs.md) |
| online_no_inputs | online (glm-4-flash) | none | 0.69 | 6 | esg_report_analysis, governance_structure, climate_emission_reduction, compliance_issues, data_protection_measures, insufficient_evidence | [results/online_no_inputs.md](results/online_no_inputs.md) |
| online_with_inputs | online (glm-4-flash) | Q+DK | 0.78 | 6 | emissions_reduction_target, emissions_comparison, committee_membership, whistleblower_policy, gift_declaration, insufficient_evidence | [results/online_with_inputs.md](results/online_with_inputs.md) |

Confidence reflects scaffold quality (grounding strength + concept cleanliness + corpus
size + section structure). `online_with_inputs` scores highest (cleanest, fully
multi-word concepts); `online_no_inputs` lowest here because that run's domain pack fell
back to noisy keyphrase concepts. Online confidence is recomputed from the committed
prompts; re-running `run_experiments.py` with a live key regenerates everything.
