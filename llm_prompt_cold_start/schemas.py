from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Human-readable labels for the internal metric/unit pattern keys. Used at
# display time (prompt + evidence digest) so the LLM never sees raw keys like
# "large_number" and echoes them back into the prompt.
METRIC_LABELS = {
    "percentage": "percentages / rates",
    "currency": "monetary amounts",
    "year": "years / fiscal periods",
    "date": "dates",
    "emissions_unit": "emissions (tCO2e / GHG)",
    "physical_unit": "physical quantities (energy, mass, area)",
    "large_number": "large numeric figures",
}


def humanize_metric(name: str) -> str:
    return METRIC_LABELS.get(name, name)


# --------------------------------------------------------------------------- #
# Parsing layer
# --------------------------------------------------------------------------- #
@dataclass
class Document:
    """A single parsed source document."""

    name: str
    text: str
    n_pages: int = 0
    sections: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Analysis layer (corpus-level extracted evidence)
# --------------------------------------------------------------------------- #
@dataclass
class CorpusProfile:
    """Aggregated, corpus-level signals extracted WITHOUT any LLM.

    This is the evidence that constrains the synthesis step so the generated
    prompt is grounded in what is actually present in the documents.
    """

    n_documents: int = 0
    n_chars: int = 0
    doc_types: dict[str, int] = field(default_factory=dict)
    # (value, count) pairs, sorted by relevance/frequency, most useful first.
    keyphrases: list[tuple[str, int]] = field(default_factory=list)
    section_titles: list[tuple[str, int]] = field(default_factory=list)
    metrics: list[tuple[str, int]] = field(default_factory=list)
    entity_hints: dict[str, int] = field(default_factory=dict)
    sample_excerpts: list[str] = field(default_factory=list)

    def evidence_summary(self, top: int = 25) -> str:
        """A compact, human/LLM-readable digest of the evidence."""

        def fmt(pairs: list[tuple[str, int]], n: int) -> str:
            return ", ".join(f"{v} ({c})" for v, c in pairs[:n]) or "(none)"

        types = ", ".join(f"{k} ({v})" for k, v in self.doc_types.items()) or "(unknown)"
        ents = ", ".join(f"{k} ({v})" for k, v in self.entity_hints.items()) or "(none)"
        metrics = ", ".join(f"{humanize_metric(v)} ({c})" for v, c in self.metrics[:top]) or "(none)"
        return (
            f"Documents: {self.n_documents}\n"
            f"Document types: {types}\n"
            f"Top keyphrases: {fmt(self.keyphrases, top)}\n"
            f"Section titles: {fmt(self.section_titles, top)}\n"
            f"Detected metrics/units: {metrics}\n"
            f"Entity signals: {ents}"
        )


# --------------------------------------------------------------------------- #
# Synthesis layer (the reusable knowledge the prompt is built from)
# --------------------------------------------------------------------------- #
@dataclass
class AnswerPolicy:
    citation_required: bool = True
    external_knowledge_allowed: bool = False
    partial_answer_allowed: bool = True
    state_missing_evidence: bool = True


@dataclass
class DomainPack:
    business_context: list[str] = field(default_factory=list)
    high_level_topics: list[str] = field(default_factory=list)
    key_concepts: list[str] = field(default_factory=list)
    entity_types: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    document_sections: list[str] = field(default_factory=list)
    reasoning_patterns: list[str] = field(default_factory=list)
    risk_policies: list[str] = field(default_factory=list)
    answer_policy: AnswerPolicy = field(default_factory=AnswerPolicy)
    # key concept -> synonyms/abbreviations found in the corpus (LLM-only; helps
    # map user phrasing to corpus terms). Empty in offline mode.
    aliases: dict[str, list[str]] = field(default_factory=dict)
    # concept -> number of documents/occurrences supporting it (reverse-verified)
    evidence: dict[str, int] = field(default_factory=dict)
    # field name -> "llm" | "fallback": which fields the LLM actually produced
    # vs. which silently fell back to the deterministic heuristic.
    provenance: dict[str, str] = field(default_factory=dict)


@dataclass
class QueryType:
    name: str
    description: str = ""
    expected_evidence_dimensions: list[str] = field(default_factory=list)
    answer_guidance: list[str] = field(default_factory=list)
    retrieval_guidance: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Final result
# --------------------------------------------------------------------------- #
@dataclass
class ColdStartResult:
    system_prompt: str
    domain_pack: DomainPack
    query_types: list[QueryType]
    corpus_profile: CorpusProfile
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)
