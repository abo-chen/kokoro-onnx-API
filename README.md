# kokoro-onnx

OpenAI-compatible TTS API powered by [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), deployed with Docker.

## Features

- OpenAI-compatible API (`POST /v1/audio/speech`, `GET /v1/models`)
- 50+ voices across 9 languages (English, Mandarin, Japanese, Spanish, French, Hindi, Italian, Portuguese)
- Multiple audio formats: MP3, WAV, FLAC, AAC, PCM
- Streaming and non-streaming response modes
- GPU (CUDA) and CPU deployment modes
- Optional Bearer Token authentication

## Quick Start

### 1. Download Model Files

```bash
mkdir -p models voices

# FP32 model (~300MB, recommended for GPU)
curl -L -o models/kokoro-v1.0.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx

# Voices file
curl -L -o voices/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
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

### GET /v1/voices

List available voices with language info:

```bash
curl http://localhost:5023/v1/voices
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

## Configuration

Environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEY` | `sk-kokoro` | Bearer token for authentication |
| `AUTH_ENABLED` | `false` | Enable authentication |
| `MODEL_PATH` | `models/kokoro-v0_19.fp16.onnx` | Path to ONNX model |
| `VOICES_PATH` | `voices/voices-v1.0.bin` | Path to voices file |
| `HOST` | `0.0.0.0` | Listen host |
| `PORT` | `5023` | Listen port |

## Available Voices

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

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- **GPU mode:** [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) + NVIDIA GPU

## License

MIT
