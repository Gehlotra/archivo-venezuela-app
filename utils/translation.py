from deep_translator import GoogleTranslator

def translate_text(text, target_lang="es"):
    """
    Translate text from English to the target language (default Spanish).
    Falls back to returning the original text if translation fails.
    """
    if not text or not isinstance(text, str):
        return ""
    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return translated
    except Exception as e:
        print(f"[Translation error] {e}")
        return text
