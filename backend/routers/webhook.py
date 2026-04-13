from datetime import datetime, timedelta, timezone, UTC
from zoneinfo import ZoneInfo

BRT = ZoneInfo("America/Sao_Paulo")


def parse_dt(value: str) -> datetime:
    """Parse ISO datetime; if naive (no offset), assume America/Sao_Paulo."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BRT)
    return dt.astimezone(UTC)
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from config import settings
from services import nlp, whatsapp
from services import events as events_service
from schemas import EventCreate, EventUpdate
from scheduler import schedule_reminder, cancel_reminder

router = APIRouter()


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.webhook_verify_token
    ):
        return params.get("hub.challenge", "")
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/webhook")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()

    try:
        value = body["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
        from_number = msg["from"]
        text = msg["text"]["body"]
    except (KeyError, IndexError):
        return {"status": "ok"}

    now = datetime.now(timezone.utc)
    try:
        parsed = await nlp.parse_message(text, now)
    except Exception as e:
        import logging
        logging.error(f"NLP error: {type(e).__name__}: {e}")
        await whatsapp.send_message(from_number, f"Erro interno ao processar mensagem: {type(e).__name__}")
        return {"status": "error", "detail": str(e)}

    if parsed.get("clarification_needed"):
        await whatsapp.send_message(from_number, parsed["clarification_question"])
        return {"status": "ok"}

    intent = parsed.get("intent")

    if intent == "create":
        event_dt = parse_dt(parsed["datetime"])
        remind_at = parse_dt(parsed["remind_at"])
        event = await events_service.create_event(db, EventCreate(
            title=parsed["title"],
            event_datetime=event_dt,
            remind_at=remind_at,
            user_phone=from_number,
        ))
        schedule_reminder(event.id, event.remind_at)
        await whatsapp.send_message(
            from_number,
            f"Evento criado: {event.title}\n"
            f"Data: {event_dt.strftime('%d/%m/%Y às %H:%M')}\n"
            f"Lembrete: {remind_at.strftime('%d/%m/%Y às %H:%M')}",
        )

    elif intent == "list":
        events = await events_service.list_events(db)
        if not events:
            await whatsapp.send_message(from_number, "Nenhum evento pendente.")
        else:
            lines = ["*Seus próximos eventos:*"]
            for e in events[:10]:
                lines.append(f"• {e.title} — {e.event_datetime.strftime('%d/%m às %H:%M')}")
            await whatsapp.send_message(from_number, "\n".join(lines))

    elif intent == "cancel":
        events = await events_service.list_events(db)
        ref = (parsed.get("event_reference") or "").lower()
        matched = next((e for e in events if ref in e.title.lower()), None)
        if matched:
            await events_service.cancel_event(db, matched.id)
            cancel_reminder(matched.id)
            await whatsapp.send_message(from_number, f"Evento cancelado: {matched.title}")
        else:
            await whatsapp.send_message(from_number, "Evento não encontrado.")

    elif intent == "edit":
        events = await events_service.list_events(db)
        ref = (parsed.get("event_reference") or "").lower()
        matched = next((e for e in events if ref in e.title.lower()), None)
        if matched:
            field = parsed.get("field_to_edit")
            new_val = parsed.get("new_value")
            update_data: dict = {}
            if field == "datetime":
                new_dt = parse_dt(new_val)
                update_data["event_datetime"] = new_dt
                update_data["remind_at"] = new_dt - timedelta(minutes=30)
            elif field == "title":
                update_data["title"] = new_val
            elif field == "remind_at":
                update_data["remind_at"] = parse_dt(new_val)
            updated = await events_service.update_event(db, matched.id, EventUpdate(**update_data))
            if updated:
                cancel_reminder(matched.id)
                schedule_reminder(updated.id, updated.remind_at)
                await whatsapp.send_message(from_number, f"Evento atualizado: {updated.title}")
        else:
            await whatsapp.send_message(from_number, "Evento não encontrado.")

    elif intent in ("query", "unknown"):
        upcoming = await events_service.list_upcoming_events(db)
        response_text = await nlp.chat_response(text, upcoming, now)
        await whatsapp.send_message(from_number, response_text)

    return {"status": "ok"}
