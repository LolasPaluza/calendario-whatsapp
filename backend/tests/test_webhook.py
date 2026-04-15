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
    with patch("routers.webhook.CalendarAgent") as MockAgent, \
         patch("routers.webhook.whatsapp.send_message", new_callable=AsyncMock):

        mock_instance = MockAgent.return_value
        mock_instance.run = AsyncMock(return_value="Evento criado: *Reunião*")

        payload = {
            "entry": [{"changes": [{"value": {
                "messages": [{"id": "msg_001", "from": "5511999999999", "text": {"body": "reunião amanhã às 15h"}}]
            }}]}]
        }
        response = await app_client_no_auth.post("/webhook", json=payload)

        assert response.status_code == 200
        mock_instance.run.assert_called_once()
        call_kwargs = mock_instance.run.call_args.kwargs
        assert call_kwargs["phone"] == "5511999999999"
        assert call_kwargs["text"] == "reunião amanhã às 15h"
        assert "db" in call_kwargs
