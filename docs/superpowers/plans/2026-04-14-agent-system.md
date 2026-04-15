# Agent System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refatorar o backend para um CalendarAgent com tool calling nativo do Gemini, histórico de conversa por usuário em PostgreSQL, e correção do bug de isolamento multi-usuário.

**Architecture:** Um `CalendarAgent` em `services/agent.py` encapsula o loop LLM + tool calling. O `webhook.py` vira uma camada thin de HTTP (~30 linhas). Quatro tool functions em `services/tools.py` executam as ações no DB e retornam strings formatadas (short-circuit sem segundo LLM call). Histórico dos últimos 10 turnos por usuário é persistido em `conversation_messages` no PostgreSQL.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, Gemini 2.5 Flash (google-genai), pytest-asyncio, SQLite (testes)

---

## File Map

| Arquivo | Ação |
|---|---|
| `backend/services/events.py` | MODIFICAR — adicionar parâmetro `user_phone` opcional em list methods |
| `backend/models.py` | MODIFICAR — adicionar `ConversationMessage` |
| `backend/tests/conftest.py` | MODIFICAR — trocar `ANTHROPIC_API_KEY` por `GEMINI_API_KEY` |
| `backend/services/tools.py` | CRIAR — 4 tool functions |
| `backend/tests/test_tools.py` | CRIAR — testes das tools |
| `backend/services/agent.py` | CRIAR — `CalendarAgent` class |
| `backend/tests/test_agent.py` | CRIAR — testes do agent |
| `backend/routers/webhook.py` | SIMPLIFICAR — remover toda lógica de negócio |
| `backend/services/nlp.py` | DELETAR |
| `backend/tests/test_nlp.py` | DELETAR |

---

## Task 1: Fix user_phone isolation em events service

**Files:**
- Modify: `backend/services/events.py`
- Modify: `backend/tests/test_events_service.py`

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `backend/tests/test_events_service.py`:

```python
@pytest.mark.asyncio
async def test_list_events_isolated_by_phone(db):
    """Usuário A não deve ver eventos do usuário B."""
    await create_event(db, EventCreate(title="Evento A", event_datetime=make_dt(1), user_phone="phone_a"))
    await create_event(db, EventCreate(title="Evento B", event_datetime=make_dt(2), user_phone="phone_b"))

    events_a = await list_events(db, user_phone="phone_a")
    events_b = await list_events(db, user_phone="phone_b")

    assert len(events_a) == 1
    assert events_a[0].title == "Evento A"
    assert len(events_b) == 1
    assert events_b[0].title == "Evento B"


@pytest.mark.asyncio
async def test_list_upcoming_isolated_by_phone(db):
    """list_upcoming_events filtra por phone."""
    await create_event(db, EventCreate(title="Futuro A", event_datetime=make_dt(1), user_phone="phone_a"))
    await create_event(db, EventCreate(title="Futuro B", event_datetime=make_dt(2), user_phone="phone_b"))

    upcoming_a = await list_upcoming_events(db, user_phone="phone_a")

    assert len(upcoming_a) == 1
    assert upcoming_a[0].title == "Futuro A"
```

Também atualizar o import no topo de `test_events_service.py`:
```python
from services.events import create_event, list_events, list_upcoming_events, get_event, update_event, cancel_event
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd backend && python -m pytest tests/test_events_service.py::test_list_events_isolated_by_phone -v
```
Esperado: `FAILED` — `list_events() got an unexpected keyword argument 'user_phone'`

- [ ] **Step 3: Implementar o fix em `services/events.py`**

Substituir as funções `list_events` e `list_upcoming_events` por:

```python
async def list_events(db: AsyncSession, user_phone: str | None = None, status: str = "pending") -> list[Event]:
    query = select(Event).where(Event.status == status)
    if user_phone:
        query = query.where(Event.user_phone == user_phone)
    result = await db.execute(query.order_by(Event.event_datetime))
    return list(result.scalars().all())


async def list_upcoming_events(db: AsyncSession, user_phone: str | None = None) -> list[Event]:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    query = (
        select(Event)
        .where(Event.event_datetime > now, Event.status != "cancelled")
    )
    if user_phone:
        query = query.where(Event.user_phone == user_phone)
    result = await db.execute(query.order_by(Event.event_datetime))
    return list(result.scalars().all())
```

