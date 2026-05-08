"""Text normalization for TTS using nemo_text_processing."""

import logging

logger = logging.getLogger(__name__)

_normalizers: dict[str, object] = {}


def init_normalizer():
    """Initialize text normalizers. Call during app startup."""
    from nemo_text_processing.text_normalization.normalize import Normalizer

    for lang in ("en", "fr"):
        try:
            _normalizers[lang] = Normalizer(
                input_case="cased",
                lang=lang,
                deterministic=True,
            )
            logger.info(f"Text normalizer ({lang}) loaded")
        except Exception as e:
            logger.warning(f"Text normalizer ({lang}) not available: {e}")


# Voice prefix → TN language mapping
_VOICE_LANG = {
    "af": "en", "am": "en",
    "bf": "en", "bm": "en",
    "ff": "fr", "fm": "fr",
}


def normalize_text(text: str, lang: str | None = None) -> str:
    """Normalize text for TTS. Auto-detects language if not specified."""
    if not _normalizers:
        return text

    normalizer = _normalizers.get(lang)
    if normalizer is None:
        return text
    try:
        return normalizer.normalize(text, verbose=False)
    except Exception as e:
        logger.warning(f"Text normalization ({lang}) failed: {e}")
        return text
