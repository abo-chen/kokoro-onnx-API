# kokoro-onnx API

OpenAI-compatible TTS API powered by [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), deployed with Docker.

## Features

- OpenAI-compatible API (`POST /v1/audio/speech`, `GET /v1/models`)
- 50+ voices across 9 languages (English, Mandarin, Japanese, Spanish, French, Hindi, Italian, Portuguese)
- Chinese model with mixed CN/EN support (tech terms, abbreviations, English words)
- Japanese TTS via misaki-fork[ja] G2P with unidic dictionary
- Text chunking for long input (sentence-level splitting to reduce VRAM usage)
- Multiple audio formats: MP3, WAV, FLAC, AAC, PCM (PyAV, no ffmpeg subprocess)
- Streaming and non-streaming response modes
- GPU (CUDA) and CPU deployment modes
- Optional Bearer Token authentication
- Interactive demo page at `/demo`

## Quick Start

### 1. Download Model Files

```bash
mkdir -p models voices

# Primary model (English/multilingual)
curl -L -o models/kokoro-v0_19.fp16.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.fp16.onnx

curl -L -o voices/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

# Chinese model (optional, enables Chinese + mixed CN/EN)
curl -L -o models/kokoro-v1.1-zh.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.1-zh.onnx

curl -L -o voices/voices-v1.1-zh.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.1-zh.bin

curl -L -o models/config.json \
  https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh/raw/main/config.json
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env as needed
```

### 3. Run with Docker

**GPU mode (default):**

```bash
docker compose up -d
```

**CPU mode:**

```bash
docker compose -f docker-compose.cpu.yml up -d
```

The service will be available at `http://localhost:5023`.

## API Endpoints

### POST /v1/audio/speech

Generate speech audio.

```bash
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Authorization: Bearer sk-kokoro" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hello, world!",
    "voice": "af_nicole",
    "response_format": "mp3",
    "speed": 1.0,
    "stream": false
  }' \
  --output speech.mp3
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | `"kokoro"` | Model name |
| `input` | string | required | Text to synthesize (max 4096 chars) |
| `voice` | string | `"af_nicole"` | Voice name |
| `response_format` | string | `"mp3"` | `mp3`, `wav`, `flac`, `aac`, `pcm` |
| `speed` | float | `1.0` | Speed (0.25 - 4.0) |
| `stream` | bool | `false` | Enable streaming response |

### GET /v1/models

```bash
curl http://localhost:5023/v1/models
```

### GET /demo

Interactive demo page for testing speech synthesis in the browser.

### GET /v1/audio/voices

List available voices with language info:

```bash
curl http://localhost:5023/v1/audio/voices
```

```json
{
  "object": "list",
  "data": [
    {"id": "af_heart", "language": "en", "description": "US Female"},
    {"id": "zf_xiaoxiao", "language": "cmn", "description": "Mandarin Female"},
    {"id": "am_adam", "language": "en", "description": "US Male"}
  ]
}
```

## Japanese TTS

Japanese voices (`jf_*` / `jm_*`) use the primary model with misaki-fork[ja] G2P for text-to-phoneme conversion. The unidic dictionary (~775MB) is automatically downloaded on first use and persisted via Docker volume. Long text is split at sentence boundaries to reduce VRAM usage.

```bash
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "こんにちは、世界！", "voice": "jf_heart"}' \
  --output japanese.wav
```

## Chinese & Mixed Language Support

When the Chinese model is enabled (`ZH_ENABLED=true`), the API automatically detects Chinese characters in the input text and routes to the Chinese model with a three-level G2P strategy for handling embedded English words:

1. **High-frequency dictionary** - exact match for known tech terms and common words
   - `GitHub` → 给特哈布, `Docker` → 多克, `bug` → 巴格, `Python` → 派森
2. **Uppercase abbreviations** - letter-by-letter spelling (e.g. `API`, `GPU`, `SSH`)
3. **g2p_en fallback** - ARPABET phoneme prediction mapped to Chinese characters for unknown English words

### Chinese model voices

The Chinese model has its own voice set (`zf_001` - `zf_099`, `zm_009` - `zm_100`). When using a Chinese voice (`zf_*` / `zm_*`) or when input contains Chinese characters, the Chinese model is used automatically.

```bash
# Pure Chinese
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "千里之行，始于足下。", "voice": "zf_001"}' \
  --output chinese.wav