- [ ] **Step 4: Rodar todos os testes de events**

```bash
cd backend && python -m pytest tests/test_events_service.py -v
```
Esperado: todos passando (`PASSED`)

- [ ] **Step 5: Commit**

```bash
cd backend && git add services/events.py tests/test_events_service.py
git commit -m "fix: isolate events by user_phone in list queries"
```

---

## Task 2: Adicionar ConversationMessage ao model + fix conftest

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Escrever teste que falha**

Criar `backend/tests/test_conversation_model.py`:

```python
import pytest
from datetime import datetime, timezone
from models import ConversationMessage


@pytest.mark.asyncio
async def test_save_and_load_conversation(db):
    from sqlalchemy import select

    db.add(ConversationMessage(user_phone="5511999", role="user", content="oi"))
    db.add(ConversationMessage(user_phone="5511999", role="model", content="olá!"))
    await db.commit()

    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.user_phone == "5511999")
        .order_by(ConversationMessage.created_at)
    )
    msgs = list(result.scalars().all())

    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "oi"
    assert msgs[1].role == "model"
    assert msgs[1].content == "olá!"
    assert msgs[0].created_at is not None


@pytest.mark.asyncio
async def test_conversation_isolated_by_phone(db):
    from sqlalchemy import select

    db.add(ConversationMessage(user_phone="phone_a", role="user", content="msg a"))
    db.add(ConversationMessage(user_phone="phone_b", role="user", content="msg b"))
    await db.commit()

    result = await db.execute(
        select(ConversationMessage).where(ConversationMessage.user_phone == "phone_a")
    )
    msgs = list(result.scalars().all())
    assert len(msgs) == 1
    assert msgs[0].content == "msg a"
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd backend && python -m pytest tests/test_conversation_model.py -v
```
Esperado: `FAILED` — `cannot import name 'ConversationMessage' from 'models'`

- [ ] **Step 3: Adicionar ConversationMessage em `backend/models.py`**

Adicionar ao final do arquivo (após a classe `Event`):

```python
class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_phone: Mapped[str] = mapped_column(String(30), index=True)
    role: Mapped[str] = mapped_column(String(10))  # "user" | "model"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
```

- [ ] **Step 4: Trocar env var em `backend/tests/conftest.py`**

Substituir a linha:
```python
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
```
Por:
```python
os.environ.setdefault("GEMINI_API_KEY", "test")
```

- [ ] **Step 5: Rodar para confirmar passa**

```bash
cd backend && python -m pytest tests/test_conversation_model.py -v
```
Esperado: `PASSED`

- [ ] **Step 6: Confirmar que todos os testes anteriores ainda passam**

```bash
cd backend && python -m pytest tests/test_events_service.py tests/test_conversation_model.py -v
```
Esperado: todos `PASSED`

- [ ] **Step 7: Commit**

```bash
git add models.py tests/conftest.py tests/test_conversation_model.py
git commit -m "feat: add ConversationMessage model for per-user chat history"
```

---

## Task 3: Criar services/tools.py

**Files:**
- Create: `backend/services/tools.py`
- Create: `backend/tests/test_tools.py`

- [ ] **Step 1: Escrever testes que falham**

Criar `backend/tests/test_tools.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
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

    with patch("services.tools.cancel_reminder"):
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
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd backend && python -m pytest tests/test_tools.py -v
```
Esperado: `FAILED` — `ModuleNotFoundError: No module named 'services.tools'`

- [ ] **Step 3: Criar `backend/services/tools.py`**

```python
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

    cancel_reminder(matched.id)
    schedule_reminder(updated.id, updated.remind_at)
    return f"Evento atualizado: *{updated.title}*"
```

