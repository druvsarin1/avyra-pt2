import sys
import os

# Ensure the chart-extraction root is on the path so imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from agent.agent import run_extraction

load_dotenv()

# ── Section 1: Study Setup ────────────────────────────────────────────────────

st.title("Retrospective Chart Extraction")

study_context = st.text_area(
    "Study Description",
    placeholder="Describe the study being conducted...",
)

# Dynamic variable list
if "variable_count" not in st.session_state:
    st.session_state.variable_count = 1

st.subheader("Variables to Extract")
variables = []
for i in range(st.session_state.variable_count):
    val = st.text_input(f"Variable {i + 1}", key=f"var_{i}")
    if val.strip():
        variables.append(val.strip())

if st.button("Add Variable"):
    st.session_state.variable_count += 1
    st.rerun()

mrn_text = st.text_area("Patient MRNs", placeholder="One MRN per line")

run_button = st.button("Run Extraction")

# ── Section 2: Processing ─────────────────────────────────────────────────────

if run_button:
    mrns = [m.strip() for m in mrn_text.split("\n") if m.strip()]

    if not mrns:
        st.error("Please enter at least one MRN.")
    elif not variables:
        st.error("Please enter at least one variable.")
    elif not study_context.strip():
        st.error("Please enter a study description.")
    else:
        all_results = []
        progress = st.progress(0)

        for i, mrn in enumerate(mrns):
            with st.status(f"Processing MRN: {mrn}..."):
                result = run_extraction(mrn, study_context, variables)
                all_results.append(result)
            progress.progress((i + 1) / len(mrns))

        # ── Section 3: Results ─────────────────────────────────────────────

        rows = []
        for res in all_results:
            for var_result in res.get("results", []):
                rows.append({
                    "mrn": res["mrn"],
                    "variable": var_result.get("variable", ""),
                    "value": var_result.get("value", ""),
                    "source": var_result.get("source", ""),
                    "confidence": var_result.get("confidence", ""),
                    "notes": var_result.get("notes", ""),
                })

        if rows:
            df = pd.DataFrame(rows)
            st.subheader("Extraction Results")
            st.dataframe(df)

            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="extraction_results.csv",
                mime="text/csv",
            )
        else:
            st.warning("No results were extracted. Check MRNs and Epic connection.")
