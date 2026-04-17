import io

import numpy as np
import soundfile as sf
from pydub import AudioSegment

MIME_TYPES: dict[str, str] = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "pcm": "audio/pcm",
}


def get_content_type(fmt: str) -> str:
    return MIME_TYPES.get(fmt, "application/octet-stream")


def pcm_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    return buf.getvalue()


def pcm_to_flac_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="FLAC")
    return buf.getvalue()


def _pcm_to_pydub_segment(samples: np.ndarray, sample_rate: int) -> AudioSegment:
    int16 = (samples * 32767).astype(np.int16)
    buf = io.BytesIO()
    sf.write(buf, int16, sample_rate, format="WAV", subtype="PCM_16")
    buf.seek(0)
    return AudioSegment.from_wav(buf)


def pcm_to_mp3_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    segment = _pcm_to_pydub_segment(samples, sample_rate)
    buf = io.BytesIO()
    segment.export(buf, format="mp3", bitrate="128k")
    return buf.getvalue()


def pcm_to_aac_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    segment = _pcm_to_pydub_segment(samples, sample_rate)
    buf = io.BytesIO()
    segment.export(buf, format="adts", bitrate="128k")
    return buf.getvalue()


def pcm_to_raw_bytes(samples: np.ndarray) -> bytes:
    int16 = (samples * 32767).astype(np.int16)
    return int16.tobytes()


ENCODERS: dict[str, tuple[bool, str]] = {
    # format: (needs_full_audio, description)
    "wav": (False, "pcm_to_wav_bytes"),
    "flac": (False, "pcm_to_flac_bytes"),
    "mp3": (True, "pcm_to_mp3_bytes"),
    "aac": (True, "pcm_to_aac_bytes"),
    "pcm": (False, "pcm_to_raw_bytes"),
}


def encode_audio(samples: np.ndarray, sample_rate: int, fmt: str) -> bytes:
    match fmt:
        case "wav":
            return pcm_to_wav_bytes(samples, sample_rate)
        case "flac":
            return pcm_to_flac_bytes(samples, sample_rate)
        case "mp3":
            return pcm_to_mp3_bytes(samples, sample_rate)
        case "aac":
            return pcm_to_aac_bytes(samples, sample_rate)
        case "pcm":
            return pcm_to_raw_bytes(samples)
        case _:
            raise ValueError(f"Unsupported format: {fmt}")


def needs_full_audio(fmt: str) -> bool:
    return ENCODERS.get(fmt, (True, ""))[0]
