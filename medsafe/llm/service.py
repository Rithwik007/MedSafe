from __future__ import annotations
from typing import Any
from medsafe.core.report import LlmStatus, SafetyReport
from medsafe.llm.client import LlmConfig, readiness, provider_client
from medsafe.llm.summaries import generate_summary
from medsafe.llm.report_summary import generate_report_summary
from medsafe.models.domain import Finding
from medsafe.nlp.parser import ParseResult
from medsafe.llm.parser_fallback import fallback_parse

def _provider(config: LlmConfig, state: str) -> Any | None:
    if state != "ENABLED":
        return None
    try:
        return provider_client(config)
    except Exception:
        return None

def prepare_text(text: str, parsed: ParseResult, requested: bool):
    config = LlmConfig.from_env()
    state, reason = readiness(config, requested)
    client = _provider(config, state)
    if state == "ENABLED" and client is None:
        state, reason = "NOT_AVAILABLE", "Optional LLM client could not be initialized."
    updated, counts, fallback_reason = fallback_parse(text, parsed, config,
        client if state == "ENABLED" else None, requested)
    if state == "ENABLED" and fallback_reason != "Guarded extraction completed.":
        reason = fallback_reason
    status = LlmStatus(state=state, reason=reason, model=config.model if state == "ENABLED" else None,
        parse_attempted=counts["parse_attempted"], parse_accepted=counts["parse_accepted"],
        parse_rejected=counts["parse_rejected"])
    return updated, status, client if state == "ENABLED" else None

def add_summaries(report: SafetyReport, requested: bool, status: LlmStatus | None = None,
                  client: Any | None = None, calls_used: int = 0) -> LlmStatus:
    config = LlmConfig.from_env()
    state, reason = readiness(config, requested)
    if client is not None and requested and config.enabled and config.api_key:
        state, reason = "ENABLED", "Injected LLM client enabled for this request."
    if status is None:
        status = LlmStatus(state=state, reason=reason, model=config.model if state == "ENABLED" else None)
    elif status.state != "ENABLED":
        return status
    if state != "ENABLED":
        return status
    if client is None:
        client = _provider(config, state)
    if client is None:
        status.state = "NOT_AVAILABLE"
        status.reason = "Optional LLM client could not be initialized."
        return status
    accepted = rejected = 0
    for finding in report.findings:
        if finding.ml_prediction is not None or calls_used >= 5:
            continue
        calls_used += 1
        summary, _why = generate_summary(finding, client)
        if summary is None:
            rejected += 1
        else:
            accepted += 1
            if finding.explanation is not None:
                finding.explanation.plain_language = summary
    status.summary_accepted += accepted
    status.summary_rejected += rejected
    if rejected:
        status.reason = status.reason + " Some summaries were rejected or the provider failed; deterministic text retained."
    report.llm_status = status
    return status

def explain_report(report: SafetyReport, requested: bool, client: Any | None = None) -> dict[str, Any]:
    """Generate an optional, guarded overview from aggregate report facts only."""
    config = LlmConfig.from_env()
    state, reason = readiness(config, requested)
    if not requested or state != "ENABLED":
        return {"state": state, "reason": reason, "overview": None}
    client = client or _provider(config, state)
    if client is None:
        return {"state": "NOT_AVAILABLE", "reason": "Optional LLM client could not be initialized.", "overview": None}
    overview, outcome = generate_report_summary(report, client)
    if overview is None:
        return {"state": "NOT_AVAILABLE", "reason": outcome, "overview": None}
    return {"state": "ENABLED", "reason": "Guarded AI overview accepted.", "overview": overview}
