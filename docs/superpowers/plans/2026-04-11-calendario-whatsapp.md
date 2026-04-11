# Sistema de Calendário WhatsApp — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot de WhatsApp pessoal que interpreta mensagens em linguagem natural para criar eventos, dispara lembretes no horário certo, e exibe tudo num dashboard Next.js.

**Architecture:** FastAPI recebe webhook da Meta, passa mensagens para Claude API (NLP), salva eventos no PostgreSQL, usa APScheduler para disparar lembretes de volta via WhatsApp. Next.js no Vercel consome a API REST para exibir o calendário.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, asyncpg, APScheduler 3.x, Claude claude-haiku-4-5-20251001 (Anthropic SDK async), Meta Business API v18.0, Next.js 14 App Router, Tailwind CSS, FullCalendar, Render (backend + PostgreSQL), Vercel (frontend), UptimeRobot.

---

## File Structure

```
calendario-whatsapp/
├── backend/
│   ├── main.py                  # FastAPI app + lifespan (startup/shutdown)
│   ├── config.py                # Pydantic Settings (env vars)
│   ├── database.py              # SQLAlchemy async engine + session
│   ├── models.py                # Event ORM model
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── scheduler.py             # APScheduler setup, schedule/cancel jobs, load on startup
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhook.py           # POST /webhook (Meta messages) + GET /webhook (verification)
│   │   └── events.py            # CRUD: GET/POST /events, GET/PUT/DELETE /events/{id}
│   ├── services/
│   │   ├── __init__.py
│   │   ├── nlp.py               # Claude API: parse natural language → structured JSON
│   │   ├── whatsapp.py          # Meta Graph API: send messages
│   │   └── events.py            # DB operations: create, list, get, update, cancel
│   ├── tests/
│   │   ├── conftest.py          # Async test DB fixture, app client fixture
│   │   ├── test_nlp.py          # NLP parsing (mocked Claude)
│   │   ├── test_events_service.py # CRUD service layer
│   │   ├── test_events_router.py  # API endpoints
│   │   └── test_webhook.py      # Webhook verification + message flow
│   ├── requirements.txt
│   ├── .env.example
│   └── render.yaml
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx             # Calendar view (FullCalendar)
    │   └── events/
    │       └── page.tsx         # Events list
    ├── components/
    │   ├── CalendarView.tsx     # FullCalendar wrapper
    │   ├── EventList.tsx        # Chronological list with status badges
    │   └── EventModal.tsx       # Create/edit modal
    ├── lib/
    │   └── api.ts               # Typed fetch wrapper for backend
    ├── types/
    │   └── index.ts             # Event, EventCreate, EventUpdate types
    ├── package.json
    └── .env.local.example
```

---

## Task 1: Project Structure & Requirements

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/render.yaml`

- [ ] **Step 1: Create project directories**

```bash
mkdir -p "C:/Users/loren/Documents/projetos/calendario-whatsapp/backend/routers"
mkdir -p "C:/Users/loren/Documents/projetos/calendario-whatsapp/backend/services"
mkdir -p "C:/Users/loren/Documents/projetos/calendario-whatsapp/backend/tests"
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp/backend"
python -m venv venv
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
aiosqlite==0.20.0
pydantic-settings==2.2.1
httpx==0.27.0
anthropic==0.25.0
apscheduler==3.10.4
python-dotenv==1.0.1
pytest==8.2.0
pytest-asyncio==0.23.6
```

- [ ] **Step 3: Install dependencies**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp/backend"
venv/Scripts/pip install -r requirements.txt
```

Expected: All packages installed without errors.

- [ ] **Step 4: Create `backend/.env.example`**

```
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
ANTHROPIC_API_KEY=sk-ant-...
WHATSAPP_PHONE_NUMBER_ID=1234567890
WHATSAPP_ACCESS_TOKEN=EAAxxxxxx
WEBHOOK_VERIFY_TOKEN=meu_token_secreto
API_KEY=chave_secreta_dashboard
WHATSAPP_USER_PHONE=5511999999999
```

