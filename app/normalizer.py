from typing import Dict, Any, Optional
from schemas import CanonicalMessage


def _detect_lang(text: str | None) -> Optional[str]:
    if not text:
        return None
    return "en" if all(ord(c) < 128 for c in text) else "es"


def normalize_update(update: Dict[str, Any]) -> Optional[CanonicalMessage]:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return None

    text = (msg.get("text") or "").strip()
    if not text:
        return None

    chat = msg.get("chat", {})
    from_user = msg.get("from", {})

    return CanonicalMessage(
        text=text[:2048],
        chat_id=chat.get("id"),
        user_id=from_user.get("id"),
        message_id=msg.get("message_id"),
        lang=_detect_lang(text),
        raw=update,
    )