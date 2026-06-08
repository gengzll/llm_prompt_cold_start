from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings
from .pipeline import ColdStartPipeline


def _read_lines(path: str | None) -> list[str]:
    if not path:
        return []
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cold-start-prompt",
        description="Generate a baseline system prompt from a document corpus.",
    )
    parser.add_argument("docs", nargs="+", help="Document files or directories (pdf/txt/md/docx).")
    parser.add_argument("--questions", help="Optional text file with one sample question per line.")
    parser.add_argument("--domain-knowledge", help="Optional text file with one domain-knowledge note per line.")
    parser.add_argument("-o", "--out", help="Write the system prompt to this file (default: stdout).")
    parser.add_argument("--json", dest="json_out", help="Also write the full result (pack, query types, profile) as JSON here.")
    parser.add_argument("--offline", action="store_true", help="Force offline deterministic synthesis (no API calls).")
    args = parser.parse_args(argv)

    settings = Settings.load()
    if args.offline:
        settings.offline = True

    pipeline = ColdStartPipeline(settings)
    result = pipeline.run(
        args.docs,
        questions=_read_lines(args.questions),
        domain_knowledge=_read_lines(args.domain_knowledge),
    )

    if args.out:
        Path(args.out).write_text(result.system_prompt, encoding="utf-8")
        print(f"Wrote system prompt -> {args.out}", file=sys.stderr)
    else:
        print(result.system_prompt)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Wrote full result -> {args.json_out}", file=sys.stderr)

    for note in result.notes:
        print(f"[note] {note}", file=sys.stderr)
    print(f"[confidence] {result.confidence}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
