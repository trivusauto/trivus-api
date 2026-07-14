# Trivus API — Referência completa do Backend

> **Este documento é a visão completa do backend para quem vai construir o frontend** (humano ou IA).
> Cobre: domínio, módulos, todos os endpoints (entrada/saída/permissão), regras de negócio, tabelas e enums.
> A fonte machine-readable dos schemas é o OpenAPI: `GET /openapi.json` (Swagger em `/docs`).

---

## 1. O domínio em 1 minuto

A **Trivus** é uma holding (consultoria + capacitação + agência de marketing) para **concessionárias/revendas de veículos**. Este backend é a plataforma do ecossistema:

- **Empresas** (`companies`) assinam um **plano**; cada empresa tem N **lojas** (`stores`) — os tenants operacionais.
- Cada loja trabalha **leads** (potenciais compradores de veículos) num **CRM Kanban**, recebe leads automaticamente pelo **WhatsApp (Z-API)**, marca **agendamentos**, acompanha **métricas/metas** e roda **campanhas de marketing** com análise de custo (CPL→CAC, ROAS/ROI).
- O que cada loja pode usar é controlado por **serviços → feature keys** (entitlements): a base do modelo SaaS/consultoria e do **upsell** dentro do produto.

### Glossário essencial

| Termo | Significado |
|---|---|
| `funil` (campo do lead) | **Origem** do lead: `receptivo` (chegou sozinho — WhatsApp, indicação), `prospeccao_ativa` (a equipe foi atrás), outros valores = "outros". ⚠️ Não confundir com o funil-Kanban |
| Funil (Kanban) | Pipeline de etapas (`crm_funnels` → `crm_funnel_stages`). Cada loja recebe um **clone** do funil-template do admin |
| `lid` | Chat ID do WhatsApp (Z-API), usado na deduplicação |
| `rentabilidade` | Margem da venda (receita − custo do veículo) |
| `assigned_to` | SDR responsável pelo primeiro contato |
| `vendedor_id` | Vendedor responsável pelo atendimento presencial |
| `agendado_por` | Quem marcou o agendamento |
| Feature key | Chave técnica de um recurso gateável (tela/card/área), ex.: `metrics.reports.costs` |

### Papéis (roles)

| Role | Quem é | O que enxerga |
|---|---|---|
| `admin` | Equipe Trivus (holding) | Tudo, todas as lojas. **Nunca é bloqueado por entitlements** |
| `client` | Dono de loja(s) | Suas lojas (via `user_store_access`); é "gestor" |
| `shop_user` | Colaborador de 1 loja (`parent_store_id`) | Conforme `shop_role`: `gerente` (tudo da loja), `vendedor`, `sdr`, `administrativo` |

---

## 2. Convenções da API (leia antes de integrar)

- **Auth:** `Authorization: Bearer <JWT>` em tudo, exceto `GET /health`, `POST /auth/login`, `POST /webhook/zapi/{token}` e `POST /integrations/*` (que usam tokens próprios via header).
- **Erros:** corpo `{"error": "<mensagem em pt-BR>"}` com status `400` (regra de negócio), `401`, `403`, `404`, `422` (validação Pydantic, formato FastAPI `{"detail": [...]}`).
- **Recurso bloqueado (upsell):** `403` com corpo **`{"error": "feature_locked", "feature_key": "<key>"}`** → o front renderiza, no lugar do conteúdo, o card do serviço que desbloqueia essa key (obtido em `GET /ecosystem/services`, campo `locked_unlockers`).
- **Datas:** `YYYY-MM-DD` (strings); timestamps em ISO-8601. **As métricas contam em datas locais (Brasília), não UTC.**
- **Dinheiro:** número float com 2 casas (`numeric(14,2)` no banco).
- **IDs:** UUIDs como string.
- **Multi-loja:** praticamente todas as consultas recebem `store_id` (query param). O backend valida o escopo (loja fora do escopo do usuário → `400/403`).

