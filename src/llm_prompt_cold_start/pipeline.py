from __future__ import annotations

from pathlib import Path

from .analysis import build_corpus_profile
from .config import Settings
from .llm import build_llm
from .parsing import load_documents
from .prompt_builder import build_system_prompt
from .schemas import AnswerPolicy, ColdStartResult
from .synthesis import (
    compute_confidence,
    infer_query_types,
    synthesize_domain_pack,
)


class ColdStartPipeline:
    """End-to-end: documents -> corpus profile -> domain pack + query types -> prompt."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.load()
        self.llm = build_llm(self.settings)

    def run(
        self,
        doc_paths: list[str | Path],
        *,
        questions: list[str] | None = None,
        domain_knowledge: list[str] | None = None,
        answer_policy: AnswerPolicy | None = None,
    ) -> ColdStartResult:
        questions = [q.strip() for q in (questions or []) if q.strip()]
        domain_knowledge = [d.strip() for d in (domain_knowledge or []) if d.strip()]
        notes: list[str] = []

        # 1) parse
        docs = load_documents(doc_paths)
        if not docs:
            raise ValueError("No readable documents found in the given paths.")
        notes.append(f"Parsed {len(docs)} document(s).")

        # 2) analyze -> corpus profile (evidence)
        profile = build_corpus_profile(docs)

        # 3) synthesize domain pack (LLM or deterministic fallback)
        pack = synthesize_domain_pack(profile, domain_knowledge, llm=self.llm)
        if answer_policy is not None:
            pack.answer_policy = answer_policy
        notes.append("Synthesis mode: " + ("LLM" if self.llm else "offline (deterministic)"))

        # 4) infer query types
        query_types = infer_query_types(pack, questions, llm=self.llm)

        # 5) verify + score
        confidence = compute_confidence(pack, profile)
        if confidence < 0.5:
            notes.append("Low confidence: corpus is small or weakly grounded; review the prompt before use.")

        # 6) build the system prompt
        system_prompt = build_system_prompt(pack, query_types)

        return ColdStartResult(
            system_prompt=system_prompt,
            domain_pack=pack,
            query_types=query_types,
            corpus_profile=profile,
            confidence=confidence,
            notes=notes,
        )


def generate_system_prompt(
    doc_paths: list[str | Path],
    *,
    questions: list[str] | None = None,
    domain_knowledge: list[str] | None = None,
    settings: Settings | None = None,
) -> str:
    """Convenience one-shot API returning just the prompt string."""
    result = ColdStartPipeline(settings).run(
        doc_paths, questions=questions, domain_knowledge=domain_knowledge
    )
    return result.system_prompt
