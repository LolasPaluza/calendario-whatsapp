# Agent System Design — calendario-whatsapp

**Data:** 2026-04-14  
**Objetivo:** Refatorar o backend para um agent system próprio com tool calling nativo do Gemini, histórico de conversa por usuário e correção do bug de multi-usuário.

---

## Contexto

O projeto é uma agenda pessoal via WhatsApp com chatbot baseado em Gemini. O backend atual tem três problemas estruturais:

1. **Sem tool calling** — o LLM retorna JSON de intent, o Python faz o dispatch manualmente. Frágil e verboso.
2. **Sem memória** — cada mensagem é processada do zero. Não há histórico de conversa.
3. **Bug de multi-usuário** — `list_events` não filtra por `user_phone`. Todos os usuários veem os eventos de todo mundo.

---

## Decisões de design

| Decisão | Escolha | Motivo |
|---|---|---|
| LLM | Gemini 2.5 Flash | Já integrado, plano gratuito, tool calling nativo sólido |
| Memória | PostgreSQL | Render free tier reinicia — in-memory não sobrevive |
| Arquitetura | CalendarAgent class | Separação clara, testável, extensível |
| LLM calls para ações | Short-circuit (1 call) | Evita regressão de latência em create/edit/cancel |

---

## Arquitetura

```
WhatsApp → webhook.py (thin, ~30 linhas)
               ↓
          agent.run(phone, text, db)
               ↓
     [CalendarAgent — services/agent.py]
       1. carrega histórico (últimos 10 turnos, PostgreSQL)
       2. monta system prompt + tools + histórico
       3. Gemini call
          ├── function_call → executa tool → salva histórico → retorna ToolResult
          └── texto direto → salva histórico → retorna texto
               ↓
     whatsapp.send_message(phone, reply)
```

---

## Banco de dados

### Nova tabela: `conversation_messages`

```python
class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: UUID (PK, default uuid4)
    user_phone: str          # identifica o usuário
    role: str                # "user" | "model"
    content: str             # texto da mensagem
    created_at: datetime     # UTC
```

- Janela de contexto: últimos **10 turnos** por usuário enviados ao Gemini
- Mensagens mais antigas ficam no banco mas não vão ao LLM
- Migração automática via `Base.metadata.create_all` no startup

### Fix: `events` — filtro por usuário

Todos os métodos de `services/events.py` que listam eventos passam a incluir `Event.user_phone == user_phone` no WHERE. Nenhuma mudança de schema.

---

## Tool System — `services/tools.py`

Quatro funções puras. `user_phone` e `db` são injetados pelo agent — invisíveis ao Gemini.

### Declarações expostas ao Gemini

```
create_event(title: str, datetime_iso: str, remind_at_iso?: str)
list_events()
cancel_event(event_reference: str)
edit_event(event_reference: str, field: "datetime"|"title"|"remind_at", new_value: str)
```

### Comportamento

- **create_event** — cria no DB, agenda lembrete via scheduler, retorna confirmação formatada
- **list_events** — retorna string com até 10 eventos futuros do usuário
- **cancel_event** — fuzzy match por título (similaridade de string), cancela e remove lembrete
- **edit_event** — fuzzy match, atualiza campo, reeschedula lembrete se `datetime` ou `remind_at`

Todas retornam `str` (ToolResult). O agent usa esse texto como resposta final sem segundo LLM call.

---

## CalendarAgent — `services/agent.py`

```python
class CalendarAgent:
    async def run(self, phone: str, text: str, db: AsyncSession) -> str:
        history = await self._load_history(phone, db)      # últimos 10 turnos
        response = await self._call_llm(text, history)     # 1 LLM call

        if response.has_function_call:
            result = await self._execute_tool(response.function_call, phone, db)
            await self._save_turn(phone, text, result, db)
            return result                                  # short-circuit

        reply = response.text
        await self._save_turn(phone, text, reply, db)
        return reply
```

**System prompt (injetado em toda chamada):**
```
Você é um assistente de agenda pessoal via WhatsApp.
Data/hora atual: {now_brt} (horário de Brasília)
Responda sempre em português brasileiro, de forma curta e natural.
Para criar, listar, editar ou cancelar eventos — use as tools disponíveis.
```

---

## Webhook refatorado — `routers/webhook.py`

Remove toda lógica de negócio. Responsabilidade única: extrair phone + text do payload Meta, chamar o agent, enviar resposta.

```python
@router.post("/webhook")
async def receive_message(request: Request, db: AsyncSession = Depends(get_db)):
    phone, text = _extract(body)
    if not phone or not text:
        return {"status": "ok"}
    if msg_id in _processed_ids:
        return {"status": "ok"}

    agent = CalendarAgent()
    reply = await agent.run(phone, text, db)
    await whatsapp.send_message(phone, reply)
    return {"status": "ok"}
```

---

## Latência

| Intent | Antes | Depois |
|---|---|---|
| Criar / editar / cancelar | 1 LLM call | 1 LLM call |
| Listar | 1 LLM call | 1 LLM call |
| Query / chat | 2 LLM calls | 1–2 LLM calls |
| Overhead de histórico | — | ~50ms (DB read/write) |

Sem regressão. Queries ficam iguais ou mais rápidas.

---

## O que não muda

- Frontend (Next.js + Vercel) — zero alterações
- Deploy Render — mesma configuração
- Variáveis de ambiente — nenhuma nova
- Webhook Meta WhatsApp — mesmo endpoint
- Scheduler de lembretes (`scheduler.py`) — intocado
- `routers/events.py` — intocado
- `services/whatsapp.py` — intocado

---

## Arquivos afetados

| Arquivo | Ação |
|---|---|
| `backend/services/agent.py` | CRIAR |
| `backend/services/tools.py` | CRIAR |
| `backend/models.py` | MODIFICAR — adicionar ConversationMessage |
| `backend/routers/webhook.py` | SIMPLIFICAR |
| `backend/services/events.py` | CORRIGIR — filtro user_phone |
| `backend/services/nlp.py` | DELETAR |
