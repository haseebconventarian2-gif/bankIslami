import asyncio
import os

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from .azure import (
  audio_content_type,
  generate_text,
  synthesize_speech,
  transcribe_audio,
)
from rag_pipeline import answer_with_vectorstore, build_vectorstore_from_path, format_response
from .whatsapp import (
  debug_access_token,
  download_media,
  get_audio,
  parse_message,
  push_text,
  reply_audio,
  reply_text,
)
from .ui import UI_HTML


def create_app() -> FastAPI:
  app = FastAPI(title="Azure AI Bot")
  rag_store = None
  rag_path = os.getenv("RAG_DATA_PATH", "bank.json")
  if os.path.exists(rag_path):
    try:
      rag_store = build_vectorstore_from_path(rag_path)
      print(f"RAG loaded from {rag_path}")
    except Exception as exc:
      print(f"RAG load failed for {rag_path}: {exc}")

  async def get_answer(user_text: str) -> str:
    normalized = user_text.strip().lower()
    if normalized in {"hi", "hello", "hey", "salam", "assalamualaikum", "asalamualaikum"}:
      return "Welcome to BankIslami! How can I help you today?"
    if rag_store:
      answer = answer_with_vectorstore(user_text, rag_store)
      if answer and "i don't know" not in answer.lower():
        return answer
    return format_response(await generate_text(user_text))

  @app.get("/")
  def ui() -> Response:
    return Response(content=UI_HTML, media_type="text/html")

  @app.get("/health")
  def health() -> JSONResponse:
    return JSONResponse({"ok": True})

  @app.post("/text")
  async def text_reply(payload: dict) -> JSONResponse:
    user_text = str(payload.get("text") or "").strip()
    if not user_text:
      raise HTTPException(status_code=400, detail="Missing text")
    answer = await get_answer(user_text)
    return JSONResponse({"text": answer})

  @app.get("/whatsapp/diagnose")
  async def whatsapp_diagnose(check_token: bool = False) -> JSONResponse:
    report = {
      "has_access_token": bool(os.getenv("ACCESS_TOKEN")),
      "has_phone_number_id": bool(os.getenv("PHONE_NUMBER_ID")),
      "has_verify_token": bool(os.getenv("VERIFY_TOKEN")),
      "has_public_base_url": bool(os.getenv("PUBLIC_BASE_URL")),
      "has_app_id": bool(os.getenv("APP_ID")),
      "has_app_secret": bool(os.getenv("APP_SECRET")),
      "has_recipient_waid": bool(os.getenv("RECIPIENT_WAID")),
      "version": os.getenv("VERSION") or os.getenv("META_API_VERSION") or "v20.0",
    }
    if check_token:
      try:
        report["token_debug"] = await debug_access_token()
      except Exception as exc:
        report["token_debug_error"] = str(exc)
    return JSONResponse(report)

  @app.post("/whatsapp/push")
  async def whatsapp_push(payload: dict) -> JSONResponse:
    text = str(payload.get("text") or "").strip()
    to_number = str(payload.get("to") or "").strip() or None
    if not text:
      raise HTTPException(status_code=400, detail="Missing text")
    await push_text(text, to_number)
    return JSONResponse({"ok": True})

  @app.post("/audio")
  async def audio_reply(file: UploadFile = File(...)) -> Response:
    audio_bytes = await file.read()
    if not audio_bytes:
      raise HTTPException(status_code=400, detail="Missing audio file")

    transcript = await transcribe_audio(audio_bytes, file.filename or "", file.content_type)
    answer = await get_answer(transcript)
    audio_out = await synthesize_speech(answer)
    return Response(content=audio_out, media_type=audio_content_type())

  @app.get("/media/{media_id}")
  def media(media_id: str) -> Response:
    item = get_audio(media_id)
    if not item:
      raise HTTPException(status_code=404, detail="Not found")
    return Response(content=item["buffer"], media_type=item["content_type"])

  @app.get("/webhook")
  def webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
  ) -> Response:
    verify_token = os.getenv("VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and hub_verify_token == verify_token and hub_challenge:
      return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403, content="Forbidden", media_type="text/plain")

  @app.post("/webhook")
  async def webhook_events(request: Request) -> JSONResponse:
    try:
      payload = await request.json()
    except Exception:
      return JSONResponse({"ok": True})

    try:
      print("Webhook payload:", payload)
    except Exception:
      print("Webhook payload: <unavailable>")

    msg = parse_message(payload)
    if not msg:
      return JSONResponse({"ok": True})

    try:
      meta = (
        payload.get("entry", [])[0]
        .get("changes", [])[0]
        .get("value", {})
        .get("metadata", {})
      )
      print(
        "Webhook meta:",
        {"from": msg.get("from"), "phone_number_id": meta.get("phone_number_id")},
      )
    except Exception:
      print("Webhook meta: <unavailable>")

    async def handle_message() -> None:
      try:
        if msg["type"] == "text":
          answer = await get_answer(msg["text"])
          recipient = os.getenv("RECIPIENT_WAID") or msg["from"]
          await reply_text(recipient, answer)
          audio_out = await synthesize_speech(answer)
          await reply_audio(recipient, audio_out, audio_content_type())
          return

        if msg["type"] == "audio":
          audio_bytes = await download_media(msg["media_id"])
          transcript = await transcribe_audio(audio_bytes, "audio", msg.get("media_type") or None)
          answer = await get_answer(transcript)
          recipient = os.getenv("RECIPIENT_WAID") or msg["from"]
          await reply_text(recipient, answer)
          audio_out = await synthesize_speech(answer)
          await reply_audio(recipient, audio_out, audio_content_type())
          return
      except Exception as exc:
        print("Webhook handler error:", exc)

    asyncio.create_task(handle_message())
    return JSONResponse({"ok": True})

  return app
