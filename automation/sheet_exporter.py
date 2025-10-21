import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# -----------------------------
# Load credentials
# -----------------------------
load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "google_credentials.json")

# Google Sheets API scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

st.set_page_config(page_title="📤 Google Sheet Exporter", layout="wide")
st.title("📤 Google Sheet Exporter")
st.info("Exports bilingual post drafts to a Google Sheet and optionally shares it.")

# -----------------------------
# Step 1: Load posts_draft.json
# -----------------------------
if not os.path.exists("data/posts_draft.json"):
    st.error("❌ File `posts_draft.json` not found. Please run the Caption Generator first.")
    st.stop()

with open("data/posts_draft.json", "r", encoding="utf-8") as f:
    posts = json.load(f)

if not posts:
    st.warning("⚠️ No data found in posts_draft.json.")
    st.stop()

st.success(f"✅ Loaded {len(posts)} posts for export.")

# -----------------------------
# Step 2: Authenticate Google Sheets
# -----------------------------
try:
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"⚠️ Failed to authenticate Google credentials: {e}")
    st.stop()

# -----------------------------
# Step 3: Create new Google Sheet
# -----------------------------
month_year = datetime.now().strftime("%B %Y")
sheet_title = f"Omeka Social Media Queue – {month_year}"

try:
    sheet = client.create(sheet_title)
    worksheet = sheet.sheet1
    worksheet.append_row([
        "Item Title", "Creator", "Caption_EN", "Caption_ES",
        "Hashtags", "Image URL", "Approved?", "Reviewer Notes", "Scheduled Date"
    ])

    # Write posts
    for post in posts:
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

    st.success(f"✅ Successfully exported to Google Sheets!")
    st.markdown(f"🔗 **[Open Sheet in Google Drive]({sheet.url})**")

except Exception as e:
    st.error(f"❌ Failed to export to Google Sheets: {e}")
    st.stop()

# -----------------------------
# Step 4: Optional sharing feature
# -----------------------------
st.markdown("---")
st.subheader("👥 Share Sheet Access")

user_email = st.text_input("Enter email address to share this Google Sheet:")

if st.button("📩 Share Sheet"):
    if not user_email:
        st.warning("⚠️ Please enter a valid email address before sharing.")
    else:
        try:
            sheet.share(user_email, perm_type="user", role="writer")
            st.success(f"✅ Shared successfully with {user_email}")
        except Exception as e:
            st.error(f"❌ Failed to share the sheet: {e}")

st.markdown("---")
st.caption("Developed by Raagya Gehlot • Archivo Venezuela • 2025 Edition")
