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
async def test_webhook_dispatches_to_agent(app_client_no_auth):
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value="Evento criado: *Reunião*")
    with patch("routers.webhook._agent", mock_agent), \
         patch("routers.webhook.whatsapp.send_message", new_callable=AsyncMock):

        payload = {
            "entry": [{"changes": [{"value": {
                "messages": [{"id": "msg_001", "from": "5511999999999", "text": {"body": "reunião amanhã às 15h"}}]
            }}]}]
        }
        response = await app_client_no_auth.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_agent.run.assert_called_once()
        call_kwargs = mock_agent.run.call_args.kwargs
        assert call_kwargs["phone"] == "5511999999999"
        assert call_kwargs["text"] == "reunião amanhã às 15h"
        assert "db" in call_kwargs


@pytest.mark.asyncio
async def test_webhook_deduplicates_same_message_id(app_client_no_auth):
    """Same msg_id sent twice should only dispatch agent once."""
    mock_agent = AsyncMock()
    mock_agent.run = AsyncMock(return_value="ok")
    with patch("routers.webhook._agent", mock_agent), \
         patch("routers.webhook.whatsapp.send_message", new_callable=AsyncMock):

        payload = {
            "entry": [{"changes": [{"value": {
                "messages": [{"id": "dup_msg_002", "from": "5511999999999", "text": {"body": "oi"}}]
            }}]}]
        }

        await app_client_no_auth.post("/webhook", json=payload)
        await app_client_no_auth.post("/webhook", json=payload)

    assert mock_agent.run.call_count == 1
