"""Human-readable rendering of an assessment.

Turns the structured result into plain text a person can read, for both the
eligible case (a coverage report) and the ineligible case (a reasoned
rejection). The JSON form remains available separately for the eval pipeline.
"""
from __future__ import annotations

import textwrap
from collections import Counter

from .schema import AssessmentResult, Coverage, EligibilityVerdict, GovGapReport

_DIV = "=" * 72
_SUB = "-" * 72

_CODE_LABEL = {
    Coverage.ADDRESSED_M: "ADDRESSED  (working mechanism)",
    Coverage.ADDRESSED_P: "ADDRESSED  (foreclosed by prohibition)",
    Coverage.PARTIAL:     "PARTIAL    (mentioned but vague or non-binding)",
    Coverage.GAP:         "GAP        (document is silent)",
}

_REJECTION_HINT = {
    "NOT_GOVERNANCE":
        "This does not read as a binding governance document. It looks more "
        "like an article, page, or general text.",
    "WRONG_LEVEL":
        "This is a market- or organisation-level framework that sits above the "
        "developer workflow, so the framework would only report level-mismatch "
        "gaps rather than real findings.",
    "NON_BINDING_ADVISORY":
        "This is voluntary advisory guidance with no obligation a contributor "
        "or user must follow, so there is no mechanism to assess.",
    "NOT_CODING_SPECIFIC":
        "This is about AI in general rather than a software-development or "
        "contribution workflow.",
    "DRAFT":
        "This appears to be a draft or proposal rather than an adopted policy.",
}


def _wrap(text: str, indent: str = "    ") -> str:
    return textwrap.fill(text, width=72, initial_indent=indent, subsequent_indent=indent)


def render_report(report: GovGapReport) -> str:
    out = [_DIV, "GOVERNANCE COVERAGE REPORT", "",
           f"Document : {report.document_name}",
           f"Source   : {report.source}", _DIV, ""]

    counts = Counter(f.coverage for f in report.findings)
    if report.foreclosure:
        out.append("Result   : FORECLOSED. The document bans AI-assisted contribution,")
        out.append("           so all six risks are foreclosed by prohibition.")
    else:
        addressed = counts[Coverage.ADDRESSED_M] + counts[Coverage.ADDRESSED_P]
        out.append(
            f"Result   : {addressed} addressed, {counts[Coverage.PARTIAL]} partial, "
            f"{counts[Coverage.GAP]} gap  (of 6 risks)"
        )
    out.append("")

    for i, f in enumerate(report.findings, 1):
        out.append(f"C{i}  {f.category}")
        out.append(f"    -> {_CODE_LABEL[f.coverage]}")
        if f.evidence:
            out.append(_wrap(f'evidence: "{f.evidence}"'))
        out.append(_wrap(f"why: {f.rationale}"))
        if f.recommendation:
            out.append(_wrap(f"fix: {f.recommendation}"))
        out.append("")

    out.append(_SUB)
    out.append(_wrap(report.summary, indent=""))
    out.append(_DIV)
    return "\n".join(out)


def render_rejection(source: str, kind: str, verdict: EligibilityVerdict) -> str:
    out = [_DIV, "NOT ASSESSED  (document is out of scope)", _DIV, "",
           f"Source        : {source}  ({kind})",
           f"Detected type : {verdict.document_type}",
           f"Reason        : {verdict.category.value} "
           f"(confidence: {verdict.confidence.value})", ""]
    out.append(_wrap(verdict.reason, indent="  "))
    hint = _REJECTION_HINT.get(verdict.category.value)
    if hint:
        out.append("")
        out.append(_wrap(hint, indent="  "))
    out += ["", _SUB,
            "This tool assesses developer- and team-level AI-governance documents:",
            "  - an open-source project's AI contribution policy, or",
            "  - a vendor's terms for an AI coding tool.",
            "Provide a document of that kind to get a coverage report.", _DIV]
    return "\n".join(out)


def render_assessment(result: AssessmentResult) -> str:
    if result.eligibility.eligible and result.report is not None:
        return render_report(result.report)
    return render_rejection(result.source, result.ingested_kind, result.eligibility)