- [ ] **Step 4: Rodar para confirmar passa**

```bash
cd backend && python -m pytest tests/test_tools.py -v
```
Esperado: todos os 7 testes `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/tools.py tests/test_tools.py
git commit -m "feat: add tool functions for agent system"
```

---

## Task 4: Criar services/agent.py

**Files:**
- Create: `backend/services/agent.py`
- Create: `backend/tests/test_agent.py`

- [ ] **Step 1: Escrever testes que falham**

Criar `backend/tests/test_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


def _make_gemini_text_response(text: str):
    """Mock de resposta Gemini com texto direto (sem tool call)."""
    part = MagicMock()
    part.function_call = None
    part.text = text
    candidate = MagicMock()
    candidate.content.parts = [part]
    response = MagicMock()
    response.candidates = [candidate]
    response.text = text
    return response


def _make_gemini_tool_response(tool_name: str, args: dict):
    """Mock de resposta Gemini com function_call."""
    fc = MagicMock()
    fc.name = tool_name
    fc.args = args
    part = MagicMock()
    part.function_call = fc
    candidate = MagicMock()
    candidate.content.parts = [part]
    response = MagicMock()
    response.candidates = [candidate]
    return response


@pytest.mark.asyncio
async def test_agent_conversational_response(db):
    """Agent retorna texto direto quando Gemini não chama tool."""
    from services.agent import CalendarAgent
    agent = CalendarAgent()

    mock_response = _make_gemini_text_response("Olá! Como posso ajudar?")

    with patch.object(agent.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_response
        reply = await agent.run(phone="5511999", text="oi", db=db)

    assert reply == "Olá! Como posso ajudar?"


@pytest.mark.asyncio
async def test_agent_tool_create_event(db):
    """Agent executa tool create_event quando Gemini retorna function_call."""
    from services.agent import CalendarAgent
    from datetime import timedelta
    agent = CalendarAgent()

    now = datetime.now(timezone.utc)
    future_iso = (now + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S-03:00")
    mock_response = _make_gemini_tool_response("create_event", {
        "title": "Reunião",
        "datetime_iso": future_iso,
    })

    with patch.object(agent.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_generate, \
         patch("services.tools.schedule_reminder"):
        mock_generate.return_value = mock_response
        reply = await agent.run(phone="5511999", text="reunião amanhã às 10h", db=db)

    assert "Reunião" in reply
    assert "Evento criado" in reply


@pytest.mark.asyncio
async def test_agent_saves_history(db):
    """Agent persiste turnos no DB após cada interação."""
    from services.agent import CalendarAgent
    from models import ConversationMessage
    from sqlalchemy import select
    agent = CalendarAgent()

    mock_response = _make_gemini_text_response("Tudo bem!")

    with patch.object(agent.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_response
        await agent.run(phone="5511999", text="como vai?", db=db)

    result = await db.execute(
        select(ConversationMessage).where(ConversationMessage.user_phone == "5511999")
    )
    msgs = list(result.scalars().all())
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "como vai?"
    assert msgs[1].role == "model"
    assert msgs[1].content == "Tudo bem!"


@pytest.mark.asyncio
async def test_agent_loads_history_in_context(db):
    """Agent inclui histórico anterior no contexto enviado ao Gemini."""
    from services.agent import CalendarAgent
    from models import ConversationMessage
    from datetime import datetime, timezone
    agent = CalendarAgent()

    # Pré-popular histórico
    db.add(ConversationMessage(user_phone="5511999", role="user", content="mensagem anterior"))
    db.add(ConversationMessage(user_phone="5511999", role="model", content="resposta anterior"))
    await db.commit()

    mock_response = _make_gemini_text_response("Resposta atual")

    with patch.object(agent.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_response
        await agent.run(phone="5511999", text="nova mensagem", db=db)

    call_args = mock_generate.call_args
    contents = call_args.kwargs.get("contents") or call_args.args[1] if call_args.args else call_args.kwargs["contents"]
    # Deve ter pelo menos 3 itens: 2 de histórico + 1 atual
    assert len(contents) >= 3


@pytest.mark.asyncio
async def test_agent_gemini_error_returns_fallback(db):
    """Agent retorna mensagem de fallback se Gemini falhar."""
    from services.agent import CalendarAgent
    agent = CalendarAgent()

    with patch.object(agent.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = Exception("API timeout")
        reply = await agent.run(phone="5511999", text="oi", db=db)

    assert "problema" in reply.lower() or "tente" in reply.lower()
```

