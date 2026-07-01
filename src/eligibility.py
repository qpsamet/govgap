"""Eligibility gate.

A focused LLM classifier that decides whether a document is in scope for the
framework before any coding happens. It encodes the corpus inclusion and
exclusion criteria, so it rejects level-mismatch documents (the EU AI Act,
NIST, ISO) and non-binding advisory guidance (OWASP) with a stated reason
instead of letting the coder fabricate six Gaps on an out-of-scope document.
"""
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from json_repair import repair_json
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from .schema import EligibilityVerdict

load_dotenv()


_PROMPT_PATH = Path(
    os.environ.get("GOVGAP_ELIGIBILITY_PATH", "prompts/eligibility_prompt.md")
)
ELIGIBILITY_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


async def classify_eligibility(text: str) -> EligibilityVerdict:
    """Return an eligibility verdict for the supplied document text."""
    client = FoundryChatClient(credential=AzureCliCredential())
    agent = Agent(client=client, instructions=ELIGIBILITY_PROMPT)
    result = await agent.run(
        "Classify the following document.\n\n---\n" + text[:20_000] + "\n---"
    )
    raw = getattr(result, "text", None) or str(result)
    obj = repair_json(_strip_fences(raw), return_objects=True)
    return EligibilityVerdict.model_validate(obj)
