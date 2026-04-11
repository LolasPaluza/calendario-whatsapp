import uuid
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

scheduler = AsyncIOScheduler(timezone="UTC")


async def _send_reminder(event_id: str) -> None:
    """Fetch event from DB and send WhatsApp reminder."""
    from database import SessionLocal
    from models import Event
    from services.whatsapp import send_message
    from sqlalchemy import select

    async with SessionLocal() as db:
        result = await db.execute(select(Event).where(Event.id == uuid.UUID(event_id)))
        event = result.scalar_one_or_none()
        if event and event.status == "pending":
            await send_message(
                event.user_phone,
                f"Lembrete: {event.title}\n {event.event_datetime.strftime('%d/%m/%Y às %H:%M')}",
            )
            event.status = "sent"
            await db.commit()


def schedule_reminder(event_id: uuid.UUID, remind_at: datetime) -> None:
    scheduler.add_job(
        _send_reminder,
        trigger=DateTrigger(run_date=remind_at),
        args=[str(event_id)],
        id=str(event_id),
        replace_existing=True,
    )


def cancel_reminder(event_id: uuid.UUID) -> None:
    try:
        scheduler.remove_job(str(event_id))
    except Exception:
        pass


async def load_pending_reminders() -> None:
    """On startup: reschedule all pending future reminders from DB."""
    from database import SessionLocal
    from models import Event
    from sqlalchemy import select

    async with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Event).where(Event.status == "pending", Event.remind_at > now)
        )
        events = result.scalars().all()
        for event in events:
            schedule_reminder(event.id, event.remind_at)
