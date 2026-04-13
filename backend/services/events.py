import uuid
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Event
from schemas import EventCreate, EventUpdate


async def create_event(db: AsyncSession, data: EventCreate) -> Event:
    remind_at = data.remind_at or (data.event_datetime - timedelta(minutes=30))
    event = Event(
        title=data.title,
        description=data.description,
        event_datetime=data.event_datetime,
        remind_at=remind_at,
        user_phone=data.user_phone,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_events(db: AsyncSession, status: str = "pending") -> list[Event]:
    result = await db.execute(
        select(Event).where(Event.status == status).order_by(Event.event_datetime)
    )
    return list(result.scalars().all())


async def get_event(db: AsyncSession, event_id: uuid.UUID) -> Event | None:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def update_event(db: AsyncSession, event_id: uuid.UUID, data: EventUpdate) -> Event | None:
    event = await get_event(db, event_id)
    if not event:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(event, field, value)
    await db.commit()
    await db.refresh(event)
    return event


async def list_upcoming_events(db: AsyncSession) -> list[Event]:
    """Return all non-cancelled future events (regardless of reminder status)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Event)
        .where(Event.event_datetime > now, Event.status != "cancelled")
        .order_by(Event.event_datetime)
    )
    return list(result.scalars().all())


async def cancel_event(db: AsyncSession, event_id: uuid.UUID) -> Event | None:
    event = await get_event(db, event_id)
    if not event:
        return None
    event.status = "cancelled"
    await db.commit()
    await db.refresh(event)
    return event
