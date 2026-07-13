# Trivus API

[![CI](https://github.com/trivusauto/trivus-api/actions/workflows/ci.yml/badge.svg)](https://github.com/trivusauto/trivus-api/actions/workflows/ci.yml)

Backend da plataforma **Trivus** — gestão de performance para concessionárias e revendas de veículos, e hub do **ecossistema da holding** (consultoria, capacitação e agência de marketing). Substitui o acesso direto do frontend ao Supabase por uma API própria.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL 16 · JWT + argon2 · uv · pytest · ruff · mypy

**Arquitetura:** hexagonal/DDD por módulo (`domain → application → infrastructure → interface`). Regras de negócio são serviços de domínio puros, testados sem I/O; repositórios SQLAlchemy implementam os ports; routers FastAPI fazem só a costura.

---

## Módulos

| Módulo | O que faz |
|---|---|
| `auth` | Login JWT, senha argon2 (migra hash legado no 1º login), RBAC, escopo multi-loja |
| `stores` / `users` | Lojas, usuários portal, colaboradores (`shop_role`), vínculos multi-loja, rótulos de papéis |
| `crm` | Kanban de leads: funis, etapas, regras de campo por coluna, patches de agenda/comparecimento/fechamento, cooling, histórico, clone/sync de funil-template |
| `webhook` | Captação automática WhatsApp (Z-API): dedup por telefone/LID, round-robin de SDRs, auto-match de campanha |
| `agenda` | Agendamentos com filtros por tipo de data, presets de período e escopo por papel |
| `metrics` | Dashboard, relatórios por origem (com custos CPL…CAC), projeções Meta/Realizado/Projetando com sinaleiros, performance da equipe, modo indicadores |
| `marketing` | Campanhas, funil de custos do receptivo (CPL, CAC, ROAS, ROI), funil por campanha, bloqueio de avanço sem campanha |
| `legacy_leads` / `indicators` / `goals` / `action_plans` | Modo indicadores (lançamento diário com upsert), metas mensais, planos de ação |
| `bulk_send` | Disparos de WhatsApp em massa via n8n, com callback de status |
| `ecosystem` | Empresas, planos, assinaturas (manual + trial automático), catálogo de serviços → **feature keys** (gates por tela/card), upsell com fila comercial, eventos de cobrança do framework de pagamentos |

Documentação completa em [`docs/`](docs/): [engenharia reversa do domínio](docs/MIGRACAO_BACKEND.md) · [spec do ecossistema](docs/ECOSSISTEMA_TRIVUS.md) · [modelo de dados (23 tabelas)](docs/db/MODELO_ALVO.md) · [planos de implementação](docs/plans/00-INDEX.md) · [integração de cobrança](docs/BILLING_GATEWAY.md).

---

## Rodando localmente

Pré-requisitos: [uv](https://docs.astral.sh/uv/), Docker.

```bash
# 1. dependências
uv sync

# 2. banco (Postgres 16 na porta 5433)
docker compose up -d db

# 3. env
cp .env.example .env

# 4. migrations (23 tabelas) + admin inicial
uv run alembic upgrade head
uv run python -m scripts.seed_admin     # admin@trivus.local / admin123 — troque em produção!

# 5. sobe a API
uv run uvicorn src.main:app --reload --port 3001
```

- API: http://localhost:3001 · Swagger: http://localhost:3001/docs · Health: `GET /health`

### Testes e qualidade

```bash
uv run pytest          # unit + integração + e2e (precisa do banco de pé)
uv run ruff check .    # lint
uv run mypy src        # tipos (strict)
```

## Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `DATABASE_URL` | — | `postgresql+asyncpg://user:pass@host:5432/db` |
| `JWT_SECRET` | — | Segredo do JWT (gere com `openssl rand -hex 32`) |
| `JWT_EXPIRES_MINUTES` | `10080` | Validade do token (7 dias) |
| `N8N_BULK_SEND_WEBHOOK_URL` | vazio | Fluxo n8n dos disparos em massa (opcional) |
| `N8N_INTEREST_WEBHOOK_URL` | vazio | Notificação de interesse/upsell ao comercial (opcional) |
| `N8N_TOKEN` | `dev-n8n-token` | Token do callback de status do n8n (`x-n8n-token`) |
| `BILLING_GATEWAY_ENABLED` | `false` | Liga o endpoint de eventos de cobrança ([guia](docs/BILLING_GATEWAY.md)) |
| `BILLING_TOKEN` | `dev-billing-token` | Token do framework de pagamentos (`x-billing-token`) |

## Deploy (Coolify)

O deploy é **automático**: todo push na `main` roda o CI (lint + tipos + 154 testes) e, se verde, o job `deploy` dispara o webhook do Coolify, que rebuilda a aplicação pelo `Dockerfile` (as migrations rodam no boot do container).

### Configuração inicial no Coolify (uma vez)

1. **Nova aplicação** → fonte: este repositório GitHub → build pack **Dockerfile** → porta **3001** → healthcheck `GET /health`.
2. **Banco:** crie um PostgreSQL 16 no Coolify (ou aponte para um existente) e configure as envs da aplicação (tabela acima) — `DATABASE_URL` com o prefixo `postgresql+asyncpg://`.
3. **Desative o auto-deploy por push do próprio Coolify** (para o deploy só acontecer com CI verde): na aplicação, desligue "Auto Deploy".
4. **Webhook:** copie a *Deploy Webhook URL* da aplicação e crie um API token (Keys & Tokens → API tokens).
5. **No GitHub** → Settings → Secrets and variables → Actions, crie:
   - `COOLIFY_WEBHOOK_URL` — a URL do webhook de deploy
   - `COOLIFY_TOKEN` — o API token
6. **Primeiro boot:** rode o seed uma vez no terminal do container (`uv run python -m scripts.seed_admin`) e **troque a senha do admin** via `POST /auth/change-password`.

> Sem os secrets configurados, o job de deploy apenas avisa e não falha — o CI continua útil desde já.

## Convenções

- **TDD** — toda regra nasce com teste (domínio puro → use case com fakes → repositório com Postgres → e2e via httpx).
- **Conventional Commits** (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`).
- Migrations **sempre** via Alembic; o schema-alvo canônico vive em [`docs/db/MODELO_ALVO.md`](docs/db/MODELO_ALVO.md).
