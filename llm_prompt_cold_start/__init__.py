"""Cold-start system-prompt generator.

Turn a document corpus (plus optional questions and domain knowledge) into a
baseline ``system`` prompt for a document-grounded LLM/RAG application.
"""

from .config import Settings
from .pipeline import ColdStartPipeline, generate_system_prompt
from .schemas import (
    AnswerPolicy,
    ColdStartResult,
    CorpusProfile,
    DomainPack,
    QueryType,
)

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "ColdStartPipeline",
    "generate_system_prompt",
    "ColdStartResult",
    "CorpusProfile",
    "DomainPack",
    "QueryType",
    "AnswerPolicy",
]
