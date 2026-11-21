"""GET /brief/audio: ElevenLabs text-to-speech, cached on disk by a hash of the text."""
import hashlib
import os
import re

import httpx

import store

CACHE = store.DATA / "audio"


class VoiceError(Exception):
    pass


def speak(text: str) -> bytes:
    text = re.sub(r"\s*\[\d+\]", "", text).strip()
    path = CACHE / f"{hashlib.sha256(text.encode()).hexdigest()[:24]}.mp3"
    if path.exists():
        return path.read_bytes()
    if os.environ.get("BRAIN_NO_VOICE") == "1":
        raise VoiceError("voice disabled (BRAIN_NO_VOICE=1)")
    key, voice = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        raise VoiceError("ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID is not set")
    try:
        r = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": key},
            json={"text": text, "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")},
            timeout=30,
        )
    except httpx.HTTPError as e:
        raise VoiceError(f"ElevenLabs unreachable ({type(e).__name__})")
    if r.status_code != 200 or not r.content:
        raise VoiceError(f"ElevenLabs returned {r.status_code}")
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return r.content