---

## 3. Ciclo de vida do lead (a regra de negócio central)

Etapas padrão do Kanban e **campos obrigatórios para avançar** para cada etapa (validação no `PATCH /crm/leads/{id}/stage`; nomes de etapa são normalizados sem acento/maiúsculas):

| Etapa | Campos obrigatórios para entrar |
|---|---|
| RECEBIDOS | `funil`, `telefone` |
| CLASSIFICADOS | `nome`, `cidade` |
| QUALIFICADOS | `modelo`, `ano` |
| AGENDADOS | `data_agendamento`, `hora_agendamento` |
| EM ATENDIMENTO | `compareceu_agendamento = true`, depois `vendedor_id` |
| VEÍCULOS COMPRADOS | `valor_compra` |
| VEÍCULOS VENDIDOS | `receita`, `despesa`, `rentabilidade` |

- Avançar N etapas de uma vez valida **todas** as etapas intermediárias. Voltar etapa não valida nada.
- Erro de validação: `400 {"error": "Preencha os campos obrigatórios: <labels>."}`.
- **Bloqueio por campanha:** se a loja tem `require_campaign_on_lead = true`, lead **receptivo** sem `campaign_id` não avança (`400 {"error": "Preencha a campanha de marketing..."}`).
- Todo movimento grava histórico (`crm_lead_stage_history`) e atividade (`crm_activity_log`).

**Patches com efeitos automáticos** (o backend seta datas sozinho — o front NÃO envia):
- 1º agendamento completo → seta `agendado_por = usuário` e `data_marcacao_agendamento = hoje`; limpar agendamento zera ambos.
- 1º `compareceu = true` → seta `data_compareceu = hoje`; `false` zera.
- Fechamento → seta `fechou_negocio = true`, `data_fechou_negocio = hoje` (1ª vez); aceita dinheiro em formato BR (`"1.000,00"`).

**"Qual data conta" nas métricas** (regra de ouro — idêntica ao sistema antigo):
- Lead conta em `created_at` (data local) · Agendamento conta em `data_marcacao_agendamento` (fallback `data_agendamento`) · Comparecimento em `data_compareceu` · Conversão/receita em `data_fechou_negocio`.
- **Qualificado/Classificado** = lead que **entrou** na etapa (histórico) **ou** está nela/posterior — mesmo que tenha regredido depois.
- **Dias úteis** (projeções): sábado conta, domingo e feriados nacionais BR (fixos + móveis via Páscoa: Carnaval, Sexta Santa, Corpus Christi) não.

---

## 4. Endpoints por módulo

Legenda de acesso: 🌐 público · 🔑 autenticado · 👑 `admin` · 🛡️ gate por feature key (retorna `feature_locked` p/ não-admin sem o serviço).

### 4.1 Health & Auth

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `GET /health` | 🌐 | — | `{"status":"ok"}` |
| `POST /auth/login` | 🌐 | `{email, password}` | `{access_token, user:{id,email,name,role,parent_store_id}}` · 401 credenciais · 403 usuário inativo |
| `GET /auth/me` | 🔑 | — | `user` (mesmo shape acima) |
| `POST /auth/change-password` | 🔑 | `{current_password, new_password}` | user · 401 senha atual errada |

> Senhas legadas (formato antigo `hashed_<senha>`) são aceitas no login e **re-hasheadas para argon2 automaticamente** na primeira vez.

