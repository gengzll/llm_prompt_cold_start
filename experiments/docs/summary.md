# Experiment group: docs (inputs x mode, 2x2)

Corpus: `sample_docs`
Inputs: `questions.txt` + `domain_knowledge.txt` in this folder.

| Variant | Mode | Inputs | Confidence | #Types | Query types | Prompt |
|---|---|---|---:|---:|---|---|
| offline_no_inputs | offline | none | 0.47 | 6 | fact_extraction, comparison, policy_interpretation, summary, evidence_lookup, insufficient_evidence | [results/offline_no_inputs.md](results/offline_no_inputs.md) |
| offline_with_inputs | offline | Q+DK | 0.47 | 5 | fact_extraction, comparison, evidence_lookup, policy_interpretation, insufficient_evidence | [results/offline_with_inputs.md](results/offline_with_inputs.md) |
| online_no_inputs | online (glm-4-flash) | none | 0.82 | 6 | sustainability_report_analysis, climate_target_evaluation, governance_structure_inspection, compliance_policy_analysis, whistleblower_channel_evaluation, insufficient_evidence | [results/online_no_inputs.md](results/online_no_inputs.md) |
| online_with_inputs | online (glm-4-flash) | Q+DK | 0.91 | 6 | climate_target_query, emission_comparison_query, governance_structure_query, policy_procedure_query, financial_metric_query, insufficient_evidence | [results/online_with_inputs.md](results/online_with_inputs.md) |
