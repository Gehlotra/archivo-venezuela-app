import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from utils.translation import translate_text

load_dotenv()

WS_KEY = os.getenv("WS_KEY")
WS_SECRET = os.getenv("WS_SECRET")

# Token cache to avoid refetching every record
_token_cache = {"token": None, "expires_at": 0}


def fetch_oclc_token() -> str:
    """Obtain OCLC OAuth token using WS_KEY and WS_SECRET."""
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 10:
        return _token_cache["token"]

    url = "https://oauth.oclc.org/token"
    auth = (WS_KEY, WS_SECRET)
    payload = {"grant_type": "client_credentials", "scope": "wcapi"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    resp = requests.post(url, auth=auth, data=payload, headers=headers, timeout=20)
    if resp.status_code == 200:
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        return _token_cache["token"]
    else:
        raise Exception(f"Token Error {resp.status_code}: {resp.text}")


def fetch_worldcat_data(oclc_number: str, token: str) -> dict | None:
    """Fetch metadata for a given OCLC number."""
    url = f"https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs/{oclc_number}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code == 200:
        return resp.json()
    else:
        return None


def clean_worldcat_data(data: dict, oclc_number: str) -> dict:
    """Extract bilingual metadata fields from WorldCat record."""
    def safe_get(obj, *keys):
        try:
            for k in keys:
                obj = obj[k]
            return obj
        except Exception:
            return ""

    title_en = safe_get(data, "title", "mainTitles", 0, "text")
    author_en = ""
    try:
        creators = data.get("contributor", {}).get("creators", [])
        if creators:
            first_creator = creators[0]
            author_en = first_creator.get("name") or first_creator.get("firstName", {}).get("text", "")
    except Exception:
        pass

    subjects = []
    try:
        for s in data.get("subjects", []):
            subj = s.get("subjectName", {}).get("text") or s.get("label")
            if subj:
                subjects.append(subj)
    except Exception:
        pass

    publisher_en = safe_get(data, "publishers", 0, "publisherName", "text")
    description_en = safe_get(data, "description", "physicalDescription") or safe_get(data, "description", "abstract")
    format_en = safe_get(data, "format", "generalFormat")
    pub_date = safe_get(data, "date", "publicationDate")
    lang_en = safe_get(data, "language", "itemLanguage")

    # Translate important fields
    title_es = translate_text(title_en)
    author_es = translate_text(author_en)
    description_es = translate_text(description_en)
    publisher_es = translate_text(publisher_en)
    subjects_es = translate_text("; ".join(subjects))
    format_es = translate_text(format_en)
    lang_es = translate_text(lang_en)

    return {
        "OCLC Number": oclc_number,
        "Title (English)": title_en,
        "Title (Spanish)": title_es,
        "Author (English)": author_en,
        "Author (Spanish)": author_es,
        "Subjects (English)": "; ".join(subjects),
        "Subjects (Spanish)": subjects_es,
        "Publisher (English)": publisher_en,
        "Publisher (Spanish)": publisher_es,
        "Description (English)": description_en,
        "Description (Spanish)": description_es,
        "Format (English)": format_en,
        "Format (Spanish)": format_es,
        "Date": pub_date,
        "Language (English)": lang_en,
        "Language (Spanish)": lang_es
    }


def fetch_metadata_from_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Fetch metadata for each OCLC number in CSV."""
    results = []
    failed = []

    try:
        token = fetch_oclc_token()
    except Exception as e:
        raise Exception(f"❌ Token fetch failed: {e}")

    for _, row in df.iterrows():
        oclc_number = str(row["OCLC Number"]).strip()
        if not oclc_number:
            continue
        try:
            wc_data = fetch_worldcat_data(oclc_number, token)
            if wc_data:
                record = clean_worldcat_data(wc_data, oclc_number)
                results.append(record)
            else:
                failed.append(oclc_number)
        except Exception as e:
            failed.append(f"{oclc_number} ({e})")

        time.sleep(1)  # polite delay

    if failed:
        print("⚠️ Failed:", ", ".join(failed))

    return pd.DataFrame(results)