- [ ] **Step 5: Create `backend/render.yaml`**

```yaml
services:
  - type: web
    name: calendario-whatsapp-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: calendario-db
          property: connectionString
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: WHATSAPP_PHONE_NUMBER_ID
        sync: false
      - key: WHATSAPP_ACCESS_TOKEN
        sync: false
      - key: WEBHOOK_VERIFY_TOKEN
        sync: false
      - key: API_KEY
        sync: false
      - key: WHATSAPP_USER_PHONE
        sync: false

databases:
  - name: calendario-db
    databaseName: calendario
    user: calendario
```

- [ ] **Step 6: Init git repo**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp"
git init
echo "backend/venv/\n*.pyc\n__pycache__/\n.env\nbackend/.env\nfrontend/.env.local\nfrontend/node_modules/\n.next/" > .gitignore
git add .
git commit -m "chore: project structure and requirements"
```

---

## Task 2: Config & Database

**Files:**
- Create: `backend/config.py`
- Create: `backend/database.py`

- [ ] **Step 1: Create `backend/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    whatsapp_phone_number_id: str
    whatsapp_access_token: str
    webhook_verify_token: str
    api_key: str
    whatsapp_user_phone: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

- [ ] **Step 2: Create `backend/database.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3: Create `.env` from example for local dev**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp/backend"
copy .env.example .env
```

Edit `.env` and set `DATABASE_URL=sqlite+aiosqlite:///./dev.db` for local development. Fill other values with placeholders for now.

- [ ] **Step 4: Commit**

```bash
git add backend/config.py backend/database.py
git commit -m "feat: config and database setup"
```

---

## Task 3: Event Model & Schemas

**Files:**
- Create: `backend/models.py`
- Create: `backend/schemas.py`

- [ ] **Step 1: Create `backend/models.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    user_phone: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow()
    )
```

- [ ] **Step 2: Create `backend/schemas.py`**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add backend/models.py backend/schemas.py
git commit -m "feat: event model and pydantic schemas"
```

---

## Task 4: Events Service (with tests)

**Files:**
- Create: `backend/services/events.py`
- Create: `backend/services/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_events_service.py`

- [ ] **Step 1: Create `backend/services/__init__.py`**

```python
```
(empty file)

- [ ] **Step 2: Write failing test — `backend/tests/conftest.py`**

```python
import os
# Set env vars before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "123")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test_key")
os.environ.setdefault("API_KEY", "test_key")
os.environ.setdefault("WHATSAPP_USER_PHONE", "5511999999999")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database import Base
import models  # noqa: F401 — registers models with Base

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 3: Write failing tests — `backend/tests/test_events_service.py`**

```python
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
    # remind_at defaults to 30min before
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
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp/backend"
venv/Scripts/pytest tests/test_events_service.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `services.events` not found.

- [ ] **Step 5: Create `backend/services/events.py`**

```python
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


async def cancel_event(db: AsyncSession, event_id: uuid.UUID) -> Event | None:
    event = await get_event(db, event_id)
    if not event:
        return None
    event.status = "cancelled"
    await db.commit()
    await db.refresh(event)
    return event
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_events_service.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/services/ backend/tests/conftest.py backend/tests/test_events_service.py
git commit -m "feat: events service with CRUD operations"
```

---

## Task 5: NLP Service (with tests)

**Files:**
- Create: `backend/services/nlp.py`
- Create: `backend/tests/test_nlp.py`

- [ ] **Step 1: Write failing tests — `backend/tests/test_nlp.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from services.nlp import parse_message


def mock_claude_response(json_str: str):
    mock_content = MagicMock()
    mock_content.text = json_str
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