### 4.2 Lojas & Usuários

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `GET /admin/stores` | 👑 | — | `[{id, nome_fantasia, crm_enabled, active}]` |
| `POST /admin/stores` | 👑 | `{nome_fantasia*, razao_social, cnpj}` | 201 store |
| `PATCH /admin/stores/{id}` | 👑 | dict com campos: `nome_fantasia, razao_social, cnpj, crm_enabled, zapi_webhook_enabled, webhook_token, active, company_id, require_campaign_on_lead` | store. **Ligar `crm_enabled` clona o funil-template para a loja (1ª vez)** |
| `GET /admin/stores/{id}/role-labels` | 👑/`client` | — | `{sdr, vendedor, administrativo, gerente}` (rótulos customizados com defaults) |
| `PATCH /admin/stores/{id}/role-labels` | 👑/`client` | dict parcial (`{"sdr": "Pré-vendas"}`) | merge com defaults (máx 80 chars, chaves inválidas ignoradas) |
| `PUT /admin/stores/{id}/services` | 👑 | `{service_key*, enabled*}` | `{ok}` · 400 se serviço fora do plano da empresa / loja sem empresa |
| `GET /admin/users` | 👑 | — | usuários portal (`role=client`) |
| `POST /admin/users` | 👑 | `{email*, password*, name}` | 201 usuário `client` |
| `PUT /admin/users/{id}/stores` | 👑 | `{store_ids*[], owner_store_ids[]}` | substitui **todos** os vínculos multi-loja · 400 lista vazia |
| `GET /stores/{store_id}/team` | 👑/`client` | — | colaboradores da loja |
| `POST /stores/{store_id}/team` | 👑/`client` | `{email*, password*, name*, shop_role, menu_permissions[], can_see_unassigned_leads}` | 201 `shop_user` vinculado à loja |

### 4.3 CRM (Kanban) — gate `crm.kanban` nas listagens

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `GET /crm/funnels?store_id` | 🔑🛡️ | — | `[{id, name, sort_order, stages:[{id,name,sort_order}]}]` |
| `POST /crm/stages` | 🔑 | `{funnel_id*, name*, sort_order}` | 201 etapa |
| `PATCH /crm/stages/{id}` | 🔑 | `{name*}` | etapa renomeada |
| `PUT /crm/stages/{id}/cooling-rules` | 🔑 | `[{hours_threshold*, card_color, message}]` | substitui as regras de esfriamento da etapa (defaults: `#facc15`, "Lead esfriando") |
| `GET /crm/leads?store_id` | 🔑🛡️ | — | leads da loja (objeto completo, ~35 campos). **SDR vê só os `assigned_to` dele**; demais papéis veem todos |
| `POST /crm/leads` | 🔑 | `{store_id*, stage_id*, campaign_id, funil, nome, telefone, cidade, modelo, ano, assigned_to}` | 201 lead |
| `PATCH /crm/leads/{id}` | 🔑 | campos editáveis (incl. `campaign_id` — **preenchimento manual da campanha**, `vendedor_id`, dados do veículo, `observacoes`...) | lead atualizado |
| `DELETE /crm/leads/{id}` | 🔑 | — | 204 |
| `PATCH /crm/leads/{id}/stage` | 🔑 | `{to_stage_id*}` | lead movido · 400 campos faltando / campanha obrigatória (§3) |
| `PATCH /crm/leads/{id}/agendamento` | 🔑 | `{data_agendamento, hora_agendamento}` (vazios = desmarcar) | lead (datas automáticas — §3) |
| `PATCH /crm/leads/{id}/comparecimento` | 🔑 | `{compareceu*: bool}` | lead |
| `PATCH /crm/leads/{id}/fechamento` | 🔑 | `{receita, despesa, rentabilidade}` (aceita `"1.000,00"`) | lead com `fechou_negocio=true` |
| `GET /admin/crm/templates` | 👑 | — | funis-template com etapas |
| `POST /admin/crm/templates` | 👑 | `{name*, stages: [nomes]}` | 201 template |
| `POST /admin/crm/templates/{id}/sync` | 👑 | — | **propaga o template para todos os clones**: renomeia, cria etapas novas, move leads de etapas removidas para a 1ª etapa e as apaga |

