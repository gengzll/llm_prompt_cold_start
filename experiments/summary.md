# Experiment results: inputs x mode (2x2)

Corpus: `examples/sample_docs` (GreenCo ESG + policy). Inputs: `examples/questions.txt` + `examples/domain_knowledge.txt`.

| Group | Mode | Inputs | Confidence | #Types | Query types | Prompt |
|---|---|---|---:|---:|---|---|
| offline_no_inputs | offline (-) | none | 0.47 | 6 | fact_extraction, comparison, policy_interpretation, summary, evidence_lookup, insufficient_evidence | [results/offline_no_inputs.md](results/offline_no_inputs.md) |
| offline_with_inputs | offline (-) | Q+DK | 0.47 | 5 | fact_extraction, comparison, evidence_lookup, policy_interpretation, insufficient_evidence | [results/offline_with_inputs.md](results/offline_with_inputs.md) |
| online_no_inputs | online (glm-4-flash) | none | 0.85 | 6 | sustainability_report_analysis, climate_target_evaluation, governance_practice_inspection, whistleblower_protection_assessment, data_protection_analysis, insufficient_evidence | [results/online_no_inputs.md](results/online_no_inputs.md) |
| online_with_inputs | online (glm-4-flash) | Q+DK | 0.88 | 6 | emissions_reduction_target, scope_emissions_comparison, committee_structure, whistleblower_policy, gift_declaration_policy, insufficient_evidence | [results/online_with_inputs.md](results/online_with_inputs.md) |
