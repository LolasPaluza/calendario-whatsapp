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
