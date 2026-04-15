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
