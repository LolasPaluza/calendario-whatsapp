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
