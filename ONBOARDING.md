# Trivus — Guia da Equipe: rodar local e testar

Sistema novo da Trivus em dois repositórios:

| Repo | O quê | Branch |
|---|---|---|
| [`trivusauto/trivus-api`](https://github.com/trivusauto/trivus-api) | Backend FastAPI + PostgreSQL | `main` |
| [`trivusauto/trivus`](https://github.com/trivusauto/trivus) | Frontend novo Next.js 16 | **`release/new-web`** ⚠️ (a `master` é o app antigo) |

## Pré-requisitos

- Acesso aos repositórios da org `trivusauto` no GitHub
- **Docker Desktop** rodando (é só o que precisa para o modo rápido)
- Para desenvolver com hot-reload (opcional): **Node 20+** e **uv** (Python 3.12) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

## 1. Clonar (lado a lado, nomes exatos)

O compose espera as pastas irmãs com estes nomes:

```bash
mkdir trivus && cd trivus
git clone https://github.com/trivusauto/trivus-api.git
git clone -b release/new-web https://github.com/trivusauto/trivus.git trivus-web
```

> ⚠️ O `trivus-web` no final do segundo clone é obrigatório — renomeia a pasta.

## 2. Subir tudo com Docker (modo rápido)

```bash
cd trivus-api/deploy
docker compose up -d --build          # primeiro build demora alguns minutos
docker compose exec api uv run python -m scripts.seed_demo   # popula dados de demonstração
```

| Serviço | URL |
|---|---|
| Front | http://localhost:3000 |
| API (docs em `/docs`) | http://localhost:3001 |
| PostgreSQL | `localhost:5433` · user/senha/db: `trivus`/`trivus`/`trivus` |

**Logins de teste:**

| Usuário | Senha | Perfil |
|---|---|---|
| `admin@trivus.local` | `admin123` | Admin Trivus (vê tudo, incl. telas de admin da holding) |
| `carlos@trivus.local` | `demo123` | Dono (client) — demonstra o estado "nenhuma loja vinculada" |
| Equipe das lojas (SDR, vendedor, gerente…) | `demo123` | Veja os e-mails em **Admin › Usuários** |

**O cenário de demonstração** (recriado a qualquer momento re-rodando o `seed_demo` — ele limpa e repopula):

- **AutoStar Matriz/Filial** — plano Full: tudo liberado, ~175 leads, campanhas, indicadores, metas
- **NovaMarca Veículos** — plano Essencial (só CRM): Marketing/Relatórios/Métricas aparecem **com cadeado + card de upsell** (comportamento esperado, não é bug!)
- **Zeta Motors** — assinatura **suspensa**
- Admin da holding: Empresas, Planos, Catálogo de Serviços, Assinaturas, Interesses (kanban)

Derrubar: `docker compose down` (mantém os dados) · `docker compose down -v` (zera o banco).

## 3. Desenvolver com hot-reload (opcional)

> ⚠️ Não rode junto com a stack completa do passo 2 — as portas 3000/3001/5433 conflitam. Antes: `cd trivus-api/deploy && docker compose down`.

**Backend** (em `trivus-api/`):
```bash
uv sync
cp .env.example .env
docker compose up -d db               # só o Postgres (compose da raiz do repo)
uv run alembic upgrade head
uv run python -m scripts.seed_admin   # cria o admin
uv run python -m scripts.seed_demo    # (opcional) dados de demonstração
uv run uvicorn src.main:app --reload --port 3001
```

**Frontend** (em `trivus-web/`):
```bash
npm install
cp .env.example .env.local            # BACKEND_URL=http://localhost:3001
npm run dev                           # http://localhost:3000
```

## 4. Testes e checks (os mesmos do CI)

**Backend** (com o banco de dev up e migrado, como no passo 3):
```bash
uv run ruff check .    # lint
uv run mypy src        # tipos (strict)
uv run pytest          # 154 testes (unit + integração + e2e)
```

**Frontend:**
```bash
npm run lint
npm run build
```

## 5. Referências

- **[`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)** — todos os endpoints, payloads e regras de negócio
- **[`deploy/README.md`](deploy/README.md)** — detalhes da orquestração Docker
- **[`docs/DEPLOY_COOLIFY.md`](docs/DEPLOY_COOLIFY.md)** — como funciona o deploy de produção

## Regras de ouro

1. **Nunca** aponte `DATABASE_URL` para o banco de produção — todo teste é no Postgres local/Docker.
2. O front novo vive na branch **`release/new-web`** — não mexam na `master` (app antigo, ainda em uso).
3. Achou bug? Anote a tela, o usuário logado e a loja selecionada (o comportamento muda por plano/assinatura — cadeado e tela suspensa fazem parte do produto).