- [ ] **Step 2: Rodar para confirmar falha**

```bash
cd backend && python -m pytest tests/test_agent.py -v
```
Esperado: `FAILED` — `ModuleNotFoundError: No module named 'services.agent'`

- [ ] **Step 3: Criar `backend/services/agent.py`**

```python
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config import settings
from models import ConversationMessage
import services.tools as tool_funcs

BRT = ZoneInfo("America/Sao_Paulo")
logger = logging.getLogger(__name__)

HISTORY_LIMIT = 10

SYSTEM_PROMPT_TEMPLATE = (
    "Você é um assistente de agenda pessoal via WhatsApp.\n"
    "Data/hora atual: {now_brt} (horário de Brasília)\n"
    "Responda sempre em português brasileiro, de forma curta e natural.\n"
    "Para criar, listar, editar ou cancelar eventos — use as tools disponíveis."
)

TOOL_DECLARATIONS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="create_event",
        description="Cria um evento na agenda do usuário",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "title": types.Schema(type="STRING", description="Título do evento"),
                "datetime_iso": types.Schema(type="STRING", description="Data e hora em ISO 8601 com fuso -03:00"),
                "remind_at_iso": types.Schema(type="STRING", description="Horário do lembrete em ISO 8601. Opcional — padrão: 30min antes"),
            },
            required=["title", "datetime_iso"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_events",
        description="Lista os próximos eventos da agenda do usuário",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="cancel_event",
        description="Cancela um evento existente na agenda",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "event_reference": types.Schema(type="STRING", description="Nome ou referência do evento a cancelar"),
            },
            required=["event_reference"],
        ),
    ),
    types.FunctionDeclaration(
        name="edit_event",
        description="Edita um campo de um evento existente",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "event_reference": types.Schema(type="STRING", description="Nome ou referência do evento a editar"),
                "field": types.Schema(type="STRING", description="Campo a editar: 'datetime', 'title' ou 'remind_at'"),
                "new_value": types.Schema(type="STRING", description="Novo valor do campo"),
            },
            required=["event_reference", "field", "new_value"],
        ),
    ),
])


class CalendarAgent:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def run(self, phone: str, text: str, db: AsyncSession) -> str:
        now = datetime.now(timezone.utc)
        now_brt = now.astimezone(BRT)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            now_brt=now_brt.strftime("%A, %d/%m/%Y às %H:%M")
        )

        history = await self._load_history(phone, db)
        contents = self._build_contents(history, text)

        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=[TOOL_DECLARATIONS],
                ),
            )
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "Desculpe, tive um problema técnico. Tente novamente em instantes."

        part = response.candidates[0].content.parts[0]

        if getattr(part, "function_call", None):
            fc = part.function_call
            result = await self._execute_tool(fc.name, dict(fc.args), phone, now, db)
            await self._save_turn(phone, text, result, db)
            return result

        reply = response.text.strip()
        await self._save_turn(phone, text, reply, db)
        return reply

    async def _load_history(self, phone: str, db: AsyncSession) -> list[ConversationMessage]:
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.user_phone == phone)
            .order_by(ConversationMessage.created_at.desc())
            .limit(HISTORY_LIMIT)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    def _build_contents(self, history: list[ConversationMessage], current_text: str) -> list:
        contents = [
            types.Content(role=msg.role, parts=[types.Part(text=msg.content)])
            for msg in history
        ]
        contents.append(types.Content(role="user", parts=[types.Part(text=current_text)]))
        return contents

    async def _execute_tool(self, name: str, args: dict, phone: str, now: datetime, db: AsyncSession) -> str:
        try:
            if name == "create_event":
                return await tool_funcs.create_event(
                    title=args["title"],
                    datetime_iso=args["datetime_iso"],
                    remind_at_iso=args.get("remind_at_iso"),
                    user_phone=phone,
                    now=now,
                    db=db,
                )
            elif name == "list_events":
                return await tool_funcs.list_events(user_phone=phone, db=db)
            elif name == "cancel_event":
                return await tool_funcs.cancel_event(
                    event_reference=args["event_reference"],
                    user_phone=phone,
                    db=db,
                )
            elif name == "edit_event":
                return await tool_funcs.edit_event(
                    event_reference=args["event_reference"],
                    field=args["field"],
                    new_value=args["new_value"],
                    user_phone=phone,
                    now=now,
                    db=db,
                )
            return "Não entendi o que fazer."
        except Exception as e:
            logger.error(f"Tool error [{name}]: {e}")
            return "Tive um problema ao executar essa ação. Tente novamente."

    async def _save_turn(self, phone: str, user_text: str, model_reply: str, db: AsyncSession) -> None:
        db.add(ConversationMessage(user_phone=phone, role="user", content=user_text))
        db.add(ConversationMessage(user_phone=phone, role="model", content=model_reply))
        await db.commit()
```

