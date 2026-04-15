import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.agent import CalendarAgent
from services import whatsapp

router = APIRouter()
logger = logging.getLogger(__name__)

_processed_message_ids: set[str] = set()
_agent = CalendarAgent()
_recent_payloads: list[dict] = []


@router.get("/debug/webhook-log")
async def webhook_log():
    return {"recent_payloads": _recent_payloads[-10:]}


@router.post("/webhook")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    form = await request.form()
    payload = dict(form)
    _recent_payloads.append(payload)
    if len(_recent_payloads) > 20:
        _recent_payloads.pop(0)
    logger.info(f"Webhook received: {payload}")

    msg_id = form.get("MessageSid")
    from_field = form.get("From", "")
    phone = from_field.replace("whatsapp:", "")
    text = form.get("Body")

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
