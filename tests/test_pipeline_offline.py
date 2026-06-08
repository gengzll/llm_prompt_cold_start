from __future__ import annotations

from pathlib import Path

from llm_prompt_cold_start import ColdStartPipeline, Settings
from llm_prompt_cold_start.analysis import build_corpus_profile
from llm_prompt_cold_start.cli import main as cli_main
from llm_prompt_cold_start.parsing import load_documents

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SAMPLES = EXAMPLES / "sample_docs"


def _offline_pipeline() -> ColdStartPipeline:
    settings = Settings.load()
    settings.offline = True
    return ColdStartPipeline(settings)


def test_parses_sample_docs():
    docs = load_documents([SAMPLES])
    assert len(docs) >= 2
    assert all(d.text for d in docs)
    # markdown headings should be detected as sections
    assert any("Governance" in s for d in docs for s in d.sections)


def test_corpus_profile_extracts_signals():
    docs = load_documents([SAMPLES])
    profile = build_corpus_profile(docs)
    assert profile.n_documents >= 2
    assert profile.keyphrases, "expected some keyphrases"
    metric_names = {m for m, _ in profile.metrics}
    # the samples contain %, currency, years and emissions units
    assert {"percentage", "year"} & metric_names


def test_offline_pipeline_produces_prompt():
    result = _offline_pipeline().run(
        [SAMPLES],
        questions=["What is the 2030 target?", "Compare 2022 and 2023 emissions."],
        domain_knowledge=["Answers must be grounded in the documents."],
    )
    sp = result.system_prompt
    assert "# ROLE" in sp
    assert "# ANSWER POLICY" in sp
    assert "# QUERY-TYPE PLAYBOOK" in sp
    assert "{context}" in sp and "{question}" in sp
    # comparison question should surface a comparison query type
    assert any(qt.name == "comparison" for qt in result.query_types)
    # always include the insufficient-evidence guard
    assert any(qt.name == "insufficient_evidence" for qt in result.query_types)
    assert 0.0 <= result.confidence <= 1.0


def test_works_without_questions_or_domain_knowledge():
    result = _offline_pipeline().run([SAMPLES])
    assert result.system_prompt
    assert result.query_types  # inferred from the corpus alone


def test_concept_support_matches_paraphrased_concepts():
    # bug fix #1: cleaned/paraphrased concepts should still find corpus support
    from llm_prompt_cold_start.synthesis import _concept_support

    keyphrases = [("committee", 4), ("emissions", 7), ("greenco", 5)]
    assert _concept_support("Sustainability Committee", keyphrases) == 4
    assert _concept_support("emissions reduction", keyphrases) == 7
    assert _concept_support("unrelated term", keyphrases) == 0


def test_confidence_discriminates_clean_vs_noisy():
    # confidence must reflect scaffold quality, not return a constant.
    from llm_prompt_cold_start.synthesis import _cleanliness_score, _grounding_score

    assert _cleanliness_score(["climate targets", "emissions reduction", "governance"]) == 1.0
    assert _cleanliness_score(["usd", "tco", "year", "governance"]) < 1.0
    # graded grounding: weak support counts less than strong support
    assert _grounding_score(["x"], {"x": 1}, strong=3) < _grounding_score(["x"], {"x": 3}, strong=3)


def test_example_input_files_exist():
    assert (EXAMPLES / "questions.txt").exists()
    assert (EXAMPLES / "domain_knowledge.txt").exists()


def test_cli_demo_with_questions_and_domain_knowledge(tmp_path):
    out = tmp_path / "prompt.md"
    rc = cli_main(
        [
            str(SAMPLES),
            "--questions", str(EXAMPLES / "questions.txt"),
            "--domain-knowledge", str(EXAMPLES / "domain_knowledge.txt"),
            "--offline",
            "-o", str(out),
        ]
    )
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "# ROLE" in text and "# QUERY-TYPE PLAYBOOK" in text
    # a domain-knowledge line should be layered into the prompt context
    assert "sustainable finance" in text.lower()
