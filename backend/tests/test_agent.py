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

    from zoneinfo import ZoneInfo
    BRT = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(timezone.utc)
    future_iso = (now + timedelta(hours=3)).astimezone(BRT).strftime("%Y-%m-%dT%H:%M:%S%z")
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
    agent = CalendarAgent()

    # Pré-popular histórico
    db.add(ConversationMessage(user_phone="5511999", role="user", content="mensagem anterior"))
    db.add(ConversationMessage(user_phone="5511999", role="model", content="resposta anterior"))
    await db.commit()

    mock_response = _make_gemini_text_response("Resposta atual")

    with patch.object(agent.client.aio.models, "generate_content", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_response
        await agent.run(phone="5511999", text="nova mensagem", db=db)

    contents = mock_generate.call_args.kwargs["contents"]
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
