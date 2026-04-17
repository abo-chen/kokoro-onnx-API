# kokoro-onnx API

基于 [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) 的 OpenAI 兼容 TTS API，使用 Docker 部署。

## 特性

- OpenAI 兼容 API（`POST /v1/audio/speech`、`GET /v1/models`）
- 50+ 音色，覆盖 9 种语言（英语、普通话、日语、西班牙语、法语、印地语、意大利语、葡萄牙语）
- 中文模型支持中英文混合输入（技术术语、缩写、英文单词）
- 多种音频格式：MP3、WAV、FLAC、AAC、PCM
- 支持流式和非流式响应
- GPU（CUDA）和 CPU 两种部署模式
- 可选 Bearer Token 鉴权

## 快速开始

### 1. 下载模型文件

```bash
mkdir -p models voices

# 主模型（英语/多语言）
curl -L -o models/kokoro-v0_19.fp16.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v0_19.fp16.onnx

curl -L -o voices/voices-v1.0.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

# 中文模型（可选，启用中文及中英混合支持）
curl -L -o models/kokoro-v1.1-zh.onnx \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.1-zh.onnx

curl -L -o voices/voices-v1.1-zh.bin \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.1-zh.bin

curl -L -o models/config.json \
  https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh/raw/main/config.json
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
    "voice": "zf_001",
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
    {"id": "af_heart", "language": "en", "description": "美式女声"},
    {"id": "zf_xiaoxiao", "language": "cmn", "description": "普通话女声"},
    {"id": "am_adam", "language": "en", "description": "美式男声"}
  ]
}
```

## 中文及中英混合支持

启用中文模型后（`ZH_ENABLED=true`），API 会自动检测输入文本中的中文字符，并使用三级 G2P 策略处理其中嵌入的英文单词：

1. **高频词典** - 已知技术术语和常用词的精确匹配
   - `GitHub` → 给特哈布，`Docker` → 多克，`bug` → 巴格，`Python` → 派森
2. **大写缩写** - 逐字母朗读（如 `API`、`GPU`、`SSH`）
3. **g2p_en 回退** - 对未知英文单词使用 ARPABET 音素预测，映射为中文发音

### 中文模型音色

中文模型拥有独立的音色集（`zf_001` - `zf_099`，`zm_009` - `zm_100`）。使用中文音色（`zf_*` / `zm_*`）或输入包含中文字符时，会自动使用中文模型。

```bash
# 纯中文
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "千里之行，始于足下。", "voice": "zf_001"}' \
  --output chinese.wav

# 中英混合
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "我用Docker跑了一个API服务，用的GPU加速。", "voice": "zf_001"}' \
  --output mixed.wav
```

## 配置项

环境变量（`.env` 文件）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_KEY` | `sk-kokoro` | Bearer Token |
| `AUTH_ENABLED` | `false` | 是否开启鉴权 |
| `MODEL_PATH` | `models/kokoro-v0_19.fp16.onnx` | 主模型路径 |
| `VOICES_PATH` | `voices/voices-v1.0.bin` | 主音色文件路径 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `5023` | 监听端口 |
| `ZH_ENABLED` | `true` | 是否启用中文模型 |
| `ZH_MODEL_PATH` | `models/kokoro-v1.1-zh.onnx` | 中文模型路径 |
| `ZH_VOICES_PATH` | `voices/voices-v1.1-zh.bin` | 中文音色文件路径 |
| `ZH_VOCAB_CONFIG` | `models/config.json` | 中文词表配置路径 |

## 可用音色

### 主模型（英语/多语言）

| 前缀 | 语言 | 说明 |
|------|------|------|
| `af_` | 英语（美式） | 女声 |
| `am_` | 英语（美式） | 男声 |
| `bf_` | 英语（英式） | 女声 |
| `bm_` | 英语（英式） | 男声 |
| `zf_` | 普通话 | 女声 |
| `zm_` | 普通话 | 男声 |
| `jf_` | 日语 | 女声 |
| `jm_` | 日语 | 男声 |
| `ef_` | 西班牙语 | 女声 |
| `em_` | 西班牙语 | 男声 |
| `ff_` | 法语 | 女声 |
| `hf_` | 印地语 | 女声 |
| `hm_` | 印地语 | 男声 |
| `if_` | 意大利语 | 女声 |
| `im_` | 意大利语 | 男声 |
| `pf_` | 葡萄牙语（巴西） | 女声 |
| `pm_` | 葡萄牙语（巴西） | 男声 |

### 中文模型

| 前缀 | 范围 | 说明 |
|------|------|------|
| `af_maple` / `af_sol` / `bf_vale` | 内置英语音色 | 英语 |
| `zf_` | `zf_001` - `zf_099` | 普通话女声 |
| `zm_` | `zm_009` - `zm_100` | 普通话男声 |

## 系统要求

- [Docker](https://docs.docker.com/get-docker/)
- **GPU 模式：** [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) + NVIDIA GPU

## 许可证

MIT