### 4.4 Webhook WhatsApp (Z-API)

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `POST /webhook/zapi/{token}` | 🌐 (token da loja na URL) | payload da Z-API | `{ok, lead_id?, assigned_to?}` ou `{ok:true, skipped:"group\|from_me\|newsletter\|disabled\|no_phone\|duplicate"}` · 401 token inválido · 422 sem funil/etapa |

Fluxo: identifica a loja pelo token → ignora grupos/mensagens próprias/newsletters → extrai telefone ou `lid` → **deduplica** (por `lid` e variantes do telefone com/sem 9º dígito; se duplicado, enriquece o lead existente) → cria o lead na 1ª etapa do funil clonado com `funil="receptivo"` → **round-robin** entre SDRs com `can_see_unassigned_leads=true` (ponteiro `last_assigned_sdr_id` na loja) → tenta **auto-match de campanha** procurando o `link_code` das campanhas ativas no payload (referral/texto).

### 4.5 Agenda — gate `agenda`

| Rota | Acesso | Recebe (query) | Devolve |
|---|---|---|---|
| `GET /agenda` | 🔑🛡️ | `store_id*`, `apply_to` (`agendamento`\|`comparecimento`\|`fechamento`), `preset` (`today`\|`yesterday`\|`month`\|`previous_month`\|`from_today`\|`custom`), `from`, `to`, `search` (nome/modelo/veículo/telefone), `page`, `page_size` (25/50/100) | `{items: [lead completo], total, page, page_size}` |

Escopo: gestor (`client`, `admin` ou `shop_role=gerente`) vê tudo; demais veem leads onde são `vendedor_id`/`assigned_to` (+ sem responsável, se tiverem a permissão). Atribuir vendedor na agenda = `PATCH /crm/leads/{id}` com `{vendedor_id}`.

### 4.6 Métricas

| Rota | Acesso | Recebe (query) | Devolve |
|---|---|---|---|
| `GET /metrics/dashboard` | 🔑 | `store_id` (admin sem = todas as lojas), `start*`, `end*` | `{totals:{total_leads, qualified_leads, scheduled, attended, conversions, total_revenue}, monthly:[12 meses {month:"M/YYYY", leads, qualified, scheduled, attended, conversions, profitability}]}` |
| `GET /metrics/reports` | 🔑 | `store_id`, `start*`, `end*`, `campaign_id` (filtra leads da campanha) | `{summary:{totalLeads, classified, qualified, scheduled, attended, converted, revenue, avgTicket}, byOrigin:{receptivo, prospeccao, outros → {total, classified, qualified, scheduled, attended, converted, revenue}}, costs:{cost_per_lead, cost_per_classified, cost_per_qualified, cost_per_scheduled, cost_per_attended, cac}, investment}` — **`costs`/`investment` vêm `null` sem a key `metrics.reports.costs`** |
| `GET /metrics/projections` | 🔑 | `year*`, `month*`, `store_id` | `{working_days:{total, elapsed, remaining}, metrics:[{key: leads\|qualified\|scheduled\|attended\|conversions\|revenue, goal, actual, projected, pct_of_goal, light: green\|yellow\|red\|gray}]}` — projeção = ritmo/dia útil × dias restantes |
| `GET /metrics/team` | 🔑🛡️`metrics.team` | `store_id*`, `start*`, `end*` | `{rows:[{user_id, name, shop_role, leads, scheduled, attended, converted, revenue, conversion_rate, avg_ticket}]}` + linha `__unassigned__`. Atribuição: leads→`assigned_to`; agendamentos→`vendedor_id\|\|agendado_por`; resto→`vendedor_id` |
| `GET /metrics/indicators-report` | 🔑🛡️`indicators` | `store_id*`, `from*`, `to*`, `year*`, `month*` | mesmo shape do reports **+ `goalsComparison`**: `[{origin, "Meta Conversões", "Real Conversões", "Meta Receita", "Real Receita", "Meta Investimento", "Real Investimento"}]`. Regras: `totalLeads/classified/qualified` contam **só receptivo**; `revenue` é **líquida** (bruto − despesas diárias) |

