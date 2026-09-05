import os
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI(title="Verity Fish Audio Proxy")

# Allow Roblox requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Read environment variables (Fallback to hardcoded defaults if not provided)
FISH_API_KEY = os.getenv("FISH_API_KEY", "sk-fish-wG_FoD-dPFfkW5mi51JEIrIkxU3pDJb8v-nQnhbmWC0")
DEFAULT_VOICE_ID = os.getenv("DEFAULT_VOICE_ID", "8d21b053e2804e2a890e1cf62f267b6f")

# Simple in-memory cache to save API credits on repeated dialogue
AUDIO_CACHE = {}

class TTSRequest(BaseModel):
    text: str
    reference_id: str | None = None
    model: str = "s2.1-pro-free"  # Uses free developer tier model by default

@app.get("/")
def health_check():
    return {"status": "online", "service": "Verity Voice Proxy"}

@app.post("/v1/tts")
async def generate_tts(data: TTSRequest):
    if not data.text or not data.text.strip():
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty.")

    if not FISH_API_KEY:
        raise HTTPException(status_code=500, detail="FISH_API_KEY is not configured on Render.")

    voice_id = data.reference_id or DEFAULT_VOICE_ID
    cache_key = f"{voice_id}:{data.text.strip().lower()}"

    if cache_key in AUDIO_CACHE:
        return Response(content=AUDIO_CACHE[cache_key], media_type="audio/mpeg")

    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": data.text,
        "reference_id": voice_id,
        "format": "mp3",
        "latency": "normal"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                "https://api.fish.audio/v1/tts",
                headers=headers,
                json=payload
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Proxy error contacting Fish Audio: {exc}")

    if response.status_code == 200:
        audio_bytes = response.content
        AUDIO_CACHE[cache_key] = audio_bytes
        return Response(content=audio_bytes, media_type="audio/mpeg")
    else:
        # Prints the actual Fish Audio error into your Render logs
        print(f"Fish Audio Error {response.status_code}: {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Fish Audio Error ({response.status_code}): {response.text}"
        )
