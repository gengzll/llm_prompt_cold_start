# Experiment results: inputs x mode (2x2)

Corpus: `examples/sample_docs` (GreenCo ESG + policy). Inputs: `examples/questions.txt` + `examples/domain_knowledge.txt`.

| Group | Mode | Inputs | Confidence | #Types | Query types | Prompt |
|---|---|---|---:|---:|---|---|
| offline_no_inputs | offline (-) | none | 0.46 | 6 | fact_extraction, comparison, policy_interpretation, summary, evidence_lookup, insufficient_evidence | [results/offline_no_inputs.md](results/offline_no_inputs.md) |
| offline_with_inputs | offline (-) | Q+DK | 0.46 | 5 | fact_extraction, comparison, evidence_lookup, policy_interpretation, insufficient_evidence | [results/offline_with_inputs.md](results/offline_with_inputs.md) |
| online_no_inputs | online (glm-4-flash) | none | 0.83 | 6 | esg_report_details, governance_structure, climate_emissions_reduction, compliance_status, whistleblower_protection_policies, insufficient_evidence | [results/online_no_inputs.md](results/online_no_inputs.md) |
| online_with_inputs | online (glm-4-flash) | Q+DK | 0.89 | 6 | emissions_reduction_target, emissions_comparison, governance_structure, policy_procedure, compliance_gift_declaration, insufficient_evidence | [results/online_with_inputs.md](results/online_with_inputs.md) |
