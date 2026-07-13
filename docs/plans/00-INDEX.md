# Trivus Backend (FastAPI) — Índice dos Planos de Implementação

> **Leia este arquivo primeiro.** Define stack, arquitetura (hexagonal/DDD), padrões e a ordem dos planos. Cada plano numerado produz software funcionando e testável por conta própria.
>
> **Spec de domínio:** [`../MIGRACAO_BACKEND.md`](../MIGRACAO_BACKEND.md) (engenharia reversa completa do sistema atual: entidades, regras de negócio, endpoints, nuances). Quando um plano disser "ver §X da spec", é esse documento — ele continua sendo a fonte da verdade do **domínio**, independente da stack.

---

## Como usar estes planos (para a IA executora)

1. **Execute um plano por vez, na ordem numérica.** Não pule.
2. Dentro de um plano, **uma tarefa por vez** e **um passo (`- [ ]`) por vez**. Faça exatamente o que está escrito, rode o comando indicado e **confira a saída esperada**.
3. **TDD obrigatório:** escreva o teste que falha → rode e veja falhar → implemente o mínimo → rode e veja passar → commit. Nunca implemente antes do teste.
4. **Não invente.** Se um passo pedir um valor que você não tem (ex.: a connection string real do Supabase), **pare e peça ao humano**. Não use placeholder.
5. **Commits frequentes** com Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`).
6. Ao terminar um plano, marque-o como ✅ na tabela de roadmap e só então comece o próximo.

---

## Stack e convenções globais

| Item | Decisão |
|------|---------|
| Linguagem | **Python 3.12** |
| Framework | **FastAPI** |
| Validação / Schemas (interface) | **Pydantic v2** |
| ORM (infraestrutura) | **SQLAlchemy 2.0** (async) |
| Migrations | **Alembic** |
| Gerenciador de pacotes/venv | **uv** (já usado em `agente-whatsapp/`) |
| Banco | **PostgreSQL 16** — local via Docker Compose; prod = Railway/Supabase |
| Auth | **PyJWT** (JWT) + **argon2-cffi** (hash de senha) |
| Testes | **pytest** + **pytest-asyncio** + **httpx** (e2e) + **testcontainers** (integração de repositório) |
| Lint/format | **ruff** (lint + format) + **mypy** (tipagem estática) |
| Containers | Docker + Docker Compose |
| Deploy (prod) | **Railway** |
| CI | GitHub Actions (ruff + mypy + pytest) |

### Princípios de código

- **DDD + Hexagonal (Ports & Adapters).** O domínio não conhece framework nem banco.
- **SOLID** e **DRY**: dependências sempre apontam para abstrações (ports); lógica duplicada vira função/serviço de domínio compartilhado.
- **YAGNI**: não construa abstração que nenhum caso de uso exige hoje.
- **Tipagem estática** (mypy) em todo o código; sem `Any` solto.

### Arquitetura hexagonal/DDD — as 4 camadas

```
interface (FastAPI)  ─►  application (use cases)  ─►  domain (entidades + ports)
        │                        │                          ▲
        │                        ▼                          │
        └────────────►  infrastructure (adapters: SQLAlchemy, JWT, Z-API) ─┘ implementa os ports
