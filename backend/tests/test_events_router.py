import pytest
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
