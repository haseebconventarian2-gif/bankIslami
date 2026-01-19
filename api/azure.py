import os
import mimetypes

import httpx
from fastapi import HTTPException


def require_env(name: str) -> str:
  value = os.getenv(name)
  if not value:
    raise RuntimeError(f"Missing required env var: {name}")
  return value


def base_url() -> str:
  return require_env("AZURE_OPENAI_ENDPOINT").rstrip("/")


def api_version() -> str:
  return os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")


def api_headers() -> dict:
  return {"api-key": require_env("AZURE_OPENAI_API_KEY")}


def audio_content_type() -> str:
  fmt = os.getenv("AZURE_TTS_FORMAT", "mp3").lower()
  is_mp3 = fmt in ("mp3", "mpeg", "audio/mpeg")
  return "audio/mpeg" if is_mp3 else "audio/ogg"

def stt_language() -> str:
  return os.getenv("AZURE_STT_LANGUAGE", "auto").strip().lower()


async def generate_text(user_prompt: str) -> str:
  deployment = require_env("AZURE_GPT_DEPLOYMENT")
  url = f"{base_url()}/openai/deployments/{deployment}/chat/completions"
  params = {"api-version": api_version()}
  body = {
    "messages": [
      {
        "role": "system",
        "content": (
          "You are a helpful assistant. Keep replies concise. "
          "Reply in the same language as the user."
        ),
      },
      {"role": "user", "content": str(user_prompt or "")},
    ],
    "temperature": 0.3,
  }

  async with httpx.AsyncClient(timeout=120) as client:
    r = await client.post(url, params=params, headers=api_headers(), json=body)
    try:
      r.raise_for_status()
    except httpx.HTTPStatusError as exc:
      detail = exc.response.text
      raise HTTPException(status_code=502, detail=f"Azure GPT error: {detail}") from exc
    text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    text = (text or "").strip()
    return text or "Sorry, I could not generate a response."


async def transcribe_audio(audio_bytes: bytes, filename: str, content_type: str | None, language: str | None = None) -> str:
  deployment = require_env("AZURE_STT_DEPLOYMENT")
  url = f"{base_url()}/openai/deployments/{deployment}/audio/transcriptions"
  params = {"api-version": api_version()}
  inferred = content_type
  if not inferred:
    inferred, _ = mimetypes.guess_type(filename or "")
  files = {"file": (filename or "audio", audio_bytes, inferred or "application/octet-stream")}
  data = {}
  lang = (language or stt_language()).strip().lower()
  if lang and lang != "auto":
    data["language"] = lang

  async with httpx.AsyncClient(timeout=300) as client:
    r = await client.post(url, params=params, headers=api_headers(), files=files, data=data)
    try:
      r.raise_for_status()
    except httpx.HTTPStatusError as exc:
      detail = exc.response.text
      raise HTTPException(status_code=502, detail=f"Azure STT error: {detail}") from exc
    text = r.json().get("text", "")
    return (text or "").strip()


async def synthesize_speech(text: str) -> bytes:
  deployment = require_env("AZURE_TTS_DEPLOYMENT")
  url = f"{base_url()}/openai/deployments/{deployment}/audio/speech"
  params = {"api-version": api_version()}
  body = {
    "model": deployment,
    "input": str(text or ""),
    "voice": os.getenv("AZURE_TTS_VOICE", "alloy"),
    "format": os.getenv("AZURE_TTS_FORMAT", "mp3"),
  }

  async with httpx.AsyncClient(timeout=300) as client:
    r = await client.post(url, params=params, headers=api_headers(), json=body)
    try:
      r.raise_for_status()
    except httpx.HTTPStatusError as exc:
      detail = exc.response.text
      raise HTTPException(status_code=502, detail=f"Azure TTS error: {detail}") from exc
    return r.content
