# Plano 11 — Migração de Dados, Limpeza & Cutover

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Leia o [`00-INDEX.md`](./00-INDEX.md) e conclua 01–10. **Este plano mexe em produção — confirme cada passo destrutivo com o humano antes.**

**Goal:** Migrar os dados reais do banco atual (Supabase) para o schema-alvo, apontar o frontend para a API, remover o legado e endurecer segredos — com uma **virada única, ensaiada** (não big-bang no escuro).

**Architecture:** Construímos incremental (Planos 02–10); a **virada de dados é um evento único coordenado**, ensaiado muitas vezes contra cópias. O banco velho fica intacto como rollback.

> Responde "como migro o que já existe e depois?": ensaia em cópia → vira numa janela curta → mantém o velho como backup → desliga o legado.

---

## Task 1: Script de ETL (old → schema-alvo)

**Files:** `scripts/etl/migrate.py`, `scripts/etl/validate.sql`

> ETL = lê do banco velho, transforma (de-para do `MODELO_ALVO.md`), grava no novo. **Idempotente** (pode rodar várias vezes).

- [ ] **Step 1: Esqueleto do ETL (ordem de dependência)**

`scripts/etl/migrate.py` — conecta nos dois bancos (envs `OLD_DATABASE_URL`, `NEW_DATABASE_URL`) e migra **na ordem das FKs**:
```python
import asyncio, os
import asyncpg

ORDER = ["stores", "users", "user_store_access", "crm_funnels", "crm_funnel_stages",
         "crm_funnel_leads", "crm_lead_stage_history", "crm_stage_cooling_rules",
         "crm_activity_log", "leads", "daily_indicators", "goals", "action_plans",
         "bulk_sends", "bulk_send_contacts"]


async def migrate_leads(old, new) -> None:
    rows = await old.fetch("SELECT * FROM crm_funnel_leads")
    for r in rows:
        await new.execute(
            """INSERT INTO crm_funnel_leads (id, store_id, stage_id, nome, telefone,
                 data_agendamento, receita, despesa, rentabilidade, created_at)
               VALUES ($1,$2,$3,$4,$5, NULLIF($6,'')::date, $7,$8,$9,$10)
               ON CONFLICT (id) DO NOTHING""",
            r["id"], r["client_id"], r["stage_id"], r["nome"], r["telefone"],
            r["data_agendamento"], r["receita"], r["despesa"], r["rentabilidade"], r["created_at"])


async def main() -> None:
    old = await asyncpg.connect(os.environ["OLD_DATABASE_URL"])
    new = await asyncpg.connect(os.environ["NEW_DATABASE_URL"])
    # ... uma função migrate_<tabela> por tabela, chamadas em ORDER ...
    await migrate_leads(old, new)
    await old.close(); await new.close()

if __name__ == "__main__":
    asyncio.run(main())
```
> Escreva uma função `migrate_<tabela>` para **cada** tabela em `ORDER`, aplicando o de-para do `MODELO_ALVO.md` (`client_id→store_id`, texto→`date`, separar `users`/`stores`, etc.). `ON CONFLICT (id) DO NOTHING` garante idempotência.

- [ ] **Step 1b: Ecossistema — empresas e assinaturas dos clientes atuais (spec `ECOSSISTEMA_TRIVUS.md` §8)**

Após migrar `stores`, acrescente ao ETL (idempotente):
1. **Seeds:** crie os serviços iniciais (software com as feature keys do registro + humanos `consultoria/capacitacao/agencia` com pitch) e o plano `consultoria_full` com **todas** as keys de serviço.
2. Para **cada cliente atual** da consultoria: crie 1 `company` (nome = nome fantasia do dono), preencha `stores.company_id` das lojas dele, crie 1 `subscription` `status='active'` / `billing_mode='manual'` no plano `consultoria_full`, e ligue **todos** os serviços de software em cada loja (`store_services.enabled=true`).
3. Valide: nenhuma loja com `company_id NULL` ao final (o modo legado E6 deixa de existir) e `GET /ecosystem/my-entitlements` de uma loja migrada retorna todas as keys.
> Resultado: **ninguém percebe a mudança** — os clientes atuais continuam com acesso total.

- [ ] **Step 2: Dados sujos (órfãos achados no Plano 01 Task 2)**

Para registros órfãos (ex.: lead cujo `client_id` não existe em `stores`), decida (conforme `ESTRATEGIA_MIGRACAO.md`): corrigir o `store_id`, descartar, ou inserir numa tabela `_quarantine`. Implemente no ETL.

- [ ] **Step 3: Queries de validação**

