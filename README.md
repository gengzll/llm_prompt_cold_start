# llm_prompt_cold_start

Turn a **document corpus** into a **baseline `system` prompt** for a document-grounded
LLM / RAG application — even when you start cold, with no labeled Q&A and no hand-written
prompt.

You give it documents (PDF / TXT / MD / DOCX). Optionally you add a few sample questions
and/or some domain knowledge. It gives you back a ready-to-use system prompt containing
the role, domain knowledge, answer/format constraints, and a per-query-type playbook —
all **grounded in what is actually in your documents**, not in what a user guessed.

```
documents (+ optional questions, + optional domain knowledge)
        │
        ▼
   system prompt
```

## Why

Most teams adopting RAG have lots of documents but **no gold Q&A and no good starting
prompt**. They also often describe their own domain imprecisely. This tool extracts the
domain signal directly from the corpus so the baseline prompt does not depend on a
user's (possibly inaccurate) description.

The result is a *baseline*: not guaranteed optimal, but immediately usable and grounded.

## How it works

A small, explicit pipeline. Each stage is plain and inspectable.

| Stage | Module | What it does | Libraries |
|---|---|---|---|
| 1. Parse | `parsing.py` | Read pdf/txt/md/docx → text + detected section headings | `pymupdf` (PDF only, lazy) |
| 2. Analyze | `analysis.py` | Extract corpus evidence: keyphrases (TF/doc-freq), metric/unit patterns, doc-type, entity signals | stdlib only |
| 3. Synthesize | `synthesis.py` | Turn evidence (+ optional user input) into a Domain Pack | LLM, or deterministic fallback |
| 4. Query types | `synthesis.py` | Infer reusable query types from questions or from the corpus | LLM, or deterministic fallback |
| 5. Verify | `synthesis.py` | Count corpus support per concept; score confidence | stdlib only |
| 6. Build | `prompt_builder.py` | Assemble the final system prompt | stdlib only |

Key design choices:

- **Corpus-grounded, not user-dictated.** User-provided domain knowledge is treated as an
  optional *signal*, layered on top of evidence mined from the documents — it does not
  drive the content on its own.
- **The LLM synthesizes, it does not invent.** The synthesis prompt is constrained to the
  extracted evidence and forbidden from fabricating values, names, or claims. System and
  user roles are separated so the stable instruction/schema can be provider-cached.
- **Works offline with zero dependencies.** Without an API key (or with `--offline`), a
  deterministic fallback maps the mined evidence straight into the prompt. Great for
  testing, air-gapped use, and reproducibility.

## Install

No packaging/build step needed. Just clone and install the dependencies, then run the
CLI directly from the folder:

```bash
git clone https://github.com/gengzll/llm_prompt_cold_start.git
cd llm_prompt_cold_start
pip install -r requirements.txt
```

The **offline path needs none of these** — pure standard library (PDF input still needs
`pymupdf`).

> Prefer an installed console command? `pip install -e .` is still supported and gives you
> the `cold-start-prompt` entry point — but it is optional.

## Configure

```bash
cp .env.example .env
# set OPENAI_API_KEY, optionally OPENAI_BASE_URL (DeepSeek/Together/Ollama/...), COLD_START_MODEL
```

## Use

### CLI (run directly, no install)

From the project folder, use either the launcher script or the module form:

```bash
# Offline, no API key — grounded deterministic prompt
python cold_start.py ./examples/sample_docs --offline -o prompt.md

# Equivalent module form
python -m llm_prompt_cold_start.cli ./examples/sample_docs --offline -o prompt.md

# Online synthesis with sample questions + domain notes, also dump artifacts
python cold_start.py ./docs \
    --questions questions.txt \
    --domain-knowledge domain.txt \
    -o prompt.md --json result.json
```

(If you did `pip install -e .`, the same thing is available as `cold-start-prompt ...`.)

### Python

Run your script from the project folder (so `llm_prompt_cold_start/` is importable), or
add the project root to `sys.path` — see `examples/run_example.py`.

```python
from llm_prompt_cold_start import generate_system_prompt

prompt = generate_system_prompt(
    ["./docs"],
    questions=["What is the 2030 target?"],     # optional
    domain_knowledge=["Answer only from the documents."],  # optional
)
print(prompt)
```

For full artifacts (domain pack, query types, corpus profile, confidence):

```python
from llm_prompt_cold_start import ColdStartPipeline, Settings

settings = Settings.load()
settings.offline = True
result = ColdStartPipeline(settings).run(["./docs"])
print(result.confidence, [qt.name for qt in result.query_types])
```

### Try it now

```bash
python examples/run_example.py     # offline, uses bundled sample docs
```

## Output shape

The generated prompt has these sections:

```
# ROLE              role + domain specialization
# CONTEXT           what the corpus is / business context
# DOMAIN KNOWLEDGE  key concepts, entity types, metrics, answer-bearing sections, reasoning patterns
# ANSWER POLICY     grounding + citation + abstention + format constraints
# QUERY-TYPE PLAYBOOK   per query type: what to cover, how to answer, retrieval focus, risks
# TASK              {context} / {question} template to fill at runtime
```

## Status & roadmap

This is a clean first version. Deliberately minimal. Natural next steps:

- Better keyphrase extraction (`yake` / KeyBERT) and table-aware PDF parsing.
- Cross-document entity normalization and a co-occurrence graph (GraphRAG-style).
- Few-shot example selection from the corpus.
- Optional self-consistency on the synthesis step and richer confidence calibration.

## Tests

```bash
python -m pytest tests/ -q
```
