import streamlit as st
import os, json, pandas as pd
from dotenv import load_dotenv
from googletrans import Translator

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="🌍 Dublin Core Mapper + Validator", layout="wide")
st.title("🌍 Bilingual Dublin Core Mapper + Validator")

st.info("""
This tool converts your aggregated `raw_metadata.json` into **bilingual Dublin Core (English + Spanish)** records,
validates metadata completeness, and exports two files:
- `dublin_core_bilingual.csv` → main dataset
- `metadata_issues.csv` → incomplete or invalid records
""")

load_dotenv()
os.makedirs("data", exist_ok=True)
translator = Translator()

# ---------------------------
# HELPERS
# ---------------------------
def translate_text(text):
    """Translate text using Google Translate (English→Spanish, automatic detection)."""
    if not text or not isinstance(text, str):
        return ""
    try:
        return translator.translate(text, dest="es").text
    except Exception:
        return text  # fallback

def validate_record(dc_row):
    """Return list of missing required Dublin Core fields."""
    required = ["Title (EN)", "Creator (EN)", "Description (EN)", "Date"]
    return [r for r in required if not dc_row.get(r, "").strip()]

def map_to_dublin_core(item):
    """Map one metadata record (any source) to bilingual Dublin Core."""
    title = item.get("title") or item.get("Title") or ""
    creator = item.get("creator") or item.get("Creator") or ""
    desc = item.get("description") or item.get("Description") or ""
    date = item.get("date") or item.get("Date") or ""
    tags = item.get("tags", [])
    img = item.get("media_urls", [])

    dc = {
        "Source": item.get("source", ""),
        "Identifier": item.get("id", ""),
        "Title (EN)": title,
        "Title (ES)": translate_text(title),
        "Creator (EN)": creator,
        "Creator (ES)": translate_text(creator),
        "Description (EN)": desc,
        "Description (ES)": translate_text(desc),
        "Date": date,
        "Tags": "; ".join(tags) if isinstance(tags, list) else tags,
        "Media URL": img[0] if isinstance(img, list) and img else "",
    }
    dc["Missing Fields"] = ", ".join(validate_record(dc))
    return dc

# ---------------------------
# MAIN
# ---------------------------
import os, json, pandas as pd
import streamlit as st

# Attempt to locate metadata JSON in multiple common paths
possible_paths = [
    "data/raw_metadata.json",
    "data/items_metadata.json",
    "items_metadata.json",
    "data/raw_metadta.json"  # typo safeguard
]

items = None
for path in possible_paths:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        st.success(f"✅ Loaded {len(items)} records from `{path}` for mapping.")
        break

if items is None:
    st.error("❌ No metadata file found. Please run the Metadata Poller or Aggregator first.")
    st.stop()

# Generate Bilingual Dublin Core
if st.button("🚀 Generate Bilingual Dublin Core"):
    with st.spinner("Translating + mapping metadata..."):
        try:
            mapped = [map_to_dublin_core(i) for i in items]

            df = pd.DataFrame(mapped)
            issues_df = df[df["Missing Fields"].astype(bool)]

            os.makedirs("data", exist_ok=True)
            dc_csv = "data/dublin_core_bilingual.csv"
            issues_csv = "data/metadata_issues.csv"

            df.to_csv(dc_csv, index=False, encoding="utf-8-sig")
            issues_df.to_csv(issues_csv, index=False, encoding="utf-8-sig")

            st.success(f"✅ Mapped {len(df)} records. {len(issues_df)} incomplete entries flagged.")
            st.markdown("### 🔍 Preview of Bilingual Dublin Core")
            st.dataframe(df.head(10), use_container_width=True)

            # Downloads
            st.download_button(
                "⬇️ Download Bilingual Dublin Core CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="dublin_core_bilingual.csv",
                mime="text/csv"
            )
            st.download_button(
                "⚠️ Download Metadata Issues CSV",
                data=issues_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="metadata_issues.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"❌ Error generating Dublin Core mapping: {e}")

st.divider()
st.caption("Developed by Raagya Gehlot • Archivo Venezuela • 2025 Edition")
