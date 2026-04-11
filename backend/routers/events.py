import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import EventCreate, EventUpdate, EventOut
from services import events as events_service
from scheduler import schedule_reminder, cancel_reminder
from config import settings

router = APIRouter()


def require_api_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("/events", response_model=list[EventOut], dependencies=[Depends(require_api_key)])
async def list_events(db: AsyncSession = Depends(get_db)):
    return await events_service.list_events(db)


@router.post("/events", response_model=EventOut, status_code=201, dependencies=[Depends(require_api_key)])
async def create_event(data: EventCreate, db: AsyncSession = Depends(get_db)):
    event = await events_service.create_event(db, data)
    schedule_reminder(event.id, event.remind_at)
    return event


@router.get("/events/{event_id}", response_model=EventOut, dependencies=[Depends(require_api_key)])
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    event = await events_service.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/events/{event_id}", response_model=EventOut, dependencies=[Depends(require_api_key)])
async def update_event(event_id: uuid.UUID, data: EventUpdate, db: AsyncSession = Depends(get_db)):
    event = await events_service.update_event(db, event_id, data)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    cancel_reminder(event_id)
    schedule_reminder(event.id, event.remind_at)
    return event


@router.delete("/events/{event_id}", response_model=EventOut, dependencies=[Depends(require_api_key)])
async def cancel_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    event = await events_service.cancel_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    cancel_reminder(event_id)
    return event
