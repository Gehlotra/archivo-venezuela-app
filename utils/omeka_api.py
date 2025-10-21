# utils/omeka_api.py
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OMEKA_API_KEY = os.getenv("OMEKA_API_KEY")
OMEKA_URL = os.getenv("OMEKA_URL")

# ✅ Valid Dublin Core element IDs for Archivo Venezuela (adjust if needed)
DC_ELEMENTS = {
    "Title (English)": 50,
    "Title (Spanish)": 50,
    "Author (English)": 39,
    "Author (Spanish)": 39,
    "Subjects (English)": 49,
    "Subjects (Spanish)": 49,
    "Description (English)": 41,
    "Description (Spanish)": 41,
    "Date": 40,
    "Language (English)": 44,
    "Language (Spanish)": 44,
    "Publisher (English)": 45,
    "Publisher (Spanish)": 45,
    "Format (English)": 42,
    "Format (Spanish)": 42,
}

def row_to_omeka_json(row: dict) -> dict:
    """Convert one DataFrame row to Omeka JSON payload."""
    metadata = []
    for col, value in row.items():
        if not str(value).strip():
            continue
        element_id = DC_ELEMENTS.get(col)
        if not element_id:
            continue
        metadata.append({
            "element": {"id": element_id},
            "text": str(value),
            "html": False
        })

    return {
        "public": True,
        "featured": False,
        "element_texts": metadata
    }

def upload_item_to_omeka(row: dict):
    """Upload one metadata row to Omeka Classic via API."""
    payload = row_to_omeka_json(row)
    try:
        response = requests.post(
            OMEKA_URL,
            headers={"Content-Type": "application/json"},
            params={"key": OMEKA_API_KEY},
            data=json.dumps(payload),
            timeout=60
        )
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)
