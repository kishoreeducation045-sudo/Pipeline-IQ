# app/models/rca.py
from pydantic import BaseModel, Field
from typing import Literal, Optional

class FlakyAssessment(BaseModel):
    is_flaky: bool
    flaky_score: float = Field(ge=0, le=1)
    flaky_category: Optional[str] = None
    matched_signals: list[dict] = []
    recommended_action: str

class Evidence(BaseModel):
    source: Literal["log", "diff", "test", "commit"]
    location: str                               # e.g. "logs:line 42" or "diff:requirements.txt"
    snippet: str                                # Actual text
    relevance_score: float = Field(ge=0, le=1)

class Hypothesis(BaseModel):
    rank: int = Field(ge=1, le=5)
    title: str                                  # Short headline
    description: str                            # 2-3 sentence explanation
    failure_class: Literal[
        "dependency_conflict",
        "flaky_test",
        "config_drift",
        "resource_exhaustion",
        "code_regression",
        "infrastructure_error",
        "unknown"
    ]
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]

class Remediation(BaseModel):
    action: str                                 # e.g. "Pin requests dependency"
    rationale: str
    commands: list[str] = []                    # e.g. ["pip install requests==2.31.0"]
    risk_level: Literal["low", "medium", "high"]

class RCAReport(BaseModel):
    failure_id: str
    generated_at: str                           # ISO 8601
    hypotheses: list[Hypothesis]                # Ranked, max 3
    recommended_remediation: Remediation
    summary: str                                # 1-sentence human summary
    latency_ms: int                             # How long Claude took
    similar_past_failures: list[str] = []       # IDs of retrieved past cases
    flaky_assessment: Optional[FlakyAssessment] = None
