# omeka_metadata_poller.py
import os
import json
import time
import re
from html import unescape
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

OMEKA_API_URL = os.getenv("OMEKA_API_URL", "https://archivovenezuela.com/test/api/items")
OMEKA_API_KEY = os.getenv("OMEKA_API_KEY", "")

PER_PAGE_DEFAULT = int(os.getenv("OMEKA_PER_PAGE", "50"))

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", str(raw_html))
    return unescape(text).strip()

def normalize_tags(raw_tags):
    out = []
    for t in (raw_tags or []):
        if isinstance(t, dict) and "name" in t:
            out.append(t["name"])
        elif isinstance(t, str):
            out.append(t)
    return out

def get_files_url_from_item(item: dict) -> str | None:
    files_obj = item.get("files")
    if isinstance(files_obj, dict):
        return files_obj.get("url")
    return None

def fetch_item_detail(item_id: int) -> dict | None:
    try:
        r = requests.get(
            f"{OMEKA_API_URL.rstrip('/')}/{item_id}",
            params={"key": OMEKA_API_KEY} if OMEKA_API_KEY else {},
            timeout=20,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def fetch_item_files(item: dict) -> list[str]:
    """Return list of original image URLs for this item using files endpoint."""
    files_url = get_files_url_from_item(item)
    if not files_url:
        # fallback: construct from base path
        base = OMEKA_API_URL.replace("/items", "/files")
        files_url = f"{base}?item={item.get('id')}"
    try:
        r = requests.get(files_url, params={"key": OMEKA_API_KEY} if OMEKA_API_KEY else {}, timeout=20)
        if r.status_code == 200:
            urls = []
            for f in r.json():
                orig = (f.get("file_urls") or {}).get("original")
                if orig:
                    urls.append(orig)
            return urls
    except Exception:
        pass
    return []

def poll_items(days:int=30, per_page:int=PER_PAGE_DEFAULT, max_pages:int=50) -> list[dict]:
    """Fetch items added in the last `days`. Uses pagination; auto-stops when pages end."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    page = 1
    results = []

    while page <= max_pages:
        params = {"per_page": per_page, "page": page}
        if OMEKA_API_KEY:
            params["key"] = OMEKA_API_KEY

        resp = requests.get(OMEKA_API_URL, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"❌ API error on page {page}: {resp.status_code}")
            break

        batch = resp.json()
        if not batch:
            break

        for item in batch:
            added_str = item.get("added") or ""
            try:
                added_dt = datetime.fromisoformat(added_str.replace("Z", "+00:00"))
            except Exception:
                continue

            if added_dt < cutoff:
                # we still continue the page in case there are mixed dates,
                # but often items are roughly chronological
                pass

            detail = fetch_item_detail(item.get("id"))
            if not detail:
                continue

            meta = {
                "id": item.get("id"),
                "date_added": added_dt.strftime("%Y-%m-%d"),
                "title": "",
                "creator": "",
                "description": "",
                "tags": normalize_tags(detail.get("tags")),
                "media_urls": [],
            }

            for e in detail.get("element_texts", []):
                name = (e.get("element") or {}).get("name", "").lower()
                if not name:
                    continue
                text = clean_html(e.get("text", ""))
                if name == "title":
                    meta["title"] = text
                elif name == "creator":
                    meta["creator"] = text
                elif name == "description":
                    meta["description"] = text

            meta["media_urls"] = fetch_item_files(item)

            # Only keep if within range; else skip
            if added_dt >= cutoff:
                results.append(meta)

        page += 1
        time.sleep(0.3)  # be polite

    # If nothing recent, fallback to return the first page (so you see something)
    if not results:
        print("⚠️ No items in the selected date range; returning most recent page instead.")
        results = []
        params = {"per_page": per_page, "page": 1}
        if OMEKA_API_KEY:
            params["key"] = OMEKA_API_KEY
        r2 = requests.get(OMEKA_API_URL, params=params, timeout=20)
        if r2.status_code == 200:
            for item in r2.json():
                detail = fetch_item_detail(item.get("id"))
                if not detail:
                    continue
                meta = {
                    "id": item.get("id"),
                    "date_added": (item.get("added") or "")[:10],
                    "title": "",
                    "creator": "",
                    "description": "",
                    "tags": normalize_tags(detail.get("tags")),
                    "media_urls": fetch_item_files(item),
                }
                for e in (detail.get("element_texts") or []):
                    name = (e.get("element") or {}).get("name", "").lower()
                    text = clean_html(e.get("text", ""))
                    if name == "title":
                        meta["title"] = text
                    elif name == "creator":
                        meta["creator"] = text
                    elif name == "description":
                        meta["description"] = text
                results.append(meta)

    return results

def main():
    days = int(os.getenv("POLL_DAYS", "30"))
    per_page = int(os.getenv("OMEKA_PER_PAGE", str(PER_PAGE_DEFAULT)))
    items = poll_items(days=days, per_page=per_page)

    with open("items_metadata.json", "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    with open("polling_log.txt", "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().isoformat()}Z - polled {len(items)} items (last {days} days)\n")

    print(f"✅ Wrote items_metadata.json with {len(items)} items")
    print("📝 Appended to polling_log.txt")

if __name__ == "__main__":
    main()