Sinaleiro (`light`): verde ≥100% da meta, amarelo ≥80%, vermelho <80%, cinza sem meta. Metas são mensais por loja — com várias lojas ou período >1 mês, tudo cinza.

### 4.7 Marketing — gates `metrics.marketing` / `marketing.campaigns`

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `GET /campaigns?store_id` | 🔑🛡️ | — | `[{id, store_id, name, started_at, ended_at, budget, link_code}]` (`ended_at:null` = ativa) |
| `POST /campaigns` | 🔑 | `{store_id*, name*, started_at*, ended_at, budget, link_code}` | 201 campanha. `link_code` = identificador p/ auto-match no WhatsApp |
| `PATCH /campaigns/{id}` | 🔑 | campos parciais | campanha |
| `GET /marketing/funnel` | 🔑🛡️ | `store_id*`, `start*`, `end*`, `campaign_id` | Funil de custos do **receptivo**: `{stages:[6× {stage: leads\|classified\|qualified\|scheduled\|attended\|sales, label, quantity, unit_cost, conversion_from_previous, goal, pct_of_goal, light}], investment, revenue, roas, roi, investment_goal}` |
| `GET /marketing/by-campaign` | 🔑🛡️ | `store_id*`, `start*`, `end*` | `[{campaign:{...}, funnel:{...}}]` — um funil por campanha ativa/encerrada no período (base das seções 2 e 3 da tela) |

Fórmulas: `unit_cost = investimento ÷ quantidade` (CPL na etapa leads, **CAC** na etapa sales) · `ROAS = receita ÷ investimento` · `ROI = (receita − investimento) ÷ investimento`. Investimento do funil geral = soma dos lançamentos diários (`marketing_investment` dos indicadores); do funil por campanha = `budget` da campanha. **Prospecção ativa fica fora** (sem investimento de mídia).

### 4.8 Indicadores, Metas e Planos de Ação

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `GET /indicators` 🛡️`indicators` | 🔑 | `store_id*`, `from`, `to` | lançamentos diários |
| `POST /indicators` | 🔑 | `{store_id*, reference_date*, origin* (receptivo\|prospeccao\|outros), origin_custom, total_leads, qualified_leads, classified_leads, scheduled_leads, attended_leads, converted_leads, profitability, daily_expenses, marketing_investment, notes}` | **upsert** por `(loja, data, origem)` — reenviar o mesmo dia atualiza |
| `GET /goals` 🛡️`goals` | 🔑 | `store_id*`, `year*`, `month*` | metas do mês (por origem) |
| `POST /admin/goals` | 👑 | `{store_id*, year*, month*, origin*, leads_quantity, qualified_quantity, scheduled_quantity, attended_quantity, conversions_quantity, profitability_goal, average_ticket_goal, marketing_investment_goal}` | **upsert** por `(loja, ano, mês, origem)` |
| `DELETE /admin/goals/{id}` | 👑 | — | 204 |
| `GET /action-plans` 🛡️`action_plans` | 🔑 | `store_id*` | planos da loja |
| `PATCH /action-plans/{id}/status` | 🔑 | `{status*: a_fazer\|em_andamento\|concluido}` | a loja atualiza o andamento |
| `POST /admin/action-plans` · `PATCH/DELETE /admin/action-plans/{id}` | 👑 | `{store_id*, title*, description, status}` | CRUD do admin |
| `GET/POST/PATCH/DELETE /leads...` | 🔑 | leads **legado** (modo sem CRM): `{store_id*, name, phone, car, city, origin, entry_date}` + flags `qualified/disqualified/scheduled/attended/converted/profitability` | CRUD simples |

