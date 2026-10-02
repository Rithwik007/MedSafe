"""Structured deterministic safety report model."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

from medsafe.models.domain import Explanation, Finding, UnresolvedItem


class MlStatus(BaseModel):
    state: Literal["ENABLED", "DISABLED_BY_GATE", "NOT_AVAILABLE"] = "NOT_AVAILABLE"
    reason: str = "Model has not been checked."
    model_fingerprint: str | None = None
    tau: float | None = None


class LlmStatus(BaseModel):
    state: Literal["ENABLED", "DISABLED", "NOT_AVAILABLE"] = "DISABLED"
    reason: str = "LLM is disabled by default."
    model: str | None = None
    parse_attempted: int = 0
    parse_accepted: int = 0
    parse_rejected: int = 0
    summary_accepted: int = 0
    summary_rejected: int = 0


class SuggestedMatch(BaseModel):
    item: str
    suggestion: str
    confidence: float
    reason: str


class CheckerStatus(BaseModel):
    checker: str
    status: str
    reason: str
    rules_loaded: int


class SafetyReport(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    suggested_matches: list[SuggestedMatch] = Field(default_factory=list)
    checker_status: list[CheckerStatus] = Field(default_factory=list)
    overall_statement: str = ""
    disclaimer: str = "Decision support demo only. A qualified clinician must review all results. No warning does not mean a prescription is safe."
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    kb_fingerprint: str = ""
    ml_status: MlStatus | None = None
    llm_status: LlmStatus | None = None
