from __future__ import annotations

import json

from .schemas import METRIC_LABELS, AnswerPolicy, CorpusProfile, DomainPack, QueryType

# The DomainPack content fields that are synthesized (LLM or fallback), used for
# provenance tracking and the synthesis-completeness confidence signal.
_PACK_FIELDS = [
    "business_context",
    "high_level_topics",
    "key_concepts",
    "entity_types",
    "metrics",
    "document_sections",
    "reasoning_patterns",
    "risk_policies",
]

# --------------------------------------------------------------------------- #
# Domain pack synthesis
# --------------------------------------------------------------------------- #
_DOMAIN_SYSTEM = """You are a domain analyst building a reusable Domain Knowledge Pack \
for a document-grounded question-answering system.

You are given EVIDENCE that was automatically extracted from the corpus (keyphrases, \
section titles, detected metrics, document types) and OPTIONAL user-provided domain \
knowledge. Organize this into a clean, reusable knowledge pack.

Rules:
- Only use concepts grounded in the provided evidence or the user knowledge.
- Do NOT invent organization-specific facts, numeric values, names, or claims.
- Prefer higher-frequency evidence. If a field has weak evidence, keep it short.
- Keep every item concise (a short noun phrase or one clause).
- For key_concepts, fill `aliases` with REAL synonyms or abbreviations that appear
  in (or are standard for) the corpus, e.g. "emissions": ["GHG", "carbon", "tCO2e"].
  Only include genuine aliases; do not invent them. Aliases are optional.
- For metrics, describe the quantity in words (e.g. "monetary amounts",
  "percentages"); never output internal keys like "large_number".
- Output STRICTLY valid JSON matching the requested schema. No commentary."""

_DOMAIN_SCHEMA = """{
  "business_context": [string],        // what this corpus is and what users ask about
  "high_level_topics": [string],       // 4-8 broad themes
  "key_concepts": [string],            // concrete domain concepts/terms
  "aliases": {"concept": [string]},    // optional synonyms/abbreviations per key concept
  "entity_types": [string],            // kinds of entities (org, committee, metric, date...)
  "metrics": [string],                 // measurable quantities, in words (not internal keys)
  "document_sections": [string],       // section types likely to hold answers
  "reasoning_patterns": [string],      // e.g. extraction, comparison, policy interpretation
  "risk_policies": [string]            // answering rules / things to be careful about
}"""


def synthesize_domain_pack(
    profile: CorpusProfile,
    user_domain_knowledge: list[str],
    llm=None,
) -> DomainPack:
    """Build the domain pack. Uses the LLM when available, else a deterministic
    corpus-grounded fallback. Either way, evidence counts are attached and the
    result is verified against the corpus."""
    base = _deterministic_domain_pack(profile, user_domain_knowledge)
    base.provenance = {f: "fallback" for f in _PACK_FIELDS}
    if llm is None:
        return _attach_evidence(base, profile)

    user_msg = (
        f"EVIDENCE (auto-extracted from corpus):\n{profile.evidence_summary()}\n\n"
        f"USER-PROVIDED DOMAIN KNOWLEDGE (optional, may be empty):\n"
        f"{chr(10).join('- ' + x for x in user_domain_knowledge) or '(none)'}\n\n"
        f"SAMPLE EXCERPTS:\n{chr(10).join(profile.sample_excerpts[:5])}\n\n"
        f"Return JSON with this schema:\n{_DOMAIN_SCHEMA}"
    )
    try:
        data = llm.complete_json(_DOMAIN_SYSTEM, user_msg)
    except Exception:
        return _attach_evidence(base, profile)  # provenance already all-fallback

    # Merge LLM output over the deterministic base, recording, per field, whether
    # the value came from the LLM or silently fell back to the heuristic. The
    # fallback is no longer invisible: it shows up as lower synthesis provenance.
    base_values = {
        "business_context": base.business_context,
        "high_level_topics": base.high_level_topics,
        "key_concepts": base.key_concepts,
        "entity_types": base.entity_types,
        "metrics": base.metrics,
        "document_sections": base.document_sections,
        "reasoning_patterns": base.reasoning_patterns,
        "risk_policies": base.risk_policies,
    }
    merged = DomainPack(answer_policy=base.answer_policy)
    for fname in _PACK_FIELDS:
        value, source = _pick_with_source(data.get(fname), base_values[fname])
        setattr(merged, fname, value)
        merged.provenance[fname] = source
    merged.aliases = _normalize_aliases(data.get("aliases"))
    return _attach_evidence(merged, profile)