### 4.9 Disparos em massa (WhatsApp via n8n)

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `GET /admin/bulk-sends` | 👑 | — | `[{id, title, total_contacts, status, success_count, error_count}]` |
| `POST /admin/bulk-sends` | 👑 | `{title, message_template, variations: [até 5], phones: [strings BR], delay_min_sec, delay_max_sec}` | 201 `{id, stats:{total, duplicated, invalid}}` — telefones normalizados/deduplicados no servidor; dispara o fluxo n8n se configurado |
| `GET /admin/bulk-sends/{id}/logs` | 👑 | — | contatos ordenados `pending → sent → error` |
| `PATCH /integrations/bulk-send/contacts/{id}/status` | header `x-n8n-token` | `{status: sent\|error, error_message}` | o n8n reporta o resultado de cada envio |

### 4.10 Ecossistema (empresas, planos, assinaturas, serviços, upsell)

**Cadeia de acesso:** feature desbloqueada ⇔ assinatura da empresa utilizável (`active`, ou `trialing` com `trial_ends_at` ≥ hoje) **E** o plano contém o serviço **E** o serviço está ligado na loja **E** a key ∈ `feature_keys` do serviço. Loja sem `company_id` = **modo legado, sem gate** (transitório até a migração). Admin nunca é gateado.

| Rota | Acesso | Recebe | Devolve |
|---|---|---|---|
| `GET /ecosystem/my-entitlements?store_id` | 🔑 | — | `{feature_keys: [...]}` — **o front usa isso pra montar menu/telas/cards** |
| `GET /ecosystem/services?store_id` | 🔑 | — | `{services:[{key, name, type: software\|humano, what_it_is, what_it_does, upsell_pitch, unlocked}], unlocked_feature_keys, locked_unlockers:{<feature_key>: {service_key, name, upsell_pitch}}}` — catálogo + de-para "key bloqueada → serviço que desbloqueia" |
| `POST /ecosystem/interests` | 🔑 | `{store_id*, service_key*}` | 201 interesse (status `novo`) + **notifica o comercial via n8n** |
| `GET /ecosystem/feature-keys` | 👑 | — | picklist das keys válidas `[{key, label, kind: modulo\|tela\|area}]` (definidas no código) |
| `GET/POST /admin/services` · `PATCH/DELETE /admin/services/{id}` | 👑 | `{key*, name*, type*, what_it_is, what_it_does, upsell_pitch, feature_keys[], sort_order}` | CRUD do catálogo. Regras: `key` imutável; `feature_keys` validadas contra a picklist; DELETE = desativar (bloqueado se estiver em algum plano) |
| `GET/POST /admin/plans` · `PATCH /admin/plans/{id}` | 👑 | `{key*, name*, service_keys[], max_stores, price_month}` | planos (combinações de serviços) |
| `GET/POST /admin/companies` · `PATCH /admin/companies/{id}` | 👑 | `{name*, cnpj, responsible_name}` | empresas. Vincular loja: `PATCH /admin/stores/{id}` com `{company_id}` |
| `GET/POST /admin/subscriptions` | 👑 | `{company_id*, plan_id*, status*: trialing\|active, trial_ends_at (obrigatório se trialing), notes}` | assinaturas. Valida `max_stores` do plano |
| `PATCH /admin/subscriptions/{id}/status` | 👑 | `{status: active\|suspended\|canceled\|trialing}` | suspender/reativar/cancelar (manual, v1) |
| `PATCH /admin/subscriptions/{id}/plan` | 👑 | `{plan_id}` | migração SaaS ↔ consultoria = trocar o plano |
| `GET /admin/interests?status` · `PATCH /admin/interests/{id}` | 👑 | `{status: novo\|contatado\|convertido\|descartado, notes}` | fila comercial do upsell |
| `POST /integrations/billing/events` | header `x-billing-token` | evento do framework de pagamentos (ver [BILLING_GATEWAY.md](BILLING_GATEWAY.md)) | 409 enquanto `BILLING_GATEWAY_ENABLED=false` |

