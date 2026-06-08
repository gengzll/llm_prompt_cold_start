"""Run the cold-start pipeline offline on the bundled sample documents.

    python examples/run_example.py

No API key required: this forces offline (deterministic) synthesis.
"""

from __future__ import annotations

from pathlib import Path

from llm_prompt_cold_start import ColdStartPipeline, Settings

HERE = Path(__file__).parent


def main() -> None:
    settings = Settings.load()
    settings.offline = True  # deterministic, no network

    pipeline = ColdStartPipeline(settings)
    result = pipeline.run(
        [HERE / "sample_docs"],
        questions=[
            "What is GreenCo's 2030 emissions reduction target?",
            "Compare Scope 1 emissions in 2022 and 2023.",
            "How does the whistleblower policy work?",
            "Who chairs the Sustainability Committee?",
        ],
        domain_knowledge=[
            "Answers must be grounded in the provided documents.",
            "This corpus covers ESG, climate targets, and corporate governance.",
        ],
    )

    print("=" * 70)
    print("GENERATED SYSTEM PROMPT")
    print("=" * 70)
    print(result.system_prompt)
    print("=" * 70)
    print(f"confidence: {result.confidence}")
    print(f"query types: {[qt.name for qt in result.query_types]}")
    print(f"doc types: {result.corpus_profile.doc_types}")
    print(f"top keyphrases: {[p for p, _ in result.corpus_profile.keyphrases[:10]]}")
    for note in result.notes:
        print(f"note: {note}")


if __name__ == "__main__":
    main()
