from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from services.events import (
    create_event as db_create_event,
    list_upcoming_events,
    cancel_event as db_cancel_event,
    update_event,
)
from schemas import EventCreate, EventUpdate
from scheduler import schedule_reminder, cancel_reminder

BRT = ZoneInfo("America/Sao_Paulo")


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=BRT)
    return dt.astimezone(timezone.utc)


def _fuzzy_match(reference: str, title: str) -> bool:
    ref = reference.lower().strip()
    t = title.lower().strip()
    if ref in t or t in ref:
        return True
    return any(word in t for word in ref.split() if len(word) > 2)


async def create_event(
    title: str,
    datetime_iso: str,
    remind_at_iso: str | None,
    user_phone: str,
    now: datetime,
    db: AsyncSession,
) -> str:
    event_dt = _parse_dt(datetime_iso)
    remind_dt = _parse_dt(remind_at_iso) if remind_at_iso else event_dt - timedelta(minutes=30)

    event = await db_create_event(db, EventCreate(
        title=title,
        event_datetime=event_dt,
        remind_at=remind_dt,
        user_phone=user_phone,
    ))
    schedule_reminder(event.id, event.remind_at)

    dt_brt = event_dt.astimezone(BRT)
    remind_brt = remind_dt.astimezone(BRT)
    return (
        f"Evento criado: *{title}*\n"
        f"Data: {dt_brt.strftime('%d/%m/%Y às %H:%M')}\n"
        f"Lembrete: {remind_brt.strftime('%d/%m/%Y às %H:%M')}"
    )


async def list_events(user_phone: str, db: AsyncSession) -> str:
    events = await list_upcoming_events(db, user_phone=user_phone)
    if not events:
        return "Nenhum evento pendente na agenda."
    lines = ["*Seus próximos eventos:*"]
    for e in events[:10]:
        dt_brt = e.event_datetime.astimezone(BRT)
        lines.append(f"• {e.title} — {dt_brt.strftime('%d/%m às %H:%M')}")
    return "\n".join(lines)


async def cancel_event(event_reference: str, user_phone: str, db: AsyncSession) -> str:
    events = await list_upcoming_events(db, user_phone=user_phone)
    matched = next((e for e in events if _fuzzy_match(event_reference, e.title)), None)
    if not matched:
        return f"Não encontrei nenhum evento com '{event_reference}'."

    await db_cancel_event(db, matched.id)
    cancel_reminder(matched.id)
    return f"Evento cancelado: *{matched.title}*"


async def edit_event(
    event_reference: str,
    field: str,
    new_value: str,
    user_phone: str,
    now: datetime,
    db: AsyncSession,
) -> str:
    events = await list_upcoming_events(db, user_phone=user_phone)
    matched = next((e for e in events if _fuzzy_match(event_reference, e.title)), None)
    if not matched:
        return f"Não encontrei nenhum evento com '{event_reference}'."

    update_data: dict = {}
    if field == "datetime":
        new_dt = _parse_dt(new_value)
        update_data["event_datetime"] = new_dt
        update_data["remind_at"] = new_dt - timedelta(minutes=30)
    elif field == "title":
        update_data["title"] = new_value
    elif field == "remind_at":
        update_data["remind_at"] = _parse_dt(new_value)
    else:
        return f"Campo '{field}' não reconhecido. Use: datetime, title ou remind_at."

    updated = await update_event(db, matched.id, EventUpdate(**update_data))
    if not updated:
        return "Não foi possível atualizar o evento."

    if "event_datetime" in update_data or "remind_at" in update_data:
        cancel_reminder(matched.id)
        schedule_reminder(updated.id, updated.remind_at)
    return f"Evento atualizado: *{updated.title}*"
