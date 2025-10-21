# utils/fast_semantic_enrichment.py
import pandas as pd
import time
from keybert import KeyBERT
from utils.translation import translate_text

# Initialize the KeyBERT model (this loads once)
kw_model = KeyBERT(model='all-MiniLM-L6-v2')

def extract_semantic_keywords(title: str, description: str) -> list[str]:
    """
    Extracts 5–8 meaningful subject-like phrases from the title and description.
    Focuses on thematic, conceptual words (migration, memory, exile, trauma, etc.)
    """
    try:
        text = f"{title}. {description}".strip()
        if not text:
            return []

        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words='english',
            top_n=8
        )
        # Extract phrases only
        subjects = [kw for kw, score in keywords]
        # De-duplicate and clean
        subjects = list(dict.fromkeys([s.title().strip() for s in subjects if len(s) > 2]))
        return subjects
    except Exception:
        return []

def enrich_with_fast_semantic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich metadata with thematic English and Spanish subject phrases.
    """
    results = []

    for _, row in df.iterrows():
        title = str(row.get("Title (English)", "")).strip()
        desc = str(row.get("Description (English)", "")).strip()
        author = row.get("Author (English)", "")
        oclc = row.get("OCLC Number", "")

        if not title:
            continue

        subjects_en = extract_semantic_keywords(title, desc)
        subjects_es = [translate_text(s) for s in subjects_en]

        results.append({
            "OCLC Number": oclc,
            "Author": author,
            "Title": title,
            "Subjects (EN)": "; ".join(subjects_en),
            "Subjects (ES)": "; ".join(subjects_es)
        })

        # small pause to avoid too many translations in a row
        time.sleep(0.5)

    return pd.DataFrame(results)
