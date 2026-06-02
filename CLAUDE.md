# kokoro-onnx API

OpenAI-compatible TTS API built on [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx). FastAPI + ONNX Runtime, deployed via Docker.

## Architecture

```
app/
  main.py          # FastAPI app, lifespan (model loading), global error handler
  config.py        # Settings from .env (pydantic-settings)
  models.py        # Pydantic request/response models
  g2p.py           # Chinese mixed CN/EN G2P (dict → abbreviations → g2p_en fallback)
  tn.py            # English/French text normalization (nemo_text_processing WFST)
  split.py         # Sentence splitting (spaCy sentencizer for en/fr, regex fallback for zh/ja)
  audio.py         # Audio encoding (PyAV: mp3/wav/flac/aac/pcm)
  auth.py          # Optional Bearer token auth middleware
  timing.py        # DEBUG_TIMING: Timer context manager + VRAM logging
  routers/
    speech.py      # POST /v1/audio/speech, VRAM release via set_providers
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
- Chinese percentage normalization: regex-based preprocessor in `app/g2p.py` (`_normalize_percent`) converts `99.9%` → `百分之九十九点九` before G2P. Handles decimals and integers.

## Text Normalization (TN)

English and French text is preprocessed by [nemo_text_processing](https://github.com/NVIDIA/NeMo-text-processing) before G2P. This handles:
- Numbers: `1,000` → `one thousand`, `2024` → `twenty twenty four`
- Symbols: `C++` → `C plus plus`, `C#` → `c sharp`, `Node.js` → `node dot js`
- Abbreviations: `Dr.` → `doctor`, `St.` → `Street`
- Electronic text: `user@email.com` → `user at email dot com`, URLs expanded
- Currency: `$3.14` → `three dollars fourteen cents`
- French-specific: `1 500 euros` → `mille cinq cents euros`, `99,5%` → `quatre-vingt-dix-neuf virgule cinq pour cent`

Language detection: TN language is inferred from voice ID prefix (`af`/`am`/`bf`/`bm` → English, `ff`/`fm` → French). No need to specify `language` parameter — the voice determines the language, same as Edge TTS. The `language` parameter is deprecated and ignored. TN is only applied to the default (non-Chinese, non-Japanese) mode.

TN adds ~10s to startup (FST grammar compilation for en+fr), ~50MB to Docker image, and microseconds per request at runtime. No GPU usage.

## Sentence Splitting

Long text is split into sentences before TTS to bound peak VRAM. The splitting strategy varies by language:

- **English/French (default mode):** [spaCy](https://spacy.io/) sentencizer on blank models (`spacy.blank("en")` / `spacy.blank("fr")` + sentencizer pipe). Handles abbreviations, Roman numerals, decimal numbers, ellipsis — much smarter than simple regex. Runs after TN, so most abbreviation periods are already resolved.
- **Chinese/Japanese:** Regex fallback (`(?<=[。！？.!?\n])`) — CJK punctuation is unambiguous, no need for NLP.

After splitting, short sentences are merged up to `max_chars` (auto-derived from VRAM budget) for better prosodic continuity.

### Mid-request VRAM release

ONNX BFC arena accumulates VRAM across sentences within a single request and never shrinks. To bound peak VRAM for long text, CUDA is released and reloaded mid-request when accumulated chars/phonemes exceed a threshold:

- **default mode:** tracks accumulated chars, releases at `batch_chars` threshold (~2.2 MB/char)
- **zh/ja mode:** tracks accumulated phonemes, releases at `batch_phonemes` threshold (Chinese chars ~4x denser than English)

Both thresholds are auto-derived from `GPU_MEM_LIMIT_MB`. Each mid-release adds ~0.5s overhead but keeps VRAM within budget regardless of total text length. Manual override via `SPLIT_MAX_CHARS` / `SPLIT_BATCH_CHARS` env.

Startup overhead: ~1.2s for en+fr. No model download needed. `app/split.py`.

## Known Issues & Patches

- **Speed < 1.0 bug**: The kokoro-onnx library (v0.5.0) casts speed to `np.int32` for `input_ids` format models, making only 0.5→0, 1.0→1, 2.0→2 work. Patched in Dockerfile: `sed -i 's/dtype=np.int32)/dtype=np.float32)/'`. The HuggingFace Chinese model also fixes this at the ONNX level.
- **Speed range**: 0.5 to 2.0. Values outside this range cause runtime errors.
- **VRAM**: ONNX BFC arena grows monotonically and never releases memory. After each TTS request, CUDA provider is unloaded via `session.set_providers(["CPUExecutionProvider"])` to release VRAM, then reloaded before the next request. Adds ~0.3-0.5s overhead per request. `gpu_mem_limit` configurable via `GPU_MEM_LIMIT_MB` env (default 2048=2GB). For long text, mid-request CUDA release bounds arena accumulation (see Sentence Splitting section).
- **DEBUG_TIMING**: Env toggle (`DEBUG_TIMING=true`) logs timing + VRAM at key points (model load, CUDA reload/release, per-sentence inference). `app/timing.py`.

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

Key variables: `API_KEY`, `AUTH_ENABLED`, `MODEL_PATH`, `VOICES_PATH`, `HOST`, `PORT`, `ZH_ENABLED`, `ZH_MODEL_PATH`, `ZH_VOICES_PATH`, `ZH_VOCAB_CONFIG`, `GPU_MEM_LIMIT_MB`, `DEBUG_TIMING`. Defaults in `app/config.py`.

## Development

```bash
uv sync                    # Install dependencies
uv run python -m uvicorn app.main:app --reload  # Dev server
```

User language preference: Chinese (中文).