`scripts/etl/validate.sql` — contagens por tabela para comparar old vs new:
```sql
SELECT 'crm_funnel_leads' AS tabela, count(*) FROM crm_funnel_leads
UNION ALL SELECT 'stores', count(*) FROM stores
UNION ALL SELECT 'users', count(*) FROM users;
-- (uma linha por tabela)
```
Commit (`feat(etl): add data migration script and validation`).

---

## Task 2: Ensaiar contra uma cópia de produção (risco zero)

- [ ] **Step 1: Dump do Supabase de produção**

```bash
pg_dump "<SUPABASE_URL>" --no-owner --no-privileges -Fc -f prod-snapshot.dump
```

- [ ] **Step 2: Restaurar numa cópia "velha" local + subir um "novo" local limpo**

```bash
# cópia do banco velho:
createdb trivus_old && pg_restore --no-owner -d trivus_old prod-snapshot.dump
# banco novo limpo (schema-alvo) já existe via docker compose + alembic upgrade head
```

- [ ] **Step 3: Rodar o ETL e validar**

```bash
OLD_DATABASE_URL=postgresql://localhost/trivus_old NEW_DATABASE_URL=postgresql://trivus:trivus@localhost:5432/trivus uv run python -m scripts.etl.migrate
psql "$NEW_DATABASE_URL" -f scripts/etl/validate.sql
```
Expected: contagens batem com o velho (descontados os órfãos tratados). Achou divergência → conserta o ETL → **roda de novo** (é idempotente). Repita até zerar diferenças.

> No fim desta task, o ETL já rodou dezenas de vezes sem erro. A virada não é um salto no escuro.

---

## Task 3: A virada (cutover — janela curta)

> Confirme a janela com o humano. No volume pequeno→médio, o ETL roda em minutos.

- [ ] **Step 1: Manutenção (congela escritas no sistema atual)**

Coloque o app atual em manutenção (página de aviso ou pausa). Objetivo: ninguém criar dado no velho durante a cópia.

- [ ] **Step 2: ETL final (produção velha → produção nova)**

Aponte `OLD_DATABASE_URL` para o Supabase de produção e `NEW_DATABASE_URL` para o Postgres de produção do backend novo. Rode o ETL e o `validate.sql`. Confirme as contagens.

- [ ] **Step 3: Virar a chave**

Aponte o frontend para a API nova (Task 4) e tire da manutenção. Monitore os logs do backend e erros 4xx/5xx por algumas horas.

---

## Task 4: Migrar o frontend para a API (incremental)

> Esta parte **pode** ser incremental (Strangler Fig na UI). Mas a virada de dados (Task 3) é única.

- [ ] **Step 1: Camada de cliente HTTP no front**

No projeto `trivus/trivus`, crie um `apiClient` (fetch tipado) apontando para a URL do backend, injetando o JWT. Gere o **client tipado a partir do OpenAPI** do FastAPI (`openapi-typescript`) para ter os tipos de ponta a ponta.

- [ ] **Step 2: Trocar `supabase.from(...)` por chamadas à API, módulo a módulo**

Para cada tela, substitua o acesso direto ao Supabase pela rota equivalente (catálogo de endpoints na spec §7). Teste cada módulo no ar antes de seguir.

- [ ] **Step 3: Remover o SDK do Supabase**

Quando nenhuma tela usar mais `supabase.from(...)`:
```bash
# no front:
rg "from\('" app lib   # nada relevante deve sair
npm uninstall @supabase/supabase-js
```

---

## Task 5: Estabilizar, limpar e endurecer

- [ ] **Step 1: Manter o velho como backup (rollback)**

Deixe o Supabase de produção **em leitura** por alguns dias/semanas. Não apague na hora.

- [ ] **Step 2: Remover fallbacks legados**

Como o schema-alvo já não tem duplicação, confirme que não há código de fallback `users↔stores` remanescente. Rode toda a suíte (`uv run pytest`).

- [ ] **Step 3: Rotacionar segredos**

Rotacione a `anon key` e a `service_role key` do Supabase (estavam expostas — spec §9/§13). Troque a senha do admin master via `POST /auth/change-password`.

- [ ] **Step 4: Desativar o acesso direto e concluir**

Com confiança, desligue o acesso direto ao Supabase pelo browser (já removido no front) e aposente o schema velho. Atualize o status do Plano 11 para ✅ em [`00-INDEX.md`](./00-INDEX.md).

---

## Resultado final

- Dados reais migrados para o schema-alvo limpo, frontend falando só com a API, legado removido, segredos rotacionados, e o banco velho preservado como rede de segurança até a estabilização.
- A migração está completa, do banco mal modelado para um modelo correto e escalável — sem big-bang e sem deixar o sistema fora do ar.
