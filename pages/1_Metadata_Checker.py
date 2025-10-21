import streamlit as st
import requests
import pandas as pd
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# ----------------------------------------
# CONFIGURATION
# ----------------------------------------
st.set_page_config(page_title="Archivo Venezuela — Metadata Checker", layout="wide")

# Load environment variables
load_dotenv()
OMEKA_API_URL = os.getenv("OMEKA_API_URL", "https://archivovenezuela.com/test/api/items")
OMEKA_API_KEY = os.getenv("OMEKA_API_KEY", "")

# ----------------------------------------
# HEADER
# ----------------------------------------
st.title("🧩 Archivo Venezuela Metadata Checker")
st.caption("Developed by Raagya Gehlot • Archivo Venezuela • 2025 Edition")

st.info("""
This tool checks existing Omeka records for:
- Missing or empty metadata fields  
- Broken or missing images  
- Invalid URLs  
""")

# ----------------------------------------
# USER INPUT
# ----------------------------------------
custom_url = st.text_input("🔗 Omeka API URL", OMEKA_API_URL)
custom_key = st.text_input("🔑 API Key", OMEKA_API_KEY, type="password")

OMEKA_API_URL = custom_url.strip() or OMEKA_API_URL
OMEKA_API_KEY = custom_key.strip() or OMEKA_API_KEY

limit = st.slider("Number of recent items to check", 5, 100, 10)

# ----------------------------------------
# HELPERS
# ----------------------------------------
def clean_html(raw_html):
    """Remove HTML tags from metadata fields."""
    if not raw_html:
        return ""
    return BeautifulSoup(str(raw_html), "html.parser").get_text().strip()

def check_url(url):
    """Check if a URL is reachable."""
    if not url or not isinstance(url, str):
        return False
    try:
        r = requests.head(url, timeout=10)
        return r.status_code < 400
    except Exception:
        return False

def fetch_items(limit=20):
    """Fetch item list from Omeka and then retrieve each item’s full JSON detail."""
    try:
        params = {"per_page": limit}
        if OMEKA_API_KEY:
            params["key"] = OMEKA_API_KEY

        list_response = requests.get(OMEKA_API_URL, params=params, timeout=25)
        if list_response.status_code != 200:
            st.error(f"❌ Failed to fetch items list — {list_response.status_code}")
            return []

        list_data = list_response.json()
        detailed_items = []

        # Fetch full item JSON for each ID
        for entry in list_data:
            item_id = entry.get("id")
            if not item_id:
                continue

            item_url = f"{OMEKA_API_URL.rstrip('/')}/{item_id}"
            params_detail = {"key": OMEKA_API_KEY} if OMEKA_API_KEY else {}
            detail_resp = requests.get(item_url, params=params_detail, timeout=25)

            if detail_resp.status_code == 200:
                detailed_items.append(detail_resp.json())
            else:
                st.warning(f"⚠️ Could not fetch details for item {item_id} ({detail_resp.status_code})")

        return detailed_items
    except Exception as e:
        st.error(f"⚠️ Connection error while fetching items: {e}")
        return []


def extract_field(elements, field_name):
    """Extract and clean text for a given field name."""
    for e in elements:
        if e["element"]["name"].lower() == field_name.lower():
            return clean_html(e.get("text", ""))
    return ""

def validate_metadata(items):
    """Validate metadata completeness, images, and URLs using full item details."""
    results = []

    for i, item in enumerate(items, start=1):
        try:
            elements = item.get("element_texts", [])
            files = item.get("files") or []

            def get_field(name_options):
                for e in elements:
                    field_name = e["element"]["name"].strip().lower()
                    if any(field_name == opt.lower() for opt in name_options):
                        return clean_html(e.get("text", ""))
                return ""

            # Extract fields (support both English and DC naming)
            title = get_field(["Title", "Dublin Core:Title"])
            creator = get_field(["Creator", "Dublin Core:Creator"])
            description = get_field(["Description", "Dublin Core:Description"])
            date = get_field(["Date", "Dublin Core:Date"])

            # Image check
            has_image = isinstance(files, list) and len(files) > 0
            image_ok = False
            img_url = ""

            if has_image:
                first_file = files[0] if isinstance(files[0], dict) else {}
                img_url = first_file.get("file_urls", {}).get("original", "")
                if img_url and img_url.startswith("http"):
                    image_ok = check_url(img_url)

            # URL check
            all_links = [
                e.get("text") for e in elements
                if isinstance(e.get("text"), str) and "http" in e.get("text")
            ]
            has_url = len(all_links) > 0
            url_ok = any(check_url(link) for link in all_links) if has_url else False

            # Metadata completeness
            missing = [
                field for field, value in {
                    "Title": title,
                    "Creator": creator,
                    "Description": description,
                    "Date": date
                }.items() if not value
            ]

            status = "✅ Complete"
            if missing:
                status = f"⚠️ Missing: {', '.join(missing)}"
            if has_image and not image_ok:
                status += " | ⚠️ Broken Image"

            # Append result
            results.append({
                "Item ID": item.get("id", ""),
                "Title": title or "(No Title)",
                "Creator": creator or "(No Creator)",
                "Description": (description[:80] + "...") if description else "(No Description)",
                "Date": date or "(No Date)",
                "Image URL": img_url or "(None)",
                "Image Status": "✅ OK" if image_ok else ("⚠️ Broken" if has_image else "❌ None"),
                "Links OK": "✅" if url_ok else ("⚠️ Invalid" if has_url else "❌ None"),
                "Overall Status": status.strip(" |")
            })

        except Exception as e:
            st.warning(f"⚠️ Error checking item {i}: {e}")

    return pd.DataFrame(results)


# ----------------------------------------
# MAIN LOGIC
# ----------------------------------------
if st.button("🔍 Run Metadata Validation"):
    with st.spinner("Fetching and validating metadata... ⏳"):
        items = fetch_items(limit)
        if not items:
            st.warning("⚠️ No items retrieved. Check API URL or key.")
        else:
            df = validate_metadata(items)
            st.success(f"✅ Checked {len(df)} items successfully.")
            st.dataframe(df, use_container_width=True)

            # Summary
            complete = df["Overall Status"].str.contains("✅ Complete").sum()
            incomplete = len(df) - complete
            st.markdown(f"**🟢 Complete:** {complete}  **🔴 Incomplete:** {incomplete}")

            # Download
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Download Metadata Report",
                data=csv_data,
                file_name="metadata_checker_report.csv",
                mime="text/csv"
            )
