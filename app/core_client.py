import httpx
from settings import settings
from schemas import CoreQuery

async def ask_core(payload: CoreQuery) -> str | None:
    """
    Call the core service with the given payload and return the answer.
    """
    if not settings.CORE_URL:
        return None

    async with httpx.AsyncClient(timeout=100.0) as client:
        try:
            r = await client.post(settings.CORE_URL, json=payload.dict())
            r.raise_for_status()
        except httpx.TimeoutException as e:
            print("Timeout calling core:", e)
            raise
        except httpx.HTTPStatusError as e:
            print("Error:")
            print("   Status:", e.response.status_code)
            try:
                print("   Body:", e.response.json())
            except Exception:
                print("   Body (raw):", e.response.text)
            raise

        data = r.json()
        if isinstance(data, dict) and "answer" in data:
            return data["answer"]

        print("Unexpected answer:", data)
        return None