from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from config import settings
from services.agent import CalendarAgent
from services import whatsapp

router = APIRouter()

_processed_message_ids: set[str] = set()


def _extract(body: dict) -> tuple[str | None, str | None, str | None]:
    """Extrai (msg_id, phone, text) do payload Meta. Retorna (None, None, None) se inválido."""
    try:
        value = body["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
        return msg.get("id", ""), msg["from"], msg["text"]["body"]
    except (KeyError, IndexError):
        return None, None, None


@router.get("/webhook")
async def verify_webhook(request: Request):
    from fastapi.responses import PlainTextResponse
    from fastapi import HTTPException
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

    if not phone or not text:
        return {"status": "ok"}

    if msg_id in _processed_message_ids:
        return {"status": "ok"}
    _processed_message_ids.add(msg_id)
    if len(_processed_message_ids) > 1000:
        _processed_message_ids.clear()

    agent = CalendarAgent()
    reply = await agent.run(phone=phone, text=text, db=db)
    await whatsapp.send_message(phone, reply)
    return {"status": "ok"}
