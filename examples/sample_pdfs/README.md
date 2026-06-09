# sample_pdfs

Drop document-corpus PDFs here to run the PDF demo:

```bash
python experiments/run_pdf_demo.py        # offline only
# add OPENAI_API_KEY / OPENAI_BASE_URL / COLD_START_MODEL for the online group
```

The PDFs themselves are **not committed** (large binaries / third-party reports — see
`.gitignore`). The committed demo (`experiments/results_pdf/`, `experiments/summary_pdf.md`)
was produced from these four public reports:

- `110724_FINAL_2023_ESG-Report_Ooredoo.pdf` (45 pages)
- `45459-PZ-Cussons-AR24-web-singles.pdf` (216 pages)
- `e0522-asmptesgreport.pdf` (114 pages)
- `Ooredoo-Annual-Report-2023-ENGLISH-V2.pdf` (77 pages)

Total ~452 pages / ~1.6M characters across ESG and annual reports.
