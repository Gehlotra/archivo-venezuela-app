import streamlit as st
import os, json, csv, re
from datetime import datetime
import requests
import pandas as pd
from dotenv import load_dotenv
from html import unescape

# Optional WorldCat helpers if present in your repo
try:
    from utils.fetch_helpers import fetch_oclc_token, fetch_worldcat_data, clean_worldcat_data
    WORLDCAT_OK = True
except Exception:
    WORLDCAT_OK = False

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="📡 Cross-Platform Metadata Aggregator", layout="wide")
st.title("📡 Cross-Platform Metadata Aggregator")
st.info(
    "Fetch metadata from multiple sources (OMDb/IMDb, YouTube, Spotify, WorldCat) and save a unified `raw_metadata.json` for the next steps.\n"
    "YouTube & Spotify use oEmbed (no API key). OMDb & WorldCat require keys in `.env`."
)

load_dotenv()
os.makedirs("data", exist_ok=True)

OMDB_API_KEY = os.getenv("OMDB_API_KEY", "").strip()
WS_KEY = os.getenv("WS_KEY", "").strip()
WS_SECRET = os.getenv("WS_SECRET", "").strip()

# ---------------------------
# HELPERS
# ---------------------------
def clean_text(x: str) -> str:
    if not x:
        return ""
    x = re.sub(r"<[^>]+>", "", str(x))
    return unescape(x).strip()

def save_outputs(rows, source_name):
    """Append rows to raw_metadata.json and log to source_log.csv."""
    raw_path = "data/raw_metadata.json"
    # Load existing
    existing = []
    if os.path.exists(raw_path):
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # Append and save
    merged = existing + rows
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    # Log
    log_path = "data/source_log.csv"
    new_entries = [{"timestamp": datetime.now().isoformat()+"Z",
                    "source": source_name,
                    "count": len(rows)}]
    write_header = not os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "source", "count"])
        if write_header:
            writer.writeheader()
        for r in new_entries:
            writer.writerow(r)

    st.success(f"✅ Saved {len(rows)} records to `data/raw_metadata.json`")
    st.caption(f"Logged import → `data/source_log.csv`")

def show_preview(rows, max_rows=5):
    if not rows:
        st.warning("No rows to preview.")
        return
    st.markdown("### 🔍 Preview")
    df = pd.DataFrame(rows)
    st.dataframe(df.head(max_rows), use_container_width=True)
    st.download_button(
        "⬇️ Download this batch as CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="aggregated_preview.csv",
        mime="text/csv"
    )

# ---------------------------
# TABS
# ---------------------------
tab1, tab2, tab3, tab4 = st.tabs(["🎬 OMDb / IMDb", "▶️ YouTube (oEmbed)", "🎵 Spotify (oEmbed)", "📚 WorldCat (OCLC)"])

