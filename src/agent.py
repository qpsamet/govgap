import asyncio
import os
import re
import sys
import tempfile
from typing import Annotated, Callable, Optional

from dotenv import load_dotenv
from json_repair import repair_json
from pydantic import Field, ValidationError
from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from .tools import fetch_document_impl
from .codebook import SYSTEM_PROMPT
from .schema import AssessmentResult, Coverage, GovGapReport
from .ingest import load_document
from .eligibility import classify_eligibility

load_dotenv()


@tool
def fetch_document(
    source: Annotated[str, Field(description="A snapshot file path or a URL")]
) -> str:
    """Read a pinned snapshot or fetch a URL, return clean text."""
    return fetch_document_impl(source)


def _strip_fences(text: str) -> str:
    """Pull JSON out of a ```json ... ``` fence if the model added one."""
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def parse_report(raw: str) -> GovGapReport:
    """Extract, repair, and validate the model's JSON.

    Foreclosure is a whole-document property: when the model flags the document
    as foreclosing AI contributions, every category is Addressed-P. We enforce
    that here so the single document-level judgment is applied uniformly.
    """
    obj = repair_json(_strip_fences(raw), return_objects=True)
    report = GovGapReport.model_validate(obj)
    if report.foreclosure:
        for f in report.findings:
            f.coverage = Coverage.ADDRESSED_P
    return report


async def assess(source: str) -> str:
    """Run the six-category coder on a document at `source` (path or URL).

    This is the coding step used by the evaluation pipeline. It is unchanged
    from the validated version, so eval numbers remain comparable.
    """
    client = FoundryChatClient(credential=AzureCliCredential())
    agent = Agent(client=client, instructions=SYSTEM_PROMPT, tools=[fetch_document])
    msg = (f"Assess the governance document at this source: {source}. "
           f"Call fetch_document to read it, then return the JSON report "
           f"with all six findings.")
    result = await agent.run(msg)
    return getattr(result, "text", None) or str(result)


async def _code_text(text: str) -> GovGapReport:
    """Code already-ingested text by routing it through the unchanged coder.

    The text is written to a temporary file so the coding step is byte-for-byte
    the same path the evaluation uses (the agent reads it via fetch_document),
    which keeps user-facing results consistent with the measured ones.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write(text)
        tmp = tf.name
    try:
        return parse_report(await assess(tmp))
    finally:
        os.unlink(tmp)


async def assess_user_document(
    source: str,
    *,
    log: Optional[Callable[[str], None]] = None,
) -> AssessmentResult:
    """Full user-facing flow: ingest any format, screen, then code if eligible."""
    def stage(msg: str) -> None:
        if log:
            log(msg)

    stage("Reading the document ...")
    ingested = load_document(source)
    stage(f"Read {len(ingested.text)} characters ({ingested.kind}). "
          f"Checking whether this is an AI-governance document the framework can assess ...")

    verdict = await classify_eligibility(ingested.text)
    if not verdict.eligible:
        stage(f"Out of scope: {verdict.category.value}.")
        return AssessmentResult(source=ingested.label, ingested_kind=ingested.kind,
                                eligibility=verdict, report=None)

    stage("Eligible. Assessing the six risk categories ...")
    report = await _code_text(ingested.text)
    stage("Done.")
    return AssessmentResult(source=ingested.label, ingested_kind=ingested.kind,
                            eligibility=verdict, report=report)


def main():
    """Developer entry point: code one document and print raw JSON."""
    if len(sys.argv) < 2:
        sys.exit("Usage: python -m src.agent <snapshot-path-or-url>")
    raw = asyncio.run(assess(sys.argv[1]))
    try:
        report = parse_report(raw)
    except (ValidationError, ValueError) as e:
        print("RAW OUTPUT:\n", raw, "\n\nFAILED:\n", e)
        sys.exit(1)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
