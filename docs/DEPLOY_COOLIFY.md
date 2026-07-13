# Deploy no Coolify — Guia passo a passo

> Como colocar a **Trivus API** em produção no Coolify, com deploy automático
> disparado pelo GitHub Actions **somente quando o CI está verde**.
>
> Fluxo final: `git push na main` → CI (lint + mypy + 154 testes) → ✅ → webhook → Coolify rebuilda pelo `Dockerfile`.

---

## Visão geral do que vamos montar

```
GitHub (push na main)
   └─► GitHub Actions (job test: ruff + mypy + pytest)
          └─► job deploy: chama o Deploy Webhook do Coolify
                 └─► Coolify: git pull + docker build (Dockerfile) + up
                        └─► container roda: alembic upgrade head → uvicorn :3001
                               └─► Postgres 16 (também no Coolify)
```

O container **roda as migrations sozinho no boot** (está no `CMD` do Dockerfile) — você nunca precisa migrar na mão.

---

## Passo 1 — Criar o banco PostgreSQL no Coolify

1. No Coolify: **+ New → Database → PostgreSQL** (versão **16**).
2. Defina um nome claro (ex.: `trivus-db`), usuário, senha forte e nome do banco (ex.: `trivus`).
3. Crie o banco **no mesmo projeto/ambiente** onde a API vai rodar (assim eles se enxergam pela rede interna do Coolify).
4. Depois de subir, anote o **endereço interno** do banco. O Coolify mostra algo como:
   ```
   postgres://USUARIO:SENHA@NOME-DO-SERVICO:5432/trivus
   ```
   > ⚠️ **Não exponha a porta do Postgres publicamente** — a API acessa pela rede interna.

5. **Monte a `DATABASE_URL` da API** trocando o prefixo para o driver async:
   ```
   postgresql+asyncpg://USUARIO:SENHA@NOME-DO-SERVICO:5432/trivus
   ```
   > O prefixo `postgresql+asyncpg://` é obrigatório — com `postgres://` puro a API não sobe.

---

## Passo 2 — Criar a aplicação

1. **+ New → Resource → (Public ou Private) Repository**.
   - Repo: `trivusauto/trivus-api` · Branch: `main`.
   - Se o repo for privado, conecte via **GitHub App** do Coolify (ele guia o fluxo).
2. **Build Pack:** `Dockerfile` (o Coolify detecta o `Dockerfile` na raiz).
3. **Port:** `3001` (é a porta exposta pelo container).
4. **Health check:** habilite e aponte para `GET /health` (porta 3001). A API responde `{"status":"ok"}`.
5. **Domínio:** defina o domínio desejado (ex.: `api.trivus.com.br`). O Coolify/Traefik emite o certificado HTTPS sozinho — só garanta que o DNS do domínio aponta para o servidor do Coolify.

### 2.1 — Desligar o Auto Deploy do Coolify (importante!)

Na aplicação → **Settings/General → desligue "Auto Deploy"**.

> Por quê: o Coolify, por padrão, deploya a cada push. Nós **não** queremos isso — queremos que o deploy só aconteça **depois do CI passar**. Quem dispara o deploy é o GitHub Actions via webhook (Passo 4).

---

## Passo 3 — Variáveis de ambiente da aplicação

Na aplicação → **Environment Variables**, cadastre:

| Variável | Valor | Obrigatória? |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://USUARIO:SENHA@trivus-db:5432/trivus` (do Passo 1) | ✅ |
| `JWT_SECRET` | gere com `openssl rand -hex 32` | ✅ |
| `ENV` | `production` | ✅ |
| `JWT_EXPIRES_MINUTES` | `10080` (7 dias — ajuste se quiser) | opcional |
| `N8N_BULK_SEND_WEBHOOK_URL` | URL do fluxo n8n de disparos em massa | opcional (vazio = não chama) |
| `N8N_INTEREST_WEBHOOK_URL` | URL do fluxo n8n que avisa o comercial sobre interesses/upsell | opcional (vazio = não chama) |
| `N8N_TOKEN` | gere com `openssl rand -hex 32` — o n8n manda esse valor no header `x-n8n-token` | ✅ se usar n8n |
| `BILLING_GATEWAY_ENABLED` | `false` (ligar só quando integrar o framework de pagamentos — ver [BILLING_GATEWAY.md](BILLING_GATEWAY.md)) | ✅ |
| `BILLING_TOKEN` | gere com `openssl rand -hex 32` — o framework de pagamentos manda no header `x-billing-token` | ✅ se ligar billing |

