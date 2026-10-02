"""Pure deterministic explanation rendering; no clinical inference."""
import re
from medsafe.core.report import SafetyReport
from medsafe.models.domain import Explanation, Finding

ML_LIMITATION_NOTE = ("ML estimates come from a model trained on DDInter labels. They are not "
    "DDInter database classifications and lack broad outside-source review. "
    "A pharmacist must review each estimate.")

_ML_REASON_WORDING = {
    "UNKNOWN_DRUG": ("pair includes a drug absent from model data",
                     "pairs include drugs absent from model data"),
    "PAIR_NOT_LISTED": ("pair not listed by DDInter", "pairs not listed by DDInter"),
    "PAIR_ALREADY_LABELED": ("pair already has a source classification",
                              "pairs already have source classifications"),
    "BELOW_THRESHOLD": ("pair below model threshold", "pairs below model threshold"),
    "MODEL_DISABLED": ("model disabled by gate", "model disabled by gate"),
    "MAJOR_WITHHELD": ("estimate withheld pending outside review",
                       "estimates withheld pending outside review"),
}


def _render_ml_status_reason(reason: str) -> str:
    for code, (singular, plural) in _ML_REASON_WORDING.items():
        pattern = re.compile(rf"(?:\b(\d+)\s+{code}\b|\b{code}=(\d+)\b)")

        def replace(match: re.Match[str]) -> str:
            count = int(match.group(1) or match.group(2))
            wording = singular if count == 1 else plural
            return f"{count} {wording}"

        reason = pattern.sub(replace, reason)
    return reason


def explain_finding(finding: Finding) -> Explanation:
    pair = " + ".join(finding.drugs_involved)
    if finding.type.value == "DDI":
        match = re.search(r"Ingredient pair: ([^.]+)\.", finding.reason)
        pair = match.group(1) if match else pair
        headline = f"{finding.severity.value}: {pair}"
    elif finding.type.value == "DOSE":
        headline = f"{finding.severity.value}: Dose limit exceeded for {pair}"
    elif finding.type.value == "DUPLICATE":
        match = re.match(r"([^ ]+) appears in ", finding.reason)
        duplicate_name = match.group(1) if match else pair
        headline = f"{finding.severity.value}: Duplicate {duplicate_name}"
    else:
        headline = f"{finding.severity.value}: {pair}"
    if finding.type.value == "DOSE":
        risk = finding.reason
    elif finding.type.value == "DDI":
        risk = f"DDInter lists this pair at {finding.severity.value.title()} severity."
    elif finding.type.value == "DUPLICATE":
        risk = f"Duplicate policy flags this at {finding.severity.value.title()} severity."
    else:
        risk = f"{finding.type.value.replace('_', ' ').title()} finding has {finding.severity.value.title()} severity."
    reviewed = finding.evidence.review_label == "Reviewed"
    if finding.type.value == "DOSE":
        why = DOSE_SOURCE_WHY
    elif finding.type.value == "DUPLICATE":
        why = "Not applicable to duplicate-therapy findings."
    else:
        why = (finding.mechanism.strip() if reviewed and finding.mechanism and finding.mechanism.strip()
               else "Mechanism not provided by the source dataset.")
    recommendation = finding.recommendation.strip()
    if finding.type.value == "DDI" and not reviewed:
        recommendation = "No management guidance in the source dataset. Ask a pharmacist or check an authoritative label."
    if finding.severity.value == "UNSPECIFIED":
        recommendation = (recommendation.rstrip() + " Severity was not classified by the source.").strip()
    source = finding.evidence.source_url or finding.evidence.source_name
    if finding.evidence.ddinter_ids:
        source += " (DDInter IDs: " + ", ".join(finding.evidence.ddinter_ids) + ")"
    trigger = finding.reason.strip().replace("\n", " ")
    pair_match = re.search(r"Ingredient pair: ([^.]+)\.", trigger)
    if finding.type.value == "DOSE":
        trigger = DOSE_SINGLE_ORDER_TRIGGER
    elif finding.type.value == "DDI" and pair_match:
        orders = ", ".join(finding.drugs_involved)
        trigger = f"Ingredients: {pair_match.group(1)}. Orders: {orders}."
    elif finding.type.value == "DUPLICATE":
        shared = re.match(r"([^ ]+) appears in ", trigger)
        ingredient = shared.group(1) if shared else "unknown ingredient"
        trigger = (f"Shared ingredient: {ingredient}. Orders: "
                   f"{', '.join(finding.drugs_involved)}.")
    elif pair_match:
        orders = ", ".join(finding.drugs_involved)
        trigger = f"Ingredients: {pair_match.group(1)}. Orders: {orders}."
    ml_note = None
    if finding.ml_prediction is not None:
        prediction = finding.ml_prediction
        ml_note = ("Experimental ML estimate (unverified, not a database classification): "
            f"possibly {prediction.predicted_label}. Estimated from patterns in other "
            "DDInter-classified pairs; other sources may disagree. Pharmacist review is still required.")
        if prediction.predicted_label == "Minor":
            ml_note += " This estimate does not lower the need for review."
    return Explanation(headline=headline, risk=risk, why=why,
        trigger=trigger, recommendation=recommendation, source=source,
        review_label=finding.evidence.review_label, rule_id=finding.rule_id,
        ml_note=ml_note)


