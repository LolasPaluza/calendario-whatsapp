# Design: Sistema de Calendário via WhatsApp

**Data:** 2026-04-11  
**Objetivo:** Sistema pessoal de lembretes integrado ao WhatsApp, com dashboard web para visualização.

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + APScheduler + PostgreSQL |
| NLP | Claude API (Anthropic) |
| WhatsApp | Meta Business API (free tier) |
| Frontend | Next.js 14 (App Router) + Tailwind |
| Hospedagem backend | Render (gratuito) |
| Hospedagem frontend | Vercel (gratuito) |
| Keep-alive | UptimeRobot (gratuito) |

---

## Arquitetura

```
[Usuário no WhatsApp]
       ↓ mensagem
[Meta Business API]
       ↓ webhook POST
[FastAPI no Render]
       ↓ extrai intenção
[Claude API]  →  JSON estruturado { title, datetime, remind_at }
       ↓
[PostgreSQL]  →  salva evento
       ↓
[APScheduler] →  agenda lembrete
       ↓ no horário
[Meta Business API] →  manda lembrete via WhatsApp

[Next.js no Vercel] ←→ [FastAPI] ←→ [PostgreSQL]
```

---

## Modelo de Dados

```sql
CREATE TABLE events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    description TEXT,
    datetime    TIMESTAMPTZ NOT NULL,
    remind_at   TIMESTAMPTZ NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending', -- pending | sent | cancelled
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | /webhook | Recebe mensagens da Meta Business API |
| GET | /events | Lista todos os eventos |
| POST | /events | Cria evento manualmente |
| PUT | /events/{id} | Edita evento |
| DELETE | /events/{id} | Cancela evento |
| GET | /events/{id} | Detalhe de um evento |

Autenticação: API key simples via header `X-API-Key` (exceto `/webhook` que usa verificação da Meta).

---

## Fluxo de Mensagens WhatsApp

### Criar evento
- Input: *"reunião com cliente amanhã às 15h"*
- Claude extrai: `{ title, datetime, remind_at }` — se não mencionado, `remind_at` padrão = 30min antes
- Bot responde: *"Evento criado: reunião com cliente — 12/04 às 15h. Lembrete 30min antes."*

### Listar eventos
- Input: *"quais são meus compromissos esta semana?"*
- Bot responde com lista dos próximos eventos

### Cancelar evento
- Input: *"cancela a reunião de amanhã"*
- Claude identifica o evento → status = cancelled → APScheduler remove job

### Editar evento
- Input: *"muda o dentista para 11h"*
- Claude identifica o evento e o campo a alterar → atualiza banco + reescalona job

### Casos ambíguos
- Datas vagas (*"qualquer dia"*, *"quando der"*) → bot pede confirmação: *"Qual data exata você prefere?"*

---

## Dashboard Next.js

### Telas

**1. Calendário** (tela principal)
- Visualização mensal com eventos marcados
- Clica no evento para ver detalhes
- Botão para criar evento manualmente

**2. Lista de eventos**
- Eventos futuros em ordem cronológica
- Status: pendente / lembrete enviado / cancelado
- Ações: editar, cancelar

**3. Criar/editar evento** (modal)
- Campos: título, descrição, data, hora, antecipação do lembrete (15min, 30min, 1h, 1 dia)

---

## Tratamento de Erros

- Webhook com payload inválido → retorna 200 (evita reenvio da Meta) + loga erro
- Claude API falha → bot responde *"Não entendi, tente novamente."*
- APScheduler job perdido (restart do servidor) → ao iniciar, recarrega todos os eventos `pending` com `remind_at > now()` do banco
- Render reinicia → jobs são reativos do PostgreSQL na startup

---

## Fora do Escopo (por agora)

- Múltiplos usuários
- Recorrência de eventos (ex: "toda semana")
- Integração com Google Calendar
- Notificações por email
