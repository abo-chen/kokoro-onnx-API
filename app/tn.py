"""Text normalization for TTS using nemo_text_processing."""

import logging
import re

logger = logging.getLogger(__name__)

_normalizers: dict[str, object] = {}

_FRENCH_CHARS = re.compile(r"[éèêëàâùûüçîïôœæÉÈÊËÀÂÙÛÜÇÎÏÔŒÆ]")


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


def normalize_text(text: str, lang: str | None = None) -> str:
    """Normalize text for TTS. Auto-detects language if not specified."""
    if not _normalizers:
        return text

    if lang is None:
        lang = "fr" if _FRENCH_CHARS.search(text) else "en"

    normalizer = _normalizers.get(lang)
    if normalizer is None:
        return text
    try:
        return normalizer.normalize(text, verbose=False)
    except Exception as e:
        logger.warning(f"Text normalization ({lang}) failed: {e}")
        return text
