# Trivus — Documento de Migração para Backend Dedicado

> **Propósito:** engenharia reversa completa do sistema atual (entidades, regras de negócio, endpoints, integrações, nuances) + plano de migração passo a passo. Serve como especificação para reescrever o backend numa arquitetura organizada (NestJS + TypeScript) sem perder nenhuma regra.
>
> **Base de análise:** todo o código de `app/`, `lib/`, `contexts/` e `app/api/` + a [Documentação Técnica](./DOCUMENTACAO_TECNICA.md).
> **Data:** 2026-06-29.

---

## Sumário

1. [Resumo executivo e princípio central](#1-resumo-executivo-e-princípio-central)
2. [Estado atual (como funciona hoje)](#2-estado-atual-como-funciona-hoje)
3. [Arquitetura-alvo do novo backend](#3-arquitetura-alvo-do-novo-backend)
4. [Modelo de dados completo (entidades)](#4-modelo-de-dados-completo-entidades)
5. [Enums e valores fixos](#5-enums-e-valores-fixos)
6. [Catálogo de regras de negócio](#6-catálogo-de-regras-de-negócio)
7. [Catálogo de endpoints (API REST nova)](#7-catálogo-de-endpoints-api-rest-nova)
8. [Integrações externas](#8-integrações-externas)
9. [Segurança — o que corrigir na migração](#9-segurança--o-que-corrigir-na-migração)
10. [Nuances e armadilhas (gotchas)](#10-nuances-e-armadilhas-gotchas)
11. [Mapa de tradução: `lib/` atual → módulos do backend](#11-mapa-de-tradução-lib-atual--módulos-do-backend)
12. [Plano de migração passo a passo (faseado)](#12-plano-de-migração-passo-a-passo-faseado)
13. [Checklist de dados e ambiente](#13-checklist-de-dados-e-ambiente)

---

## 1. Resumo executivo e princípio central

O Trivus é um sistema de **gestão de performance comercial para lojas de veículos**. Hoje é um **Next.js 14 (App Router)** em JavaScript, que fala **direto com o Supabase (PostgreSQL)** a partir do browser usando a `anon key`. As regras de negócio vivem em `lib/` no cliente; só existem **3 rotas de servidor** (login, vínculo loja-usuário, webhook Z-API).

**Princípio central da migração:** o que cria a dor de "migrar tudo de novo" não é o banco Supabase — é o **acesso direto ao banco a partir do browser**. A solução é introduzir uma **camada de API (backend)** entre o front e o banco. Com isso:

- O frontend nunca sabe onde o banco mora → passa a falar só com a API.
- Trocar de host do Postgres depois (Supabase → Neon/Railway/VPS) vira **trocar connection string + dump/restore**, não um rewrite.
- Módulos novos nascem **desacoplados** do Supabase.
- Os buracos de segurança (auth fraca, RLS desligado, lógica exposta) se resolvem **por construção**.

> **Importante:** Supabase **já é PostgreSQL**. Não há "migrar para Postgres" — você já está nele. A recomendação é começar conectando o novo backend ao **próprio Postgres do Supabase** (os dados já estão lá, zero migração no dia 1) e trocar o host quando quiser.

---

## 2. Estado atual (como funciona hoje)

### 2.1 Stack

| Camada | Hoje |
|--------|------|
| Frontend | Next.js 14 (App Router), React 18, **JavaScript puro** |
| Estilo | Tailwind CSS 3 |
| Banco/Backend | Supabase (PostgreSQL gerenciado), SDK `@supabase/supabase-js` 2.39 |
| Auth | **Customizada** (tabela `users`, hash próprio, sessão em `localStorage`) — **não usa Supabase Auth** |
| Deploy | Vercel |
| Integrações | Z-API (WhatsApp→CRM), n8n (disparos em massa) |
| Projeto paralelo | `agente-whatsapp/` (Python) — fica fora desta migração, fala HTTP |

### 2.2 Padrão de acesso a dados (o problema)

- **~178 chamadas diretas ao banco a partir do browser** (`from('...')`): 132 em `app/`, 46 em `lib/`.
- Tabelas mais acessadas: `users` (24), `goals` (14), `daily_indicators` (14), `crm_funnel_stages` (13), `crm_funnel_leads` (13), `leads` (11), `stores` (10), `crm_funnels` (10), `action_plans` (10), `bulk_sends` (6).
- Sessão do usuário em `localStorage` (`trivus_user`), loja selecionada em `localStorage` (`trivus_selected_store`).
- Proteção de rota **só no client** (`DashboardLayout` + `canAccessPath`).

### 2.3 Dois modos operacionais por loja

- **Modo indicadores** (`crm_enabled = false`): tabela `leads` + lançamento manual em `daily_indicators`.
- **Modo CRM** (`crm_enabled = true`): Kanban com funis/etapas, leads em `crm_funnel_leads`, agenda, webhook Z-API. Quando o CRM está ligado, `/indicators` fica oculto e as métricas são **calculadas a partir do CRM**.

### 2.4 Hierarquia de acesso

```
Admin Trivus (role=admin)
        │  gerencia
        ▼
Usuário portal da loja (role=client, parent_client_id = NULL)
        │  user_store_access (N:N)
        ▼
Lojas (stores)
        │  parent_client_id = stores.id
        ▼
Colaboradores (role=shop_user, shop_role ∈ {sdr, vendedor, administrativo, gerente})
```

---

## 3. Arquitetura-alvo do novo backend

### 3.1 Visão

```
Browser (Next.js + TypeScript)
        │  HTTP + JWT (Authorization: Bearer)
        ▼
  API NestJS + TypeScript
   ├── AuthModule         (login, JWT, refresh, hash argon2)
   ├── UsersModule        (admin + colaboradores)
   ├── StoresModule       (lojas + user_store_access)
   ├── CrmModule          (funis, etapas, leads, histórico, cooling, atividade)
   ├── LeadsLegacyModule  (leads sem CRM)
   ├── IndicatorsModule   (daily_indicators)
   ├── GoalsModule        (metas)
   ├── ActionPlansModule  (planos de ação)
   ├── MetricsModule      (dashboard/marketing/relatórios/projeções)
   ├── BulkSendModule     (disparos em massa)
   └── WebhookModule      (Z-API inbound)
        │  Prisma (ORM)
        ▼
  PostgreSQL  (Supabase hoje → host próprio depois, sem mexer no resto)
        ▲
        │ HTTP
  Z-API · n8n · agente-whatsapp (Python)
```

### 3.2 Princípios de organização

- **Modular por domínio** (um módulo NestJS por área de negócio acima).
- **Camadas dentro de cada módulo:** `controller` (HTTP/validação DTO) → `service` (regra de negócio) → `repository`/Prisma (dados). Nenhuma regra de negócio no controller.
- **DTOs validados** com `class-validator` (substituem as validações soltas de hoje).
- **As funções puras de `lib/` migram quase 1:1 para `services`** — elas já estão testáveis e sem dependência de UI (ver [§11](#11-mapa-de-tradução-lib-atual--módulos-do-backend)). Esse é o maior ativo da migração: a regra de negócio já está isolada.
- **Guards** para auth/role (`@Roles('admin')`, `StoreScopeGuard`) substituem `canAccessPath` no client.
- **TypeScript de ponta a ponta:** tipos compartilhados front↔back (ex.: pacote `@trivus/types` ou OpenAPI gerando o client).

---

## 4. Modelo de dados completo (entidades)

> Convenção crítica: em quase todas as tabelas de negócio, **`client_id` referencia `stores.id`** (mesmo UUID preservado na migração de jun/2026). Há **fallbacks legados** que tratam `users.id` (role=client) como loja quando `stores` ainda não tem o registro.

### 4.1 `users` — credenciais e perfil de acesso

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | uuid PK | |
| `email` | text | login (único na prática) |
| `password_hash` | text | **hoje:** `hashed_<senha>` (placeholder inseguro) |
| `name` | text | nome exibido |
| `role` | text | `admin` \| `client` \| `shop_user` |
| `parent_client_id` | uuid FK→stores.id | só `shop_user`; NULL para `client`/`admin` |
| `shop_role` | text | `sdr` \| `vendedor` \| `administrativo` \| `gerente` (só shop_user) |
| `menu_permissions` | jsonb | array de rotas permitidas ao colaborador (ex.: `["/dashboard","/crm"]`) |
| `can_see_unassigned_leads` | boolean | colaborador vê leads CRM sem responsável; **entra na fila round-robin de SDR** |
| `active` | boolean | bloqueia login se false |
| `last_assigned_sdr_id` | uuid | **legado** (round-robin) — hoje preferir `stores.last_assigned_sdr_id`, mas o webhook ainda escreve aqui (ver §10.4) |
| `utiliza_ia` | boolean | flag opcional |
| `created_at` | timestamptz | |
| **Legado** (migrados p/ `stores`): `nome_fantasia`, `razao_social`, `cnpj`, `nome_responsavel`, `cep`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado`, `crm_enabled`, `zapi_webhook_enabled`, `webhook_token`, `shop_role_labels` | vários | usados só em fallback durante transição |

### 4.2 `stores` — dados da loja/empresa

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | uuid PK | mesmo ID do client legado |
| `nome_fantasia` | text NOT NULL | |
| `razao_social` | text | |
| `cnpj` | text | |
| `nome_responsavel` | text | |
| `cep`, `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado` | text | endereço |
| `crm_enabled` | boolean | habilita módulo CRM |
| `zapi_webhook_enabled` | boolean | aceita leads via WhatsApp |
| `webhook_token` | text UNIQUE | token na URL do webhook Z-API |
| `shop_role_labels` | jsonb | rótulos custom dos 4 papéis |
| `last_assigned_sdr_id` | uuid FK→users | ponteiro round-robin |
| `active` | boolean | |
| `created_at`, `updated_at` | timestamptz | |

**RLS:** desabilitado hoje. No novo backend isso deixa de importar (o browser não acessa o banco).

### 4.3 `user_store_access` — vínculo N:N usuário↔loja

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | uuid PK | |
| `user_id` | uuid FK→users | |
| `store_id` | uuid FK→stores | |
| `is_owner` | boolean | dono original da loja |
| `created_at` | timestamptz | |
| UNIQUE | `(user_id, store_id)` | |

### 4.4 `leads` — modo legado (sem CRM)

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `client_id` | uuid | |
| `name`, `phone`, `car`, `city` | text | dados do lead |
| `origin` | text | `receptivo` \| `prospeccao` \| `outros` |
| `origin_custom` | text | texto livre quando `origin = outros` |
| `entry_date` | date | |
| `qualified`, `disqualified` | boolean | |
| `disqualification_reason` | text | |
| `scheduled`, `attended`, `converted` | boolean | flags de funil |
| `profitability` | numeric | rentabilidade na conversão |
| `created_at`, `updated_at` | timestamptz | |

### 4.5 `daily_indicators` — indicadores diários (modo sem CRM)

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `client_id` | uuid | |
| `reference_date` | date | dia de referência |
| `origin` | text | `receptivo` \| `prospeccao` \| `outros` |
| `origin_custom` | text | |
| `total_leads`, `qualified_leads` | int | `qualified` só para receptivo |
| `scheduled_leads`, `attended_leads`, `converted_leads` | int | |
| `profitability` | numeric | rentabilidade bruta |
| `daily_expenses` | numeric | despesas do dia |
| `notes` | text | |
| UNIQUE | `(client_id, reference_date, origin)` | viola com erro Postgres `23505` |

### 4.6 `goals` — metas mensais por loja e origem

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `client_id` | uuid | |
| `month`, `year` | int | |
| `origin` | text | `receptivo` \| `prospeccao` \| `outros` |
| `leads_quantity`, `qualified_quantity` | int | |
| `scheduled_quantity`, `attended_quantity`, `conversions_quantity` | int | |
| `profitability_goal`, `average_ticket_goal` | numeric | |

### 4.7 `action_plans` — planos de ação Trivus→loja

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `client_id` | uuid | |
| `title`, `description` | text | |
| `status` | text | `a_fazer` \| `em_andamento` \| `concluido` |
| `created_at`, `updated_at` | timestamptz | |

### 4.8 Tabelas CRM

#### `crm_funnels`
| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | uuid PK | |
| `client_id` | uuid | **NULL = funil template** (admin) |
| `name` | text | |
| `sort_order` | int | |
| `is_template` | boolean | funil modelo Trivus |
| `template_source_id` | uuid FK→crm_funnels | funil de origem quando clonado para a loja |
| `created_at` | timestamptz | |

#### `crm_funnel_stages`
| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `funnel_id` | uuid | |
| `name` | text | coluna (RECEBIDOS, AGENDADOS...) |
| `sort_order` | int | |
| `template_stage_id` | uuid | vínculo com a etapa do template (p/ sync) |

#### `crm_funnel_leads` — lead no Kanban (entidade mais rica)
| Grupo | Colunas |
|-------|---------|
| Identificação | `id`, `stage_id`, `client_id`, `sort_order`, `assigned_to` (uuid→users), `created_at`, `updated_at` |
| Captação | `funil` (`receptivo` \| `prospeccao_ativa` \| `outros`), `qualificado` (bool), `origem_mkt`, `urgencia_venda` |
| Contato | `nome`, `telefone`, `lid` (ID anônimo WhatsApp), `bairro`, `cidade` |
| Veículo | `modelo`, `veiculo`, `ano`, `cor`, `combustivel`, `quilometragem`, `transmissao`, `valor_tabela_fipe`, `tem_financiamento` (bool), `saldo_quitacao`, `valor_pretendido`, `valor_compra` |
| Agenda | `data_agendamento`, `hora_agendamento`, `agendado_por`, `data_marcacao_agendamento`, `compareceu_agendamento` (bool), `data_compareceu`, `vendedor_id` (uuid→users) |
| Fechamento | `fechou_negocio` (bool), `data_fechou_negocio`, `receita`, `despesa`, `rentabilidade` |
| Outros | `observacoes` |

> **Atenção:** existe **índice único** relacionado a telefone/lid por cliente (o webhook trata `23505` como duplicata — ver §10.4). Confirmar a definição exata no banco e replicar.

#### `crm_stage_cooling_rules` — alerta visual de lead parado
| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `stage_id` | uuid | |
| `hours_threshold` | int | horas sem movimento |
| `card_color` | text | hex (default `#facc15`) |
| `message` | text | default `'Lead esfriando'` |
| `sort_order` | int | |

#### `crm_lead_stage_history` — histórico de entrada em colunas
| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `lead_id`, `stage_id` | uuid | |
| `entered_at` | timestamptz | usado para cooling e para saber se passou por QUALIFICADOS |

#### `crm_activity_log` — auditoria CRM
| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `client_id` | uuid | |
| `actor_user_id` | uuid | quem executou |
| `action` | text | ver enum `CRM_ACTION` (§5) |
| `entity_type`, `entity_id` | text/uuid | |
| `payload` | jsonb | |

### 4.9 Disparos em massa

#### `bulk_sends`
| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `title` | | |
| `total_contacts`, `success_count`, `error_count` | int | |
| `status` | text | `draft` \| `running` \| `paused` \| `completed` |
| `message_template`, `variation_1`…`variation_5` | text | |
| `delay_min_sec`, `delay_max_sec` | int | mínimo 30 |
| `started_at`, `completed_at`, `created_at` | timestamptz | |

#### `bulk_send_contacts`
| Coluna | Tipo | Notas |
|--------|------|-------|
| `id`, `bulk_send_id` | uuid | |
| `phone` | text | normalizado (13 díg. `55DDD9xxxxxxxx`) |
| `variation_index` | int | 0–4 |
| `status` | text | `pending` \| `sent` \| `error` |
| `scheduled_at`, `sent_at`, `error_message` | | |
| UNIQUE | `(bulk_send_id, phone)` | |

#### `bulk_send_contacts_ordered` (VIEW)
Ordena contatos `pending → sent → error`. No novo backend pode virar um simples `ORDER BY CASE status`.

---

## 5. Enums e valores fixos

| Enum | Valores | Onde |
|------|---------|------|
| `users.role` | `admin`, `client`, `shop_user` | global |
| `users.shop_role` | `sdr`, `vendedor`, `administrativo`, `gerente` | `shopRoleLabels.js` |
| origem (leads/indicators/goals) | `receptivo`, `prospeccao`, `outros` | |
| `crm_funnel_leads.funil` | `receptivo`, `prospeccao_ativa`, `outros` | **diferente** da origem: `prospeccao_ativa` normaliza para `prospeccao` em métricas (`normalizeFunilKey`) |
| `action_plans.status` | `a_fazer`, `em_andamento`, `concluido` | |
| `bulk_sends.status` | `draft`, `running`, `paused`, `completed` | |
| `bulk_send_contacts.status` | `pending`, `sent`, `error` | |
| Colunas do funil-template (nome normalizado) | `RECEBIDOS`, `CLASSIFICADOS`, `QUALIFICADOS`, `AGENDADOS`, `EM ATENDIMENTO`, `VEICULOS COMPRADOS`, `VEICULOS VENDIDOS` | `crmStageFieldRules.js` |
| `CRM_ACTION` (auditoria) | `lead_moved`, `lead_created`, `lead_updated`, `lead_deleted`, `funnel_created`, `funnel_renamed`, `funnel_deleted`, `stage_created`, `stage_deleted`, `stage_reordered`, `lead_reordered` | `crmActivity.js` |
| Origem MKT por funil (`origem_mkt`) | receptivo: facebook, instagram, landing_page, whatsapp, outro · prospeccao_ativa: icarros, marketplace, olx, webmotors, outro · outros: fluxo_loja, indicacao, midias_off | `crmOrigemOptions.js` |
| Rótulos de papel default | sdr→SDR, vendedor→Vendedor, administrativo→Administrativo, gerente→Gerente (customizáveis por loja, máx 80 chars) | `shopRoleLabels.js` |

---

## 6. Catálogo de regras de negócio

> Esta é a parte mais importante para não perder nuance. Cada regra abaixo deve virar um método de service com teste.

### 6.1 Autenticação e sessão (`lib/auth.js`, `authCredentials.js`, `userSession.js`)

- **Login:** busca `users` por email → se não existe, "Usuário ou senha inválidos" → se `active = false`, "Acesso bloqueado..." → `verifyPassword`. Em sucesso, remove `password_hash`, carrega lojas vinculadas (`loadUserStoresForSession`) e devolve user enriquecido.
- **`verifyPassword(pwd, hash)` atual:** `hash === 'hashed_'+pwd || hash === pwd`. **⚠️ Substituir por argon2/bcrypt na migração** (ver §9).
- **Mensagem de conectividade:** erros de rede/DNS (`Failed to fetch`, `ENOTFOUND` etc.) devem retornar mensagem específica de conectividade, **não** "senha inválida" (`isConnectivityError`). Manter essa distinção na nova API/cliente.
- **`loadUserStoresForSession`:**
  - `admin` → `[]` (não tem loja).
  - `shop_user` com `parent_client_id` → busca a `store` desse id (fallback: registro legado em `users`).
  - `client` → lojas via `user_store_access` (join `stores`); fallback legado: a própria `users.id` como loja.
- **`enrichUserSession`:** filtra lojas `active !== false`, define `crm_enabled = alguma loja tem crm_enabled`, anexa `stores` ao user.
- **Criar colaborador (`createShopTeamUser`):** insere `role='shop_user'`, `parent_client_id`, `menu_permissions`, `shop_role`, `can_see_unassigned_leads`, `active=true`.
- **`updateUser`:** se vier `password`, gera `password_hash` e remove `password` do payload.

### 6.2 Escopo multi-loja (`lib/storeScope.js`)

- **`getAccessibleStores(user)`:** shop_user → só a loja pai; client → `user.stores` ativas; fallback client legado → a própria `user.id`.
- **`getStoreScopeIds(user, selectedStoreId='all')`:** se `all` → todas as lojas acessíveis; senão → a loja selecionada (se acessível) ou a primeira.
- **`applyClientIdScope(query, storeIds)`:** 0 lojas → filtra por UUID zero (`00000000-...`) = **nada** (segurança: nunca vaza tudo); 1 loja → `eq client_id`; várias → `in client_id`. **Replicar essa proteção no backend** (toda query de negócio é escopada por loja).
- **`resolveStoreClientId`:** id efetivo da loja no contexto atual.
- **`resolveCrmEnabledForScope`:** CRM do escopo (loja selecionada ou "alguma loja tem CRM").

### 6.3 Permissões e acesso a rotas (`lib/storeUser.js`)

`canAccessPath(user, pathname)` — replicar como **guard/policy** no backend (por recurso, não por rota de UI):
- `admin` → tudo.
- `/change-password` → sempre liberado.
- CRM ligado + path de indicators → bloqueado para client e shop_user.
- `client` (dono): tudo, **exceto** áreas CRM (`/crm`, `/agenda`) se `crm_enabled=false`.
- `shop_user`: bloqueado em `/usuarios` e `/leads` sempre; áreas CRM bloqueadas se sem CRM; demais conforme `menu_permissions` (que nunca inclui `/leads`).
- **`STORE_MENU_PERMISSION_OPTIONS`** define o que pode ser concedido: dashboard, crm (requiresCrm), agenda (requiresCrm), marketing, reports, projections, indicators (excludedWhenCrm), action-plans.
- `firstAllowedPathForShopUser`: primeira rota permitida, com fallback `/change-password`.

### 6.4 CRM — regras de campos por coluna (`lib/crmStageFieldRules.js`)

Tabela `STAGE_FIELD_RULES` (campos **obrigatórios** por coluna):

| Coluna | Obrigatórios | Opcionais |
|--------|--------------|-----------|
| RECEBIDOS | `funil`, `telefone` | — |
| CLASSIFICADOS | `nome`, `cidade` | `bairro` |
| QUALIFICADOS | `modelo`, `ano` | cor, combustivel, quilometragem, transmissao, valor_tabela_fipe, tem_financiamento, saldo_quitacao, valor_pretendido |
| AGENDADOS | `data_agendamento`, `hora_agendamento` | — |
| EM ATENDIMENTO | `compareceu_agendamento`, `vendedor_id` | — |
| VEICULOS COMPRADOS | `valor_compra` | — |
| VEICULOS VENDIDOS | `receita`, `despesa`, `rentabilidade` | — |

Regras de preenchimento (`isFieldFilled`):
- **Campos monetários** (`valor_tabela_fipe`, `saldo_quitacao`, `valor_pretendido`, `valor_compra`, `receita`, `despesa`, `rentabilidade`): número finito **ou** string contendo dígito.
- **Booleanos de select** (`tem_financiamento`, `compareceu_agendamento`): precisa ser `true` ou `false` (não null).
- **`telefone`**: ao menos 1 dígito. **`funil`/`hora_agendamento`**: string não vazia.
- **Normalização de nome de coluna** (`normalizeStageName`): sem acentos, maiúsculas, trim (por isso "VEÍCULOS" vira "VEICULOS").
- **Caso especial EM ATENDIMENTO:** se `compareceu_agendamento !== true` → falta "Compareceu?"; se compareceu mas sem vendedor → falta "Vendedor". `compareceu = não` mantém o lead em AGENDADOS.
- **`computeAutoStageIndex`:** índice da coluna mais avançada cujos obrigatórios (e dos estágios anteriores) estão completos — usado para reposicionar o lead automaticamente.
- **`canAdvanceToStage` / `getMissingFieldsForAdvance`:** valida campos de `fromIndex` até `toIndex` inclusive antes de mover (drag-and-drop).

### 6.5 CRM — métricas (`lib/crmLeadMetrics.js`)

**Qual data conta para cada métrica** (núcleo das métricas — replicar exatamente):

| Métrica | Condição | Data de referência |
|---------|----------|--------------------|
| Total de leads | sempre | `created_at` (convertido p/ YMD local) |
| Qualificados | passou pela coluna QUALIFICADOS | conta na data de `created_at` |
| Agendamentos | tem `data_agendamento` **e** `hora_agendamento` | `data_marcacao_agendamento` (fallback: `data_agendamento`) — via `scheduleMarkedYmd` |
| Comparecimentos | `compareceu_agendamento === true` | `data_compareceu` |
| Conversões | `fechou_negocio === true` | `data_fechou_negocio` |
| Receita | idem conversão | soma de `rentabilidade` (numérico finito) |

- **`leadPassedQualificadosStage`:** usa `crm_lead_stage_history` (passou por um stage QUALIFICADOS) **ou**, fallback, a coluna atual estar em QUALIFICADOS ou posterior. O contexto (`fetchCrmQualificationContext`) resolve os `stage_id` que são QUALIFICADOS e os "iguais ou posteriores" por funil-template clonado.
- **`normalizeFunilKey`:** `''/'receptivo'`→`receptivo`; `prospeccao_ativa`→`prospeccao`; resto→`outros`.
- **Datas sempre em YMD local** (`todayLocalYmd`, `toLocalYmdFromIso`) — **não** UTC. Crítico para não contar evento no dia errado (ver §10.1).
- **Períodos** (`resolveCalendarPeriodRange`): `today`, `month`, `previous_month`, `custom`.
- **Paginação:** `fetchAllCrmLeadsForClient` lê em páginas de 1000. No backend, preferir agregação em SQL onde possível, mas a lógica de "qual data conta" precisa ser idêntica.
- **Agregações expostas:** totais globais, por origem, série mensal (12m dashboard / 6m marketing), pizza de agendamentos por origem, comparação com metas (`buildCrmReportProcessedData`: avgTicket = receita/conversões).

### 6.6 CRM — performance por colaborador (`lib/crmTeamMetrics.js`)

Atribuição por membro no período:
- **Leads:** `created_at` no período → atribui a `assigned_to`.
- **Agendamentos:** marcação no período → `vendedor_id` **ou** `agendado_por`.
- **Comparecimentos:** `data_compareceu` no período → `vendedor_id`.
- **Conversões/Receita:** `data_fechou_negocio` no período → `vendedor_id`.
- Sem responsável → bucket `__unassigned__` (só aparece se tiver algum número).
- **`conversionRate`** = converted/attended×100 (fallback converted/scheduled×100); **`avgTicket`** = revenue/converted.
- Equipe = colaboradores ativos (`parent_client_id = loja`) + dono.

### 6.7 Agenda (`lib/agendaUtils.js`)

- **Aplicação de período por tipo** (`periodApplyTo`): `agendamento` (filtra `data_agendamento` e `hora_agendamento` não nulos), `comparecimento` (`compareceu_agendamento=true` + `data_compareceu`), `fechamento` (`fechou_negocio=true` + `data_fechou_negocio`). Cada um usa seu `dateField` no range.
- **Presets:** from_today, today, yesterday, previous_month, month, custom (inverte se from>to).
- **Permissões de visão (`canSeeAgendaLead`):** gestor (dono **ou** `shop_role=gerente`) vê tudo; demais veem onde são `vendedor_id` ou `assigned_to`, ou (com `can_see_unassigned_leads`) leads sem responsável. `buildAgendaOwnerFilterOr` monta o `.or()` equivalente para a query.
- **Edição de vendedor** só por gestor (`canEditAgendaVendedor`).
- **Busca** (`buildAgendaSearchOrFilter`): por nome/modelo/veiculo/telefone com escape de `% _ \`.

### 6.8 CRM — patches de mutação (`lib/crmLeadPatch.js`)

Regras de transição de estado (replicar exatamente — controlam datas derivadas):
- **`buildAgendamentoPatch`:** ao completar agendamento (data+hora) pela 1ª vez, grava `agendado_por = userId` e `data_marcacao_agendamento = hoje`; ao limpar, zera ambos.
- **`buildCompareceuPatch`:** marcar compareceu pela 1ª vez grava `data_compareceu = hoje`; desmarcar zera.
- **`buildFechouNegocioPatch`:** grava `data_fechou_negocio = hoje` (se ainda não fechado), `rentabilidade`, e `receita/despesa` só se houver dígitos.
- **`buildDesfazerNegocioPatch`:** zera fechamento.
- **Rentabilidade** (`rentabilidadeMaskFromReceitaDespesa`): `venda − valor_compra − despesa`.

### 6.9 CRM — funil-template: clone e sincronização (`lib/crmTemplateFunnel.js`)

- **`cloneTemplateFunnel`:** ao habilitar CRM numa loja, copia funil template → cria `crm_funnels` (client, `template_source_id`), copia stages (com `template_stage_id`) e copia cooling rules de cada stage.
- **`syncClientFunnelFromTemplate` / `syncTemplateFunnelToClients`:** propaga mudanças do template para os clones — renomeia, cria stages novos, faz backfill de `template_stage_id`, **move leads de stages órfãos** para o stage de fallback antes de deletar o órfão, e recopia cooling rules.
- Operação transacional e idempotente — **forte candidato a virar transação no Prisma** (hoje são vários updates sequenciais sem transação).

### 6.10 Cooling rules (`lib/crmCoolingRules.js`)

- `getActiveCoolingRule(horas, rules)`: regra de **maior** `hours_threshold` já atingido.
- `hoursInColumn(enteredAt)`: horas desde a entrada na coluna (do `crm_lead_stage_history`).
- `saveCoolingRules`: delete + insert em batch (defaults cor `#facc15`, msg `Lead esfriando`).

### 6.11 Round-robin de SDR (`lib/webhookUtils.js`)

- **Elegíveis:** SDRs ativos com `can_see_unassigned_leads = true`.
- **`pickNextSdrId(sdrIds, lastAssignedSdrId)`:** próximo na fila circular após o último atribuído.
- Ponteiro persistido em `last_assigned_sdr_id` (ver §10.4 sobre a inconsistência stores vs users).

### 6.12 Telefones (`lib/bulkSendUtils.js`, `lib/zapiLeadUtils.js`)

- **`normalizeBrazilianPhone`:** valida celular BR (DDD + 9 + 8 díg.), normaliza para 13 dígitos `55DDD9xxxxxxxx`; rejeita inválidos.
- **`parsePhonesFromPaste` / `parsePhonesFromCSV`:** extrai telefones de texto colado ou CSV (detecta coluna por palavra-chave ou por densidade de dígitos), deduplica, conta inválidos/duplicados.
- **`extractLeadIdentity` (Z-API):** separa **telefone real** de **LID** (ID anônimo do WhatsApp, `@lid` — não é telefone). Remove DDI 55, `@c.us`.
- **`phoneMatchVariants`:** gera variantes com/sem o **9º dígito** para casar duplicatas (WhatsApp ora manda com, ora sem).

### 6.13 Cálculos auxiliares (`lib/utils.js`)

- **Máscaras:** telefone, moeda (`maskCurrency`/`unformatCurrency` — base 100/centavos), CNPJ, CEP.
- **Dias úteis:** `holidays` 2024–2027 hardcoded; `isWorkingDay` (exclui domingo + feriados; **sábado conta como útil**); `getWorkingDaysInMonth`, `getElapsedWorkingDays`, `getRemainingWorkingDays` — base das **projeções** (ritmo vs. meta). **Atualizar tabela de feriados** ou calcular (Páscoa/Carnaval/Corpus Christi são móveis).
- **`netProfitabilityFromIndicator`:** `profitability − daily_expenses` (rentabilidade líquida no modo indicadores).

---

## 7. Catálogo de endpoints (API REST nova)

> Proposta de endpoints que substituem o acesso direto ao banco. Todos sob `/api/v1`, autenticados via JWT (exceto login e webhook), **escopados por loja** via guard. Convenção REST; ajuste à vontade.

### 7.1 Auth
| Método | Rota | Descrição | Regras |
|--------|------|-----------|--------|
| POST | `/auth/login` | login | §6.1; retorna `{ accessToken, refreshToken, user }` (sem hash) |
| POST | `/auth/refresh` | renova token | novo |
| POST | `/auth/logout` | revoga refresh | novo |
| GET | `/auth/me` | sessão atual + lojas | substitui hidratação do `localStorage` |
| POST | `/auth/change-password` | troca senha do próprio usuário | substitui `/change-password` (hoje update direto) |

### 7.2 Usuários (admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/users` | lista usuários portal + acesso multi-loja |
| POST | `/admin/users` | cria usuário `client` |
| PATCH | `/admin/users/:id` | edita (ativar/desativar, dados) |
| PUT | `/admin/users/:id/stores` | vincula lojas (substitui `/api/admin/user-store-access`; §6.1) |

### 7.3 Colaboradores da loja (portal — só dono)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/stores/:storeId/team` | lista colaboradores |
| POST | `/stores/:storeId/team` | cria colaborador (`shop_user`) |
| PATCH | `/stores/:storeId/team/:userId` | edita papel, permissões, `can_see_unassigned_leads` |
| DELETE/`PATCH active` | `/stores/:storeId/team/:userId` | inativa |
| GET/PUT | `/stores/:storeId/role-labels` | rótulos de papéis (`shop_role_labels`) |

### 7.4 Lojas (admin)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/stores` | lista lojas |
| POST | `/admin/stores` | cria loja |
| PATCH | `/admin/stores/:id` | edita; togglar `crm_enabled` dispara clone do template (§6.9) |
| GET | `/admin/stores/:id/webhook` | retorna URL Z-API (`{APP_URL}/api/v1/webhook/zapi/{token}`) |

### 7.5 CRM
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/crm/funnels` | funis da loja (com stages) |
| POST/PATCH/DELETE | `/crm/funnels[/:id]` | CRUD funil |
| POST/PATCH/DELETE | `/crm/stages[/:id]` | CRUD etapa (+ reorder) |
| PUT | `/crm/stages/:id/cooling-rules` | salva cooling rules (§6.10) |
| GET | `/crm/leads` | leads (filtros: stage, responsável, busca) — **escopo por papel** (§6.7) |
| POST | `/crm/leads` | cria lead manual (campo `funil` só p/ quem pode — `canSeeLeadFunilField`) |
| PATCH | `/crm/leads/:id` | edita campos |
| PATCH | `/crm/leads/:id/stage` | move de coluna — valida `canAdvanceToStage` (§6.4), grava histórico, loga atividade |
| PATCH | `/crm/leads/:id/agendamento` | aplica `buildAgendamentoPatch` (§6.8) |
| PATCH | `/crm/leads/:id/comparecimento` | `buildCompareceuPatch` |
| PATCH | `/crm/leads/:id/fechamento` | `buildFechouNegocioPatch` / desfazer |
| DELETE | `/crm/leads/:id` | remove (loga atividade) |
| GET | `/crm/activity` | log de auditoria (filtros) |
| **Admin** GET/POST/PATCH | `/admin/crm/templates` | funis-template; salvar dispara `syncTemplateFunnelToClients` |

### 7.6 Agenda
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/agenda` | leads agendados; filtros de período por tipo (§6.7), paginação 25/50/100, escopo por papel |

### 7.7 Leads legado (sem CRM)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET/POST/PATCH/DELETE | `/leads[/:id]` | CRUD; qualificar/desqualificar; marcar scheduled/attended/converted + `profitability` |

### 7.8 Indicadores
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/indicators` | por período/origem |
| POST/PUT | `/indicators` | upsert por `(client_id, reference_date, origin)` — tratar conflito `23505` como update (§10.3) |

### 7.9 Metas
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/goals` | metas por loja/mês/ano/origem |
| POST/PUT/DELETE | `/admin/goals[/:id]` | CRUD (admin) |

### 7.10 Planos de ação
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/action-plans` | lista da loja |
| PATCH | `/action-plans/:id/status` | loja atualiza status |
| POST/PATCH/DELETE | `/admin/action-plans[/:id]` | CRUD (admin) |

### 7.11 Métricas/relatórios (read models)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/metrics/dashboard` | cards + séries (CRM ou indicadores conforme modo) |
| GET | `/metrics/marketing` | por origem/funil + metas |
| GET | `/metrics/reports` | relatório processado (§6.5) |
| GET | `/metrics/projections` | ritmo vs. meta (dias úteis, §6.13) |
| GET | `/metrics/team` | performance por colaborador (§6.6) |
| GET | `/admin/metrics/*` | versões globais (todas as lojas) |

### 7.12 Disparos em massa
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/admin/bulk-sends` | lista |
| POST | `/admin/bulk-sends` | cria `bulk_sends` + `bulk_send_contacts` (telefones validados/dedup) → dispara n8n |
| GET | `/admin/bulk-sends/:id` | detalhe |
| GET | `/admin/bulk-sends/:id/logs` | contatos (ordem pending→sent→error) |
| PATCH | `/admin/bulk-sends/:id` | pausar/retomar |

### 7.13 Webhook (público, sem JWT)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/webhook/zapi/:token` | inbound WhatsApp → cria lead (§8.1) |

---

## 8. Integrações externas

### 8.1 Z-API (WhatsApp → CRM) — fluxo do webhook (`app/api/webhook/zapi/[token]/route.js`)

Replicar passo a passo (com idempotência):
1. Identifica a loja por `webhook_token` (stores; fallback `users` legado). Se não achar → 401.
2. Se loja `!active || !zapi_webhook_enabled || !crm_enabled` → `{ ok:true, skipped:'disabled' }`.
3. Ignora `isGroup`, `fromMe`, `isNewsletter`.
4. `extractLeadIdentity`: telefone real + LID. Sem nenhum → `skipped:'no_phone'`.
5. **Duplicata:** procura lead do mesmo cliente por `lid`, por `telefone == lid`, ou por variantes do 9º dígito. Se existe → enriquece (grava `lid`/troca telefone) e retorna `skipped:'duplicate'`. **Usa `.limit(1)`, não `.maybeSingle()`** (ver §10.4).
6. Acha o funil clonado do template (`template_source_id IS NOT NULL`, menor `sort_order`).
7. Primeira coluna (menor `sort_order`).
8. **Round-robin** entre SDRs elegíveis; atualiza `last_assigned_sdr_id`.
9. `sort_order` do novo lead = contagem atual da etapa (vai pro fim).
10. Insere lead (`funil:'receptivo'`, `nome = chatName/senderName/telefone/lid`). Em `23505` (corrida) → trata como duplicata.
11. Registra `crm_lead_stage_history`.

### 8.2 n8n (disparos em massa)

- Frontend cria `bulk_sends` + `bulk_send_contacts`, depois `POST` para `NEXT_PUBLIC_N8N_BULK_SEND_WEBHOOK_URL`.
- n8n itera contatos, envia via WhatsApp, atualiza status no banco. Detalhe do payload em [`bulk-send-webhook-payload.md`](./bulk-send-webhook-payload.md).
- No novo backend, o disparo ao n8n passa a sair do **servidor** (não do browser), e o n8n pode atualizar status via endpoint autenticado em vez de escrever direto no banco.

---

## 9. Segurança — o que corrigir na migração

| Item | Hoje | Alvo |
|------|------|------|
| Hash de senha | `hashed_<senha>` (texto) | **argon2id** (ou bcrypt). Migrar hashes: re-hash no próximo login bem-sucedido. |
| Sessão | `localStorage` (XSS) | **JWT** (access curto + refresh httpOnly cookie) |
| Autorização | `canAccessPath` no client | **Guards no servidor** por recurso + escopo de loja obrigatório |
| Acesso ao banco | anon key no browser, RLS parcial | Só o backend acessa; service role/connection string **nunca** no front |
| Rota admin sem auth | `/api/admin/user-store-access` aceita qualquer um | Guard `@Roles('admin')` |
| Segredos no README/`.env` versionado | chaves expostas | **Rotacionar** anon key e service role; mover p/ secret manager |
| Migrations fora do git | `*.sql` no `.gitignore` | Versionar via Prisma Migrate |
| Validação de input | dispersa no client | **DTOs** validados no servidor |

> Ao migrar, **rotacionar imediatamente** as chaves Supabase que aparecem em `DOCUMENTACAO_TECNICA.md` §5 e no README — elas estão expostas.

---

## 10. Nuances e armadilhas (gotchas)

Coisas que vão te morder se não souber:

### 10.1 Datas em horário local, não UTC
Todas as métricas usam YMD **local** (`todayLocalYmd`, `toLocalYmdFromIso`), não `toISOString()`. Se o backend rodar em UTC e você usar `toISOString().slice(0,10)`, eventos perto da meia-noite caem no dia errado. **Fixe o timezone** (America/Sao_Paulo) ou replique a conversão local. `isHoliday` usa `toISOString()` — bug latente a corrigir.

### 10.2 `funil` ≠ origem
`crm_funnel_leads.funil` usa `prospeccao_ativa`, mas metas/indicadores usam `prospeccao`. Sempre passe por `normalizeFunilKey` ao cruzar os dois.

### 10.3 Constraints únicas viram upsert
`daily_indicators (client_id, reference_date, origin)` e `bulk_send_contacts (bulk_send_id, phone)` são únicos; o código atual reage ao erro `23505`. No backend, prefira `upsert`/`onConflict` explícito.

### 10.4 Idempotência e fallbacks do webhook
- Usa `.limit(1)` em vez de `.maybeSingle()` de propósito: com duplicatas pré-existentes, `.maybeSingle()` dava erro e **criava lead novo a cada mensagem**. Mantenha.
- **Inconsistência conhecida:** o webhook lê `last_assigned_sdr_id` da loja (`stores`) mas, ao atualizar, escreve em `users` (`.eq('id', client.id)`). Em loja já migrada para `stores`, o ponteiro pode não persistir corretamente. **Corrigir na migração** (ler e escrever na mesma tabela).
- Variantes do 9º dígito são essenciais para não duplicar leads do WhatsApp.

### 10.5 Loop infinito de re-render (contexto histórico)
`patchUserStoresCrmFlag` preserva a referência do array `stores` de propósito — sem isso, um `.map()` gerava novo array a cada render e disparava update infinito. No backend isso some (estado de sessão deixa de ser client-side), mas é bom saber por que o código existe.

### 10.6 Fallbacks legados em todo lugar
`stores`/`users`, `crm_funnel_leads`/`leads`, `stores.webhook_token`/`users.webhook_token`, `last_assigned_sdr_id` em ambos. Esses fallbacks existem porque a migração de jun/2026 (separar `stores` de `users`) **pode não estar 100% concluída**. **Antes de remover fallbacks, confirme que todos os clientes estão em `stores`.** Idealmente, rode um script de consolidação como parte da migração e elimine o legado de uma vez.

### 10.7 Template funnel sync não é transacional hoje
`syncClientFunnelFromTemplate` faz N updates/inserts/deletes sem transação — se falhar no meio, deixa estado inconsistente. **Envolver em transação** no novo backend.

### 10.8 `valor_compra` na rentabilidade
Rentabilidade = `receita − valor_compra − despesa`. O `valor_compra` vem da coluna VEICULOS COMPRADOS; certifique-se de carregá-lo no cálculo (o form mascara os três).

---

## 11. Mapa de tradução: `lib/` atual → módulos do backend

> Boa notícia: as funções de `lib/` já são **puras e testáveis**. Migram quase 1:1 para services. Telas (`app/*/page.js`) viram chamadas à API.

| `lib/` atual | Vira | Observação |
|--------------|------|------------|
| `auth.js`, `authCredentials.js` | `AuthModule` (service + argon2) | trocar hash |
| `userSession.js` | `AuthService.loadSession` | |
| `storeScope.js`, `storeUser.js` | `StoreScopeGuard` + `PermissionsService` | escopo vira guard |
| `stores.js` | `StoresService` | remover fallback legado pós-consolidação |
| `shopRoleLabels.js` | `StoresService` (role labels) | |
| `crmStageFieldRules.js` | `CrmStageRulesService` | **migrar com testes — núcleo do CRM** |
| `crmLeadMetrics.js` | `MetricsService` | idem — definição de "qual data conta" |
| `crmTeamMetrics.js` | `MetricsService.team` | |
| `crmLeadPatch.js` | `CrmLeadsService` (patches) | |
| `crmTemplateFunnel.js` | `CrmTemplatesService` | envolver em transação |
| `crmCoolingRules.js` | `CrmCoolingService` | |
| `crmActivity.js` | `CrmActivityService` (interceptor?) | |
| `crmOrigemOptions.js` | constante/enum compartilhado | |
| `crmLeadForm.js` | `PermissionsService.canSeeLeadFunil` | |
| `agendaUtils.js` | `AgendaService` | filtros viram query builder |
| `bulkSendUtils.js`, `zapiLeadUtils.js`, `webhookUtils.js` | `WebhookModule` + `PhoneService` | |
| `utils.js` (dias úteis) | `WorkingDaysService` | corrigir feriados móveis |

---

## 12. Plano de migração passo a passo (faseado)

> Estratégia **Strangler Fig**: sobe o backend ao lado do sistema atual e migra **um módulo por vez**, mantendo o app no ar. Cada fase: `spec do recorte → plano → implementação com testes → cutover`.

### Fase 0 — Fundação (sem mudar comportamento)
1. Criar projeto NestJS + TypeScript, ESLint/Prettier, estrutura modular, CI.
2. **Prisma com introspecção** (`prisma db pull`) do banco Supabase atual → schema versionado. Não recria dados.
3. `AuthModule`: login com JWT + **argon2**; estratégia de re-hash no login (aceita hash legado uma vez, regrava em argon2).
4. `StoreScopeGuard` + `RolesGuard` (porta de `storeScope`/`storeUser`).
5. Frontend: criar camada `apiClient` (fetch tipado) e mover **só o login** para a nova API. Resto continua no Supabase. **Critério de pronto:** login funciona via backend, sessão em cookie/JWT.

### Fase 1 — Primeiro módulo de ponta a ponta (recomendado: CRM)
Por que CRM primeiro: é o coração do produto, tem mais regra, e validar a abordagem aqui derisca o resto.
1. `CrmModule`: funis, etapas, leads, histórico, cooling, atividade. Portar `crmStageFieldRules` + `crmLeadPatch` + `crmTemplateFunnel` (com transação) **com testes unitários** comparando com o comportamento atual.
2. `WebhookModule`: migrar o webhook Z-API (corrigir o bug do ponteiro SDR, §10.4).
3. Frontend: reescrever **só as telas de CRM/agenda** contra a API.
4. **Cutover:** apontar Z-API para a nova URL; validar criação de lead real.

### Fase 2 — Métricas e leitura
`MetricsModule` (dashboard, marketing, relatórios, projeções, team). Portar `crmLeadMetrics`/`crmTeamMetrics` preservando exatamente "qual data conta". Reescrever telas de leitura.

### Fase 3 — Módulos restantes
`Goals`, `ActionPlans`, `Indicators`, `LeadsLegacy`, `Users/Stores admin`, `BulkSend`. Cada um: API → telas → cutover.

### Fase 4 — Limpeza
1. Remover SDK Supabase e todas as chamadas `from('...')` do frontend.
2. Rodar **consolidação de dados** (todos os clientes em `stores`) e **remover fallbacks legados** (§10.6).
3. (Opcional) trocar host do Postgres (Supabase → Neon/Railway/VPS): só connection string + dump/restore.
4. Rotacionar segredos, versionar migrations, remover credenciais do README.

### Ordem sugerida de dependências
`Auth/Stores/Users` (base) → `CRM` → `Métricas` → `Indicadores/Leads/Metas/Planos` → `BulkSend` → limpeza.

---

## 13. Checklist de dados e ambiente

**Dados a preservar/migrar:**
- [ ] Todas as 15 tabelas + a view `bulk_send_contacts_ordered`.
- [ ] Confirmar índices únicos reais (`crm_funnel_leads` telefone/lid, `daily_indicators`, `bulk_send_contacts`, `user_store_access`).
- [ ] Exportar a pasta `supabase/migrations/` (não está no git) para reconstruir o schema, ou usar `prisma db pull`.
- [ ] Verificar quais clientes ainda estão em `users` (legado) vs. `stores` antes de remover fallbacks.

**Ambiente:**
- [ ] Connection string do Postgres (Supabase) para o backend (não a anon key).
- [ ] Rotacionar `SUPABASE_SERVICE_ROLE_KEY` e anon key (expostas).
- [ ] Variáveis novas: `JWT_SECRET`, `JWT_REFRESH_SECRET`, `DATABASE_URL`, `N8N_BULK_SEND_WEBHOOK_URL`, `APP_URL`.
- [ ] Reconfigurar URL do webhook Z-API por loja para o novo backend.
- [ ] Trocar a senha do admin master.

---

*Documento de migração gerado a partir da engenharia reversa completa do código atual (app/, lib/, contexts/, api/) — junho/2026.*
