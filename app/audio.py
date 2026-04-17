import io

import av
import numpy as np
import soundfile as sf

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


def _encode_with_av(
    samples: np.ndarray, sample_rate: int, codec: str, container_format: str, bitrate: int = 128000
) -> bytes:
    """Encode PCM samples using PyAV (in-process, no subprocess)."""
    int16 = (samples * 32767).astype(np.int16)
    buf = io.BytesIO()
    container = av.open(buf, mode="w", format=container_format)
    stream = container.add_stream(codec, rate=sample_rate, layout="mono")
    stream.bit_rate = bitrate

    frame = av.AudioFrame.from_ndarray(int16.reshape(1, -1), format="s16", layout="mono")
    frame.sample_rate = sample_rate

    for packet in stream.encode(frame):
        container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)

    container.close()
    return buf.getvalue()


def pcm_to_mp3_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    return _encode_with_av(samples, sample_rate, codec="mp3", container_format="mp3", bitrate=128000)


def pcm_to_aac_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    return _encode_with_av(samples, sample_rate, codec="aac", container_format="adts", bitrate=128000)


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
