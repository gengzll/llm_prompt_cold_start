from __future__ import annotations

import re
from collections import Counter

from .schemas import CorpusProfile, Document

# A compact English stopword set (kept inline to avoid a dependency).
STOPWORDS = set(
    """a an the and or but if then else for to of in on at by with without within from into
    over under again further once here there all any both each few more most other some such no
    nor not only own same so than too very can will just should now is are was were be been being
    have has had do does did doing this that these those it its as we you they he she them his her
    our your their which who whom what when where why how about above below up down out off above
    per via etc may might must shall would could also which whose between among during before after
    against through toward towards upon across whereas while whether amongst regarding concerning
    page table figure section chapter report based using used use including include includes""".split()
)

# regex patterns that flag the presence of "answer-grade" facts in a corpus.
_PATTERNS: dict[str, re.Pattern] = {
    "percentage": re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%"),
    "currency": re.compile(r"(?:[$€£¥]|USD|EUR|RMB|CNY)\s?\d", re.IGNORECASE),
    "year": re.compile(r"\b(?:19|20)\d{2}\b"),
    "date": re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    "emissions_unit": re.compile(r"\b(?:tco2e?|co2e?|ghg|mtco2)\b", re.IGNORECASE),
    "physical_unit": re.compile(r"\b\d+(?:\.\d+)?\s?(?:kg|tonnes?|tons?|mw|gwh|kwh|km|m2|ha)\b", re.IGNORECASE),
    "large_number": re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b"),
}

# doc-type heuristics: type -> trigger terms (lowercased substring match).
_DOC_TYPE_TRIGGERS: dict[str, list[str]] = {
    "annual_report": ["annual report", "10-k", "form 10", "fiscal year", "shareholder"],
    "esg_sustainability": ["esg", "sustainability", "scope 1", "scope 2", "scope 3", "emissions", "net zero", "carbon"],
    "policy_or_governance": ["policy", "governance", "committee", "board of directors", "compliance", "code of conduct"],
    "legal_contract": ["agreement", "hereby", "party", "clause", "terms and conditions", "shall be"],
    "manual_or_sop": ["procedure", "manual", "step 1", "instructions", "standard operating", "guideline"],
    "financial_statement": ["balance sheet", "income statement", "cash flow", "consolidated", "audit"],
    "research_or_technical": ["abstract", "methodology", "experiment", "hypothesis", "we propose", "results show"],
}

# entity-signal heuristics: label -> trigger terms.
_ENTITY_TRIGGERS: dict[str, list[str]] = {
    "organization": ["inc", "ltd", "corp", "company", "group", "委员会", "公司"],
    "committee_or_role": ["committee", "officer", "chair", "director", "ceo", "cfo"],
    "metric": ["target", "rate", "ratio", "kpi", "metric", "index"],
    "date_or_period": ["fiscal", "quarter", "year ended", "as of"],
    "policy_or_regulation": ["regulation", "standard", "framework", "disclosure", "requirement"],
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]{1,}")


def build_corpus_profile(docs: list[Document], max_keyphrases: int = 40) -> CorpusProfile:
    """Aggregate per-document signals into a single corpus-level profile."""
    n_docs = len(docs)
    full_lower = "\n".join(d.text for d in docs).lower()

    return CorpusProfile(
        n_documents=n_docs,
        n_chars=sum(len(d.text) for d in docs),
        doc_types=_classify_doc_types(docs),
        keyphrases=_keyphrases(docs, max_keyphrases),
        section_titles=_aggregate_sections(docs),
        metrics=_detect_metrics(full_lower),
        entity_hints=_detect_entities(full_lower),
        sample_excerpts=_sample_excerpts(docs),
    )


