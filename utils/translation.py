from googletrans import Translator
import time

translator = Translator()

# manual fallback for common terms
_MANUAL_MAP = {
    "Short stories": "Cuentos cortos",
    "Fiction": "Ficción",
    "Novels": "Novelas",
    "Politics": "Política",
    "Refugees": "Refugiados",
    "Venezuela": "Venezuela",
    "Poetry": "Poesía",
    "History": "Historia",
    "Migration": "Migración",
    "Book": "Libro",
    "Literature": "Literatura",
    "Culture": "Cultura",
}

def translate_text(text: str, target_lang: str = "es") -> str:
    """
    Robust English → Spanish translator.
    - Uses manual fallback map for known words.
    - Retries if the translation is identical.
    - Handles network errors gracefully.
    """
    if not text or str(text).strip() == "":
        return ""

    text = str(text).strip()

    # manual fallback
    if text in _MANUAL_MAP:
        return _MANUAL_MAP[text]

    try:
        # Attempt translation
        result = translator.translate(text, dest=target_lang)
        translated = result.text.strip()

        # If translation same as original, try lowercase version once
        if translated.lower() == text.lower():
            time.sleep(0.5)
            result2 = translator.translate(text.lower(), dest=target_lang)
            translated2 = result2.text.strip()
            if translated2.lower() != text.lower():
                return translated2

        return translated
    except Exception:
        # fallback — if network or API issue
        return text
