import logging
from urllib.parse import parse_qs
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
        raw = await request.body()
        parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        payload = {k: v[0] for k, v in parsed.items()}
    except Exception as e:
        logger.error(f"Body parse error: {e}")
        _recent_payloads.append({"error": f"body_parse: {e}"})
        return {"status": "ok"}

    _recent_payloads.append(payload)
    if len(_recent_payloads) > 20:
        _recent_payloads.pop(0)
    logger.info(f"Webhook received: {payload}")

    msg_id = payload.get("MessageSid")
    from_field = payload.get("From", "")
    phone = from_field.replace("whatsapp:", "").lstrip("+")
    text = payload.get("Body")

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
