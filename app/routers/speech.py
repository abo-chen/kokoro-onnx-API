import asyncio
import logging
import time

import numpy as np
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse

from app.audio import encode_audio, get_content_type, needs_full_audio
from app.auth import verify_api_key
from app.models import SpeechRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["audio"])

# Global reference set by lifespan
kokoro = None
kokoro_lock: asyncio.Lock | None = None


def set_kokoro(instance, lock: asyncio.Lock):
    global kokoro, kokoro_lock
    kokoro = instance
    kokoro_lock = lock


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

    # Validate voice exists
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
        return await _stream_response(body, fmt, content_type)
    else:
        return await _full_response(body, fmt, content_type)


async def _full_response(body: SpeechRequest, fmt: str, content_type: str) -> Response:
    start = time.time()

    async with kokoro_lock:
        samples, sample_rate = await asyncio.to_thread(
            kokoro.create, body.input, body.voice, body.speed
        )

    audio_bytes = encode_audio(samples, sample_rate, fmt)
    elapsed_ms = int((time.time() - start) * 1000)
    logger.info(f"Generated {len(samples)} samples in {elapsed_ms}ms (non-stream)")

    return Response(
        content=audio_bytes,
        media_type=content_type,
        headers={"x-processing-ms": str(elapsed_ms)},
    )


async def _stream_response(body: SpeechRequest, fmt: str, content_type: str) -> StreamingResponse:
    if needs_full_audio(fmt):
        # MP3/AAC: collect all chunks, then encode
        async def generate():
            start = time.time()
            all_samples = []
            async with kokoro_lock:
                async for samples, sample_rate in kokoro.create_stream(
                    body.input, body.voice, body.speed
                ):
                    all_samples.append(samples)
            combined = np.concatenate(all_samples)
            audio_bytes = encode_audio(combined, sample_rate, fmt)
            elapsed_ms = int((time.time() - start) * 1000)
            logger.info(f"Generated {len(combined)} samples in {elapsed_ms}ms (pseudo-stream {fmt})")
            yield audio_bytes

        return StreamingResponse(generate(), media_type=content_type)
    else:
        # WAV/FLAC/PCM: true streaming per chunk
        async def generate():
            start = time.time()
            chunk_count = 0
            async with kokoro_lock:
                async for samples, sample_rate in kokoro.create_stream(
                    body.input, body.voice, body.speed
                ):
                    chunk_count += 1
                    yield encode_audio(samples, sample_rate, fmt)
            elapsed_ms = int((time.time() - start) * 1000)
            logger.info(f"Streamed {chunk_count} chunks in {elapsed_ms}ms (true-stream {fmt})")

        return StreamingResponse(generate(), media_type=content_type)
