import asyncio
import logging
import time
import warnings
from contextlib import asynccontextmanager

import onnxruntime as rt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from kokoro_onnx import Kokoro

from app.config import settings
from app.routers import models as models_router
from app.routers import speech as speech_router

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

kokoro_lock = asyncio.Lock()
kokoro_instance: Kokoro | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kokoro_instance
    logger.info(f"Loading model from {settings.MODEL_PATH}")
    t0 = time.time()
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    session = rt.InferenceSession(settings.MODEL_PATH, providers=providers)
    logger.info(f"ONNX session providers: {session.get_providers()}")
    kokoro_instance = Kokoro.from_session(session, settings.VOICES_PATH)
    logger.info(f"Model loaded in {time.time() - t0:.1f}s, voices: {kokoro_instance.get_voices()}")

    speech_router.set_kokoro(kokoro_instance, kokoro_lock)
    models_router.set_kokoro(kokoro_instance)

    # Warmup: trigger CUDA kernel compilation
    if "CUDAExecutionProvider" in session.get_providers():
        logger.info("Warming up GPU...")
        t1 = time.time()
        kokoro_instance.create("Warmup.", voice="af_heart", speed=1.0)
        logger.info(f"Warmup done in {time.time() - t1:.1f}s")
    else:
        logger.info("GPU not available, running in CPU mode")

    yield

    kokoro_instance = None


app = FastAPI(
    title="Kokoro TTS API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(speech_router.router, prefix="/v1")
app.include_router(models_router.router, prefix="/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "The server had an error while processing your request.",
                "type": "server_error",
                "param": None,
                "code": None,
            }
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
