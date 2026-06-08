#!/usr/bin/env python
"""Root launcher so you can run the tool directly without installing it:

    python cold_start.py ./docs --offline -o prompt.md

This is just a thin wrapper around llm_prompt_cold_start.cli:main, which you can
also call as:  python -m llm_prompt_cold_start.cli ...
"""

from llm_prompt_cold_start.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
