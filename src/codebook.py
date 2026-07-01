import os
from pathlib import Path

_PATH = Path(os.environ.get("GOVGAP_CODEBOOK_PATH", "prompts/codebook_prompt.md"))

SYSTEM_PROMPT = _PATH.read_text(encoding="utf-8")
