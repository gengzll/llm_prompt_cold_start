"""Run a 2x2 experiment matrix and save every generated prompt.

Axes:
  - inputs:  with questions+domain_knowledge   vs   none (docs only)
  - mode:    offline (deterministic)            vs   online (LLM)

Produces 4 groups. Offline groups always run. Online groups run only when an
API key is configured (OPENAI_API_KEY, optionally OPENAI_BASE_URL / COLD_START_MODEL),
otherwise they are skipped with a note.

    python experiments/run_experiments.py

Outputs:
  experiments/results/<group>.md   - the generated system prompt for each group
  experiments/summary.json         - machine-readable metrics
  experiments/summary.md           - human-readable comparison table
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm_prompt_cold_start import ColdStartPipeline, Settings  # noqa: E402

SAMPLES = ROOT / "examples" / "sample_docs"
RESULTS = ROOT / "experiments" / "results"


def _read_lines(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


QUESTIONS = _read_lines(ROOT / "examples" / "questions.txt")
DOMAIN_KNOWLEDGE = _read_lines(ROOT / "examples" / "domain_knowledge.txt")

# (group name, offline?, with inputs?)
GROUPS = [
    ("offline_no_inputs", True, False),
    ("offline_with_inputs", True, True),
    ("online_no_inputs", False, False),
    ("online_with_inputs", False, True),
]


def run() -> list[dict]:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []

    for name, offline, with_inputs in GROUPS:
        settings = Settings.load()
        settings.offline = offline

        if not offline and not settings.can_use_llm:
            print(f"[skip] {name}: no API key set — online groups need OPENAI_API_KEY")
            summary.append({"group": name, "mode": "online", "status": "skipped (no API key)"})
            continue

        questions = QUESTIONS if with_inputs else []
        domain_knowledge = DOMAIN_KNOWLEDGE if with_inputs else []

        result = ColdStartPipeline(settings).run(
            [SAMPLES], questions=questions, domain_knowledge=domain_knowledge
        )

        out_file = RESULTS / f"{name}.md"
        out_file.write_text(result.system_prompt, encoding="utf-8")

        summary.append(
            {
                "group": name,
                "mode": "offline" if offline else "online",
                "model": settings.model if not offline else "-",
                "questions": bool(questions),
                "domain_knowledge": bool(domain_knowledge),
                "confidence": result.confidence,
                "n_query_types": len(result.query_types),
                "query_types": [t.name for t in result.query_types],
                "prompt_chars": len(result.system_prompt),
                "prompt_file": f"results/{name}.md",
            }
        )
        print(
            f"[ok] {name}: mode={summary[-1]['mode']} "
            f"confidence={result.confidence} "
            f"types={[t.name for t in result.query_types]}"
        )

    _write_summary(summary)
    return summary


def _write_summary(summary: list[dict]) -> None:
    (ROOT / "experiments" / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Experiment results: inputs x mode (2x2)",
        "",
        "Corpus: `examples/sample_docs` (GreenCo ESG + policy). "
        "Inputs: `examples/questions.txt` + `examples/domain_knowledge.txt`.",
        "",
        "| Group | Mode | Inputs | Confidence | #Types | Query types | Prompt |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for s in summary:
        if s.get("status"):
            lines.append(
                f"| {s['group']} | {s['mode']} | - | - | - | _{s['status']}_ | - |"
            )
            continue
        inputs = "Q+DK" if s["questions"] else "none"
        types = ", ".join(s["query_types"])
        lines.append(
            f"| {s['group']} | {s['mode']} ({s['model']}) | {inputs} | "
            f"{s['confidence']} | {s['n_query_types']} | {types} | "
            f"[{s['prompt_file']}]({s['prompt_file']}) |"
        )
    lines.append("")
    (ROOT / "experiments" / "summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run()
