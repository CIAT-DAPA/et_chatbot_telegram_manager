import httpx
from settings import settings

API_BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=15) as client:
        payload = {"chat_id": chat_id, "text": text}
        r = await client.post(f"{API_BASE}/sendMessage", json=payload)
        r.raise_for_status()
        return r.json()