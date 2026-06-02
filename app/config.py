from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    API_KEY: str = "sk-kokoro"
    AUTH_ENABLED: bool = False
    MODEL_PATH: str = "models/kokoro-v0_19.fp16.onnx"
    VOICES_PATH: str = "voices/voices-v1.0.bin"
    HOST: str = "0.0.0.0"
    PORT: int = 5023

    # Chinese model (optional, enables Chinese + mixed CN/EN support)
    ZH_MODEL_PATH: str = "models/kokoro-v1.1-zh.onnx"
    ZH_VOICES_PATH: str = "voices/voices-v1.1-zh.bin"
    ZH_VOCAB_CONFIG: str = "models/config.json"
    ZH_ENABLED: bool = True

    # GPU VRAM limit in MB (default 2048 = 2GB)
    GPU_MEM_LIMIT_MB: int = 2048

    # Max chars per TTS chunk. Auto-derived from GPU_MEM_LIMIT_MB if not set.
    # Set manually to override: e.g. SPLIT_MAX_CHARS=300
    SPLIT_MAX_CHARS: int = 0

    # Accumulated chars before mid-request CUDA release (default mode).
    # Auto-derived from GPU_MEM_LIMIT_MB if not set.
    SPLIT_BATCH_CHARS: int = 0

    # Debug: log timing and VRAM at key points (set via .env)
    DEBUG_TIMING: bool = False


settings = Settings()
