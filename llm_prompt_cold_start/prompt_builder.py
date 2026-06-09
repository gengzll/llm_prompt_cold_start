from __future__ import annotations

from .schemas import AnswerPolicy, DomainPack, QueryType


def build_system_prompt(
    domain_pack: DomainPack,
    query_types: list[QueryType],
    *,
    include_playbook: bool = True,
) -> str:
    """Render a baseline system prompt from the synthesized knowledge.

    The output is plain text designed to be dropped straight into the
    ``system`` message of a document-grounded QA / RAG application.
    """
    p = domain_pack
    out: list[str] = []

    # 1) Role & domain ------------------------------------------------------- #
    role_domain = ", ".join(p.high_level_topics[:6]) or "the provided documents"
    out.append("# ROLE")
    out.append(
        f"You are a precise, document-grounded assistant specialized in {role_domain}. "
        "You answer questions strictly using the retrieved document context provided at query time."
    )
    if p.business_context:
        out.append("")
        out.append("# CONTEXT")
        out.extend(f"- {c}" for c in p.business_context)

    # 2) Domain knowledge: compact reference vocabulary, NOT instructions. ---- #
    # Inline (comma-separated) so the model reads it as terminology to recognize,
    # not a checklist to execute. Entity types and reasoning patterns are omitted
    # here on purpose: the former is generic, the latter duplicates the playbook.
    out.append("")
    out.append("# DOMAIN KNOWLEDGE")
    _inline_kv(out, "Vocabulary", _format_vocabulary(p.key_concepts[:18], p.aliases), sep="; ")
    _inline_kv(out, "Quantities you'll see", p.metrics)
    _inline_kv(out, "Where answers live", p.document_sections[:12])

    # 3) Answer policy (format & grounding constraints) ---------------------- #
    out.append("")
    out.append("# ANSWER POLICY")
    out.extend(_render_policy(p.answer_policy, p.risk_policies))

    # 4) Query-type playbook ------------------------------------------------- #
    if include_playbook and query_types:
        out.append("")
        out.append("# QUERY-TYPE PLAYBOOK")
        out.append("Identify the question's type, then follow the matching guidance:")
        for qt in query_types:
            out.append("")
            out.append(f"## {qt.name}")
            if qt.description:
                out.append(qt.description)
            _inline_block(out, "Must cover", qt.expected_evidence_dimensions)
            _inline_block(out, "How to answer", qt.answer_guidance)
            _inline_block(out, "Retrieval focus", qt.retrieval_guidance)
            _inline_block(out, "Watch out for", qt.risk_flags)

    # 5) Task template ------------------------------------------------------- #
    out.append("")
    out.append("# TASK")
    out.append("Use ONLY the context below to answer the user's question.")
    out.append("")
    out.append("Context:")
    out.append("{context}")
    out.append("")
    out.append("Question:")
    out.append("{question}")

    return "\n".join(out).strip() + "\n"


def _render_policy(policy: AnswerPolicy, risk_policies: list[str]) -> list[str]:
    lines: list[str] = []
    if policy.citation_required:
        lines.append("- Cite the supporting context for every factual claim.")
    if not policy.external_knowledge_allowed:
        lines.append("- Use only the provided context. Do not rely on outside or prior knowledge.")
    if policy.state_missing_evidence:
        lines.append("- If the context does not contain the answer, say so explicitly.")
    if policy.partial_answer_allowed:
        lines.append("- A partial answer is acceptable; clearly mark what is and isn't supported.")
    else:
        lines.append("- Do not give partial answers; answer fully or state that you cannot.")
    lines.append("- Never invent values, dates, names, or citations.")
    for rp in risk_policies:
        # avoid duplicating the generic rules already emitted above
        if rp.strip().rstrip(".").lower() not in {l.strip("- ").rstrip(".").lower() for l in lines}:
            lines.append(f"- {rp}")
    return lines


def _format_vocabulary(concepts: list[str], aliases: dict[str, list[str]]) -> list[str]:
    """Render concepts as a glossary, attaching synonyms when known:
    "emissions (aka GHG, carbon)". Bare term when there are no aliases."""
    out: list[str] = []
    for c in concepts:
        al = (aliases or {}).get(c)
        out.append(f"{c} (aka {', '.join(al)})" if al else c)
    return out


def _inline_kv(out: list[str], label: str, items: list[str], sep: str = ", ") -> None:
    cleaned = [it for it in items if it]
    if cleaned:
        out.append("")
        out.append(f"{label}: {sep.join(cleaned)}")


def _inline_block(out: list[str], label: str, items: list[str]) -> None:
    if items:
        out.append(f"- {label}: {'; '.join(items)}")