def render_text(report: SafetyReport) -> str:
    lines = ["MedSafe medication safety report", report.overall_statement]
    estimate_count = sum(finding.ml_prediction is not None for finding in report.findings)
    if estimate_count:
        lines.append(f"{estimate_count} finding(s) carry an unverified ML estimate; these are not database classifications.")
        lines.append(ML_LIMITATION_NOTE)
    lines += [
             f"Generated at: {report.generated_at}", f"Knowledge base SHA-256: {report.kb_fingerprint}",
             "", "Checker status:"]
    lines.extend(f"- {item.checker}: {item.status} ({item.rules_loaded} rules; {item.reason})"
                 for item in report.checker_status)
    if report.ml_status is not None:
        lines.append(f"- ML estimate: {report.ml_status.state} ({_render_ml_status_reason(report.ml_status.reason)})")
    if report.llm_status is not None:
        lines.append(f"- LLM: {report.llm_status.state} ({report.llm_status.reason})")
    lines += ["", "Findings:"]
    if not report.findings:
        lines.append("- None generated.")
    for finding in report.findings:
        explanation = (explain_finding(finding) if finding.ml_prediction is not None
                       else finding.explanation or explain_finding(finding))
        lines += [f"- {explanation.headline}", f"  Risk: {explanation.risk}",
                  f"  Why: {explanation.why}", f"  Trigger: {explanation.trigger}",
                  f"  Recommendation: {explanation.recommendation}",
                  f"  Source: {explanation.source}", f"  Review: {explanation.review_label}"]
        if explanation.ml_note:
            lines.append(f"  ML-PREDICTED (unverified): {explanation.ml_note}")
        if explanation.plain_language:
            lines.append("  AI-worded summary (wording only; the fields above are authoritative): "
                         + explanation.plain_language)
    lines += ["", "Unresolved items:"]
    lines.extend(f"- {item.item}: {item.reason}" for item in report.unresolved_items)
    if not report.unresolved_items:
        lines.append("- None.")
    lines += ["", "Suggested matches:"]
    lines.extend(f"- {item.item}: {item.suggestion} ({item.confidence:g}; confirmation needed)"
                 for item in report.suggested_matches)
    if not report.suggested_matches:
        lines.append("- None.")
    lines += ["", f"Disclaimer: {report.disclaimer}"]
    return "\n".join(lines)


PHARMACIST_REVIEW_LINE = "Ask a pharmacist to review this label-based finding."
DOSE_REVIEW_LINE = "Pharmacist review required; confirm the source label and patient context."
DOSE_SINGLE_ORDER_TRIGGER = "Daily total is calculated from this order only; separate orders are not added."
DOSE_SOURCE_WHY = "The comparison uses the recorded label row without unit conversion."
DOSE_CHECKER_LIMITATION = "Coverage is a few source-text-checked label rows; adult single-order checks only; this is not clinical review."
DOSE_UNRESOLVED = {
    "PATIENT_AGE_MISSING": "dose not checked: patient age not provided",
    "ADULTS_ONLY": "dose not checked: row covers adults only",
    "PARSE_CONFIDENCE": "dose not checked: parse confidence is not HIGH",
    "QUANTITY_UNKNOWN": "dose not checked: quantity per intake is unknown",
    "UNIT_MISMATCH": "dose not checked: order unit does not match the label row",
    "FREQUENCY_UNKNOWN": "dose not checked: frequency is unknown",
    "AS_NEEDED": "dose not checked: as-needed order has no fixed daily frequency",
    "ONE_TIME": "dose not checked: one-time order is not a daily schedule",
    "ROUTE_MISMATCH": "dose not checked: route does not match the label row",
}


def dose_exceeded_text(rule_id: str, source_section: str, daily_total: str,
                       max_daily: str, single_total: str, max_single: str,
                       unit: str) -> str:
    return (f"Dose comparison for source row {rule_id}, section {source_section}: "
            f"this order totals {daily_total} {unit} per day (label daily maximum {max_daily} {unit}) "
            f"and {single_total} {unit} per intake (label single maximum {max_single} {unit}).")


ALLERGY_CHECKER_LIMITATION = "Coverage is a handful of source-text-checked label rows; this is not clinical review."
DISEASE_CHECKER_LIMITATION = "Coverage is a handful of source-text-checked label rows; condition matching uses exact phrases only and this is not clinical review."
ALLERGY_NO_PATIENT_DATA = "No patient allergy data supplied; no exact allergy match was evaluated."
DISEASE_NO_PATIENT_DATA = "No patient condition data supplied; no exact drug-condition match was evaluated."
UNMATCHED_ALLERGEN = "No exact reviewed allergy rule matched this allergen; this does not establish absence of a concern."
UNMATCHED_CONDITION = "No exact reviewed drug-condition rule matched this condition; this does not establish absence of a concern."
