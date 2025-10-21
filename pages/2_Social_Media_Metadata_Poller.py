import streamlit as st
import json
import os
from datetime import datetime
from automation.omeka_metadata_poller import poll_items

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Archivo Venezuela — Social Media Metadata Poller",
    layout="wide"
)

st.title("📲 Social Media Metadata Poller")
st.markdown("""
This tool fetches the most recent Omeka items (from the last N days)
and prepares them for social-media caption generation.
""")

# -----------------------------
# USER INPUT
# -----------------------------
days = st.slider("How many past days to include?", 5, 90, 30)
limit = st.number_input("Maximum number of items to fetch", 10, 200, 50)

# -----------------------------
# FETCH BUTTON
# -----------------------------
if st.button("📥 Fetch Metadata from Omeka"):
    with st.spinner("Fetching items from Omeka..."):
        items = poll_items(days=days, per_page=limit)

    if not items:
        st.warning("⚠️ No items found for the selected period.")
    else:
        st.success(f"✅ {len(items)} items fetched successfully.")
        st.write("---")

        # Save locally for next steps
        os.makedirs("data", exist_ok=True)
        with open("data/items_metadata.json", "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

        with open("data/polling_log.txt", "a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat()}Z — {len(items)} items (last {days} days)\n")

        # -----------------------------
        # PREVIEW SECTION
        # -----------------------------
        st.markdown("### 🔍 Preview of Fetched Items")
        for i, item in enumerate(items[:5]):  # show first 5
            st.markdown(f"#### 📘 {i+1}. {item.get('title', 'Untitled')}")
            st.write(f"**Creator:** {item.get('creator', 'N/A')}")
            st.write(f"**Description:** {(item.get('description') or '')[:300]}...")
            tags = item.get("tags", [])
            if tags:
                st.write("**Tags:** " + ", ".join(tags))
            else:
                st.write("**Tags:** None")

            # Image preview
            if item.get("media_urls"):
                st.image(item["media_urls"][0], width=400)
            else:
                st.info("🖼️ No image available.")

            st.markdown(f"🗓️ **Added:** {item.get('date_added', 'Unknown')}")
            st.markdown("---")

        st.download_button(
            "⬇️ Download Metadata JSON",
            data=json.dumps(items, ensure_ascii=False, indent=2),
            file_name="items_metadata.json",
            mime="application/json"
        )

st.divider()
st.caption("Developed by Raagya Gehlot • Archivo Venezuela • 2025 Edition")