```

**Regra de dependência (inviolável):** as setas de dependência apontam **para dentro**.
- `domain/` — entidades, value objects, serviços de domínio, **ports** (interfaces abstratas de repositório/serviço). **Python puro**, zero import de FastAPI/SQLAlchemy.
- `application/` — **use cases** (1 caso de uso = 1 classe com `execute()`), DTOs de comando/consulta. Depende só de `domain` (pelos ports).
- `infrastructure/` — **adapters**: modelos SQLAlchemy, repositórios concretos que implementam os ports, mappers ORM↔domínio, clientes externos (Z-API, n8n), segurança (JWT/argon2).
- `interface/` — routers FastAPI, schemas Pydantic (request/response), e a **composição de dependências** (DI via `Depends`).

### Estrutura de pastas (alvo)

```
trivus-backend/
├── src/
│   ├── main.py                     # cria o app FastAPI, inclui routers
│   ├── shared/
│   │   ├── domain/                 # Entity base, ValueObject, erros de domínio
│   │   ├── application/             # UseCase base, UnitOfWork (port)
│   │   ├── infrastructure/          # engine/session async, settings, security (jwt, argon2)
│   │   └── interface/               # deps comuns (get_session, get_current_user), exception handlers
│   └── modules/
│       └── <context>/               # ex.: auth, stores, crm, agenda, metrics, ...
│           ├── domain/
│           ├── application/
│           ├── infrastructure/
│           └── interface/
├── migrations/                      # Alembic
├── tests/
│   ├── unit/                        # domínio + use cases (com fakes)
│   ├── integration/                 # repositórios contra Postgres real (testcontainers)
│   └── e2e/                         # API via httpx
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── pyproject.toml
└── .github/workflows/ci.yml
```

### Padrão de módulo (vertical slice) — todo módulo segue isto

Para cada caso de uso: **(1)** entidade/serviço de domínio + port → **(2)** use case → **(3)** adapter de repositório → **(4)** router + schema Pydantic + wiring `Depends`. Cada camada com seu teste:
- **domínio**: unit puro (sem I/O).
- **use case**: unit com **repositório fake** (em memória) implementando o port.
- **repositório**: integração contra Postgres real (testcontainers).
- **endpoint**: e2e via httpx.

O Plano 03 (Auth) implementa esse padrão por inteiro e serve de **template** para os módulos 04–10.

### Definition of Done (cada tarefa)

- [ ] Teste escrito **antes** da implementação e passando.
- [ ] `ruff check` e `ruff format --check` sem erros; `mypy src` sem erros.
- [ ] `pytest` verde.
- [ ] Commit feito.

---

## Roadmap dos planos

| # | Plano | Escopo | Produz | Status |
|---|-------|--------|--------|--------|
| 01 | [Descoberta & Modelagem de Dados](./01-data-discovery-modeling.md) | Introspecção do banco real, ERD, **schema-alvo limpo**, quick-wins de índice, estratégia de migração | Spec do modelo de dados correto | ⬜ |
| 02 | [Fundação & Deploy](./02-foundation-and-deploy.md) | uv + FastAPI scaffold, hexagonal base, Postgres em compose, SQLAlchemy/Alembic (schema-alvo), health, CI, deploy | Backend rodando local e em prod | ✅ |
| 03 | [Auth & Sessão (template)](./03-auth.md) | JWT, argon2, use cases de login, guards, **vertical slice hexagonal completa** | Login real + o template de módulo | ✅ |
| 04 | [Usuários & Lojas](./04-users-and-stores.md) | users (admin), stores, user_store_access, role labels | Admin gerencia lojas/usuários | ✅ |
| 05 | [CRM (núcleo)](./05-crm.md) | funis, etapas, leads, regras de campo, patches, clone template, cooling, atividade | Kanban via API | ✅ |
| 05b | [CRM templates admin](./05b-crm-templates.md) | funis-template CRUD + sync para clientes | admin/crm | ✅ |
| 06 | [Webhook Z-API](./06-webhook-zapi.md) | inbound WhatsApp → cria lead (round-robin, dedup, lid; bug do ponteiro corrigido) | Captação automática | ✅ |
| 07 | [Agenda](./07-agenda.md) | leads agendados, filtros por período/tipo, escopo por papel | Agenda via API | ✅ |
| 08 | [Métricas](./08-metrics.md) | dashboard, relatórios, projeções, team; dias úteis corrigidos | Read models | ✅ |
| 08b | [Métricas avançadas](./08b-advanced-metrics.md) | qualificação, séries mensais, modo indicadores, global admin | Cobertura total do front | ✅ |
| 09 | [Legado & Metas & Planos](./09-legacy-goals-plans.md) | leads, daily_indicators (upsert), goals, action_plans | Modo indicadores + metas + planos | ✅ |
| 10 | [Disparos em massa](./10-bulk-send.md) | bulk_sends, bulk_send_contacts, integração n8n | Disparos via API | ⬜ |
| 10b | [Módulo Marketing](./10b-marketing.md) | campanhas, funil de custos (CPL/CAC/ROAS/ROI), classificados, investimento, sinaleiros, filtro por campanha, bloqueio por campanha | Marketing novo + relatórios com custos | ⬜ |
| 12 | [Ecossistema](./12-ecosystem.md) | empresas, planos, assinaturas (manual+trial), serviços com CRUD → feature keys, gates (`require_feature`), upsell + n8n, cobrança via framework (desligada) | Plataforma da holding | ⬜ |
| 11 | [Migração de dados, Limpeza & Cutover](./11-cleanup-cutover.md) | ETL ensaiado (inclui empresas/assinaturas) → virada única, frontend→API, remover legado, segredos | Produção endurecida | ⬜ |

> **Todos os planos estão escritos em detalhe** (baby-steps TDD, formato hexagonal do Plano 03). Ordem de execução: **01 → 02 → 03 → 04 → 05 → 05b → 06 → 07 → 08 → 08b → 09 → 10 → 10b → 12 → 11** (o 11 — cutover — é sempre o último). O status ⬜ é de **execução** — marque ✅ ao concluir. O modelo de dados aprovado está em [`../db/MODELO_ALVO.md`](../db/MODELO_ALVO.md) (**23 tabelas**). Specs: [`../MIGRACAO_BACKEND.md`](../MIGRACAO_BACKEND.md) (domínio), `MUDANCAS_MARKETING_RELATORIOS.md` (marketing), [`../ECOSSISTEMA_TRIVUS.md`](../ECOSSISTEMA_TRIVUS.md) (ecossistema).

### Mapa domínio → módulo (resumo; detalhe na spec §11)

`auth/` (login, JWT, escopo de loja) · `stores/` + `users/` · `crm/` (regras de coluna, métricas-fonte, template) · `webhook/` (Z-API) · `agenda/` · `metrics/` (read models) · `legacy/` (leads + indicadores) · `goals/` · `action_plans/` · `bulk_send/`.

---

*Índice gerado a partir de `MIGRACAO_BACKEND.md`. Mantenha a tabela de status atualizada.*
