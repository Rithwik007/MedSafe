import requests
import streamlit as st

st.set_page_config(page_title="MedSafe", page_icon="💊", layout="wide")
st.title("MedSafe | Medication safety demo")
st.warning("Decision support demo only. A qualified clinician must review results. No warning does not mean safe.")
with st.sidebar:
    st.subheader("Patient context")
    age = st.number_input("Age", min_value=0, max_value=120, value=40)
    weight = st.number_input("Weight (kg)", min_value=0.0, value=0.0)
    egfr = st.number_input("eGFR", min_value=0.0, max_value=200.0, value=0.0)
    allergies = st.text_input("Allergies (comma separated)")
    diagnoses = st.text_input("Diagnoses (comma separated)")
    meds = st.text_input("Current medications (comma separated)")
st.markdown("Enter one prescription per line. Supported demo format: `Drug 500 mg BD`.")
text = st.text_area("Prescription", height=130, placeholder="metformin 500 mg BD")
if st.button("Analyze", type="primary"):
    current = [{"drug_name": x.strip()} for x in meds.split(",") if x.strip()]
    patient = {"age": age, "weight_kg": weight or None, "egfr": egfr or None,
        "allergies": [x.strip() for x in allergies.split(",") if x.strip()],
        "diagnoses": [x.strip() for x in diagnoses.split(",") if x.strip()], "current_meds": current}
    try:
        response = requests.post("http://127.0.0.1:8000/analyze-text", json={"patient": patient, "prescription_text": text}, timeout=10)
        response.raise_for_status()
        report = response.json()
        if report["findings"]:
            for finding in report["findings"]:
                with st.container(border=True):
                    st.subheader(f"{finding['severity']} · {finding['type']}")
                    st.write(finding["reason"])
                    st.write(finding["recommendation"])
                    st.caption(f"Review: {finding['evidence']['review_label']} · Rule: {finding['rule_id']} · Source: {finding['evidence']['source_name']}")
        else:
            st.info("No findings returned. This does not establish that prescription is safe.")
        if report["unresolved_items"]:
            st.subheader("Unable to verify")
            for item in report["unresolved_items"]:
                st.write(f"- **{item['item']}**: {item['reason']}")
    except requests.RequestException as exc:
        st.error(f"API unavailable: {exc}")
