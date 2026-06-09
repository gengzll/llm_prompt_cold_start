"""Run the experiment matrix for one or both corpus groups.

Two groups, each a full 2x2 (inputs x mode):
  - docs : the markdown corpus in examples/sample_docs
  - pdf  : the PDF corpus in examples/sample_pdfs

Each group runs four experiments:
  offline_no_inputs, offline_with_inputs, online_no_inputs, online_with_inputs

Per-group inputs live in experiments/<group>/{questions,domain_knowledge}.txt.
Outputs go under the same folder:
  experiments/<group>/results/<variant>.md   - generated system prompt
  experiments/<group>/summary.json / .md      - metrics + comparison table

Usage:
  python experiments/run_experiments.py            # both groups
  python experiments/run_experiments.py docs       # one group only
  python experiments/run_experiments.py pdf

Online variants run only when an API key is configured (OPENAI_API_KEY, and
optionally OPENAI_BASE_URL / COLD_START_MODEL); otherwise they are skipped.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm_prompt_cold_start import ColdStartPipeline, Settings  # noqa: E402

EXPERIMENTS = ROOT / "experiments"

# group -> how to collect its corpus document paths
GROUPS = {
    "docs": lambda: [ROOT / "examples" / "sample_docs"],
    "pdf": lambda: sorted((ROOT / "examples" / "sample_pdfs").glob("*.pdf")),
}

# (variant name, offline?, with inputs?)
VARIANTS = [
    ("offline_no_inputs", True, False),
    ("offline_with_inputs", True, True),
    ("online_no_inputs", False, False),
    ("online_with_inputs", False, True),
]


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def run_group(name: str) -> list[dict]:
    gdir = EXPERIMENTS / name
    results_dir = gdir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    corpus = GROUPS[name]()
    questions = _read_lines(gdir / "questions.txt")
    domain_knowledge = _read_lines(gdir / "domain_knowledge.txt")

    summary: list[dict] = []
    for variant, offline, with_inputs in VARIANTS:
        settings = Settings.load()
        settings.offline = offline
        if not offline and not settings.can_use_llm:
            print(f"[skip] {name}/{variant}: no API key — online needs OPENAI_API_KEY")
            summary.append({"group": name, "variant": variant, "mode": "online", "status": "skipped (no API key)"})
            continue

        q = questions if with_inputs else []
        dk = domain_knowledge if with_inputs else []
        t0 = time.time()
        result = ColdStartPipeline(settings).run(corpus, questions=q, domain_knowledge=dk)
        elapsed = time.time() - t0

        (results_dir / f"{variant}.md").write_text(result.system_prompt, encoding="utf-8")
        summary.append(
            {
                "group": name,
                "variant": variant,
                "mode": "offline" if offline else "online",
                "model": settings.model if not offline else "-",
                "inputs": bool(q or dk),
                "confidence": result.confidence,
                "n_query_types": len(result.query_types),
                "query_types": [t.name for t in result.query_types],
                "prompt_chars": len(result.system_prompt),
                "seconds": round(elapsed, 1),
                "prompt_file": f"results/{variant}.md",
            }
        )
        print(f"[ok] {name}/{variant}: conf={result.confidence} ({elapsed:.1f}s)")

    _write_summary(name, gdir, corpus, summary)
    return summary


def _write_summary(name: str, gdir: Path, corpus: list, summary: list[dict]) -> None:
    (gdir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    docs = ", ".join(f"`{Path(c).name}`" for c in corpus)
    lines = [
        f"# Experiment group: {name} (inputs x mode, 2x2)",
        "",
        f"Corpus: {docs}",
        "Inputs: `questions.txt` + `domain_knowledge.txt` in this folder.",
        "",
        "| Variant | Mode | Inputs | Confidence | #Types | Query types | Prompt |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for s in summary:
        if s.get("status"):
            lines.append(f"| {s['variant']} | {s['mode']} | - | - | - | _{s['status']}_ | - |")
            continue
        model = "" if s["mode"] == "offline" else f" ({s['model']})"
        inputs = "Q+DK" if s["inputs"] else "none"
        types = ", ".join(s["query_types"])
        lines.append(
            f"| {s['variant']} | {s['mode']}{model} | {inputs} | {s['confidence']} | "
            f"{s['n_query_types']} | {types} | [{s['prompt_file']}]({s['prompt_file']}) |"
        )
    lines.append("")
    (gdir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> None:
    requested = argv[1:] or list(GROUPS)
    for name in requested:
        if name not in GROUPS:
            print(f"[error] unknown group '{name}'. Choose from: {', '.join(GROUPS)}")
            continue
        print(f"=== group: {name} ===")
        run_group(name)


if __name__ == "__main__":
    main(sys.argv)
