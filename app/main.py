from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from settings import settings
from normalizer import normalize_update
from dispatcher import send_message
from core_client import ask_core
from schemas import CoreQuery
import asyncio
import httpx
import uuid

app = FastAPI(title="Telegram Message Manager", version="1.1.1")

@app.post(f"/webhook/{{secret}}")
async def webhook(secret: str, request: Request, background: BackgroundTasks):
    if settings.WEBHOOK_SECRET_PATH and secret != settings.WEBHOOK_SECRET_PATH:
        raise HTTPException(status_code=403, detail="Forbidden")

    if settings.TELEGRAM_SECRET_TOKEN:
        if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.TELEGRAM_SECRET_TOKEN:
            raise HTTPException(status_code=403, detail="Invalid secret header")

    print("Call revieved from", getattr(request.client, "host", "-"))

    update = await request.json()
    print("UPDATE RAW:", update)

    cm = normalize_update(update)
    if not cm:
        print("Ignored: no text message found.")
        return JSONResponse({"ignored": True})

    print("Normalized message", cm.dict())

    async def process_and_reply():
        try:
            answer = None
            if settings.CORE_URL:
                payload = CoreQuery(
                    text=cm.text, lang=cm.lang,
                    chat_id=cm.chat_id, user_id=cm.user_id,
                    message_id=cm.message_id
                )
                
                print(f"The payload is: {payload}")
                answer = await ask_core(payload)
                print("Response from core:", answer)

            if not answer:
                answer = f"Echo: {cm.text}\n(lang={cm.lang}, user={cm.user_id})"

            resp = await send_message(cm.chat_id, answer)
            print("Answer send to telegram:", resp)
        except Exception as e:
            print("Error in process_and_reply:", e)

    background.add_task(process_and_reply)
    return JSONResponse({"ok": True})