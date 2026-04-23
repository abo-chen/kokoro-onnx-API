# kokoro-onnx API

基于 [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) 的 OpenAI 兼容 TTS API，使用 Docker 部署。

## 特性

- OpenAI 兼容 API（`POST /v1/audio/speech`、`GET /v1/models`）
- 50+ 音色，覆盖 9 种语言（英语、普通话、日语、西班牙语、法语、印地语、意大利语、葡萄牙语）
- 中文模型支持中英文混合输入（技术术语、缩写、英文单词）
- 日语 TTS 通过 misaki-fork[ja] G2P + unidic 词典实现
- 长文本自动分句处理（降低显存占用）
- 多种音频格式：MP3、WAV、FLAC、AAC、PCM（PyAV 编码，无 ffmpeg 子进程）
- 支持流式和非流式响应
- GPU（CUDA）和 CPU 两种部署模式
- 可选 Bearer Token 鉴权
- 交互式 Demo 页面（`/demo`）

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
# 使用 HuggingFace 版本 — GitHub Releases 版本的 speed 参数存在 < 1.0 的 bug（speed 被转为 int32）
curl -L -o models/kokoro-v1.1-zh.onnx \
  https://huggingface.co/onnx-community/Kokoro-82M-v1.1-zh-ONNX/resolve/main/onnx/model.onnx

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
| `speed` | float | `1.0` | 语速（0.5 - 2.0） |
| `stream` | bool | `false` | 启用流式响应 |

### GET /v1/models

```bash
curl http://localhost:5023/v1/models
```

### GET /demo

交互式 Demo 页面，可在浏览器中测试语音合成。

### GET /v1/audio/voices

查询可用音色及语言信息：

```bash
curl http://localhost:5023/v1/audio/voices
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

## 日语 TTS

日语音色（`jf_*` / `jm_*`）使用主模型配合 misaki-fork[ja] G2P 进行文本到音素的转换。unidic 词典（约 775MB）首次使用时自动下载，通过 Docker 卷持久化保存。长文本按句子拆分以降低显存占用。

```bash
curl -X POST http://localhost:5023/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "こんにちは、世界！", "voice": "jf_heart"}' \
  --output japanese.wav
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

音色列表接口仅返回中文音色（`zf_*` / `zm_*`）。内置英语音色（`af_maple`、`af_sol`、`bf_vale`）仍可正常使用，但不在列表中显示，以避免与主模型的英语音色混淆。如需显示全部音色，移除 `app/routers/models.py` 中的过滤逻辑即可。

| 前缀 | 范围 | 说明 |
|------|------|------|
| `af_maple` / `af_sol` / `bf_vale` | 内置英语音色 | 英语（已从列表隐藏） |
| `zf_` | `zf_001` - `zf_099` | 普通话女声 |
| `zm_` | `zm_009` - `zm_100` | 普通话男声 |

## GPU 显存（VRAM）行为

ONNX Runtime 的 CUDA 分配器使用 arena（内存池）模式，分配的内存不会归还给 GPU。本项目通过以下 CUDA Provider 选项缓解显存无限增长：

- `arena_extend_strategy: kSameAsRequested` — 按需分配，避免默认的 2 的幂次翻倍预留
- `cudnn_conv_algo_search: HEURISTIC` — 避免穷举算法调优时分配大量临时工作空间
- `gpu_mem_limit: 2GB` — arena 分配硬上限

在此配置下，同一语言重复生成时显存会趋于稳定：

| 场景 | 稳定显存 |
|------|----------|
| 基线（空闲） | ~1300 MB |
| 英文（97 秒音频，重复生成） | ~2013 MB |
| 中文（97 秒音频，重复生成） | ~2300 MB |
| 日语（82 秒音频，重复生成） | ~2314 MB |
| 多语言切换 | 最高 ~4 GB |

短文本生成显存增量很小，接近基线水平。

日语通过 G2P（文本 → 音素 → 音频）使用主模型推理，中文使用独立模型。日语的音素序列比原始文本更长，因此每秒显存占用高于英文和中文。

> **注意：** 显存数据仅供参考，实际值因 GPU、驱动版本和输入内容而异。

## 系统要求

- [Docker](https://docs.docker.com/get-docker/)
- **GPU 模式：** [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) + NVIDIA GPU
- **平台：** 仅支持 x86_64（AMD64/Intel 64），不支持 ARM 平台（如 Apple Silicon、树莓派等）

## 更新日志

### 语速 < 1.0 修复

GitHub Releases 提供的中文模型（`kokoro-v1.1-zh.onnx`）存在一个 bug：`speed` 参数在底层被转为 `int32`，导致只有 0.5、1.0、2.0 三个值可用，其他值会报运行时错误。

**修复方案：** 使用 HuggingFace 导出的模型（`speed` 定义为 `float32`）：
- 模型地址：[onnx-community/Kokoro-82M-v1.1-zh-ONNX](https://huggingface.co/onnx-community/Kokoro-82M-v1.1-zh-ONNX)
- 问题参考：[kokoro-onnx#155](https://github.com/thewh1teagle/kokoro-onnx/issues/155)

Dockerfile 中同时 patch 了 kokoro-onnx 库（`np.int32` → `np.float32`）作为双保险。

## 许可证

MIT
