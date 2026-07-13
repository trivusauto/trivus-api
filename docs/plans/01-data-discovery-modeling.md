# Plano 01 — Descoberta & Modelagem de Dados

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans para executar passo a passo. Leia antes o [`00-INDEX.md`](./00-INDEX.md). Este plano produz **artefatos e uma spec de dados** (não código de aplicação) — é a fundação de tudo. **É estritamente READ-ONLY no banco atual:** só `SELECT` e `pg_dump --schema-only`, nunca escreve. Quando aparecer `<SUPABASE_URL>`, **peça ao humano** — e use uma connection string de **usuário read-only** (uma role só com `SELECT`, incapaz de escrever).

**Goal:** Recuperar a verdade do banco atual (que foi modelado errado e não tem todos os relacionamentos declarados), desenhar o **schema-alvo limpo** (FKs, índices, sem duplicação legada) a partir do domínio já documentado, e definir a **estratégia de migração incremental por contexto**. **O banco de produção NÃO é modificado** — nenhuma escrita, nenhum índice, nada.

**Architecture:** Abordagem híbrida (ver `00-INDEX` / orientação): modelo limpo desenhado agora, dados migrados incrementalmente; o repositório hexagonal (planos seguintes) absorve a diferença old↔new. Índices só no banco novo (Plano 02).

**Entregáveis:** `docs/db/schema-atual.sql`, `docs/db/erd-atual.md`, `docs/db/MODELO_ALVO.md` (a spec do schema-alvo), `docs/db/ESTRATEGIA_MIGRACAO.md`.

> ## ⚠️ DECISÃO DO DONO: introspecção do banco PULADA
>
> **Sem acesso ao banco de produção até o Plano 11.** As Tasks 1, 2 e 4 deste plano
> (que conectam no Supabase) estão **PULADAS**. O modelo de dados foi recuperado **do
> código** (spec §4/§11) e **já está aprovado** em [`../db/MODELO_ALVO.md`](../db/MODELO_ALVO.md)
> — é a fonte da verdade. Construa em cima dele "na fé".
>
> **O que fica de fato:** o `MODELO_ALVO.md` (Task 3, já pronto) e a estratégia de
> migração (Task 5). **Vá direto para o Plano 02.**
>
> **Único risco de pular a conferência:** se o banco real tiver alguma peça que o código
> não revelou (ex.: a definição exata de um índice único de telefone/lid, ou uma política
> `ON DELETE`), isso é detectado e ajustado **no Plano 11**, quando o ETL finalmente
> conecta no banco. É um risco pequeno e recuperável.

---

## Task 1: Introspectar o schema real do Supabase

**Files:**
- Create: `docs/db/schema-atual.sql`, `docs/db/constraints-atual.txt`

> Pré-requisito: ter `postgresql-client` (psql, pg_dump) instalado. Se faltar, peça ao humano (`brew install libpq` no macOS).

- [ ] **Step 1: Obter a connection string READ-ONLY (humano)**

Peça ao humano a connection string de um **usuário read-only** do Supabase (formato `postgresql://trivus_readonly:<senha>@db.<ref>.supabase.co:5432/postgres`). Essa role só tem `SELECT` — qualquer escrita é negada pelo banco. **Não commite** esse valor (vai só no ambiente). Se o usuário read-only ainda não existir, o humano cria antes com: `CREATE ROLE trivus_readonly LOGIN PASSWORD '...'; GRANT USAGE ON SCHEMA public TO trivus_readonly; GRANT SELECT ON ALL TABLES IN SCHEMA public TO trivus_readonly;`.

- [ ] **Step 2: Dump do schema (sem dados)**

```bash
mkdir -p docs/db
pg_dump "<SUPABASE_URL>" --schema-only --no-owner --no-privileges -n public -f docs/db/schema-atual.sql
```
Expected: arquivo com o `CREATE TABLE` real de todas as tabelas.

- [ ] **Step 3: Extrair as constraints e FKs REAIS que existem**

