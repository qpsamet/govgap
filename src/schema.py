from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---- Coding (six-category coverage) -----------------------------------------

class Coverage(str, Enum):
    ADDRESSED_M = "Addressed-M"
    ADDRESSED_P = "Addressed-P"
    PARTIAL = "Partial"
    GAP = "Gap"


class Finding(BaseModel):
    category: str
    coverage: Coverage
    evidence: str = Field(default="")
    rationale: str
    recommendation: str = Field(default="")


class GovGapReport(BaseModel):
    document_name: str
    source: str
    foreclosure: bool = False
    findings: list[Finding] = Field(min_length=6, max_length=6)
    summary: str


# ---- Eligibility (front-door screening) -------------------------------------

class EligibilityCategory(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_GOVERNANCE = "NOT_GOVERNANCE"
    WRONG_LEVEL = "WRONG_LEVEL"
    NON_BINDING_ADVISORY = "NON_BINDING_ADVISORY"
    NOT_CODING_SPECIFIC = "NOT_CODING_SPECIFIC"
    DRAFT = "DRAFT"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EligibilityVerdict(BaseModel):
    eligible: bool
    category: EligibilityCategory
    document_type: str
    reason: str
    confidence: Confidence = Confidence.MEDIUM


# ---- Combined result returned by the user-facing flow -----------------------

class AssessmentResult(BaseModel):
    source: str
    ingested_kind: str
    eligibility: EligibilityVerdict
    report: Optional[GovGapReport] = None
