from typing import Literal

from pydantic import BaseModel, Field


class SpeechRequest(BaseModel):
    model: str = "kokoro"
    input: str = Field(..., max_length=4096)
    voice: str = "af_nicole"
    response_format: Literal["mp3", "wav", "flac", "aac", "pcm"] = "mp3"
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    stream: bool = False


class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelObject]
