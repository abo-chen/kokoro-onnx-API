import asyncio
import logging
import time
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
from contextlib import asynccontextmanager

import onnxruntime as rt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from kokoro_onnx import Kokoro

from app.config import settings
from app.routers import models as models_router
from app.routers import speech as speech_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

kokoro_lock = asyncio.Lock()
kokoro_instance: Kokoro | None = None

# Chinese model (optional)
zh_lock: asyncio.Lock | None = None
zh_kokoro: Kokoro | None = None
zh_g2p = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global kokoro_instance, zh_kokoro, zh_g2p, zh_lock

    # Load primary (English/multilingual) model
    logger.info(f"Loading model from {settings.MODEL_PATH}")
    t0 = time.time()

    # Configure session options to reduce memory usage
    so = rt.SessionOptions()
    so.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL

    # CUDA provider options to control arena growth and reduce VRAM accumulation
    providers = [
        ("CUDAExecutionProvider", {
            "device_id": "0",
            "gpu_mem_limit": "2147483648",  # 2GB hard cap on arena
            "arena_extend_strategy": "kSameAsRequested",  # allocate only what's needed
            "cudnn_conv_algo_search": "HEURISTIC",  # avoid exhaustive workspace allocation
        }),
        "CPUExecutionProvider",
    ]
    session = rt.InferenceSession(settings.MODEL_PATH, sess_options=so, providers=providers)
    logger.info(f"ONNX session providers: {session.get_providers()}")
    kokoro_instance = Kokoro.from_session(session, settings.VOICES_PATH, vocab_config="models/config.json")
    logger.info(f"Model loaded in {time.time() - t0:.1f}s, voices: {kokoro_instance.get_voices()}")

    speech_router.set_kokoro(kokoro_instance, kokoro_lock)

    # Warmup: trigger CUDA kernel compilation
    if "CUDAExecutionProvider" in session.get_providers():
        logger.info("Warming up GPU...")
        t1 = time.time()
        kokoro_instance.create("Warmup.", voice="af_heart", speed=1.0)
        logger.info(f"Warmup done in {time.time() - t1:.1f}s")
    else:
        logger.info("GPU not available, running in CPU mode")

    # Load Chinese model (optional)
    if settings.ZH_ENABLED:
        try:
            import os
            if not os.path.exists(settings.ZH_MODEL_PATH):
                logger.warning(f"Chinese model not found at {settings.ZH_MODEL_PATH}, skipping")
            else:
                from app.g2p import replace_english
                from misaki import zh

                logger.info(f"Loading Chinese model from {settings.ZH_MODEL_PATH}")
                t2 = time.time()
                zh_session = rt.InferenceSession(settings.ZH_MODEL_PATH, providers=providers)
                zh_kokoro = Kokoro.from_session(zh_session, settings.ZH_VOICES_PATH, vocab_config=settings.ZH_VOCAB_CONFIG)
                zh_g2p = zh.ZHG2P(version="1.1")
                zh_lock = asyncio.Lock()
                logger.info(f"Chinese model loaded in {time.time() - t2:.1f}s, voices: {zh_kokoro.get_voices()}")

                # Warmup Chinese model
                if "CUDAExecutionProvider" in zh_session.get_providers():
                    logger.info("Warming up Chinese model GPU...")
                    t3 = time.time()
                    phonemes, _ = zh_g2p("测试")
                    zh_kokoro.create(phonemes, voice="zf_001", speed=1.0, is_phonemes=True)
                    logger.info(f"Chinese warmup done in {time.time() - t3:.1f}s")
        except Exception as e:
            logger.warning(f"Failed to load Chinese model: {e}")
            zh_kokoro = None
            zh_g2p = None

    speech_router.set_zh_kokoro(zh_kokoro, zh_lock, zh_g2p)
    models_router.set_kokoro(kokoro_instance)
    models_router.set_zh_kokoro(zh_kokoro)

    # Load Japanese G2P (misaki-fork[ja])
    try:
        import os
        import shutil
        import tempfile
        from unidic import DICDIR
        from misaki import ja
        unidic_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "unidic")
        if not os.path.isfile(os.path.join(DICDIR, "sys.dic")):
            if os.path.isdir(unidic_data_dir) and os.path.isfile(os.path.join(unidic_data_dir, "sys.dic")):
                os.makedirs(DICDIR, exist_ok=True)
                for item in os.listdir(unidic_data_dir):
                    src = os.path.join(unidic_data_dir, item)
                    dst = os.path.join(DICDIR, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                logger.info("UniDic installed from data/unidic")
            else:
                logger.info("UniDic not found, downloading...")
                import urllib.request
                url = "https://cotonoha-dic.s3-ap-northeast-1.amazonaws.com/unidic-3.1.0.zip"
                zip_path = os.path.join(tempfile.gettempdir(), "unidic.zip")
                tmp_dir = os.path.join(tempfile.gettempdir(), "unidic_tmp")
                urllib.request.urlretrieve(url, zip_path)
                import zipfile
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(tmp_dir)
                os.remove(zip_path)
                extracted = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
                # Save to persistent data/unidic
                os.makedirs(unidic_data_dir, exist_ok=True)
                for item in os.listdir(extracted):
                    src = os.path.join(extracted, item)
                    dst = os.path.join(unidic_data_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                shutil.rmtree(tmp_dir)
                # Copy to DICDIR for runtime use
                os.makedirs(DICDIR, exist_ok=True)
                for item in os.listdir(unidic_data_dir):
                    src = os.path.join(unidic_data_dir, item)
                    dst = os.path.join(DICDIR, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                # Create mecabrc required by fugashi
                mecabrc_path = os.path.join(DICDIR, "mecabrc")
                if not os.path.isfile(mecabrc_path):
                    with open(mecabrc_path, "w") as f:
                        f.write(f"dicdir = {DICDIR}\n")
                mecabrc_data = os.path.join(unidic_data_dir, "mecabrc")
                if not os.path.isfile(mecabrc_data):
                    with open(mecabrc_data, "w") as f:
                        f.write(f"dicdir = {DICDIR}\n")
                logger.info("UniDic downloaded and saved to data/unidic")
        ja_g2p_instance = ja.JAG2P()
        speech_router.set_ja_g2p(ja_g2p_instance)
        logger.info("Japanese G2P loaded")
    except Exception as e:
        logger.warning(f"Failed to load Japanese G2P: {e}")
    models_router.set_zh_kokoro(zh_kokoro)

    yield

    kokoro_instance = None
    zh_kokoro = None
    zh_g2p = None


app = FastAPI(
    title="Kokoro TTS API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(speech_router.router, prefix="/v1")
app.include_router(models_router.router, prefix="/v1")

import os
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/demo", StaticFiles(directory=_static_dir, html=True), name="static")


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
