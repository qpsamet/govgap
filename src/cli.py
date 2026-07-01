#!/usr/bin/env python3
"""GovGap command-line interface.

Give it one document and it reports how well that document addresses the six
developer-level risks of using AI coding agents.

  python -m src.cli https://example.com/ai-contribution-policy
  python -m src.cli ./policy.pdf
  python -m src.cli ./terms.docx
"""
import argparse
import asyncio
import sys

from .ingest import ACCEPTED_FORMATS, IngestError
from .agent import assess_user_document
from .report import render_assessment

BANNER = f"""GovGap - AI-governance coverage checker

Give it one document and it reports how well that document addresses the six
developer-level risks of using AI coding agents.

Accepted input: {ACCEPTED_FORMATS}.

Examples:
  python -m src.cli https://example.com/ai-contribution-policy
  python -m src.cli ./policy.pdf
  python -m src.cli ./terms.docx

Options:
  --json        also print the structured JSON
  -h, --help    show this message
"""


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("source", nargs="?")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")
    args = parser.parse_args()

    if args.help or not args.source:
        print(BANNER)
        return

    try:
        result = asyncio.run(assess_user_document(args.source, log=_log))
    except IngestError as e:
        _log(f"\nCould not read the document: {e}")
        sys.exit(2)
    except Exception as e:  # auth, model, network
        _log(f"\nSomething went wrong while assessing: {e}")
        sys.exit(1)

    print()
    print(render_assessment(result))
    if args.json:
        print("\n--- JSON ---")
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
