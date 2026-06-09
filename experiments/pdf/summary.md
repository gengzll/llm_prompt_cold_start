# Experiment group: pdf (inputs x mode, 2x2)

Corpus: `110724_FINAL_2023_ESG-Report_Ooredoo.pdf`, `45459-PZ-Cussons-AR24-web-singles.pdf`, `e0522-asmptesgreport.pdf`, `Ooredoo-Annual-Report-2023-ENGLISH-V2.pdf`
Inputs: `questions.txt` + `domain_knowledge.txt` in this folder.

| Variant | Mode | Inputs | Confidence | #Types | Query types | Prompt |
|---|---|---|---:|---:|---|---|
| offline_no_inputs | offline | none | 0.54 | 6 | fact_extraction, comparison, policy_interpretation, summary, evidence_lookup, insufficient_evidence | [results/offline_no_inputs.md](results/offline_no_inputs.md) |
| offline_with_inputs | offline | Q+DK | 0.54 | 4 | fact_extraction, comparison, evidence_lookup, insufficient_evidence | [results/offline_with_inputs.md](results/offline_with_inputs.md) |
| online_no_inputs | online (glm-4-flash) | none | 0.96 | 6 | financial_performance_analysis, governance_structure_evaluation, employee_engagement_inspection, customer_satisfaction_assessment, community_impact_evaluation, insufficient_evidence | [results/online_no_inputs.md](results/online_no_inputs.md) |
| online_with_inputs | online (glm-4-flash) | Q+DK | 0.93 | 6 | financial_comparison, board_member_identification, risk_assessment, sustainability_initiatives, employee_relations, insufficient_evidence | [results/online_with_inputs.md](results/online_with_inputs.md) |
