import pytest
from datetime import datetime, timezone, timedelta
from services.events import create_event, list_events, get_event, update_event, cancel_event
from schemas import EventCreate, EventUpdate


def make_dt(hours_from_now: int = 2) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours_from_now)


@pytest.mark.asyncio
async def test_create_event(db):
    event = await create_event(db, EventCreate(
        title="Reunião",
        event_datetime=make_dt(2),
        user_phone="5511999999999",
    ))
    assert event.id is not None
    assert event.title == "Reunião"
    assert event.status == "pending"
    expected_remind = event.event_datetime - timedelta(minutes=30)
    assert abs((event.remind_at - expected_remind).total_seconds()) < 2


@pytest.mark.asyncio
async def test_list_events_only_pending(db):
    await create_event(db, EventCreate(title="A", event_datetime=make_dt(1), user_phone="55"))
    await create_event(db, EventCreate(title="B", event_datetime=make_dt(2), user_phone="55"))
    events = await list_events(db)
    assert len(events) == 2
    assert all(e.status == "pending" for e in events)


@pytest.mark.asyncio
async def test_cancel_event(db):
    event = await create_event(db, EventCreate(title="X", event_datetime=make_dt(1), user_phone="55"))
    cancelled = await cancel_event(db, event.id)
    assert cancelled.status == "cancelled"
    pending = await list_events(db)
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_update_event_title(db):
    event = await create_event(db, EventCreate(title="Old", event_datetime=make_dt(1), user_phone="55"))
    updated = await update_event(db, event.id, EventUpdate(title="New"))
    assert updated.title == "New"


@pytest.mark.asyncio
async def test_get_event_not_found(db):
    import uuid
    result = await get_event(db, uuid.uuid4())
    assert result is None