```bash
psql "<SUPABASE_URL>" -c "
SELECT tc.table_name, tc.constraint_type, kcu.column_name,
       ccu.table_name AS foreign_table, ccu.column_name AS foreign_column
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
LEFT JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
WHERE tc.table_schema='public'
ORDER BY tc.table_name, tc.constraint_type;
" > docs/db/constraints-atual.txt
```
Expected: lista de PKs, UNIQUEs e (poucas) FKs declaradas. **Anote quais relacionamentos NÃO têm FK** — são os que vamos enforçar no schema-alvo.

- [ ] **Step 4: Commit dos artefatos**

```bash
git add docs/db/schema-atual.sql docs/db/constraints-atual.txt
git commit -m "docs(db): capture real supabase schema and constraints"
```

---

## Task 2: ERD do estado atual + profiling de relacionamentos

**Files:**
- Create: `docs/db/erd-atual.md`

> Confirma os relacionamentos **implícitos** (convenção `client_id`, `stage_id`, etc.) checando se os dados batem.

- [ ] **Step 1: Gerar o ERD textual a partir do schema**

Liste cada tabela e suas colunas a partir de `schema-atual.sql` e escreva em `docs/db/erd-atual.md` um diagrama (pode ser Mermaid `erDiagram`) com os relacionamentos **conhecidos pela spec §4** (mesmo os não declarados como FK). Marque cada relacionamento como `[FK declarada]` ou `[convenção — sem FK]`.

- [ ] **Step 2: Profiling — validar que os relacionamentos implícitos fecham**

Rode (ajuste nomes conforme o schema real) e registre o resultado no ERD:
```bash
psql "<SUPABASE_URL>" -c "
-- client_id de crm_funnel_leads existe em stores?
SELECT count(*) AS leads_sem_store
FROM crm_funnel_leads l LEFT JOIN stores s ON s.id = l.client_id WHERE s.id IS NULL;
-- ...ou em users (legado)?
SELECT count(*) AS leads_sem_store_mas_em_users
FROM crm_funnel_leads l
LEFT JOIN stores s ON s.id = l.client_id
LEFT JOIN users u ON u.id = l.client_id
WHERE s.id IS NULL AND u.id IS NOT NULL;
-- stage_id existe em crm_funnel_stages?
SELECT count(*) AS leads_stage_orfao
FROM crm_funnel_leads l LEFT JOIN crm_funnel_stages st ON st.id = l.stage_id WHERE st.id IS NULL;
"
```
Expected: idealmente os "órfãos" são 0. Onde houver órfão, **documente** — é dado sujo a tratar no ETL (Task 5 / Plano 11).

- [ ] **Step 3: Commit**

```bash
git add docs/db/erd-atual.md
git commit -m "docs(db): document current ERD and relationship profiling"
```

---

## Task 3: Desenhar o schema-alvo limpo (a spec do modelo)

**Files:**
- Create: `docs/db/MODELO_ALVO.md`

> A partir do domínio (spec §4) + do que a introspecção revelou, desenhamos o banco **correto**. Esta é a referência que o Plano 02 transforma em migration Alembic.

- [ ] **Step 1: Escrever o MODELO_ALVO.md — princípios**

Documente as decisões de modelagem (corrigem o "modelado errado"):
1. **FKs declaradas e enforçadas** em todos os relacionamentos (hoje são convenção). Ex.: `crm_funnel_leads.client_id → stores.id ON DELETE CASCADE/RESTRICT` (decida por tabela).
2. **Fim da duplicação legada:** `stores` é a única fonte dos dados de loja; `users` guarda **só** credenciais/perfil de acesso (remover colunas `nome_fantasia`, `cnpj`, `webhook_token`, etc. de `users` — migram para `stores`).
3. **`client_id` → renomear para `store_id`** no schema-alvo (clareza: sempre referencia `stores.id`). O mapeamento old→new fica documentado para o ETL.
4. **Tipos corretos:** datas como `date`/`timestamptz` (não texto), dinheiro como `numeric(14,2)`, enums como `text` + `CHECK` (ou tipos enum nativos) com os valores da spec §5.
5. **Índices** para as queries pesadas (ver Task 4).
6. **`updated_at`** com trigger ou via aplicação, consistente.

- [ ] **Step 2: Escrever o DDL-alvo de cada tabela**

