"""PDF demo: offline vs online on real documents, with NO user inputs.

Corpus: experiments-local `examples/sample_pdfs/` (ESG / annual reports).
Two groups only, both with no questions and no domain_knowledge:
  - offline_no_inputs (deterministic)
  - online_no_inputs  (LLM; runs only if an API key is configured)

    python experiments/run_pdf_demo.py            # offline only
    OPENAI_API_KEY=... OPENAI_BASE_URL=... COLD_START_MODEL=... \
        python experiments/run_pdf_demo.py        # + online

Outputs:
  experiments/results_pdf/<group>.md   - generated system prompt per group
  experiments/summary_pdf.json / .md   - metrics + comparison table
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm_prompt_cold_start import ColdStartPipeline, Settings  # noqa: E402

CORPUS = ROOT / "examples" / "sample_pdfs"
RESULTS = ROOT / "experiments" / "results_pdf"

GROUPS = [("offline_no_inputs", True), ("online_no_inputs", False)]


def run() -> list[dict]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []

    for name, offline in GROUPS:
        settings = Settings.load()
        settings.offline = offline
        if not offline and not settings.can_use_llm:
            print(f"[skip] {name}: no API key set — online needs OPENAI_API_KEY")
            summary.append({"group": name, "mode": "online", "status": "skipped (no API key)"})
            continue

        pdfs = sorted(CORPUS.glob("*.pdf"))  # only the PDFs, not a stray README/notes
        if not pdfs:
            print(f"[skip] {name}: no PDFs in {CORPUS}")
            continue
        t0 = time.time()
        result = ColdStartPipeline(settings).run(pdfs)  # no questions, no domain knowledge
        elapsed = time.time() - t0

        (RESULTS / f"{name}.md").write_text(result.system_prompt, encoding="utf-8")
        summary.append(
            {
                "group": name,
                "mode": "offline" if offline else "online",
                "model": settings.model if not offline else "-",
                "confidence": result.confidence,
                "n_query_types": len(result.query_types),
                "query_types": [t.name for t in result.query_types],
                "prompt_chars": len(result.system_prompt),
                "seconds": round(elapsed, 1),
                "prompt_file": f"results_pdf/{name}.md",
            }
        )
        print(f"[ok] {name}: conf={result.confidence} types={[t.name for t in result.query_types]} ({elapsed:.1f}s)")

    _write_summary(summary)
    return summary


def _write_summary(summary: list[dict]) -> None:
    (ROOT / "experiments" / "summary_pdf.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pdfs = sorted(p.name for p in CORPUS.glob("*.pdf"))
    lines = [
        "# PDF demo: offline vs online (no inputs)",
        "",
        f"Corpus: `examples/sample_pdfs/` ({len(pdfs)} real ESG / annual reports). "
        "No questions, no domain_knowledge.",
        "",
        "Documents: " + ", ".join(f"`{n}`" for n in pdfs),
        "",
        "| Group | Mode | Confidence | #Types | Query types | Prompt |",
        "|---|---|---:|---:|---|---|",
    ]
    for s in summary:
        if s.get("status"):
            lines.append(f"| {s['group']} | {s['mode']} | - | - | _{s['status']}_ | - |")
            continue
        types = ", ".join(s["query_types"])
        model = "" if s["mode"] == "offline" else f" ({s['model']})"
        lines.append(
            f"| {s['group']} | {s['mode']}{model} | {s['confidence']} | "
            f"{s['n_query_types']} | {types} | [{s['prompt_file']}]({s['prompt_file']}) |"
        )
    lines.append("")
    (ROOT / "experiments" / "summary_pdf.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run()