@pytest.mark.asyncio
async def test_parse_create_intent():
    now = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)
    json_str = '{"intent":"create","title":"Reunião com cliente","datetime":"2026-04-13T15:00:00-03:00","remind_at":"2026-04-13T14:30:00-03:00","event_reference":null,"field_to_edit":null,"new_value":null,"clarification_needed":false,"clarification_question":null}'

    with patch("services.nlp.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_claude_response(json_str))
        result = await parse_message("reunião com cliente amanhã às 15h", now)

    assert result["intent"] == "create"
    assert result["title"] == "Reunião com cliente"
    assert result["clarification_needed"] is False


@pytest.mark.asyncio
async def test_parse_list_intent():
    now = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)
    json_str = '{"intent":"list","title":null,"datetime":null,"remind_at":null,"event_reference":null,"field_to_edit":null,"new_value":null,"clarification_needed":false,"clarification_question":null}'

    with patch("services.nlp.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_claude_response(json_str))
        result = await parse_message("quais meus compromissos?", now)

    assert result["intent"] == "list"


@pytest.mark.asyncio
async def test_parse_ambiguous_returns_clarification():
    now = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)
    json_str = '{"intent":"create","title":"Médico","datetime":null,"remind_at":null,"event_reference":null,"field_to_edit":null,"new_value":null,"clarification_needed":true,"clarification_question":"Qual data e horário do médico?"}'

    with patch("services.nlp.client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_claude_response(json_str))
        result = await parse_message("preciso ir ao médico", now)

    assert result["clarification_needed"] is True
    assert "médico" in result["clarification_question"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_nlp.py -v
```

Expected: `ImportError` — `services.nlp` not found.

- [ ] **Step 3: Create `backend/services/nlp.py`**

```python
import json
from datetime import datetime
from anthropic import AsyncAnthropic
from config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are a calendar assistant. Parse the user's WhatsApp message and extract event information.

Return ONLY a valid JSON object with these fields:
- intent: "create" | "list" | "cancel" | "edit" | "unknown"
- title: string or null
- datetime: ISO 8601 string or null (event date/time)
- remind_at: ISO 8601 string or null (when to remind, default 30min before datetime)
- event_reference: string or null (for cancel/edit: which event)
- field_to_edit: "datetime" | "title" | "remind_at" or null
- new_value: string or null (for edit)
- clarification_needed: boolean
- clarification_question: string or null

Rules:
- Resolve relative dates ("amanhã", "semana que vem", "sexta") relative to current_datetime
- Timezone: America/Sao_Paulo (UTC-3)
- If time is not specified for a create intent, set clarification_needed=true
- Default remind_at = datetime - 30 minutes
- Return ONLY valid JSON, no explanation, no markdown"""


async def parse_message(message: str, current_datetime: datetime) -> dict:
    user_content = f"current_datetime: {current_datetime.isoformat()}\nmessage: {message}"

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    return json.loads(response.content[0].text)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_nlp.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/nlp.py backend/tests/test_nlp.py
git commit -m "feat: Claude NLP service for natural language parsing"
```

---

## Task 6: WhatsApp Service

**Files:**
- Create: `backend/services/whatsapp.py`

- [ ] **Step 1: Create `backend/services/whatsapp.py`**

```python
import httpx
from config import settings

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


async def send_message(to: str, text: str) -> None:
    """Send a WhatsApp text message via Meta Business API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_API_URL}/{settings.whatsapp_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
            timeout=10.0,
        )
        response.raise_for_status()
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/whatsapp.py
git commit -m "feat: Meta WhatsApp API client"
```

---

## Task 7: APScheduler Setup

**Files:**
- Create: `backend/scheduler.py`

- [ ] **Step 1: Create `backend/scheduler.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/scheduler.py
git commit -m "feat: APScheduler for reminder dispatch with DB persistence"
```

---

## Task 8: Events Router (CRUD API)

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/events.py`
- Create: `backend/tests/test_events_router.py`

- [ ] **Step 1: Create `backend/routers/__init__.py`**

```python
```
(empty file)

- [ ] **Step 2: Write failing tests — `backend/tests/test_events_router.py`**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone, timedelta


def future_dt(hours: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


@pytest.mark.asyncio
async def test_create_event_via_api(app_client):
    response = await app_client.post("/events", json={
        "title": "Dentista",
        "event_datetime": future_dt(5),
        "user_phone": "5511999999999",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Dentista"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_events_via_api(app_client):
    await app_client.post("/events", json={"title": "Evento A", "event_datetime": future_dt(1), "user_phone": "55"})
    await app_client.post("/events", json={"title": "Evento B", "event_datetime": future_dt(2), "user_phone": "55"})
    response = await app_client.get("/events")
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_delete_event_via_api(app_client):
    create_resp = await app_client.post("/events", json={"title": "Del", "event_datetime": future_dt(1), "user_phone": "55"})
    event_id = create_resp.json()["id"]
    del_resp = await app_client.delete(f"/events/{event_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_requires_api_key(app_client_no_auth):
    response = await app_client_no_auth.get("/events")
    assert response.status_code == 401
```

- [ ] **Step 3: Update `backend/tests/conftest.py` to add app fixtures**

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database import Base, get_db
import models  # noqa: F401
from httpx import AsyncClient, ASGITransport

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def app_client(db):
    from main import app
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test_key"},
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def app_client_no_auth(db):
    from main import app
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

- [ ] **Step 4: Create `backend/routers/events.py`**

```python
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
```

- [ ] **Step 5: Create minimal `backend/main.py` (enough to run tests)**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from scheduler import scheduler, load_pending_reminders
from routers.events import router as events_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    scheduler.start()
    await load_pending_reminders()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
venv/Scripts/pytest tests/test_events_router.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/ backend/tests/conftest.py backend/tests/test_events_router.py backend/main.py
git commit -m "feat: events REST API with API key auth"
```

---

## Task 9: Webhook Router

**Files:**
- Create: `backend/routers/webhook.py`
- Create: `backend/tests/test_webhook.py`

- [ ] **Step 1: Write failing tests — `backend/tests/test_webhook.py`**

```python
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta


@pytest.mark.asyncio
async def test_webhook_verification(app_client_no_auth):
    response = await app_client_no_auth.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "test_key",
        "hub.challenge": "CHALLENGE_ACCEPTED",
    })
    assert response.status_code == 200
    assert response.text == "CHALLENGE_ACCEPTED"


@pytest.mark.asyncio
async def test_webhook_verification_wrong_token(app_client_no_auth):
    response = await app_client_no_auth.get("/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token",
        "hub.challenge": "123",
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_create_event(app_client_no_auth):
    future = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    remind = (datetime.now(timezone.utc) + timedelta(hours=2, minutes=30)).isoformat()

    parsed = {
        "intent": "create", "title": "Reunião", "datetime": future,
        "remind_at": remind, "event_reference": None, "field_to_edit": None,
        "new_value": None, "clarification_needed": False, "clarification_question": None
    }

    with patch("routers.webhook.nlp.parse_message", new_callable=AsyncMock, return_value=parsed), \
         patch("routers.webhook.whatsapp.send_message", new_callable=AsyncMock), \
         patch("routers.webhook.schedule_reminder"):

        payload = {
            "entry": [{"changes": [{"value": {
                "messages": [{"from": "5511999999999", "text": {"body": "reunião amanhã às 15h"}}]
            }}]}]
        }
        response = await app_client_no_auth.post("/webhook", json=payload)
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
venv/Scripts/pytest tests/test_webhook.py -v
```

Expected: FAIL — `routers.webhook` not found.

- [ ] **Step 3: Create `backend/routers/webhook.py`**

```python
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from config import settings
from services import nlp, whatsapp
from services import events as events_service
from schemas import EventCreate, EventUpdate
from scheduler import schedule_reminder, cancel_reminder
import uuid

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
    parsed = await nlp.parse_message(text, now)

    if parsed.get("clarification_needed"):
        await whatsapp.send_message(from_number, parsed["clarification_question"])
        return {"status": "ok"}

    intent = parsed.get("intent")

    if intent == "create":
        event_dt = datetime.fromisoformat(parsed["datetime"])
        remind_at = datetime.fromisoformat(parsed["remind_at"])
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
                new_dt = datetime.fromisoformat(new_val)
                update_data["event_datetime"] = new_dt
                update_data["remind_at"] = new_dt - timedelta(minutes=30)
            elif field == "title":
                update_data["title"] = new_val
            elif field == "remind_at":
                update_data["remind_at"] = datetime.fromisoformat(new_val)
            updated = await events_service.update_event(db, matched.id, EventUpdate(**update_data))
            if updated:
                cancel_reminder(matched.id)
                schedule_reminder(updated.id, updated.remind_at)
                await whatsapp.send_message(from_number, f"Evento atualizado: {updated.title}")
        else:
            await whatsapp.send_message(from_number, "Evento não encontrado.")

    else:
        await whatsapp.send_message(
            from_number,
            "Não entendi. Exemplos:\n• 'reunião amanhã às 15h'\n• 'quais meus eventos?'\n• 'cancela a reunião de amanhã'"
        )

    return {"status": "ok"}
```

- [ ] **Step 4: Update `backend/main.py` to include webhook router**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from scheduler import scheduler, load_pending_reminders
from routers.events import router as events_router
from routers.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    scheduler.start()
    await load_pending_reminders()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(events_router)
```

- [ ] **Step 5: Verify `conftest.py` already has env vars at top**

The env vars were set in Task 4 Step 2. No changes needed here.

- [ ] **Step 6: Run all tests**

```bash
venv/Scripts/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/webhook.py backend/tests/test_webhook.py backend/main.py backend/tests/conftest.py
git commit -m "feat: webhook handler for Meta WhatsApp API"
```

---

## Task 10: Frontend Setup (Next.js)

**Files:**
- Create: `frontend/` (scaffolded by Next.js CLI)
- Create: `frontend/types/index.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/.env.local.example`

- [ ] **Step 1: Scaffold Next.js project**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp"
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*"
cd frontend
npm install @fullcalendar/react @fullcalendar/daygrid @fullcalendar/interaction
```

- [ ] **Step 2: Create `frontend/.env.local.example`**

```
NEXT_PUBLIC_API_URL=https://calendario-whatsapp-api.onrender.com
NEXT_PUBLIC_API_KEY=chave_secreta_dashboard
```

```bash
cp .env.local.example .env.local
```

Edit `.env.local` and set `NEXT_PUBLIC_API_URL=http://localhost:8000` for local dev.

- [ ] **Step 3: Create `frontend/types/index.ts`**

```typescript
export interface Event {
  id: string
  title: string
  description: string | null
  event_datetime: string
  remind_at: string
  status: 'pending' | 'sent' | 'cancelled'
  user_phone: string
  created_at: string
}

export interface EventCreate {
  title: string
  description?: string
  event_datetime: string
  remind_at?: string
  user_phone?: string
}

export interface EventUpdate {
  title?: string
  description?: string
  event_datetime?: string
  remind_at?: string
}
```

- [ ] **Step 4: Create `frontend/lib/api.ts`**

```typescript
import { Event, EventCreate, EventUpdate } from '@/types'

const BASE = process.env.NEXT_PUBLIC_API_URL!
const KEY = process.env.NEXT_PUBLIC_API_KEY!

const headers = () => ({
  'Content-Type': 'application/json',
  'X-API-Key': KEY,
})

export async function fetchEvents(): Promise<Event[]> {
  const res = await fetch(`${BASE}/events`, { headers: headers() })
  if (!res.ok) throw new Error('Failed to fetch events')
  return res.json()
}

export async function createEvent(data: EventCreate): Promise<Event> {
  const res = await fetch(`${BASE}/events`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create event')
  return res.json()
}

export async function updateEvent(id: string, data: EventUpdate): Promise<Event> {
  const res = await fetch(`${BASE}/events/${id}`, {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update event')
  return res.json()
}

export async function deleteEvent(id: string): Promise<Event> {
  const res = await fetch(`${BASE}/events/${id}`, {
    method: 'DELETE',
    headers: headers(),
  })
  if (!res.ok) throw new Error('Failed to cancel event')
  return res.json()
}
```

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp"
git add frontend/
git commit -m "feat: Next.js frontend scaffolding with API client"
```

---

## Task 11: EventModal Component

**Files:**
- Create: `frontend/components/EventModal.tsx`

- [ ] **Step 1: Create `frontend/components/EventModal.tsx`**

```typescript
'use client'
import { useState } from 'react'
import { Event, EventCreate } from '@/types'
import { createEvent, updateEvent } from '@/lib/api'

interface Props {
  event?: Event
  onClose: () => void
  onSaved: () => void
}

const REMIND_OPTIONS = [
  { label: '15 min antes', minutes: 15 },
  { label: '30 min antes', minutes: 30 },
  { label: '1 hora antes', minutes: 60 },
  { label: '1 dia antes', minutes: 1440 },
]

export default function EventModal({ event, onClose, onSaved }: Props) {
  const [title, setTitle] = useState(event?.title ?? '')
  const [description, setDescription] = useState(event?.description ?? '')
  const [datetime, setDatetime] = useState(
    event ? event.event_datetime.slice(0, 16) : ''
  )
  const [remindMinutes, setRemindMinutes] = useState(30)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title || !datetime) return
    setLoading(true)
    try {
      const dt = new Date(datetime)
      const remindAt = new Date(dt.getTime() - remindMinutes * 60 * 1000)
      if (event) {
        await updateEvent(event.id, {
          title,
          description: description || undefined,
          event_datetime: dt.toISOString(),
          remind_at: remindAt.toISOString(),
        })
      } else {
        const data: EventCreate = {
          title,
          description: description || undefined,
          event_datetime: dt.toISOString(),
          remind_at: remindAt.toISOString(),
          user_phone: '',
        }
        await createEvent(data)
      }
      onSaved()
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold mb-4">
          {event ? 'Editar evento' : 'Novo evento'}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Título</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              placeholder="Ex: Reunião com cliente"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição (opcional)</label>
            <textarea
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data e hora</label>
            <input
              type="datetime-local"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={datetime}
              onChange={(e) => setDatetime(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Lembrete</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={remindMinutes}
              onChange={(e) => setRemindMinutes(Number(e.target.value))}
            >
              {REMIND_OPTIONS.map((o) => (
                <option key={o.minutes} value={o.minutes}>{o.label}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 rounded-lg py-2 text-gray-700 hover:bg-gray-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/EventModal.tsx
git commit -m "feat: EventModal for creating and editing events"
```

---

## Task 12: EventList Component

**Files:**
- Create: `frontend/components/EventList.tsx`

- [ ] **Step 1: Create `frontend/components/EventList.tsx`**

```typescript
'use client'
import { Event } from '@/types'
import { deleteEvent } from '@/lib/api'

const STATUS_COLORS = {
  pending: 'bg-blue-100 text-blue-700',
  sent: 'bg-green-100 text-green-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

const STATUS_LABELS = {
  pending: 'Pendente',
  sent: 'Enviado',
  cancelled: 'Cancelado',
}

interface Props {
  events: Event[]
  onEdit: (event: Event) => void
  onRefresh: () => void
}

export default function EventList({ events, onEdit, onRefresh }: Props) {
  async function handleCancel(id: string) {
    if (!confirm('Cancelar este evento?')) return
    await deleteEvent(id)
    onRefresh()
  }

  if (events.length === 0) {
    return <p className="text-gray-500 text-center py-8">Nenhum evento encontrado.</p>
  }

  return (
    <ul className="space-y-3">
      {events.map((event) => (
        <li key={event.id} className="border border-gray-200 rounded-xl p-4 flex items-start justify-between gap-4">
          <div>
            <p className="font-medium text-gray-900">{event.title}</p>
            {event.description && (
              <p className="text-sm text-gray-500 mt-0.5">{event.description}</p>
            )}
            <p className="text-sm text-gray-600 mt-1">
              {new Date(event.event_datetime).toLocaleString('pt-BR', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
              })}
            </p>
            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[event.status]}`}>
              {STATUS_LABELS[event.status]}
            </span>
          </div>
          {event.status === 'pending' && (
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => onEdit(event)}
                className="text-sm text-blue-600 hover:underline"
              >
                Editar
              </button>
              <button
                onClick={() => handleCancel(event.id)}
                className="text-sm text-red-500 hover:underline"
              >
                Cancelar
              </button>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/EventList.tsx
git commit -m "feat: EventList with status badges and actions"
```

---

## Task 13: Calendar View & Main Page

**Files:**
- Create: `frontend/components/CalendarView.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Create `frontend/components/CalendarView.tsx`**

```typescript
'use client'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import { Event } from '@/types'
import ptBrLocale from '@fullcalendar/core/locales/pt-br'

interface Props {
  events: Event[]
  onEventClick: (event: Event) => void
}

export default function CalendarView({ events, onEventClick }: Props) {
  const calendarEvents = events.map((e) => ({
    id: e.id,
    title: e.title,
    start: e.event_datetime,
    color: e.status === 'sent' ? '#16a34a' : e.status === 'cancelled' ? '#9ca3af' : '#2563eb',
    extendedProps: { original: e },
  }))

  return (
    <FullCalendar
      plugins={[dayGridPlugin, interactionPlugin]}
      initialView="dayGridMonth"
      locale={ptBrLocale}
      events={calendarEvents}
      eventClick={(info) => onEventClick(info.event.extendedProps.original as Event)}
      height="auto"
    />
  )
}
```

- [ ] **Step 2: Replace `frontend/app/layout.tsx`**

```typescript
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Calendário',
  description: 'Sistema pessoal de lembretes',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  )
}
```

- [ ] **Step 3: Replace `frontend/app/page.tsx`**

```typescript
'use client'
import { useCallback, useEffect, useState } from 'react'
import { Event } from '@/types'
import { fetchEvents } from '@/lib/api'
import CalendarView from '@/components/CalendarView'
import EventList from '@/components/EventList'
import EventModal from '@/components/EventModal'

export default function HomePage() {
  const [events, setEvents] = useState<Event[]>([])
  const [view, setView] = useState<'calendar' | 'list'>('calendar')
  const [modal, setModal] = useState<{ open: boolean; event?: Event }>({ open: false })

  const load = useCallback(async () => {
    const data = await fetchEvents()
    setEvents(data)
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Meu Calendário</h1>
        <div className="flex gap-2">
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setView('calendar')}
              className={`px-3 py-1.5 text-sm ${view === 'calendar' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Calendário
            </button>
            <button
              onClick={() => setView('list')}
              className={`px-3 py-1.5 text-sm ${view === 'list' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              Lista
            </button>
          </div>
          <button
            onClick={() => setModal({ open: true })}
            className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-blue-700"
          >
            + Novo evento
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        {view === 'calendar' ? (
          <CalendarView events={events} onEventClick={(e) => setModal({ open: true, event: e })} />
        ) : (
          <EventList events={events} onEdit={(e) => setModal({ open: true, event: e })} onRefresh={load} />
        )}
      </div>

      {modal.open && (
        <EventModal
          event={modal.event}
          onClose={() => setModal({ open: false })}
          onSaved={load}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Start dev server and verify visually**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp/frontend"
npm run dev
```

Open `http://localhost:3000` — verify: calendar renders, "Novo evento" opens modal, toggle between calendar/list works.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/CalendarView.tsx frontend/app/page.tsx frontend/app/layout.tsx
git commit -m "feat: calendar and list views with event modal"
```

---

## Task 14: Deploy Backend to Render

- [ ] **Step 1: Push to GitHub**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp"
git remote add origin https://github.com/LolasPaluza/projetos.git
git push -u origin main
```

- [ ] **Step 2: Create Render service**

1. Acesse render.com → New → Web Service
2. Connect GitHub → selecione o repositório `projetos`
3. Set **Root Directory** to `calendario-whatsapp/backend`
4. Runtime: Python 3
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

- [ ] **Step 3: Create PostgreSQL database on Render**

1. Render → New → PostgreSQL
2. Name: `calendario-db`
3. Copy the **Internal Database URL** (formato `postgresql://...`)
4. Nas env vars do Web Service, adicione `DATABASE_URL` com esse valor — **substitua `postgresql://` por `postgresql+asyncpg://`**

- [ ] **Step 4: Set all environment variables on Render**

No painel do Web Service → Environment:
```
ANTHROPIC_API_KEY=sk-ant-...
WHATSAPP_PHONE_NUMBER_ID=<seu phone number id>
WHATSAPP_ACCESS_TOKEN=<seu token permanente>
WEBHOOK_VERIFY_TOKEN=<crie um token qualquer ex: meu_token_2026>
API_KEY=<crie uma chave para o dashboard>
WHATSAPP_USER_PHONE=<seu número com DDI, ex: 5511999999999>
```

- [ ] **Step 5: Verify deployment**

```bash
curl https://<seu-app>.onrender.com/events -H "X-API-Key: <sua_api_key>"
```

Expected: `[]` (empty array).

---

## Task 15: Configure Meta WhatsApp Business API

- [ ] **Step 1: Create Meta Developer App**

1. Acesse developers.facebook.com → My Apps → Create App
2. Business type → Next
3. App name: `Calendario Pessoal`
4. Adicione o produto **WhatsApp**

- [ ] **Step 2: Configure webhook**

1. WhatsApp → Configuration → Webhook
2. Callback URL: `https://<seu-app>.onrender.com/webhook`
3. Verify token: o mesmo `WEBHOOK_VERIFY_TOKEN` do Render
4. Subscribe to: `messages`
5. Clique Verify and Save

- [ ] **Step 3: Get credentials**

1. WhatsApp → API Setup
2. Copie o **Phone number ID** → coloca no Render como `WHATSAPP_PHONE_NUMBER_ID`
3. Gere um **Permanent Access Token** (System User no Business Manager) → coloca como `WHATSAPP_ACCESS_TOKEN`

- [ ] **Step 4: Test end-to-end**

Mande uma mensagem no WhatsApp para o número do bot: `"reunião de teste amanhã às 10h"`

Expected: bot responde com confirmação do evento criado.

---

## Task 16: Deploy Frontend to Vercel + UptimeRobot

- [ ] **Step 1: Deploy frontend to Vercel**

```bash
cd "C:/Users/loren/Documents/projetos/calendario-whatsapp/frontend"
npx vercel --prod
```

Quando perguntar sobre configurações:
- Root directory: `frontend`
- Framework: Next.js (detecta automaticamente)

- [ ] **Step 2: Set environment variables on Vercel**

No painel Vercel → Settings → Environment Variables:
```
NEXT_PUBLIC_API_URL=https://<seu-app>.onrender.com
NEXT_PUBLIC_API_KEY=<mesma api_key do backend>
```

Redeploy após adicionar as variáveis.

- [ ] **Step 3: Configure UptimeRobot**

1. Acesse uptimerobot.com → Create Monitor
2. Monitor Type: HTTP(s)
3. URL: `https://<seu-app>.onrender.com/events` 
4. Monitoring Interval: 5 minutes
5. Add header: `X-API-Key: <sua_api_key>`

Isso mantém o Render acordado 24h.

- [ ] **Step 4: Final end-to-end test**

- Mande mensagem no WhatsApp: `"reunião de teste em 2 minutos"`
- Acesse o dashboard Vercel — evento deve aparecer no calendário
- Aguarde 2 minutos — lembrete deve chegar no WhatsApp

- [ ] **Step 5: Final commit**

```bash
git add .
git commit -m "feat: sistema de calendário WhatsApp completo"
git push
```