# Mixed Chinese + English
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "我用Docker跑了一个API服务，用的GPU加速。", "voice": "zf_001"}' \
  --output mixed.wav
```

## Configuration

Environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `sk-kokoro` | Bearer token for authentication |
| `AUTH_ENABLED` | `false` | Enable authentication |
| `MODEL_PATH` | `models/kokoro-v0_19.fp16.onnx` | Path to primary ONNX model |
| `VOICES_PATH` | `voices/voices-v1.0.bin` | Path to primary voices file |
| `HOST` | `0.0.0.0` | Listen host |
| `PORT` | `5023` | Listen port |
| `ZH_ENABLED` | `true` | Enable Chinese model |
| `ZH_MODEL_PATH` | `models/kokoro-v1.1-zh.onnx` | Path to Chinese ONNX model |
| `ZH_VOICES_PATH` | `voices/voices-v1.1-zh.bin` | Path to Chinese voices file |
| `ZH_VOCAB_CONFIG` | `models/config.json` | Path to Chinese vocab config |

## Available Voices

### Primary model (English/multilingual)

| Prefix | Language | Description |
|--------|----------|-------------|
| `af_` | English (US) | Female |
| `am_` | English (US) | Male |
| `bf_` | English (UK) | Female |
| `bm_` | English (UK) | Male |
| `zf_` | Mandarin | Female |
| `zm_` | Mandarin | Male |
| `jf_` | Japanese | Female |
| `jm_` | Japanese | Male |
| `ef_` | Spanish | Female |
| `em_` | Spanish | Male |
| `ff_` | French | Female |
| `hf_` | Hindi | Female |
| `hm_` | Hindi | Male |
| `if_` | Italian | Female |
| `im_` | Italian | Male |
| `pf_` | Portuguese (BR) | Female |
| `pm_` | Portuguese (BR) | Male |

### Chinese model

The voices list endpoint only returns Chinese voices (`zf_*` / `zm_*`) from this model. Built-in English voices (`af_maple`, `af_sol`, `bf_vale`) still work but are hidden to avoid confusion with the primary model's English voices. To show all voices, remove the filter in `app/routers/models.py`.

| Prefix | Range | Description |
|--------|-------|-------------|
| `af_maple` / `af_sol` / `bf_vale` | English voices | English (built-in, hidden from voices list) |
| `zf_` | `zf_001` - `zf_099` | Mandarin Female |
| `zm_` | `zm_009` - `zm_100` | Mandarin Male |

## GPU Memory (VRAM) Behavior

ONNX Runtime's CUDA allocator uses an arena (memory pool) that grows monotonically — memory is never returned to the GPU once allocated. This project configures the following CUDA provider options to mitigate unbounded VRAM growth:

- `arena_extend_strategy: kSameAsRequested` — allocate only what's needed instead of doubling (default `kNextPowerOfTwo`)
- `cudnn_conv_algo_search: HEURISTIC` — avoid exhaustive algorithm benchmarking that allocates large temporary workspaces
- `gpu_mem_limit: 2GB` — hard cap on arena allocation

With these settings, VRAM stabilizes within the same language after repeated generation:

| Scenario | Stable VRAM |
|----------|-------------|
| Baseline (idle) | ~1300 MB |
| English (97s audio, repeated) | ~2013 MB |
| Chinese (97s audio, repeated) | ~2300 MB |
| Japanese (82s audio, repeated) | ~2314 MB |
| Switching between languages | up to ~4 GB |

Short text generation stays near baseline with minimal VRAM increase.

Japanese uses G2P (text → phonemes → audio) with the primary model, while Chinese uses a separate model. Japanese phoneme sequences are longer than raw text, resulting in higher per-second VRAM usage compared to English and Chinese.

> **Note:** VRAM values are for reference only and may vary by GPU, driver, and input content.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- **GPU mode:** [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) + NVIDIA GPU

## License

MIT
