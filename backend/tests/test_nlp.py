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
