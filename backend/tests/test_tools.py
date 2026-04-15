import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from services.events import create_event
from schemas import EventCreate


def make_dt(hours: int = 2) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)


@pytest.mark.asyncio
async def test_tools_create_event(db):
    from services.tools import create_event as tool_create
    now = datetime.now(timezone.utc)

    with patch("services.tools.schedule_reminder"):
        result = await tool_create(
            title="Reunião",
            datetime_iso=(now + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S-03:00"),
            remind_at_iso=None,
            user_phone="5511999",
            now=now,
            db=db,
        )

    assert "Reunião" in result
    assert "Evento criado" in result


@pytest.mark.asyncio
async def test_tools_list_events_empty(db):
    from services.tools import list_events as tool_list

    result = await tool_list(user_phone="5511999", db=db)

    assert "Nenhum evento" in result


@pytest.mark.asyncio
async def test_tools_list_events_with_data(db):
    from services.tools import list_events as tool_list
    await create_event(db, EventCreate(title="Dentista", event_datetime=make_dt(1), user_phone="5511999"))

    result = await tool_list(user_phone="5511999", db=db)

    assert "Dentista" in result


@pytest.mark.asyncio
async def test_tools_cancel_event_found(db):
    from services.tools import cancel_event as tool_cancel
    await create_event(db, EventCreate(title="Academia", event_datetime=make_dt(1), user_phone="5511999"))

    with patch("services.tools.cancel_reminder"):
        result = await tool_cancel(event_reference="academia", user_phone="5511999", db=db)

    assert "Academia" in result
    assert "cancelado" in result.lower()


@pytest.mark.asyncio
async def test_tools_cancel_event_not_found(db):
    from services.tools import cancel_event as tool_cancel

    result = await tool_cancel(event_reference="xyz inexistente", user_phone="5511999", db=db)

    assert "Não encontrei" in result


@pytest.mark.asyncio
async def test_tools_cancel_does_not_affect_other_user(db):
    from services.tools import cancel_event as tool_cancel
    await create_event(db, EventCreate(title="Reunião", event_datetime=make_dt(1), user_phone="phone_b"))

    result = await tool_cancel(event_reference="reunião", user_phone="phone_a", db=db)

    assert "Não encontrei" in result


@pytest.mark.asyncio
async def test_tools_edit_event_title(db):
    from services.tools import edit_event as tool_edit
    now = datetime.now(timezone.utc)
    await create_event(db, EventCreate(title="Consulta", event_datetime=make_dt(1), user_phone="5511999"))

    with patch("services.tools.cancel_reminder"), patch("services.tools.schedule_reminder"):
        result = await tool_edit(
            event_reference="consulta",
            field="title",
            new_value="Consulta Médica",
            user_phone="5511999",
            now=now,
            db=db,
        )

    assert "Consulta Médica" in result
    assert "atualizado" in result.lower()
