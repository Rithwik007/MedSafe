"""Run deterministic, synthetic MedSafe reports for B16."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from medsafe.api.app import app
from medsafe.core.report import SafetyReport
from medsafe.explain.templates import render_text


OUTPUT = ROOT / "reports" / "demo"
CASES = [
    {
        "patient": {},
        "prescription_text": "Combiflam\nDolo 650\nWarfarin",
        "required": ("DUPLICATE-POLICY-INGREDIENT", "DDINTER-DDInter1951-DDInter900"),
    },
    {
        "patient": {
            "allergies": ["amoxicillin"],
            "diagnoses": ["myasthenia gravis", "adrenal insufficiency"],
        },
        "prescription_text": "Amoxicillin\nCiprofloxacin",
        "required": ("B14-ALG-001", "B14-DIS-004", "adrenal insufficiency"),
    },
    {
        "patient": {},
        "prescription_text": "mystery syrup xyz 7-3-1\nLisinopril\nLevothyroxine",
        "required": ("mystery", "ML-PREDICTED (unverified)", "estimate"),
    },
]


def run_case(client: TestClient, case: dict[str, object]) -> tuple[dict, str, bytes, bytes]:
    response = client.post("/analyze-text?use_llm=false", json={
        "patient": case["patient"],
        "prescription_text": case["prescription_text"],
    })
    response.raise_for_status()
    report = SafetyReport.model_validate(response.json())
    payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False,
                         indent=2, sort_keys=True) + "\n"
    text = render_text(report) + "\n"
    return report.model_dump(mode="json"), text, payload.encode("utf-8"), text.encode("utf-8")


def without_timestamp(payload: bytes, text: bytes) -> tuple[bytes, bytes]:
    data = json.loads(payload)
    data.pop("generated_at", None)
    normalized_json = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    normalized_text = re.sub(rb"(?m)^Generated at: .*?$", b"Generated at: <timestamp>", text)
    return normalized_json, normalized_text


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with TestClient(app) as client:
        for index, case in enumerate(CASES, start=1):
            runs = [run_case(client, case) for _ in range(3)]
            baseline = without_timestamp(runs[0][2], runs[0][3])
            same = all(without_timestamp(run[2], run[3]) == baseline for run in runs[1:])
            if not same:
                print(f"Demo {index}: NONDETERMINISTIC beyond generated_at")
                return 1

            report_data, text, json_bytes, text_bytes = runs[0]
            combined = text + json_bytes.decode("utf-8")
            missing = [needle for needle in case["required"] if needle not in combined]
            if missing:
                print(f"Demo {index}: required evidence missing: {missing}")
                return 1
            if index == 2 and not any(
                item.get("item") == "adrenal insufficiency"
                for item in report_data.get("unresolved_items", [])
            ):
                print("Demo 2: adrenal insufficiency was not surfaced as unresolved")
                return 1

            txt_path = OUTPUT / f"demo_{index}.txt"
            json_path = OUTPUT / f"demo_{index}.json"
            txt_path.write_bytes(text_bytes)
            json_path.write_bytes(json_bytes)
            print(f"Demo {index}: deterministic across 3 runs except generated_at")
            print(f"Saved: {txt_path.relative_to(ROOT)} and {json_path.relative_to(ROOT)}")
            print("First 40 text lines:")
            print("\n".join(text.splitlines()[:40]))
            print()
        dose_cases = [
            ("dose_over_limit", {"age_years": 35}, "atorvastatin 40 mg 2 tabs TDS oral"),
            ("dose_missing_age", {}, "atorvastatin 40 mg 2 tabs TDS oral"),
        ]
        for name, patient, prescription_text in dose_cases:
            response = client.post("/analyze-text?use_llm=false", json={
                "patient": patient, "prescription_text": prescription_text,
            })
            response.raise_for_status()
            report = SafetyReport.model_validate(response.json())
            text = render_text(report) + "\n"
            payload = json.dumps(report.model_dump(mode="json"), ensure_ascii=False,
                                 indent=2, sort_keys=True) + "\n"
            if name == "dose_over_limit" and not any(f.type.value == "DOSE" for f in report.findings):
                print("Dose demo: expected an exceeded-row finding.")
                return 1
            if name == "dose_missing_age" and not any(
                item.reason == "dose not checked: patient age not provided"
                for item in report.unresolved_items
            ):
                print("Dose demo: missing-age wording was not surfaced.")
                return 1
            (OUTPUT / f"{name}.txt").write_text(text, encoding="utf-8")
            (OUTPUT / f"{name}.json").write_text(payload, encoding="utf-8")
            print(f"Saved dose demonstration: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
