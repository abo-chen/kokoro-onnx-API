# kokoro-onnx

基于 [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) 的 OpenAI 兼容 TTS API，使用 Docker 部署。

## 特性

- OpenAI 兼容 API（`POST /v1/audio/speech`、`GET /v1/models`）
- 50+ 音色，覆盖 9 种语言（英语、普通话、日语、西班牙语、法语、印地语、意大利语、葡萄牙语）
- 多种音频格式：MP3、WAV、FLAC、AAC、PCM
- 支持流式和非流式响应
- GPU（CUDA）和 CPU 两种部署模式
- 可选 Bearer Token 鉴权

## 快速开始

### 1. 下载模型文件

```bash
mkdir -p models voices

# FP32 模型（~300MB，推荐 GPU 使用）
curl -L -o models/kokoro-v1.0.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx

# 音色文件
curl -L -o voices/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

### 2. 配置

```bash
cp .env.example .env
# 按需编辑 .env
```

### 3. Docker 启动

**GPU 模式（默认）：**

```bash
docker compose up -d
```

**CPU 模式：**

```bash
docker compose -f docker-compose.cpu.yml up -d
```

服务地址：`http://localhost:5023`

## API 端点

### POST /v1/audio/speech

生成语音音频。

```bash
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Authorization: Bearer sk-kokoro" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "你好，世界！",
    "voice": "zf_xiaoxiao",
    "response_format": "mp3",
    "speed": 1.0,
    "stream": false
  }' \
  --output speech.mp3
```

**参数说明：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | string | `"kokoro"` | 模型名称 |
| `input` | string | 必填 | 要合成的文本（最多 4096 字符） |
| `voice` | string | `"af_nicole"` | 音色名称 |
| `response_format` | string | `"mp3"` | `mp3`、`wav`、`flac`、`aac`、`pcm` |
| `speed` | float | `1.0` | 语速（0.25 - 4.0） |
| `stream` | bool | `false` | 启用流式响应 |

### GET /v1/models

```bash
curl http://localhost:5023/v1/models
```

### GET /v1/voices

查询可用音色及语言信息：

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

## 配置项

环境变量（`.env` 文件）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_KEY` | `sk-kokoro` | Bearer Token |
| `AUTH_ENABLED` | `false` | 是否开启鉴权 |
| `MODEL_PATH` | `models/kokoro-v0_19.fp16.onnx` | ONNX 模型路径 |
| `VOICES_PATH` | `voices/voices-v1.0.bin` | 音色文件路径 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `5023` | 监听端口 |

## 可用音色

| 前缀 | 语言 | 说明 |
|------|------|------|
| `af_` | 英语（美式） | 女 |
| `am_` | 英语（美式） | 男 |
| `bf_` | 英语（英式） | 女 |
| `bm_` | 英语（英式） | 男 |
| `zf_` | 普通话 | 女 |
| `zm_` | 普通话 | 男 |
| `jf_` | 日语 | 女 |
| `jm_` | 日语 | 男 |
| `ef_` | 西班牙语 | 女 |
| `em_` | 西班牙语 | 男 |
| `ff_` | 法语 | 女 |
| `hf_` | 印地语 | 女 |
| `hm_` | 印地语 | 男 |
| `if_` | 意大利语 | 女 |
| `im_` | 意大利语 | 男 |
| `pf_` | 葡萄牙语（巴西） | 女 |
| `pm_` | 葡萄牙语（巴西） | 男 |

## 系统要求

- [Docker](https://docs.docker.com/get-docker/)
- **GPU 模式：** [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) + NVIDIA GPU

## 许可证

MIT