def _normalize_aliases(raw) -> dict[str, list[str]]:
    """Coerce the LLM `aliases` object into {concept: [alias, ...]} with cleaning."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for concept, al in raw.items():
        key = str(concept).strip()
        # drop self-aliases ("financial ratios" -> "financial ratios") and dups
        terms = list(dict.fromkeys(t for t in _as_list(al) if t.lower() != key.lower()))
        if key and terms:
            out[key] = terms
    return out


def _deterministic_domain_pack(profile: CorpusProfile, user_dk: list[str]) -> DomainPack:
    """Map the extracted evidence directly into a domain pack, no LLM."""
    top_phrases = [p for p, _ in profile.keyphrases]
    doc_type_names = list(profile.doc_types.keys())

    business = [
        f"Document-grounded question answering over: {', '.join(doc_type_names) or 'mixed documents'}."
    ]
    business += [u for u in user_dk if u]

    reasoning = ["evidence lookup", "summarization"]
    metric_names = [m for m, _ in profile.metrics]
    if any(m in metric_names for m in ("percentage", "currency", "large_number", "physical_unit", "emissions_unit")):
        reasoning += ["numeric extraction", "comparison"]
    if "policy_or_governance" in profile.doc_types or any("policy" in p for p in top_phrases):
        reasoning.append("policy interpretation")

    risk = [
        "Answer only from the provided documents.",
        "If evidence is missing, say so explicitly instead of guessing.",
        "Do not invent values, dates, or names.",
    ]

    return DomainPack(
        business_context=_dedupe(business),
        high_level_topics=_dedupe(top_phrases[:8]),
        key_concepts=_dedupe(top_phrases[:20]),
        entity_types=_dedupe(list(profile.entity_hints.keys()) or ["organization", "date", "metric"]),
        metrics=_dedupe(_humanize_metrics(metric_names)),
        document_sections=_dedupe([s for s, _ in profile.section_titles][:12]),
        reasoning_patterns=_dedupe(reasoning),
        risk_policies=_dedupe(risk),
        answer_policy=AnswerPolicy(),
    )


def _humanize_metrics(metric_keys: list[str]) -> list[str]:
    return [METRIC_LABELS.get(k, k) for k in metric_keys]


# --------------------------------------------------------------------------- #
# Query-type inference
# --------------------------------------------------------------------------- #
_QTYPE_SYSTEM = """You infer reusable QUERY TYPES for a document-grounded QA system.

