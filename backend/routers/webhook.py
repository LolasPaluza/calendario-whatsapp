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
    try:
        form = await request.form()
        payload = dict(form)
    except Exception as e:
        logger.error(f"Form parse error: {e}")
        _recent_payloads.append({"error": f"form_parse: {e}"})
        return {"status": "ok"}

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

    try:
        reply = await _agent.run(phone=phone, text=text, db=db)
    except Exception as e:
        logger.error(f"Agent error: {e}")
        reply = "Desculpe, tive um problema técnico. Tente novamente."

    try:
        await whatsapp.send_message(phone, reply)
    except Exception as e:
        logger.error(f"Twilio send error: {e}")
        _recent_payloads.append({"send_error": str(e)})

    return {"status": "ok"}
