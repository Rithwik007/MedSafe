from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
from medsafe.checkers.engine import analyze
from medsafe.explain.templates import _render_ml_status_reason
from medsafe.models.domain import Prescription, UnresolvedItem
from medsafe.core.report import SafetyReport
from medsafe.nlp.parser import ParseLimitError, parse_prescription
from medsafe.core.normalizer import normalize_drug
from medsafe.kb.rules import RULES

app = FastAPI(title="MedSafe", description="Medication safety decision-support demo; not for clinical use.")
STATIC_DIR = Path(__file__).resolve().parent / "static"
CSP_VALUE = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"

# Pre-compute config once at startup — avoids SHA-256 model check on every /config request.
def _build_cached_config() -> dict:
    from medsafe.checkers.engine import _load_ml_predictor
    from medsafe.llm.client import LlmConfig, readiness
    try:
        app_version = version("medsafe")
    except PackageNotFoundError:
        app_version = "0.1.0"
    try:
        ml_available = _load_ml_predictor().state == "ENABLED"
    except Exception:
        ml_available = False
    try:
        cfg = LlmConfig.from_env()
        llm_available = readiness(cfg, True)[0] == "ENABLED"
    except Exception:
        llm_available = False
    return {"ml_available": ml_available, "llm_available": llm_available, "version": app_version}

_CACHED_CONFIG: dict = {}

@app.on_event("startup")
async def _startup():
    global _CACHED_CONFIG
    _CACHED_CONFIG = _build_cached_config()



@app.middleware("http")
async def content_security_policy(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = CSP_VALUE
    return response


class TextRequest(BaseModel):
    patient: dict
    prescription_text: str

    @field_validator("patient")
    @classmethod
    def bound_patient_text_fields(cls, value: dict) -> dict:
        if len(value) > 12:
            raise ValueError("patient has too many fields")
        for key in ("allergies", "diagnoses"):
            items = value.get(key, [])
            if not isinstance(items, list) or len(items) > 50:
                raise ValueError(f"patient.{key} must be a list with at most 50 entries")
            if any(not isinstance(item, str) or len(item) > 200 for item in items):
                raise ValueError(f"patient.{key} entries must be text of at most 200 characters")
        current = value.get("current_meds", [])
        if not isinstance(current, list) or len(current) > 50:
            raise ValueError("patient.current_meds must be a list with at most 50 entries")
        for item in current:
            if not isinstance(item, dict) or not isinstance(item.get("drug_name"), str) or len(item["drug_name"]) > 200:
                raise ValueError("patient.current_meds entries require a drug_name of at most 200 characters")
        return value


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/static/{asset_name}", include_in_schema=False)
def static_asset(asset_name: str):
    assets = {"app.js": "text/javascript", "styles.css": "text/css"}
    media_type = assets.get(asset_name)
    if media_type is None:
        raise HTTPException(status_code=404, detail="Static asset not found.")
    return FileResponse(STATIC_DIR / asset_name, media_type=media_type)


@app.get("/config")
def config():
    return _CACHED_CONFIG if _CACHED_CONFIG else _build_cached_config()


@app.get("/health")
def health():
    return {"status": "ok", "clinical_rules_loaded": len(RULES)}


@app.post("/analyze", response_model=SafetyReport)
def analyze_structured(request: Prescription, use_llm: bool = False):
    report = analyze(request)
    from medsafe.llm.service import add_summaries
    from medsafe.llm.client import LlmConfig, readiness
    state, reason = readiness(LlmConfig.from_env(), use_llm)
    report.llm_status = add_summaries(report, use_llm)
    if report.llm_status.state == "ENABLED" and report.llm_status.summary_accepted == 0 and report.llm_status.summary_rejected == 0:
        report.llm_status.state, report.llm_status.reason = state, reason
    if report.ml_status is not None:
        report.ml_status.reason = _render_ml_status_reason(report.ml_status.reason)
    return report


@app.post("/analyze-text", response_model=SafetyReport)
def analyze_text(request: TextRequest, use_llm: bool = False):
    from medsafe.models.domain import Patient
    try:
        parsed = parse_prescription(request.prescription_text)
    except ParseLimitError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    patient = Patient.model_validate(request.patient)
    from medsafe.llm.service import prepare_text, add_summaries
    parsed, llm_status, llm_client = prepare_text(request.prescription_text, parsed, use_llm)
    report = analyze(Prescription(patient=patient, new_orders=parsed.orders_for_checking))
    report.llm_status = llm_status
    report.unresolved_items.extend(UnresolvedItem(item=item.line, reason=item.reason)
                                   for item in parsed.unparsed_lines)
    for order in parsed.orders:
        if order not in parsed.orders_for_checking:
            result = normalize_drug(order.name_used or order.drug_name)
            if result.status == "suggested" and result.suggestion:
                from medsafe.core.report import SuggestedMatch
                report.suggested_matches.append(SuggestedMatch(item=order.drug_name,
                    suggestion=result.suggestion, confidence=result.confidence,
                    reason=result.reason or "Candidate needs user confirmation."))
            else:
                report.unresolved_items.append(UnresolvedItem(item=order.drug_name,
                    reason=f"Drug name did not resolve exactly; parsed fields retained: {order.model_dump_json()}"))
        for token in order.unparsed_tokens:
            report.unresolved_items.append(UnresolvedItem(item=order.source_line or order.drug_name,
                reason=f"Unparsed token: {token}"))
        for note in order.parse_notes:
            if not note.startswith("Drug name did not resolve exactly"):
                report.unresolved_items.append(UnresolvedItem(item=order.source_line or order.drug_name,
                    reason=f"Parser note: {note}"))
    report.llm_status = add_summaries(report, use_llm, report.llm_status,
        llm_client, calls_used=report.llm_status.parse_attempted)
    return report


@app.post("/explain-report")
def explain_report(request: SafetyReport, use_llm: bool = False):
    """Return an optional aggregate overview without changing the safety report schema."""
    from medsafe.llm.service import explain_report as make_overview
    return make_overview(request, use_llm)
