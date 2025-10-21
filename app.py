import streamlit as st
import pandas as pd
from utils.fetch_helpers import fetch_metadata_from_csv


import os
from dotenv import load_dotenv

# ✅ Load environment variables from .env
load_dotenv()

# 🔑 Omeka + WorldCat credentials
OMEKA_API_URL = os.getenv("OMEKA_API_URL")
OMEKA_API_KEY = os.getenv("OMEKA_API_KEY")
WS_KEY = os.getenv("WS_KEY")
WS_SECRET = os.getenv("WS_SECRET")

# ----------------------------------
# STREAMLIT CONFIG
# ----------------------------------
st.set_page_config(
    page_title="Archivo Venezuela Metadata Tool",
    page_icon="🗂️",
    layout="wide"
)

# ----------------------------------
# HEADER
# ----------------------------------
st.markdown("""
<div style="text-align:center; padding:1rem 0;">
  <h1 style="color:#C0392B;">🗂️ Archivo Venezuela Metadata Tool</h1>
  <p style="font-size:1.1rem; color:gray;">
    Upload OCLC numbers → Fetch real metadata from WorldCat → Translate to Spanish → Preview & Download
  </p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------
# STEP 1 — UPLOAD CSV
# ----------------------------------
st.subheader("📂 Step 1 — Upload CSV of OCLC Numbers")

st.info("""
Upload a CSV with a column such as:
Column names like **OCLC**, **oclc_number**, or **OCLC Number** are all accepted.
""")

uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.success(f"✅ Loaded {len(df)} records.")
    st.dataframe(df.head(), use_container_width=True)

    # ----------------------------------
    # AUTO-DETECT OCLC COLUMN
    # ----------------------------------
    df.columns = [c.strip().lower() for c in df.columns]
    oclc_col = None
    for candidate in ["oclc number", "oclc", "oclc_number"]:
        if candidate in df.columns:
            oclc_col = candidate
            break

    if not oclc_col:
        st.error("❌ Could not find any OCLC column. Please name it 'OCLC Number' or 'OCLC'.")
    else:
        df = df.rename(columns={oclc_col: "OCLC Number"})

        # ----------------------------------
        # FETCH BUTTON
        # ----------------------------------
        if st.button("🚀 Fetch Metadata from WorldCat"):
            with st.spinner("Fetching metadata... please wait ⏳"):
                try:
                    result_df = fetch_metadata_from_csv(df)
                    st.session_state["result_df"] = result_df

                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()

            if not result_df.empty:
                st.success("✅ Metadata fetched successfully!")
                st.dataframe(result_df, use_container_width=True)

                # Download section
                csv_data = result_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="⬇️ Download Metadata CSV",
                    data=csv_data,
                    file_name="worldcat_metadata_bilingual.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ No metadata found for provided OCLC numbers.")
else:
    st.info("👆 Upload your CSV to begin.")

# ----------------------------------
# STEP 2 — UPLOAD TO OMEKA
# ----------------------------------
from utils.omeka_api import upload_item_to_omeka

st.subheader("📤 Step 2 — Upload Metadata to Omeka")

# ✅ Retrieve result_df (saved in Step 1)
result_df = st.session_state.get("result_df", None)

if result_df is not None and not result_df.empty:
    if st.button("📤 Upload to Omeka"):
        success, failed = [], []

        with st.spinner("Uploading items to Omeka..."):
            for i, row in result_df.iterrows():
                status, msg = upload_item_to_omeka(row)
                title = row.get("Title (English)") or f"Item {i + 1}"
                if status == 201:
                    success.append(title)
                else:
                    failed.append(f"{title} ({status})")

        st.success(f"✅ Uploaded {len(success)} items successfully.")
        if failed:
            st.warning(f"⚠️ Failed uploads: {', '.join(failed)}")
else:
    st.info("⚠️ No fetched metadata available. Please complete Step 1 first.")

# ----------------------------------
# STEP 3 — SEMANTIC FAST SUBJECT ENRICHMENT
# ----------------------------------
from utils.fast_semantic_enrichment import enrich_with_fast_semantic

st.subheader("📚 Step 3 — FAST Subject Enrichment (Semantic + AI)")

st.info("""
This step uses AI to extract thematic keywords from each item's title and description,
then enriches them with contextual FAST subject headings (English + Spanish).
""")

result_df = st.session_state.get("result_df", None)

if result_df is not None and not result_df.empty:
    if st.button("🚀 Semantic FAST Enrichment"):
        with st.spinner("Analyzing themes and enriching subjects..."):
            try:
                enriched_df = enrich_with_fast_semantic(result_df)
                st.session_state["fast_df"] = enriched_df
                st.success(f"✅ Enriched {len(enriched_df)} records with semantic FAST subjects.")
                st.dataframe(enriched_df, use_container_width=True)

                csv_data = enriched_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="⬇️ Download Semantic FAST CSV",
                    data=csv_data,
                    file_name="fast_semantic_subjects.csv",
                    mime="text/csv"
                )
            except Exception as e:
                st.error(f"❌ Semantic FAST enrichment failed: {e}")
else:
    st.info("⚠️ No metadata found. Please complete Step 1 first.")




st.divider()
st.caption("Developed by Raagya Gehlot • Archivo Venezuela • 2025 Edition")