# === OMDb (IMDb) ===
with tab1:
    st.subheader("🎬 OMDb / IMDb")
    st.caption("Requires OMDb API key in `.env` as `OMDB_API_KEY`. Get one at https://www.omdbapi.com/apikey.aspx")
    if not OMDB_API_KEY:
        st.error("OMDB_API_KEY is missing in your .env. This tab will be disabled until you add it.")
    else:
        mode = st.radio("Fetch by:", ["Title", "IMDb ID", "CSV of Titles/IDs"], horizontal=True)
        batch_rows = []

        if mode == "Title":
            title = st.text_input("Enter Title (e.g., Parasite)")
            year = st.text_input("Optional Year (e.g., 2019)")
            if st.button("🔎 Fetch from OMDb (Title)"):
                params = {"apikey": OMDB_API_KEY, "t": title}
                if year.strip():
                    params["y"] = year.strip()
                r = requests.get("https://www.omdbapi.com/", params=params, timeout=20)
                data = r.json()
                if data.get("Response") == "True":
                    row = {
                        "source": "omdb",
                        "id": data.get("imdbID"),
                        "title": clean_text(data.get("Title")),
                        "creator": clean_text(data.get("Director") or data.get("Writer")),
                        "description": clean_text(data.get("Plot")),
                        "date": clean_text(data.get("Year")),
                        "tags": [g.strip() for g in (data.get("Genre") or "").split(",") if g.strip()],
                        "media_urls": [data.get("Poster")] if data.get("Poster") and data.get("Poster") != "N/A" else []
                    }
                    batch_rows.append(row)
                    show_preview(batch_rows)
                    if st.button("💾 Save OMDb result"):
                        save_outputs(batch_rows, "omdb")
                else:
                    st.warning(f"OMDb returned: {data.get('Error','Unknown error')}")

        elif mode == "IMDb ID":
            imdb_id = st.text_input("Enter IMDb ID (e.g., tt6751668)")
            if st.button("🔎 Fetch from OMDb (IMDb ID)"):
                params = {"apikey": OMDB_API_KEY, "i": imdb_id}
                r = requests.get("https://www.omdbapi.com/", params=params, timeout=20)
                data = r.json()
                if data.get("Response") == "True":
                    row = {
                        "source": "omdb",
                        "id": data.get("imdbID"),
                        "title": clean_text(data.get("Title")),
                        "creator": clean_text(data.get("Director") or data.get("Writer")),
                        "description": clean_text(data.get("Plot")),
                        "date": clean_text(data.get("Year")),
                        "tags": [g.strip() for g in (data.get("Genre") or "").split(",") if g.strip()],
                        "media_urls": [data.get("Poster")] if data.get("Poster") and data.get("Poster") != "N/A" else []
                    }
                    batch_rows.append(row)
                    show_preview(batch_rows)
                    if st.button("💾 Save OMDb result"):
                        save_outputs(batch_rows, "omdb")
                else:
                    st.warning(f"OMDb returned: {data.get('Error','Unknown error')}")

        else:  # CSV
            st.caption("Upload a CSV with a column `title` **or** `imdb_id`.")
            csv_file = st.file_uploader("Upload CSV", type=["csv"], key="omdb_csv")
            if csv_file and st.button("🔎 Batch Fetch"):
                df = pd.read_csv(csv_file)
                cols = [c.lower().strip() for c in df.columns]
                title_col = "title" if "title" in cols else None
                id_col = "imdb_id" if "imdb_id" in cols else None
                if not title_col and not id_col:
                    st.error("CSV must contain `title` or `imdb_id` column.")
                else:
                    for _, row in df.iterrows():
                        if id_col:
                            params = {"apikey": OMDB_API_KEY, "i": str(row[id_col])}
                        else:
                            params = {"apikey": OMDB_API_KEY, "t": str(row[title_col])}
                        r = requests.get("https://www.omdbapi.com/", params=params, timeout=20)
                        data = r.json()
                        if data.get("Response") == "True":
                            batch_rows.append({
                                "source": "omdb",
                                "id": data.get("imdbID"),
                                "title": clean_text(data.get("Title")),
                                "creator": clean_text(data.get("Director") or data.get("Writer")),
                                "description": clean_text(data.get("Plot")),
                                "date": clean_text(data.get("Year")),
                                "tags": [g.strip() for g in (data.get("Genre") or "").split(",") if g.strip()],
                                "media_urls": [data.get("Poster")] if data.get("Poster") and data.get("Poster") != "N/A" else []
                            })
                    show_preview(batch_rows)
                    if batch_rows and st.button("💾 Save OMDb batch"):
                        save_outputs(batch_rows, "omdb")

