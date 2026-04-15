import httpx
from config import settings


async def send_message(to: str, text: str) -> None:
    """Send a WhatsApp text message via Twilio API."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={
                "From": settings.twilio_from_number,
                "To": f"whatsapp:{to}",
                "Body": text,
            },
            timeout=10.0,
        )
        response.raise_for_status()
