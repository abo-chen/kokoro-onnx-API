import asyncio
import logging
import time

import numpy as np
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse

from app.audio import encode_audio, get_content_type, needs_full_audio
from app.auth import verify_api_key
from app.g2p import contains_chinese, replace_english
from app.models import SpeechRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio"])

# Global reference set by lifespan
kokoro = None
kokoro_lock: asyncio.Lock | None = None

# Chinese model references
zh_kokoro = None
zh_lock: asyncio.Lock | None = None
zh_g2p = None

# Japanese G2P (misaki-fork[ja])
ja_g2p = None


def set_kokoro(instance, lock: asyncio.Lock):
    global kokoro, kokoro_lock
    kokoro = instance
    kokoro_lock = lock


def set_zh_kokoro(instance, lock: asyncio.Lock, g2p):
    global zh_kokoro, zh_lock, zh_g2p
    zh_kokoro = instance
    zh_lock = lock
    zh_g2p = g2p


def set_ja_g2p(g2p):
    global ja_g2p
    ja_g2p = g2p


def _get_mode(body: SpeechRequest) -> str:
    """Determine processing mode: 'zh', 'ja', or 'default'."""
    # Chinese voices -> Chinese model
    if body.voice.startswith(("zf_", "zm_")):
        return "zh"
    # Japanese voices -> Japanese G2P with primary model
    if body.voice.startswith(("jf_", "jm_")):
        return "ja" if ja_g2p is not None else "default"
    # Text contains Chinese -> Chinese model
    if contains_chinese(body.input):
        return "zh"
    return "default"


def _resolve_zh_voice(voice: str) -> str:
    """Map a voice name to a valid Chinese model voice if needed."""
    available = zh_kokoro.get_voices()
    if voice in available:
        return voice
    prefix_map = {
        "af": "zf_001",
        "am": "zm_009",
        "bf": "zf_001",
        "bm": "zm_009",
    }
    prefix = voice.split("_")[0] if "_" in voice else "zf"
    return prefix_map.get(prefix, "zf_001")


@router.post("/audio/speech")
async def create_speech(
    request: Request,
    body: SpeechRequest,
    _auth: None = Depends(verify_api_key),
):
    if kokoro is None:
        return Response(
            content='{"error":{"message":"Model not loaded","type":"server_error","param":null,"code":null}}',
            status_code=503,
            media_type="application/json",
        )

    mode = _get_mode(body)

    if mode == "zh":
        available_voices = zh_kokoro.get_voices()
        voice = _resolve_zh_voice(body.voice)
        if voice not in available_voices:
            return Response(
                content=f'{{"error":{{"message":"Voice \\"{body.voice}\\" not found in Chinese model. Available: {available_voices}","type":"invalid_request_error","param":"voice","code":null}}}}',
                status_code=400,
                media_type="application/json",
            )
    else:
        available_voices = kokoro.get_voices()
        if body.voice not in available_voices:
            return Response(
                content=f'{{"error":{{"message":"Voice \\"{body.voice}\\" not found. Available: {available_voices}","type":"invalid_request_error","param":"voice","code":null}}}}',
                status_code=400,
                media_type="application/json",
            )

    fmt = body.response_format
    content_type = get_content_type(fmt)

    if body.stream:
        return await _stream_response(body, fmt, content_type, mode)
    else:
        return await _full_response(body, fmt, content_type, mode)


async def _generate_samples(body: SpeechRequest, mode: str):
    """Generate audio samples based on mode. Returns (samples, sample_rate)."""
    if mode == "zh":
        text = replace_english(body.input)
        voice = _resolve_zh_voice(body.voice)
        async with zh_lock:
            phonemes, _ = await asyncio.to_thread(zh_g2p, text)
            samples, sample_rate = await asyncio.to_thread(
                zh_kokoro.create, phonemes, voice, body.speed, is_phonemes=True
            )
    elif mode == "ja":
        async with kokoro_lock:
            phonemes, _ = await asyncio.to_thread(ja_g2p, body.input)
            samples, sample_rate = await asyncio.to_thread(
                kokoro.create, phonemes, body.voice, body.speed, is_phonemes=True
            )
    else:
        async with kokoro_lock:
            samples, sample_rate = await asyncio.to_thread(
                kokoro.create, body.input, body.voice, body.speed
            )
    return samples, sample_rate


async def _full_response(body: SpeechRequest, fmt: str, content_type: str, mode: str) -> Response:
    start = time.time()

    samples, sample_rate = await _generate_samples(body, mode)

    audio_bytes = encode_audio(samples, sample_rate, fmt)
    elapsed_ms = int((time.time() - start) * 1000)
    logger.info(f"Generated {len(samples)} samples in {elapsed_ms}ms ({mode}, non-stream)")

    return Response(
        content=audio_bytes,
        media_type=content_type,
        headers={"x-processing-ms": str(elapsed_ms)},
    )


async def _stream_response(body: SpeechRequest, fmt: str, content_type: str, mode: str) -> StreamingResponse:
    if needs_full_audio(fmt):
        async def generate():
            start = time.time()
            samples, sample_rate = await _generate_samples(body, mode)
            audio_bytes = encode_audio(samples, sample_rate, fmt)
            elapsed_ms = int((time.time() - start) * 1000)
            logger.info(f"Generated {len(samples)} samples in {elapsed_ms}ms ({mode}, pseudo-stream {fmt})")
            yield audio_bytes

        return StreamingResponse(generate(), media_type=content_type)
    else:
        async def generate():
            start = time.time()
            chunk_count = 0
            if mode == "zh":
                text = replace_english(body.input)
                voice = _resolve_zh_voice(body.voice)
                async with zh_lock:
                    phonemes, _ = await asyncio.to_thread(zh_g2p, text)
                    samples, sample_rate = await asyncio.to_thread(
                        zh_kokoro.create, phonemes, voice, body.speed, is_phonemes=True
                    )
                    chunk_count = 1
                    yield encode_audio(samples, sample_rate, fmt)
            elif mode == "ja":
                async with kokoro_lock:
                    phonemes, _ = await asyncio.to_thread(ja_g2p, body.input)
                    samples, sample_rate = await asyncio.to_thread(
                        kokoro.create, phonemes, body.voice, body.speed, is_phonemes=True
                    )
                    chunk_count = 1
                    yield encode_audio(samples, sample_rate, fmt)
            else:
                async with kokoro_lock:
                    async for samples, sample_rate in kokoro.create_stream(
                        body.input, body.voice, body.speed
                    ):
                        chunk_count += 1
                        yield encode_audio(samples, sample_rate, fmt)
            elapsed_ms = int((time.time() - start) * 1000)
            logger.info(f"Streamed {chunk_count} chunks in {elapsed_ms}ms ({mode}, true-stream {fmt})")

        return StreamingResponse(generate(), media_type=content_type)