# --------------------------------------------------------------------------- #
# Keyphrases: n-gram document-frequency with stopword/boilerplate filtering.
# Document frequency (how many docs contain a phrase) is more robust for
# "corpus-level concepts" than raw term count in a single long document.
# --------------------------------------------------------------------------- #
def _keyphrases(docs: list[Document], top_n: int) -> list[tuple[str, int]]:
    df: Counter[str] = Counter()
    tf: Counter[str] = Counter()
    for doc in docs:
        seen: set[str] = set()
        for phrase in _candidate_phrases(doc.text):
            tf[phrase] += 1
            if phrase not in seen:
                df[phrase] += 1
                seen.add(phrase)
    n_docs = max(1, len(docs))

    scored: list[tuple[str, int, float]] = []
    for phrase, doc_freq in df.items():
        if tf[phrase] < 2 and n_docs > 1:
            continue  # drop hapax noise unless single-doc corpus
        # prefer phrases that are frequent AND spread across documents,
        # with a mild bonus for multi-word (more specific) phrases.
        specificity = 1.0 + 0.3 * (phrase.count(" "))
        score = doc_freq * specificity + 0.1 * tf[phrase]
        scored.append((phrase, doc_freq, score))

    scored.sort(key=lambda x: x[2], reverse=True)
    return _collapse_subphrases([(p, c) for p, c, _ in scored], top_n)


def _collapse_subphrases(ranked: list[tuple[str, int]], top_n: int) -> list[tuple[str, int]]:
    """Drop lower-ranked phrases that are a contiguous token-substring of an
    already-kept phrase (or vice versa), e.g. keep "anonymous reporting channel"
    and drop "anonymous reporting" / "reporting channel"."""
    kept: list[tuple[str, int]] = []
    for phrase, count in ranked:
        if any(_token_overlap(phrase, k) for k, _ in kept):
            continue
        kept.append((phrase, count))
        if len(kept) >= top_n:
            break
    return kept


def _token_overlap(a: str, b: str) -> bool:
    pa = f" {a} "
    pb = f" {b} "
    return pa in pb or pb in pa


def _candidate_phrases(text: str):
    for sentence in re.split(r"[.\n;!?]", text):
        tokens = [t.lower() for t in _WORD_RE.findall(sentence)]
        # build 1- to 3-grams that do not start/end on a stopword
        n = len(tokens)
        for size in (1, 2, 3):
            for i in range(n - size + 1):
                gram = tokens[i : i + size]
                if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
                    continue
                if any(len(w) < 2 for w in gram):
                    continue
                yield " ".join(gram)


# --------------------------------------------------------------------------- #
# Sections, metrics, entities, doc types
# --------------------------------------------------------------------------- #
def _aggregate_sections(docs: list[Document]) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for doc in docs:
        for title in doc.sections:
            counter[title.strip()] += 1
    return counter.most_common(30)


def _detect_metrics(full_lower: str) -> list[tuple[str, int]]:
    counts: list[tuple[str, int]] = []
    for name, pattern in _PATTERNS.items():
        hits = len(pattern.findall(full_lower))
        if hits:
            counts.append((name, hits))
    counts.sort(key=lambda x: x[1], reverse=True)
    return counts


def _detect_entities(full_lower: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for label, triggers in _ENTITY_TRIGGERS.items():
        score = sum(full_lower.count(t) for t in triggers)
        if score:
            out[label] = score
    return dict(sorted(out.items(), key=lambda x: x[1], reverse=True))


def _classify_doc_types(docs: list[Document]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for doc in docs:
        low = doc.text.lower()
        best, best_score = "general_document", 0
        for dtype, triggers in _DOC_TYPE_TRIGGERS.items():
            score = sum(low.count(t) for t in triggers)
            if score > best_score:
                best, best_score = dtype, score
        counter[best] += 1
    return dict(counter.most_common())


def _sample_excerpts(docs: list[Document], per_doc: int = 1, max_chars: int = 600) -> list[str]:
    """A few representative excerpts (start of each doc) for the synthesis step."""
    out: list[str] = []
    for doc in docs[:8]:
        snippet = doc.text.strip().replace("\n", " ")
        if snippet:
            out.append(f"[{doc.name}] {snippet[:max_chars]}")
    return out