A query type is a reusable category of question (not a single question). For each, \
give the evidence dimensions an answer must cover, answer guidance, retrieval guidance, \
and risk flags. Base everything on the domain pack and the sample questions if provided. \
Do not invent corpus-specific facts. Output STRICTLY valid JSON. No commentary."""

_QTYPE_SCHEMA = """{
  "query_types": [
    {
      "name": "snake_case_name",
      "description": string,
      "expected_evidence_dimensions": [string],
      "answer_guidance": [string],
      "retrieval_guidance": [string],
      "risk_flags": [string]
    }
  ]
}"""


def infer_query_types(
    domain_pack: DomainPack,
    user_questions: list[str],
    llm=None,
) -> list[QueryType]:
    base = _deterministic_query_types(domain_pack, user_questions)
    if llm is None:
        return base

    user_msg = (
        f"DOMAIN PACK:\n{json.dumps(_pack_brief(domain_pack), ensure_ascii=False, indent=2)}\n\n"
        f"SAMPLE QUESTIONS (optional, may be empty):\n"
        f"{chr(10).join('- ' + q for q in user_questions) or '(none provided — infer from the domain pack)'}\n\n"
        f"Return 3-6 query types as JSON:\n{_QTYPE_SCHEMA}"
    )
    try:
        data = llm.complete_json(_QTYPE_SYSTEM, user_msg)
    except Exception:
        return base

    out: list[QueryType] = []
    for item in data.get("query_types", []) or []:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        out.append(
            QueryType(
                name=name,
                description=str(item.get("description", "")),
                expected_evidence_dimensions=_as_list(item.get("expected_evidence_dimensions")),
                answer_guidance=_as_list(item.get("answer_guidance")),
                retrieval_guidance=_as_list(item.get("retrieval_guidance")),
                risk_flags=_as_list(item.get("risk_flags")),
            )
        )
    if not out:
        return base
    # Always keep the unanswerable/insufficient-evidence guard, like the
    # deterministic path does, even if the model didn't produce one.
    if not any(qt.name == "insufficient_evidence" for qt in out):
        out.append(_default_query_catalog()["insufficient_evidence"])
    return out


def _deterministic_query_types(domain_pack: DomainPack, questions: list[str]) -> list[QueryType]:
    """Infer query types from question keywords, or from the domain pack signals."""
    catalog = _default_query_catalog()
    chosen: dict[str, QueryType] = {}

    if questions:
        for q in questions:
            key = _bucket_question(q)
            chosen[key] = catalog[key]
    else:
        # No questions: infer plausible types from the domain pack.
        patterns = " ".join(domain_pack.reasoning_patterns).lower()
        if "extraction" in patterns or domain_pack.metrics:
            chosen["fact_extraction"] = catalog["fact_extraction"]
        if "comparison" in patterns:
            chosen["comparison"] = catalog["comparison"]
        if "policy" in patterns:
            chosen["policy_interpretation"] = catalog["policy_interpretation"]
        chosen["summary"] = catalog["summary"]
        chosen["evidence_lookup"] = catalog["evidence_lookup"]

    # Always include an unanswerable/insufficient-evidence guard.
    chosen["insufficient_evidence"] = catalog["insufficient_evidence"]
    return list(chosen.values())


def _bucket_question(q: str) -> str:
    low = q.lower()
    if any(w in low for w in ("compare", "versus", " vs ", "difference", "change from", "year-over-year", "yoy")):
        return "comparison"
    if any(w in low for w in ("who", "which committee", "responsible", "chair", "officer", "role")):
        return "evidence_lookup"
    if any(w in low for w in ("policy", "rule", "required", "regulation", "must", "shall", "allowed")):
        return "policy_interpretation"
    if any(w in low for w in ("summarize", "summary", "overview", "describe", "explain")):
        return "summary"
    if any(w in low for w in ("how much", "how many", "what is the", "target", "rate", "amount", "value", "when")):
        return "fact_extraction"
    return "evidence_lookup"


def _default_query_catalog() -> dict[str, QueryType]:
    return {
        "fact_extraction": QueryType(
            name="fact_extraction",
            description="Extract a specific value, target, date, or named fact from the documents.",
            expected_evidence_dimensions=["the specific value/target", "unit or scope", "time period", "source location"],
            answer_guidance=["State the exact value with its unit and period.", "Cite the source.", "If unavailable, say so."],
            retrieval_guidance=["Prefer tables and metric-bearing sections.", "Match the exact entity and period."],
            risk_flags=["Do not confuse similar metrics or periods.", "Do not interpolate missing values."],
        ),
        "comparison": QueryType(
            name="comparison",
            description="Compare values across time periods, entities, or categories.",
            expected_evidence_dimensions=["both compared values", "time/entity of each", "unit consistency"],
            answer_guidance=["Give both values, then the difference.", "Only compare like-for-like (same unit/basis)."],
            retrieval_guidance=["Retrieve both sides of the comparison.", "Watch for restated figures."],
            risk_flags=["Do not compare across inconsistent units or definitions."],
        ),
        "policy_interpretation": QueryType(
            name="policy_interpretation",
            description="Explain a policy, rule, requirement, or procedure stated in the documents.",
            expected_evidence_dimensions=["the relevant clause", "scope/applicability", "conditions or exceptions"],
            answer_guidance=["Quote or closely paraphrase the source clause.", "Note the section it comes from."],
            retrieval_guidance=["Prefer policy/governance sections.", "Retrieve the full clause, not a fragment."],
            risk_flags=["Do not extend interpretation beyond the documents."],
        ),
        "summary": QueryType(
            name="summary",
            description="Summarize a topic, section, or document at a requested level of detail.",
            expected_evidence_dimensions=["main points", "supporting specifics", "scope of the summary"],
            answer_guidance=["Cover the key points without inventing detail.", "Stay within the requested scope."],
            retrieval_guidance=["Retrieve the relevant section(s) broadly."],
            risk_flags=["Do not over-generalize or add outside knowledge."],
        ),
        "evidence_lookup": QueryType(
            name="evidence_lookup",
            description="Locate who/what/where information grounded in a specific passage.",
            expected_evidence_dimensions=["the named entity/answer", "the supporting passage"],
            answer_guidance=["Answer directly and cite the passage."],
            retrieval_guidance=["Match entity names and synonyms."],
            risk_flags=["Information may be outdated; note dates where relevant."],
        ),
        "insufficient_evidence": QueryType(
            name="insufficient_evidence",
            description="Questions the corpus cannot answer or only partially supports.",
            expected_evidence_dimensions=["what is present", "what is missing"],
            answer_guidance=["State clearly what the documents do and do not support.", "Offer the partial answer if any."],
            retrieval_guidance=["Confirm absence by checking the most likely sections."],
            risk_flags=["Do not fabricate an answer to seem helpful."],
        ),
    }


# --------------------------------------------------------------------------- #
# Reverse verification: count corpus support for each pack concept.
# --------------------------------------------------------------------------- #
def _attach_evidence(pack: DomainPack, profile: CorpusProfile) -> DomainPack:
    evidence: dict[str, int] = {}
    for concept in pack.key_concepts + pack.high_level_topics:
        evidence[concept] = _concept_support(concept, profile.keyphrases)
    pack.evidence = evidence
    return pack


def _concept_support(concept: str, keyphrases: list[tuple[str, int]]) -> int:
    """Corpus support for a concept, matched loosely against the keyphrases.

    Uses substring (either direction) or a shared significant token, so a
    cleaned/paraphrased concept like "Sustainability Committee" still matches
    the raw keyphrase "committee". Returns the strongest matching count.
    """
    c = concept.lower().strip()
    if not c:
        return 0
    c_tokens = {t for t in c.split() if len(t) >= 4}
    best = 0
    for phrase, count in keyphrases:
        p = phrase.lower()
        if c == p or c in p or p in c or (c_tokens & set(p.split())):
            best = max(best, count)
    return best


def compute_confidence(
    pack: DomainPack,
    profile: CorpusProfile,
    query_types: list[QueryType] | None = None,
) -> float:
    """Coarse 0-1 confidence that the generated scaffold is reliable.

    Six signals (weights sum to 1.0). The last two are what let a genuine LLM
    scaffold rank above the deterministic one: they reward richer synthesis and
    corpus-specific query types, instead of rewarding verbatim corpus echoing
    (which the offline heuristic does trivially well).

    - grounding   (0.25): how strongly key concepts are attested in the corpus,
                          graded by support count (not present/absent).
    - cleanliness (0.20): fraction of key concepts that look like real domain
                          terms rather than tokenizer noise ("usd", "tco").
    - synthesis   (0.20): fraction of pack fields actually produced by the LLM
                          rather than fallen back to the heuristic. 0 for offline;
                          a silent fallback (LLM omitting a field) lowers it.
    - specificity (0.20): fraction of query types that are corpus-specific rather
                          than generic catalog templates. 0 for offline.
    - corpus_size (0.05): more documents / more text -> more reliable.
    - sections    (0.10): presence of parsed section structure.

    Note: `synthesis` encodes the prior that LLM synthesis is more trustworthy
    than the deterministic fallback for this task; the other signals are
    observable quality measures.
    """
    if profile.n_documents == 0:
        return 0.0
    concepts = pack.key_concepts or []
    # Keyphrase counts are document frequencies (<= n_documents), so "fully
    # grounded" must be reachable on small corpora. Cap the threshold at n_docs.
    strong = max(1, min(3, profile.n_documents))
    grounding = _grounding_score(concepts, pack.evidence, strong=strong)
    cleanliness = _cleanliness_score(concepts)
    synthesis = _synthesis_score(pack)
    specificity = _query_type_specificity(query_types or [])
    corpus_size = min(1.0, profile.n_documents / 5) * min(1.0, profile.n_chars / 20000)
    section_signal = 1.0 if profile.section_titles else 0.5
    score = (
        0.25 * grounding
        + 0.20 * cleanliness
        + 0.20 * synthesis
        + 0.20 * specificity
        + 0.05 * corpus_size
        + 0.10 * section_signal
    )
    return round(score, 2)


def _synthesis_score(pack: DomainPack) -> float:
    """Fraction of pack fields actually produced by the LLM (vs deterministic
    fallback). 0.0 when there is no provenance (pure offline)."""
    if not pack.provenance:
        return 0.0
    llm = sum(1 for f in _PACK_FIELDS if pack.provenance.get(f) == "llm")
    return llm / len(_PACK_FIELDS)


def _query_type_specificity(query_types: list[QueryType]) -> float:
    """Fraction of query types that are corpus-specific rather than generic catalog
    templates. The always-present `insufficient_evidence` guard is ignored."""
    generic = set(_default_query_catalog().keys())
    scored = [qt for qt in query_types if qt.name != "insufficient_evidence"]
    if not scored:
        return 0.0
    specific = sum(1 for qt in scored if qt.name not in generic)
    return specific / len(scored)


def _grounding_score(concepts: list[str], evidence: dict[str, int], strong: int = 3) -> float:
    """Mean grounding strength. A concept needs `strong` supporting occurrences to
    count fully; weakly attested concepts contribute proportionally less."""
    if not concepts:
        return 0.0
    return sum(min(1.0, evidence.get(c, 0) / strong) for c in concepts) / len(concepts)


def _cleanliness_score(concepts: list[str]) -> float:
    """Fraction of concepts that look like genuine domain terms. Penalizes tokenizer
    noise such as 'usd', 'tco', 'year', or bare numbers/codes."""
    if not concepts:
        return 1.0
    return sum(1 for c in concepts if _looks_like_term(c)) / len(concepts)


def _looks_like_term(concept: str) -> bool:
    c = concept.strip().lower()
    if not c:
        return False
    if " " in c:  # multi-word phrase -> specific, keep
        return True
    if any(ch.isdigit() for ch in c):  # bare numbers / codes -> noise
        return False
    return len(c) >= 5  # a single word must be reasonably long to count as a term


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def _pack_brief(pack: DomainPack) -> dict:
    return {
        "business_context": pack.business_context,
        "high_level_topics": pack.high_level_topics,
        "key_concepts": pack.key_concepts[:15],
        "metrics": pack.metrics,
        "document_sections": pack.document_sections,
        "reasoning_patterns": pack.reasoning_patterns,
    }


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _pick(primary, fallback) -> list[str]:
    cleaned = _as_list(primary)
    return cleaned or fallback


def _pick_with_source(primary, fallback) -> tuple[list[str], str]:
    """Like ``_pick`` but also report whether the value came from the LLM
    (``"llm"``) or fell back to the deterministic heuristic (``"fallback"``)."""
    cleaned = _as_list(primary)
    if cleaned:
        return cleaned, "llm"
    return fallback, "fallback"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if not it:
            continue
        key = it.lower()
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out
