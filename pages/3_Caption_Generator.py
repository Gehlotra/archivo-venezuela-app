import streamlit as st
import json
import os
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv

# ----------------------------------
# CONFIG
# ----------------------------------
st.set_page_config(page_title="📝 Caption Generator & Exporter", layout="wide")
st.title("📝 Bilingual Caption Generator & Google Sheet Exporter")
st.info("Generates bilingual captions and exports them to Google Sheets with sharing options.")

load_dotenv()

# Google credentials
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# ----------------------------------
# STEP 1 — Load Captions
# ----------------------------------
output_path = "data/posts_draft.json"

if not os.path.exists(output_path):
    st.error("❌ No captions found. Please run the Caption Generator first.")
    st.stop()

with open(output_path, "r", encoding="utf-8") as f:
    previews = json.load(f)

st.success(f"✅ Loaded {len(previews)} captions from posts_draft.json.")

# ----------------------------------
# STEP 2 — Preview Section
# ----------------------------------
st.markdown("### 🪞 Preview of Generated Captions (First 5 Items)")

for post in previews[:5]:
    title = post.get("Title") or post.get("title") or "Untitled"
    creator = post.get("Creator") or post.get("creator") or "Unknown"
    caption_en = post.get("Caption_EN") or post.get("caption_en") or ""
    caption_es = post.get("Caption_ES") or post.get("caption_es") or ""
    hashtags = post.get("Hashtags") or post.get("hashtags") or ""
    image = post.get("Image") or post.get("image") or ""

    st.markdown(f"**📘 Title:** {title}")
    st.markdown(f"**✍️ Creator:** {creator}")
    st.markdown("**🇬🇧 English Caption:**")
    st.write(caption_en)
    st.markdown("**🇪🇸 Spanish Caption:**")
    st.write(caption_es)
    st.markdown(f"**🏷️ Hashtags:** {hashtags}")
    if image:
        st.image(image, width=300)
    else:
        st.info("No image available.")
    st.markdown("---")

# ----------------------------------
# STEP 3 — Export to Google Sheets
# ----------------------------------
st.subheader("📤 Export Captions to Google Sheets")

try:
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"⚠️ Google authentication failed: {e}")
    st.stop()

if st.button("📑 Export to Google Sheets"):
    from datetime import datetime

    month_year = datetime.now().strftime("%B %Y")
    sheet_title = f"Omeka Social Media Queue – {month_year}"

    try:
        sheet = client.create(sheet_title)
        worksheet = sheet.sheet1
        worksheet.append_row([
            "Item Title", "Creator", "Caption_EN", "Caption_ES",
            "Hashtags", "Image URL", "Approved?", "Reviewer Notes", "Scheduled Date"
        ])

        for post in previews:
            worksheet.append_row([
                post.get("Title", post.get("title", "")),
                post.get("Creator", post.get("creator", "")),
                post.get("Caption_EN", post.get("caption_en", "")),
                post.get("Caption_ES", post.get("caption_es", "")),
                post.get("Hashtags", post.get("hashtags", "")),
                post.get("Image", post.get("image", "")),
                "",
                "",
                ""
            ])

        st.success("✅ Captions exported successfully!")
        st.markdown(f"🔗 **[Open Google Sheet here]({sheet.url})**")
        st.session_state["sheet_url"] = sheet.url

    except Exception as e:
        st.error(f"❌ Failed to export captions: {e}")

# ----------------------------------
# STEP 4 — Share Sheet with Email
# ----------------------------------
if "sheet_url" in st.session_state:
    st.subheader("👥 Share Your Sheet")

    user_email = st.text_input("Enter the email address to share the Google Sheet:")
    if st.button("📩 Share Sheet"):
        try:
            sheet.share(user_email, perm_type="user", role="writer")
            st.success(f"✅ Shared successfully with {user_email}")
            st.markdown(f"🔗 **Sheet Link:** [{st.session_state['sheet_url']}]({st.session_state['sheet_url']})")
        except Exception as e:
            st.error(f"❌ Failed to share: {e}")

st.divider()
st.caption("Developed by Raagya Gehlot • Archivo Venezuela • 2025 Edition")
