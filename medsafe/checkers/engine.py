"""Deterministic checker registry and report assembly."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from medsafe.checkers.ddi import check_ddi
from medsafe.checkers.allergy import allergy_checker_status, check_allergies
from medsafe.checkers.drug_disease import check_drug_disease, drug_disease_checker_status
from medsafe.checkers.dose import check_dose
from medsafe.checkers.duplicate import check_duplicates, load_policy
from medsafe.checkers.ingredients import ingredient_key
from medsafe.checkers.stubs import ROOT, reviewed_rows
from medsafe.core.normalizer import normalize_drug
from medsafe.core.report import CheckerStatus, MlStatus, SafetyReport, SuggestedMatch
from medsafe.explain.templates import explain_finding
from medsafe.kb.rules import RULES
from medsafe.models.domain import Finding, MlPrediction, Prescription, UnresolvedItem


SEVERITY_ORDER = {"CONTRAINDICATED": 0, "MAJOR": 1, "MODERATE": 2,
                  "MINOR": 3, "UNSPECIFIED": 4, "INFO": 5}
TYPE_ORDER = {"DDI": 0, "ALLERGY": 1, "DRUG_DISEASE": 2,
              "DOSE": 3, "DUPLICATE": 4}

# Frozen B12 decision; see reports/b13_decision_outcome.md. This is policy, not a threshold.
WITHHOLD_MAJOR_ESTIMATES = True


@dataclass(frozen=True)
class MlPredictor:
    predict_pair: Callable[[str, str], tuple[str, float] | None] | None
    drug_names: frozenset[str]
    model_version: str = "injected-test-predictor"
    tau: float | None = None
    model_fingerprint: str | None = None
    state: Literal["ENABLED", "DISABLED_BY_GATE", "NOT_AVAILABLE"] = "ENABLED"
    reason: str = "Injected predictor."
    listed_pairs: frozenset[tuple[str, str]] | None = None
    unlabeled_pairs: frozenset[tuple[str, str]] | None = None


def _import_ml_modules():
    from medsafe.ml.features import pair_features
    from medsafe.ml.predict import load_model
    return load_model, pair_features


def _read_ml_manifest() -> dict:
    from medsafe.ml.predict import MODEL_DIR
    return json.loads((MODEL_DIR / "manifest.json").read_text(encoding="utf-8"))


def _load_ml_predictor() -> MlPredictor:
    try:
        load_model, pair_features = _import_ml_modules()
        loaded = load_model()
        manifest = _read_ml_manifest()
    except Exception as error:
        return MlPredictor(None, frozenset(), state="NOT_AVAILABLE",
            reason=f"Local model unavailable: {type(error).__name__}: {error}")
    if not loaded.enabled:
        return MlPredictor(None, frozenset(loaded.vectors.vectors),
            model_version=str(manifest.get("model_name", "unknown")), tau=loaded.tau,
            model_fingerprint=manifest.get("files", {}).get("severity_model.joblib", {}).get("sha256"),
            state="DISABLED_BY_GATE", reason="Local model gate is disabled.",
            listed_pairs=getattr(loaded, "listed_pairs", None),
            unlabeled_pairs=getattr(loaded, "unlabeled_pairs", None))

    def predict(left: str, right: str) -> tuple[str, float] | None:
        pair = tuple(sorted((left.casefold(), right.casefold())))
        if pair not in loaded.listed_pairs or pair not in loaded.unlabeled_pairs:
            return None
        values = pair_features(left, right, loaded.vectors).reshape(1, -1)
        probabilities = loaded.classifier.predict_proba(values)[0]
        index = int(probabilities.argmax())
        probability = float(probabilities[index])
        if probability < loaded.tau:
            return None
        return str(loaded.classifier.classes_[index]), probability

    return MlPredictor(predict, frozenset(loaded.vectors.vectors),
        model_version=f"{manifest.get('model_name', 'unknown')}-seed-{manifest.get('seed', 'unknown')}",
        tau=loaded.tau,
        model_fingerprint=manifest.get("files", {}).get("severity_model.joblib", {}).get("sha256"),
        state="ENABLED", reason="Local checksum-verified model loaded; estimates remain unverified.",
        listed_pairs=getattr(loaded, "listed_pairs", None),
        unlabeled_pairs=getattr(loaded, "unlabeled_pairs", None))


def _attach_ml_predictions(findings: list[Finding], predictor: MlPredictor) -> MlStatus:
    if predictor.state != "ENABLED" or predictor.predict_pair is None:
        counts = {"PAIR_ALREADY_LABELED": 0, "PAIR_NOT_LISTED": 0,
                  "BELOW_THRESHOLD": 0, "UNKNOWN_DRUG": 0, "MODEL_DISABLED": 0,
                  "MAJOR_WITHHELD": 0}
        for finding in findings:
            if finding.type.value != "DDI":
                continue
            if finding.severity.value != "UNSPECIFIED":
                counts["PAIR_ALREADY_LABELED"] += 1
            elif predictor.state != "ENABLED":
                counts["MODEL_DISABLED"] += 1
            else:
                counts["BELOW_THRESHOLD"] += 1
        reason = predictor.reason + " " + " ".join(f"{key}={value}" for key, value in counts.items())
        return MlStatus(state=predictor.state, reason=reason,
            model_fingerprint=predictor.model_fingerprint, tau=predictor.tau)
    rules = {rule.rule_id: rule for rule in RULES}
    pending: list[tuple[Finding, MlPrediction]] = []
    reason_counts = {"PAIR_ALREADY_LABELED": 0, "PAIR_NOT_LISTED": 0,
                     "BELOW_THRESHOLD": 0, "UNKNOWN_DRUG": 0, "MODEL_DISABLED": 0,
                     "MAJOR_WITHHELD": 0}
    try:
        for finding in findings:
            if finding.type.value != "DDI":
                continue
            if finding.severity.value != "UNSPECIFIED":
                reason_counts["PAIR_ALREADY_LABELED"] += 1
                continue
            rule = rules.get(finding.rule_id)
            if rule is None or len(rule.drugs) != 2:
                reason_counts["UNKNOWN_DRUG"] += 1
                continue
            left, right = (name.casefold() for name in rule.drugs)
            if left not in predictor.drug_names or right not in predictor.drug_names:
                reason_counts["UNKNOWN_DRUG"] += 1
                continue
            pair = tuple(sorted((left, right)))
            if predictor.listed_pairs is not None and pair not in predictor.listed_pairs:
                reason_counts["PAIR_NOT_LISTED"] += 1
                continue
            if predictor.unlabeled_pairs is not None and pair not in predictor.unlabeled_pairs:
                reason_counts["PAIR_ALREADY_LABELED"] += 1
                continue
            result = predictor.predict_pair(left, right)
            if result is None:
                reason_counts["BELOW_THRESHOLD"] += 1
                continue
            label, probability = result
            label = label.title()
            if label not in {"Major", "Moderate", "Minor"}:
                reason_counts["BELOW_THRESHOLD"] += 1
                continue
            if label == "Major" and WITHHOLD_MAJOR_ESTIMATES:
                reason_counts["MAJOR_WITHHELD"] += 1
                continue
            pending.append((finding, MlPrediction(predicted_label=label,
                probability=float(probability), model_version=predictor.model_version,
                tau=float(predictor.tau) if predictor.tau is not None else 1.01)))
    except Exception as error:
        return MlStatus(state="NOT_AVAILABLE",
            reason=f"Prediction failed; report checks completed without ML estimates: {type(error).__name__}: {error}",
            model_fingerprint=predictor.model_fingerprint, tau=predictor.tau)
    for finding, prediction in pending:
        finding.ml_prediction = prediction
    reasons = [predictor.reason] + [f"{count} {name}" for name, count in reason_counts.items()
                                    if count]
    return MlStatus(state="ENABLED", reason=" ".join(reasons),
        model_fingerprint=predictor.model_fingerprint, tau=predictor.tau)


def kb_fingerprint() -> str:
    digest = hashlib.sha256()
    seed_dir = ROOT / "data/seed"
    required_policy_files = (seed_dir / "severity_policy.csv", seed_dir / "conditions.csv")
    for path in sorted(set(seed_dir.glob("*.csv")) | set(required_policy_files),
                       key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes() if path.exists() else b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()


def _ddi_status() -> CheckerStatus:
    rules = [rule for rule in RULES if rule.kind.value == "DDI"]
    unspecified = sum(rule.severity.value == "UNSPECIFIED" for rule in rules)
    reasons: list[str] = []
    if not rules:
        return CheckerStatus(checker="DDI", status="NOT_RUN_NO_DATA",
            reason="No DDI rules loaded.", rules_loaded=0)
    if unspecified / len(rules) > 0.25:
        reasons.append(f"{unspecified}/{len(rules)} loaded DDI rules have UNSPECIFIED severity (>25%).")
    with (ROOT / "data/seed/class_rules.csv").open(encoding="utf-8-sig", newline="") as stream:
        class_count = sum(1 for row in csv.DictReader(stream) if row.get("rule_id", "").strip())
    if class_count == 0:
        reasons.append("No class-level DDI rules loaded.")
    return CheckerStatus(checker="DDI", status="PARTIAL" if reasons else "RAN",
        reason=" ".join(reasons) if reasons else "Loaded DDI rules checked.", rules_loaded=len(rules))


def _duplicate_status() -> CheckerStatus:
    count = len(load_policy())
    return CheckerStatus(checker="DUPLICATE", status="RAN" if count else "NOT_RUN_NO_DATA",
        reason="Duplicate policy loaded." if count else "No duplicate policy rows loaded.",
        rules_loaded=count)


def _finding_key(finding: Finding) -> tuple[str, tuple[str, ...]]:
    ingredients: set[str] = set()
    for order in finding.drugs_involved:
        result = normalize_drug(order)
        if result.ingredients:
            ingredients.update(ingredient_key(item) for item in result.ingredients)
        elif result.canonical:
            ingredients.add(ingredient_key(result.canonical))
        else:
            ingredients.add(ingredient_key(order))
    return finding.rule_id, tuple(sorted(ingredients))


def _overall(statuses: list[CheckerStatus], findings: list[Finding]) -> str:
    counts = {status: sum(item.status == status for item in statuses)
              for status in ("RAN", "PARTIAL", "NOT_RUN_NO_DATA")}
    text = (f"Checkers: {counts['RAN']} RAN, {counts['PARTIAL']} PARTIAL, "
            f"{counts['NOT_RUN_NO_DATA']} NOT_RUN_NO_DATA.")
    if findings:
        counts: dict[str, int] = {}
        for finding in findings:
            counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1
        text += " Findings by severity: " + ", ".join(
            f"{key} {counts[key]}" for key in sorted(counts, key=lambda value: SEVERITY_ORDER[value])) + "."
    text += " Absence of findings does not mean the prescription is safe."
    return text


def analyze(prescription: Prescription,
            clock: Callable[[], datetime] | None = None,
            ml_predictor: MlPredictor | None = None) -> SafetyReport:
    duplicate_report = check_duplicates(prescription)
    allergy_findings, allergy_unresolved = check_allergies(prescription)
    disease_findings, disease_unresolved = check_drug_disease(prescription)
    dose_findings, dose_unresolved, dose_status, dose_reason, dose_count = check_dose(prescription)
    findings = (list(duplicate_report.findings) + check_ddi(prescription)
                + allergy_findings + disease_findings + dose_findings)
    unique: dict[tuple[str, tuple[str, ...]], Finding] = {}
    for finding in findings:
        unique.setdefault(_finding_key(finding), finding)
    findings = list(unique.values())
    findings.sort(key=lambda finding: (SEVERITY_ORDER[finding.severity.value],
                                       TYPE_ORDER[finding.type.value], finding.rule_id))
    ml_status = _attach_ml_predictions(findings, ml_predictor or _load_ml_predictor())
    for finding in findings:
        finding.explanation = explain_finding(finding)

    unresolved = list(duplicate_report.unresolved_items)
    for item in allergy_unresolved + disease_unresolved + dose_unresolved:
        if item not in unresolved:
            unresolved.append(item)
    suggested: list[SuggestedMatch] = []
    for order in prescription.patient.current_meds + prescription.new_orders:
        result = normalize_drug(order.drug_name)
        if result.status == "suggested" and result.suggestion:
            suggested.append(SuggestedMatch(item=order.drug_name, suggestion=result.suggestion,
                confidence=result.confidence, reason=result.reason or "Confirmation required."))
        elif result.status == "unresolved":
            item = UnresolvedItem(item=order.drug_name,
                reason=result.reason or "Drug name did not resolve in curated data.")
            if item not in unresolved:
                unresolved.append(item)
    statuses = [_ddi_status(), _duplicate_status()]
    allergy_count = reviewed_rows(ROOT / "data/seed/allergy_rules.csv")
    allergy_status, allergy_reason, allergy_loaded = allergy_checker_status(
        allergy_count, bool(prescription.patient.allergies))
    statuses.append(CheckerStatus(checker="ALLERGY", status=allergy_status,
                                  reason=allergy_reason, rules_loaded=allergy_loaded))
    disease_count = reviewed_rows(ROOT / "data/seed/drug_disease_rules.csv")
    disease_status, disease_reason, disease_loaded = drug_disease_checker_status(
        disease_count, bool(prescription.patient.diagnoses))
    statuses.append(CheckerStatus(checker="DRUG_DISEASE", status=disease_status,
                                  reason=disease_reason, rules_loaded=disease_loaded))
    statuses.append(CheckerStatus(checker="DOSE", status=dose_status, reason=dose_reason,
                                  rules_loaded=dose_count))
    now = (clock or (lambda: datetime.now(timezone.utc)))()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return SafetyReport(findings=findings, unresolved_items=unresolved,
        suggested_matches=suggested, checker_status=statuses,
        overall_statement=_overall(statuses, findings), kb_fingerprint=kb_fingerprint(),
        ml_status=ml_status,
        generated_at=now.astimezone(timezone.utc).isoformat())