# === YouTube (oEmbed) ===
with tab2:
    st.subheader("▶️ YouTube (oEmbed — no API key)")
    st.caption("Paste one or more YouTube URLs (one per line). We’ll fetch title, author, thumbnail via oEmbed.")
    urls_text = st.text_area("YouTube Video URLs", placeholder="https://www.youtube.com/watch?v=...", height=120)
    batch_rows = []
    if st.button("🔎 Fetch YouTube Metadata"):
        for url in [u.strip() for u in urls_text.splitlines() if u.strip()]:
            try:
                r = requests.get("https://www.youtube.com/oembed",
                                 params={"url": url, "format": "json"}, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    batch_rows.append({
                        "source": "youtube",
                        "id": url,
                        "title": clean_text(data.get("title")),
                        "creator": clean_text(data.get("author_name")),
                        "description": "",
                        "date": "",
                        "tags": [],
                        "media_urls": [data.get("thumbnail_url")] if data.get("thumbnail_url") else []
                    })
                else:
                    st.warning(f"Could not fetch: {url} (status {r.status_code})")
            except Exception as e:
                st.warning(f"Error for {url}: {e}")
        show_preview(batch_rows)
        if batch_rows and st.button("💾 Save YouTube batch"):
            save_outputs(batch_rows, "youtube")

# === Spotify (oEmbed) ===
with tab3:
    st.subheader("🎵 Spotify (oEmbed — no API key)")
    st.caption("Paste one or more Spotify URLs (track/album/playlist), one per line.")
    sp_urls_text = st.text_area("Spotify URLs", placeholder="https://open.spotify.com/track/...", height=120)
    batch_rows = []
    if st.button("🔎 Fetch Spotify Metadata"):
        for url in [u.strip() for u in sp_urls_text.splitlines() if u.strip()]:
            try:
                r = requests.get("https://open.spotify.com/oembed",
                                 params={"url": url}, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    batch_rows.append({
                        "source": "spotify",
                        "id": url,
                        "title": clean_text(data.get("title")),
                        "creator": clean_text(data.get("author_name")),
                        "description": "",
                        "date": "",
                        "tags": [],
                        "media_urls": [data.get("thumbnail_url")] if data.get("thumbnail_url") else []
                    })
                else:
                    st.warning(f"Could not fetch: {url} (status {r.status_code})")
            except Exception as e:
                st.warning(f"Error for {url}: {e}")
        show_preview(batch_rows)
        if batch_rows and st.button("💾 Save Spotify batch"):
            save_outputs(batch_rows, "spotify")

# === WorldCat (OCLC) ===
with tab4:
    st.subheader("📚 WorldCat (OCLC)")
    if not WORLDCAT_OK:
        st.error("WorldCat helpers not found (`utils.fetch_helpers`). This tab is disabled.")
    elif not (WS_KEY and WS_SECRET):
        st.error("WS_KEY / WS_SECRET missing in `.env`. Add them to use WorldCat.")
    else:
        st.caption("Upload a CSV with a column named `oclc` (or `oclc_number`, or `OCLC Number`).")
        oclc_csv = st.file_uploader("Upload OCLC CSV", type=["csv"], key="oclc_csv_file")
        if oclc_csv and st.button("🔎 Fetch WorldCat Metadata"):
            df = pd.read_csv(oclc_csv)
            # normalize column names
            df.columns = [c.strip().lower() for c in df.columns]
            oclc_col = None
            for c in ["oclc", "oclc_number", "oclc number"]:
                if c in df.columns:
                    oclc_col = c
                    break
            if not oclc_col:
                st.error("CSV must contain one of: oclc, oclc_number, 'OCLC Number'")
            else:
                token = fetch_oclc_token()
                if not token:
                    st.error("Failed to get WorldCat token. Check WS_KEY/WS_SECRET.")
                else:
                    batch_rows = []
                    with st.spinner("Fetching OCLC records..."):
                        for _, r in df.iterrows():
                            oclc = str(r[oclc_col]).strip()
                            if not oclc:
                                continue
                            try:
                                raw = fetch_worldcat_data(oclc, token)
                                if not raw:
                                    continue
                                # Your clean_worldcat_data returns bilingual-ready dict
                                cleaned = clean_worldcat_data(raw)  # has Identifier/Title/etc.
                                # Normalize to generic unified schema
                                row = {
                                    "source": "worldcat",
                                    "id": cleaned.get("Identifier") or oclc,
                                    "title": cleaned.get("Title") or "",
                                    "creator": cleaned.get("Creator") or "",
                                    "description": cleaned.get("Description") or "",
                                    "date": cleaned.get("Date") or "",
                                    "tags": [t.strip() for t in (cleaned.get("Subject (EN)") or "").split(";") if t.strip()],
                                    "media_urls": []  # WorldCat doesn't give us images usually
                                }
                                batch_rows.append(row)
                            except Exception as e:
                                st.warning(f"OCLC {oclc} failed: {e}")

                    show_preview(batch_rows)
                    if batch_rows and st.button("💾 Save WorldCat batch"):
                        save_outputs(batch_rows, "worldcat")
