"""Sentence splitting using spaCy sentencizer."""

import logging
import re

import spacy

logger = logging.getLogger(__name__)

# spaCy pipelines: lang -> nlp instance (blank model + sentencizer)
_nlp_pipelines: dict[str, spacy.Language] = {}


def init_splitters():
    """Initialize spaCy sentencizer pipelines. Call during app startup."""
    for lang in ("en", "fr"):
        try:
            nlp = spacy.blank(lang)
            nlp.add_pipe("sentencizer")
            _nlp_pipelines[lang] = nlp
            logger.info(f"Sentence splitter ({lang}) loaded")
        except Exception as e:
            logger.warning(f"Sentence splitter ({lang}) not available: {e}")


# Voice prefix -> split language mapping (reuse tn.py voice mapping)
_VOICE_LANG = {
    "af": "en", "am": "en",
    "bf": "en", "bm": "en",
    "ff": "fr", "fm": "fr",
}


def split_sentences(text: str, lang: str | None = None, max_chars: int = 400) -> list[str]:
    """Split text into sentences.

    Uses spaCy sentencizer for en/fr (smart punctuation handling).
    Falls back to regex for zh/ja (CJK punctuation is unambiguous).
    Then merges short sentences to avoid too many tiny TTS chunks.
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

    return _merge_sentences(sentences, max_chars)


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
