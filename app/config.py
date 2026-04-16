from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    API_KEY: str = "sk-kokoro"
    AUTH_ENABLED: bool = False
    MODEL_PATH: str = "models/kokoro-v0_19.fp16.onnx"
    VOICES_PATH: str = "voices/voices-v1.0.bin"
    HOST: str = "0.0.0.0"
    PORT: int = 5023


settings = Settings()
