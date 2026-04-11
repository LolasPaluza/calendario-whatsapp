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
