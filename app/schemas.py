from pydantic import BaseModel
from typing import Optional, Dict, Any

class CanonicalMessage(BaseModel):
    text: str
    chat_id: int
    user_id: int
    lang: Optional[str] = None
    message_id: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None

class CoreQuery(BaseModel):
    text: str
    lang: Optional[str]
    chat_id: int
    user_id: int
    message_id: Optional[int] = None

class CoreAnswer(BaseModel):
    answer: str