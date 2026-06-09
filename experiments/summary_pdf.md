# PDF demo: offline vs online (no inputs)

Corpus: `examples/sample_pdfs/` (4 real ESG / annual reports). No questions, no domain_knowledge.

Documents: `110724_FINAL_2023_ESG-Report_Ooredoo.pdf`, `45459-PZ-Cussons-AR24-web-singles.pdf`, `Ooredoo-Annual-Report-2023-ENGLISH-V2.pdf`, `e0522-asmptesgreport.pdf`

| Group | Mode | Confidence | #Types | Query types | Prompt |
|---|---|---:|---:|---|---|
| offline_no_inputs | offline | 0.56 | 6 | fact_extraction, comparison, policy_interpretation, summary, evidence_lookup, insufficient_evidence | [results_pdf/offline_no_inputs.md](results_pdf/offline_no_inputs.md) |
| online_no_inputs | online (glm-4-flash) | 0.96 | 6 | financial_performance_overview, esg_initiatives_details, governance_structure_analysis, employee_management_practices, customer_relations_strategies, insufficient_evidence | [results_pdf/online_no_inputs.md](results_pdf/online_no_inputs.md) |
