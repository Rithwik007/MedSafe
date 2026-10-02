from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class FindingType(StrEnum):
    DDI = "DDI"
    DRUG_DISEASE = "DRUG_DISEASE"
    DUPLICATE = "DUPLICATE"
    DOSE = "DOSE"
    ALLERGY = "ALLERGY"


class Severity(StrEnum):
    CONTRAINDICATED = "CONTRAINDICATED"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    UNSPECIFIED = "UNSPECIFIED"
    MINOR = "MINOR"
    INFO = "INFO"


class MedOrder(BaseModel):
    """Order representation.

    dose_value/dose_unit hold PRODUCT STRENGTH as written, not dose per intake.
    Dose per intake = strength x units_per_intake. Do not use for combination products.
    unit_kind says whether dose_value is a mass, a volume, or IU. Never compare a
    VOLUME or IU value to a mass limit.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    drug_name: str = Field(min_length=1, max_length=200)
    dose_value: float | None = Field(default=None, gt=0)
    dose_unit: str | None = None
    unit_kind: str | None = None
    frequency_per_day: float | None = Field(default=None, gt=0, le=24)
    route: str | None = None
    duration_days: int | None = Field(default=None, gt=0, le=3650)
    form: str | None = None
    units_per_intake: float | None = Field(default=None, gt=0)
    frequency_code: str | None = None
    as_needed: bool = False
    one_time: bool = False
    route_is_assumed: bool = False
    parse_confidence: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    parse_notes: list[str] = Field(default_factory=list)
    unparsed_tokens: list[str] = Field(default_factory=list)
    source_line: str = ""
    name_used: str | None = None
    llm_assisted: bool = False


class Patient(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    age_years: int | None = Field(default=None, ge=0, le=120)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    egfr: float | None = Field(default=None, ge=0, le=200)
    allergies: list[str] = Field(default_factory=list)
    diagnoses: list[str] = Field(default_factory=list)
    current_meds: list[MedOrder] = Field(default_factory=list)


class Prescription(BaseModel):
    patient: Patient
    new_orders: list[MedOrder] = Field(default_factory=list)


class Evidence(BaseModel):
    source_name: str
    source_url: str | None = None
    version_or_access_date: str | None = None
    review_status: str
    review_label: str = "Not reviewed"
    rationale: str | None = None
    ddinter_ids: list[str] = Field(default_factory=list)


class Explanation(BaseModel):
    headline: str
    risk: str
    why: str
    trigger: str
    recommendation: str
    source: str
    review_label: str
    rule_id: str
    ml_note: str | None = None
    plain_language: str | None = None


class MlPrediction(BaseModel):
    predicted_label: str = ""
    probability: float = 0.0
    label_status: Literal["ML-PREDICTED, unverified"] = "ML-PREDICTED, unverified"
    model_version: str = ""
    tau: float = 1.01
    reason: str | None = None


class Finding(BaseModel):
    type: FindingType
    severity: Severity
    drugs_involved: list[str]
    reason: str
    mechanism: str | None = None
    recommendation: str
    rule_id: str
    evidence: Evidence
    explanation: Explanation | None = None
    ml_prediction: MlPrediction | None = None


class UnresolvedItem(BaseModel):
    item: str
    reason: str


class SafetyReport(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    unresolved_items: list[UnresolvedItem] = Field(default_factory=list)
    disclaimer: str = "Decision support demo only. A qualified clinician must review all results. No warning does not mean a prescription is safe."
