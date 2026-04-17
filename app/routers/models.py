import time

from fastapi import APIRouter, Depends

from app.auth import verify_api_key
from app.models import ModelListResponse, ModelObject

router = APIRouter(tags=["models"])

# Global reference set by lifespan
kokoro = None

LANGUAGE_MAP = {
    "af": "en", "am": "en",
    "bf": "en-gb", "bm": "en-gb",
    "jf": "ja", "jm": "ja",
    "zf": "cmn", "zm": "cmn",
    "ef": "es", "em": "es",
    "ff": "fr-fr", "fm": "fr-fr",
    "hf": "hi", "hm": "hi",
    "if": "it", "im": "it",
    "pf": "pt-br", "pm": "pt-br",
}

VOICE_DESCRIPTIONS = {
    "af": "US Female",
    "am": "US Male",
    "bf": "UK Female",
    "bm": "UK Male",
    "jf": "Japanese Female",
    "jm": "Japanese Male",
    "zf": "Mandarin Female",
    "zm": "Mandarin Male",
    "ef": "Spanish Female",
    "em": "Spanish Male",
    "ff": "French Female",
    "fm": "French Male",
    "hf": "Hindi Female",
    "hm": "Hindi Male",
    "if": "Italian Female",
    "im": "Italian Male",
    "pf": "(Br)Portuguese Female",
    "pm": "(Br)Portuguese Male",
}


def set_kokoro(instance):
    global kokoro
    kokoro = instance


# Chinese model references (set by main.py)
zh_kokoro = None


def set_zh_kokoro(instance):
    global zh_kokoro
    zh_kokoro = instance


@router.get("/models", response_model=ModelListResponse)
async def list_models(_auth: None = Depends(verify_api_key)):
    data = [
        ModelObject(
            id="kokoro",
            object="model",
            created=int(time.time()),
            owned_by="kokoro-onnx",
        )
    ]
    if zh_kokoro is not None:
        data.append(
            ModelObject(
                id="kokoro-zh",
                object="model",
                created=int(time.time()),
                owned_by="kokoro-onnx",
            )
        )
    return ModelListResponse(object="list", data=data)


@router.get("/voices")
async def list_voices(_auth: None = Depends(verify_api_key)):
    if kokoro is None:
        return {"error": {"message": "Model not loaded", "type": "server_error"}}
    voices = []
    for name in sorted(kokoro.get_voices()):
        prefix = name[:2]
        voices.append({
            "id": name,
            "language": LANGUAGE_MAP.get(prefix, "unknown"),
            "description": VOICE_DESCRIPTIONS.get(prefix, "Unknown"),
        })
    if zh_kokoro is not None:
        for name in sorted(zh_kokoro.get_voices()):
            prefix = name[:2]
            voices.append({
                "id": name,
                "language": LANGUAGE_MAP.get(prefix, "unknown"),
                "description": VOICE_DESCRIPTIONS.get(prefix, "Unknown"),
            })
    return {"object": "list", "data": voices}