Para cada uma das 15 entidades (spec §4), escreva o `CREATE TABLE` alvo em `MODELO_ALVO.md`, já com PK `uuid default gen_random_uuid()`, FKs, `NOT NULL` onde aplicável, `CHECK` para enums, e `@@unique` preservados (ex.: `daily_indicators (store_id, reference_date, origin)`). Inclua um bloco "De-para old→new" por tabela (coluna antiga → coluna nova; ex.: `client_id → store_id`).

- [ ] **Step 3: Listar as confirmações pendentes**

Liste explicitamente o que a introspecção **não** resolveu e precisa de decisão (ex.: política `ON DELETE` de cada FK, se algum índice único de `crm_funnel_leads` por telefone/lid existe — spec §10). Marque cada item como "decidir com o humano".

- [ ] **Step 4: Commit**

```bash
git add docs/db/MODELO_ALVO.md
git commit -m "docs(db): design clean target schema (DDD model)"
```

---

## Task 4: Índices — só no banco NOVO (o banco atual NÃO é tocado)

> **Decisão do dono:** **não mexer no banco de produção atual.** A criação de índices
> quick-win foi **removida** — este plano é **estritamente read-only** sobre o Supabase
> (só `SELECT` / `pg_dump --schema-only`, feito idealmente com um **usuário read-only**).
>
> Os índices corretos são criados **do zero no banco novo** pela migration inicial do
> Plano 02 (a partir do `MODELO_ALVO.md`), num Postgres vazio — sem risco e sem tocar na produção.
>
> **Nada a fazer nesta task.** Siga para a Task 5.

---

## Task 5: Estratégia de migração incremental por contexto

**Files:**
- Create: `docs/db/ESTRATEGIA_MIGRACAO.md`

> Como os dados vão do schema atual (sujo) para o schema-alvo (limpo), **um bounded context por vez**, sem big-bang.

- [ ] **Step 1: Escrever a estratégia**

Documente em `ESTRATEGIA_MIGRACAO.md`:
1. **Construção incremental, virada de dados única:** os módulos são construídos e testados um a um (Planos 02–10) contra o schema-alvo, mas a **migração dos dados reais é um evento único coordenado e ensaiado** (Plano 11) — não big-bang no escuro, e não cutover ao vivo por contexto (as tabelas-núcleo `stores`/`users` são compartilhadas, o que tornaria a sincronização ao vivo complexa).
2. **Ordem do ETL (dependência das FKs):** `stores` → `users` → `user_store_access` → `crm_funnels` → `crm_funnel_stages` → `crm_funnel_leads` → `crm_lead_stage_history`/`crm_stage_cooling_rules`/`crm_activity_log` → `leads`/`daily_indicators`/`goals`/`action_plans` → `bulk_sends` → `bulk_send_contacts`.
3. **Ensaio:** o ETL roda muitas vezes contra uma **cópia** do banco de produção (dump/restore) com validação de contagens, antes da virada real. Detalhe operacional no Plano 11.
4. **Dados sujos:** o que fazer com os órfãos achados na Task 2 (corrigir o `store_id`, descartar, ou parquear numa tabela `_quarantine`).
5. **Rollback:** manter o banco antigo (Supabase) intacto e em leitura até a estabilização em prod.

- [ ] **Step 2: Commit + concluir plano**

```bash
git add docs/db/ESTRATEGIA_MIGRACAO.md
git commit -m "docs(db): define incremental per-context migration strategy"
```
Atualize o status do Plano 01 para ✅ em [`00-INDEX.md`](./00-INDEX.md) e commit.

---

## Resultado deste plano

- A verdade do banco atual recuperada (schema + constraints + relacionamentos confirmados por profiling), **sem nenhuma escrita no banco de produção** (só leitura) — o "não sei meus relacionamentos" deixou de existir.
- O **schema-alvo limpo** desenhado (FKs, tipos certos, sem duplicação, índices) como spec para o Plano 02 implementar em Alembic. Os índices são criados no **banco novo**, não no atual.
- A **estratégia de migração incremental** definida — cada módulo dos próximos planos migra seus dados sozinho, sem big-bang.

**Próximo:** [`02-foundation-and-deploy.md`](./02-foundation-and-deploy.md) — scaffold FastAPI hexagonal + Alembic criando o schema-alvo + deploy.
