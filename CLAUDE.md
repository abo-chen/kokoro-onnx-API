# kokoro-onnx API

OpenAI-compatible TTS API built on [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx). FastAPI + ONNX Runtime, deployed via Docker.

## Architecture

```
app/
  main.py          # FastAPI app, lifespan (model loading), global error handler
  config.py        # Settings from .env (pydantic-settings)
  models.py        # Pydantic request/response models
  g2p.py           # Chinese mixed CN/EN G2P (dict → abbreviations → g2p_en fallback)
  audio.py         # Audio encoding (PyAV: mp3/wav/flac/aac/pcm)
  auth.py          # Optional Bearer token auth middleware
  routers/
    speech.py      # POST /v1/audio/speech
    models.py      # GET /v1/models, GET /v1/audio/voices
models/            # ONNX model files (~962MB)
voices/            # Voice bin files (~79MB)
data/unidic/       # UniDic dictionary for Japanese (~775MB)
static/            # Demo page served at /demo
```

## Models & Voices

- **Primary model** (`kokoro-v0_19.fp16.onnx`): English + multilingual (50+ voices, 9 languages). Input format: `tokens`.
- **Chinese model** (`kokoro-v1.1-zh.onnx`): Mandarin only. Input format: `input_ids`. Sourced from HuggingFace `onnx-community/Kokoro-82M-v1.1-zh-ONNX` (not the GitHub releases version — the releases version has a speed bug).
- Chinese model has its own voice set (`zf_001`-`zf_099`, `zm_009`-`zm_100`). Built-in EN voices (`af_maple`, `af_sol`, `bf_vale`) are hidden from the list endpoint.
- Voice routing: `zf_*/zm_*` prefix → Chinese model, Chinese characters in input → Chinese model, `jf_*/jm_*` → primary model with Japanese G2P, everything else → primary model.

## Known Issues & Patches

- **Speed < 1.0 bug**: The kokoro-onnx library (v0.5.0) casts speed to `np.int32` for `input_ids` format models, making only 0.5→0, 1.0→1, 2.0→2 work. Patched in Dockerfile: `sed -i 's/dtype=np.int32)/dtype=np.float32)/'`. The HuggingFace Chinese model also fixes this at the ONNX level.
- **Speed range**: 0.5 to 2.0. Values outside this range cause runtime errors.
- **VRAM**: ONNX CUDA arena grows monotonically. Mitigated with `arena_extend_strategy: kSameAsRequested`, `gpu_mem_limit: 2GB`.

## Docker

- `docker compose up -d` → GPU mode (default, requires NVIDIA GPU + Container Toolkit)
- `docker compose -f docker-compose.cpu.yml up -d` → CPU mode (base: `python:3.12-slim`)
- `data/` is volume-mounted (`./data:/app/data`) so UniDic persists across rebuilds
- UniDic auto-downloads to `data/unidic/` on first use if not present
- **Platform:** x86_64 only. ARM (Apple Silicon, Raspberry Pi) not supported.

## API Endpoints

- `POST /v1/audio/speech` — Generate speech (OpenAI-compatible)
- `GET /v1/audio/voices` — List voices with language info
- `GET /v1/models` — List loaded models
- `GET /demo` — Interactive demo page

## Configuration (.env)

Key variables: `API_KEY`, `AUTH_ENABLED`, `MODEL_PATH`, `VOICES_PATH`, `HOST`, `PORT`, `ZH_ENABLED`, `ZH_MODEL_PATH`, `ZH_VOICES_PATH`, `ZH_VOCAB_CONFIG`. Defaults in `app/config.py`.

## Development

```bash
uv sync                    # Install dependencies
uv run python -m uvicorn app.main:app --reload  # Dev server
```

User language preference: Chinese (中文).