> 🔑 **Gere um segredo diferente para cada token** (`openssl rand -hex 32` três vezes). Nunca use os valores `dev-*` do `.env.example` em produção.

---

## Passo 4 — Webhook de deploy + token da API do Coolify

1. Na aplicação → aba **Webhooks** → copie a **Deploy Webhook URL** (algo como `https://SEU-COOLIFY/api/v1/deploy?uuid=...&force=false`).
2. No Coolify → **Keys & Tokens → API tokens → Create** (permissão de deploy basta). Copie o token — ele só aparece uma vez.

## Passo 5 — Secrets no GitHub

No repositório `trivusauto/trivus-api` → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor |
|---|---|
| `COOLIFY_WEBHOOK_URL` | a Deploy Webhook URL do Passo 4.1 |
| `COOLIFY_TOKEN` | o API token do Passo 4.2 |

> O job `deploy` do [ci.yml](../.github/workflows/ci.yml) usa esses dois secrets. **Sem eles, o job não falha** — só registra um aviso e pula (útil enquanto o Coolify não está pronto).

---

## Passo 6 — Primeiro deploy e inicialização

1. Dispare o primeiro deploy manualmente no Coolify (botão **Deploy**) — ou faça um push na `main` com os secrets já configurados.
2. Acompanhe os logs do build; no boot do container você deve ver as migrations do Alembic rodando e o uvicorn subindo na 3001.
3. **Seed do admin (uma única vez):** na aplicação → **Terminal** (shell do container):
   ```bash
   uv run python -m scripts.seed_admin
   ```
   Isso cria `admin@trivus.local` / `admin123`.
4. **Troque a senha do admin imediatamente:**
   ```bash
   # 1) login pra pegar o token
   curl -s -X POST https://SEU-DOMINIO/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"email":"admin@trivus.local","password":"admin123"}'

   # 2) troca a senha (use o access_token retornado acima)
   curl -s -X POST https://SEU-DOMINIO/auth/change-password \
     -H "Authorization: Bearer SEU_TOKEN" \
     -H 'Content-Type: application/json' \
     -d '{"current_password":"admin123","new_password":"UMA-SENHA-FORTE"}'
   ```

## Passo 7 — Verificação (checklist)

```bash
# saúde
curl -s https://SEU-DOMINIO/health
# → {"status":"ok"}

# login com a senha nova
curl -s -X POST https://SEU-DOMINIO/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@trivus.local","password":"SUA-SENHA"}'
# → {"access_token": "...", "user": {...}}

# billing deve estar DESLIGADO (409)
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://SEU-DOMINIO/integrations/billing/events \
  -H 'x-billing-token: qualquer' -d '{}'
# → 409
```

E o fluxo completo: faça um commit trivial na `main` → veja o **Actions** rodar `test` → `deploy` → o Coolify iniciar um novo build sozinho.

---

## Solução de problemas

| Sintoma | Causa provável | Correção |
|---|---|---|
| Container não sobe / erro de conexão no boot | `DATABASE_URL` sem o prefixo `postgresql+asyncpg://`, ou host errado | Use o **nome interno do serviço** do Postgres no Coolify e o prefixo async |
| `relation "users" does not exist` | migrations não rodaram | Veja o log do boot — o `CMD` roda `alembic upgrade head`; confira se a `DATABASE_URL` aponta pro banco certo |
| Login 401 com admin | seed não foi rodado nesse banco | Passo 6.3 |
| Job `deploy` "pulado" no Actions | secrets não configurados | Passo 5 |
| Webhook retorna 401 | `COOLIFY_TOKEN` errado/expirado | Gere outro token no Coolify e atualize o secret |
| Deploy acontece sem esperar o CI | "Auto Deploy" ligado no Coolify | Passo 2.1 |
| Site sem HTTPS | DNS não aponta pro servidor | Ajuste o A/AAAA do domínio e redeploy |

## Rollback

- **De versão:** no Coolify, a aplicação guarda os deploys anteriores — use **Redeploy** de um build antigo, ou reverta o commit na `main` (`git revert`) e deixe o fluxo normal rodar.
- **De banco:** cada migration tem `downgrade()`: `uv run alembic downgrade -1` no terminal do container (use com cuidado em produção; prefira backup antes: o Coolify tem backup agendado para bancos — **ative-o** no serviço do Postgres).

## Próximos passos relacionados

- **Migração dos dados reais do Supabase** → [Plano 11](plans/11-cleanup-cutover.md) (ETL ensaiado, feito junto com o time).
- **Ligar a cobrança via framework de pagamentos** → [BILLING_GATEWAY.md](BILLING_GATEWAY.md).