- [ ] **Step 4: Rodar para confirmar passa**

```bash
cd backend && python -m pytest tests/test_agent.py -v
```
Esperado: todos os 5 testes `PASSED`

- [ ] **Step 5: Commit**

```bash
git add services/agent.py tests/test_agent.py
git commit -m "feat: add CalendarAgent with Gemini tool calling and conversation history"
```

---

## Task 5: Refatorar webhook.py + deletar nlp.py

**Files:**
- Modify: `backend/routers/webhook.py`
- Delete: `backend/services/nlp.py`
- Delete: `backend/tests/test_nlp.py`

- [ ] **Step 1: Substituir o conteúdo de `backend/routers/webhook.py`**

```python
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
```

- [ ] **Step 2: Deletar nlp.py e test_nlp.py**

```bash
rm /c/Users/loren/Documents/projetos/calendario-whatsapp/backend/services/nlp.py
rm /c/Users/loren/Documents/projetos/calendario-whatsapp/backend/tests/test_nlp.py
```

- [ ] **Step 3: Rodar a suite completa para confirmar que nada quebrou**

```bash
cd backend && python -m pytest tests/ -v --ignore=tests/test_nlp.py
```
Esperado: todos os testes passando. Se algum falhar por import de `nlp`, buscar e remover a referência.

- [ ] **Step 4: Commit final**

```bash
git add routers/webhook.py
git rm services/nlp.py tests/test_nlp.py
git commit -m "refactor: replace nlp.py with CalendarAgent, simplify webhook to thin HTTP layer"
```

---

## Task 6: Push e verificação final

- [ ] **Step 1: Rodar a suite completa uma última vez**

```bash
cd backend && python -m pytest tests/ -v
```
Esperado: zero falhas.

- [ ] **Step 2: Push para o GitHub**

```bash
cd /c/Users/loren/Documents/projetos/calendario-whatsapp
git push origin master
```

- [ ] **Step 3: Verificar deploy no Render**

Acessar o dashboard do Render e confirmar que o deploy subiu sem erros de startup. A nova tabela `conversation_messages` é criada automaticamente pelo `Base.metadata.create_all` no lifespan do FastAPI.

- [ ] **Step 4: Teste manual via WhatsApp** (em sandbox)

Enviar cada tipo de mensagem e verificar:
- `"quais meus eventos?"` → lista eventos do número correto
- `"agendar reunião amanhã às 15h"` → cria evento, responde com confirmação
- `"cancela a reunião"` → cancela o evento certo
- `"muda o horário da reunião para 17h"` → edita corretamente
- `"tenho tempo na sexta?"` → resposta conversacional com contexto de agenda
