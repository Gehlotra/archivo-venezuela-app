import random
from googletrans import Translator

translator = Translator()

def generate_bilingual_caption(title, creator, description, tags):
    """
    Generate simple bilingual social media captions (EN + ES)
    using free Google Translate and consistent templates.
    """

    # Basic cleanups
    title = title.strip() if title else "Untitled"
    creator = creator.strip() if creator else "Unknown"
    description = (description[:200] + "...") if description and len(description) > 200 else (description or "")
    hashtags = "#" + " #".join([t.replace(" ", "") for t in tags]) if tags else "#ArchivoVenezuela"

    # --- English Caption ---
    templates_en = [
        f"Discover *{title}* by {creator}, now part of Archivo Venezuela's digital collection. {description}",
        f"New from Archivo Venezuela: *{title}* by {creator}. Explore this cultural piece — {description}",
        f"Explore the story of *{title}* by {creator}, a new addition to our archive. {description}",
    ]
    caption_en = random.choice(templates_en)

    # --- Spanish Caption (translated) ---
    try:
        translated_caption = translator.translate(caption_en, src="en", dest="es").text
    except Exception:
        translated_caption = f"Descubre {title} de {creator}, ahora en el archivo. {description}"

    # --- Hashtags (auto-translated too) ---
    try:
        hashtags_es = translator.translate(hashtags, src="en", dest="es").text
    except Exception:
        hashtags_es = hashtags

    return {
        "Caption_EN": caption_en,
        "Caption_ES": translated_caption,
        "Hashtags": f"{hashtags} / {hashtags_es}"
    }
