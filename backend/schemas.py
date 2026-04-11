import uuid
from datetime import datetime
from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: str | None = None
    event_datetime: datetime
    remind_at: datetime | None = None
    user_phone: str = ""


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_datetime: datetime | None = None
    remind_at: datetime | None = None


class EventOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    event_datetime: datetime
    remind_at: datetime
    status: str
    user_phone: str
    created_at: datetime

    model_config = {"from_attributes": True}
