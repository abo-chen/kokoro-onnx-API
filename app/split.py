"""Sentence splitting using spaCy sentencizer."""

import logging
import re

import spacy

logger = logging.getLogger(__name__)

# spaCy pipelines: lang -> nlp instance (blank model + sentencizer)
_nlp_pipelines: dict[str, spacy.Language] = {}

# Runtime thresholds (set during init from config)
_max_chars: int = 500       # sentence merge threshold (prosody)
_batch_chars: int = 600     # default mode: accumulated chars before mid-request CUDA release
_batch_phonemes: int = 200  # zh/ja mode: accumulated phonemes before mid-request CUDA release

# Empirical VRAM: ~2.2 MB per char (measured on kokoro primary model, English).
# Chinese/Japanese: each char ≈ 1 phoneme ≈ 1 token, ~4x denser than English.
_VRAM_PER_CHAR_MB = 2.2
_ZH_DENSITY_FACTOR = 4      # zh/ja: each char ≈ 1 phoneme, English ~4 chars/token
_SAFETY_MARGIN_MB = 200
_BASE_VRAM_NO_ZH = 925
_BASE_VRAM_WITH_ZH = 1493


def calc_thresholds(gpu_mem_limit_mb: int, zh_enabled: bool) -> tuple[int, int, int]:
    """Calculate splitting thresholds from GPU VRAM budget.

    Returns (max_chars, batch_chars, batch_phonemes):
    - max_chars: sentence merge threshold (for prosody quality)
    - batch_chars: default mode — accumulated chars before mid-request CUDA release
    - batch_phonemes: zh/ja mode — accumulated phonemes before mid-request CUDA release
    """
    base = _BASE_VRAM_WITH_ZH if zh_enabled else _BASE_VRAM_NO_ZH
    available = gpu_mem_limit_mb - base - _SAFETY_MARGIN_MB
    if available <= 0:
        return 300, 300, 200

    # Default mode: measured ~2.2 MB/char
    batch_chars = max(300, min(int(available / _VRAM_PER_CHAR_MB), 600))

    # zh/ja mode: each Chinese char ≈ 1 phoneme ≈ 1 token.
    # English: ~4 chars/token, so phonemes are ~4x denser per unit.
    # VRAM per phoneme ≈ VRAM_PER_CHAR * 4
    batch_phonemes = max(100, min(int(available / (_VRAM_PER_CHAR_MB * _ZH_DENSITY_FACTOR)), 500))

    # Merge threshold: generous since mid-release handles VRAM safety
    max_chars = min(batch_chars, 500)

    return max_chars, batch_chars, batch_phonemes


def init_splitters(gpu_mem_limit_mb: int = 2048, zh_enabled: bool = True,
                   split_max_chars: int = 0, split_batch_chars: int = 0):
    """Initialize spaCy sentencizer pipelines. Call during app startup."""
    global _max_chars, _batch_chars, _batch_phonemes

    max_chars, batch_chars, batch_phonemes = calc_thresholds(gpu_mem_limit_mb, zh_enabled)

    # Manual overrides
    if split_max_chars > 0:
        max_chars = split_max_chars
    if split_batch_chars > 0:
        batch_chars = split_batch_chars

    _max_chars = max_chars
    _batch_chars = batch_chars
    _batch_phonemes = batch_phonemes

    logger.info(
        f"Split thresholds: max_chars={_max_chars}, "
        f"batch_chars={_batch_chars}, batch_phonemes={_batch_phonemes} "
        f"(gpu={gpu_mem_limit_mb}MB, zh={'on' if zh_enabled else 'off'})"
    )

    for lang in ("en", "fr"):
        try:
            nlp = spacy.blank(lang)
            nlp.add_pipe("sentencizer")
            _nlp_pipelines[lang] = nlp
            logger.info(f"Sentence splitter ({lang}) loaded")
        except Exception as e:
            logger.warning(f"Sentence splitter ({lang}) not available: {e}")


def get_batch_chars() -> int:
    return _batch_chars


def get_batch_phonemes() -> int:
    return _batch_phonemes


# Voice prefix -> split language mapping (reuse tn.py voice mapping)
_VOICE_LANG = {
    "af": "en", "am": "en",
    "bf": "en", "bm": "en",
    "ff": "fr", "fm": "fr",
}


def split_sentences(text: str, lang: str | None = None) -> list[str]:
    """Split text into sentences.

    Uses spaCy sentencizer for en/fr (smart punctuation handling).
    Falls back to regex for zh/ja (CJK punctuation is unambiguous).
    Then merges short sentences up to _max_chars per chunk.
    """
    if not text.strip():
        return [text]

    nlp = _nlp_pipelines.get(lang) if lang else None

    if nlp:
        sentences = _spacy_split(nlp, text)
    else:
        sentences = _regex_split(text)

    if not sentences:
        return [text]

    return _merge_sentences(sentences, _max_chars)


def _spacy_split(nlp: spacy.Language, text: str) -> list[str]:
    """Split using spaCy sentencizer."""
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def _regex_split(text: str) -> list[str]:
    """Regex fallback for CJK languages."""
    parts = re.split(r'(?<=[。！？.!?\n])\s*', text)
    return [p.strip() for p in parts if p.strip()]


def _merge_sentences(sentences: list[str], max_chars: int) -> list[str]:
    """Merge short sentences to avoid too many tiny TTS chunks."""
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = current + (" " if current else "") + sentence
    if current:
        chunks.append(current)
    return chunks
