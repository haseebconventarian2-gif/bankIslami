import os
import secrets
import time
from typing import Any

import httpx


_AUDIO_TTL_SECONDS = 5 * 60
_audio_store: dict[str, dict[str, Any]] = {}


def _now() -> float:
  return time.time()


def _cleanup_store() -> None:
  now = _now()
  expired = [key for key, item in _audio_store.items() if item["expires_at"] <= now]
  for key in expired:
    _audio_store.pop(key, None)


def require_env(name: str) -> str:
  value = os.getenv(name)
  if not value:
    raise RuntimeError(f"Missing required env var: {name}")
  return value


def graph_base() -> str:
  version = os.getenv("META_API_VERSION") or os.getenv("VERSION") or "v20.0"
  return f"https://graph.facebook.com/{version}"


def base_url() -> str:
  return require_env("PUBLIC_BASE_URL").strip().rstrip("/")


def auth_header() -> dict[str, str]:
  return {"Authorization": f"Bearer {require_env('ACCESS_TOKEN')}"}


def message_url() -> str:
  phone_number_id = require_env("PHONE_NUMBER_ID")
  return f"{graph_base()}/{phone_number_id}/messages"


def app_access_token() -> str:
  app_id = require_env("APP_ID")
  app_secret = require_env("APP_SECRET")
  return f"{app_id}|{app_secret}"


def save_audio(buffer: bytes, content_type: str) -> str:
  _cleanup_store()
  media_id = secrets.token_hex(16)
  _audio_store[media_id] = {
    "buffer": buffer,
    "content_type": content_type,
    "expires_at": _now() + _AUDIO_TTL_SECONDS,
  }
  return media_id


def get_audio(media_id: str) -> dict[str, Any] | None:
  _cleanup_store()
  item = _audio_store.get(media_id)
  if not item:
    return None
  if item["expires_at"] <= _now():
    _audio_store.pop(media_id, None)
    return None
  return item


def parse_message(payload: dict) -> dict[str, str] | None:
  try:
    message = payload.get("entry", [])[0].get("changes", [])[0].get("value", {}).get("messages", [])[0]
  except (IndexError, AttributeError):
    return None
  if not message:
    return None

  sender = message.get("from")
  if not sender:
    return None

  if message.get("type") == "audio":
    audio = message.get("audio") or {}
    media_id = audio.get("id")
    if not media_id:
      return None
    return {
      "from": sender,
      "type": "audio",
      "media_id": media_id,
      "media_type": audio.get("mime_type") or "",
    }

  if message.get("type") == "text":
    text = (message.get("text") or {}).get("body") or ""
    if not text.strip():
      return None
    return {"from": sender, "type": "text", "text": text}

  return None


async def download_media(media_id: str) -> bytes:
  async with httpx.AsyncClient(timeout=120) as client:
    meta = await client.get(f"{graph_base()}/{media_id}", headers=auth_header())
    meta.raise_for_status()
    media_url = meta.json().get("url")
    if not media_url:
      raise RuntimeError("WhatsApp media metadata missing URL")

    file = await client.get(media_url, headers=auth_header())
    file.raise_for_status()
    return file.content


async def reply_text(to_number: str, text: str) -> None:
  payload = {
    "messaging_product": "whatsapp",
    "to": to_number,
    "type": "text",
    "text": {"body": text},
  }
  async with httpx.AsyncClient(timeout=30) as client:
    r = await client.post(message_url(), json=payload, headers=auth_header())
    try:
      r.raise_for_status()
    except httpx.HTTPStatusError as exc:
      detail = exc.response.text
      raise RuntimeError(f"WhatsApp reply_text failed: {detail}") from exc


async def reply_audio(to_number: str, audio_buffer: bytes, content_type: str) -> None:
  media_id = save_audio(audio_buffer, content_type)
  media_url = f"{base_url()}/media/{media_id}"
  payload = {
    "messaging_product": "whatsapp",
    "to": to_number,
    "type": "audio",
    "audio": {"link": media_url},
  }
  async with httpx.AsyncClient(timeout=30) as client:
    r = await client.post(message_url(), json=payload, headers=auth_header())
    try:
      r.raise_for_status()
    except httpx.HTTPStatusError as exc:
      detail = exc.response.text
      raise RuntimeError(f"WhatsApp reply_audio failed: {detail}") from exc


async def debug_access_token() -> dict:
  params = {
    "input_token": require_env("ACCESS_TOKEN"),
    "access_token": app_access_token(),
  }
  async with httpx.AsyncClient(timeout=30) as client:
    r = await client.get(f"{graph_base()}/debug_token", params=params)
    r.raise_for_status()
    return r.json()


async def push_text(text: str, to_number: str | None = None) -> None:
  recipient = to_number or os.getenv("RECIPIENT_WAID")
  if not recipient:
    raise RuntimeError("Missing RECIPIENT_WAID or 'to' value")
  await reply_text(recipient, text)