---

## 5. Feature keys (registro atual)

`crm.kanban` · `crm.activity_log` · `agenda` · `webhook.zapi` · `metrics.dashboard` · `metrics.reports` · `metrics.reports.costs` (área: coluna de custos) · `metrics.marketing` · `metrics.projections` · `metrics.team` · `marketing.campaigns` · `bulk_send` · `indicators` · `goals` · `action_plans`

**Como o front deve usar:** ao trocar de loja, chame `GET /ecosystem/my-entitlements` e esconda o que não estiver na lista (menus, telas, cards). Para áreas bloqueadas, use `locked_unlockers` do catálogo pra renderizar o card de upsell com CTA → `POST /ecosystem/interests`. Se uma chamada retornar `403 feature_locked`, trate igual.

---

## 6. Tabelas (23) — resumo

DDL completo: [`db/MODELO_ALVO.md`](db/MODELO_ALVO.md).

| Grupo | Tabelas |
|---|---|
| Acesso | `users` (credenciais + perfil), `stores` (lojas; flags `crm_enabled`, `require_campaign_on_lead`, `company_id`), `user_store_access` (N:N c/ `is_owner`) |
| CRM | `crm_funnels` (template + clones), `crm_funnel_stages`, `crm_funnel_leads` (~35 campos, incl. `campaign_id`), `crm_lead_stage_history`, `crm_stage_cooling_rules`, `crm_activity_log` |
| Negócio | `leads` (legado), `daily_indicators` (unique loja+data+origem), `goals` (unique loja+ano+mês+origem), `action_plans` |
| Marketing | `marketing_campaigns` |
| Disparos | `bulk_sends`, `bulk_send_contacts` |
| Ecossistema | `companies`, `plans`, `subscriptions`, `services`, `store_services`, `service_interests`, `subscription_payments` |

## 7. Enums

| Campo | Valores |
|---|---|
| `users.role` | `admin` · `client` · `shop_user` |
| `users.shop_role` | `sdr` · `vendedor` · `administrativo` · `gerente` |
| `funil` (origem do lead) | `receptivo` · `prospeccao_ativa` · vazio (=receptivo) · outro (=outros) |
| `origin` (indicadores/metas/leads legado) | `receptivo` · `prospeccao` · `outros` |
| `action_plans.status` | `a_fazer` · `em_andamento` · `concluido` |
| `subscriptions.status` | `trialing` · `active` · `suspended` · `canceled` |
| `subscriptions.billing_mode` | `manual` · `gateway` |
| `services.type` | `software` · `humano` |
| `service_interests.status` | `novo` · `contatado` · `convertido` · `descartado` |
| `bulk_sends.status` | `draft` · `running` · `paused` · `completed` |
| `bulk_send_contacts.status` | `pending` · `sent` · `error` |
| `light` (sinaleiro) | `green` · `yellow` · `red` · `gray` |

## 8. Arquitetura interna (pra quem for mexer no backend)

Cada módulo em `src/modules/<nome>/` segue hexagonal/DDD:
- `domain/` — entidades e **serviços de regra puros** (ex.: `stage_rules`, `lead_patch`, `metrics_core`, `working_days`, `cost_funnel`, `phone`, `round_robin`, `entitlements`) — sem I/O, 100% testados unitariamente;
- `application/` — use cases (1 classe = 1 caso de uso, `execute()`);
- `infrastructure/` — SQLAlchemy (ORM + repositórios), clientes externos (n8n), readers;
- `interface/` — routers FastAPI + schemas Pydantic + wiring (`Depends`).

Specs de origem: [MIGRACAO_BACKEND.md](MIGRACAO_BACKEND.md) (domínio completo, engenharia reversa) · [ECOSSISTEMA_TRIVUS.md](ECOSSISTEMA_TRIVUS.md) (ecossistema) · [plans/](plans/00-INDEX.md) (planos de implementação).
