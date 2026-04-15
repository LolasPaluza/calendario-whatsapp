from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from config import settings
from services.agent import CalendarAgent
from services import whatsapp

router = APIRouter()

_processed_message_ids: set[str] = set()
_agent = CalendarAgent()


def _extract(body: dict) -> tuple[str | None, str | None, str | None]:
    """Extract (msg_id, phone, text) from Meta payload. Returns (None, None, None) if invalid."""
    try:
        value = body["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
        msg_id = msg.get("id") or None
        return msg_id, msg["from"], msg["text"]["body"]
    except (KeyError, IndexError):
        return None, None, None


@router.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.webhook_verify_token
    ):
        return PlainTextResponse(params.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/webhook")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    msg_id, phone, text = _extract(body)

    if not msg_id or not phone or not text:
        return {"status": "ok"}

    if msg_id in _processed_message_ids:
        return {"status": "ok"}
    _processed_message_ids.add(msg_id)
    if len(_processed_message_ids) > 1000:
        _processed_message_ids.clear()

    reply = await _agent.run(phone=phone, text=text, db=db)
    await whatsapp.send_message(phone, reply)
    return {"status": "ok"}
