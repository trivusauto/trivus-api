# De-Para (sistema antigo → novo) + Roadmap de testes ponto a ponto

> Sistema **antigo**: `trivus/` — Next.js 14 (JS) falando **direto com o Supabase** do browser (auth caseira, ~178 chamadas, sem backend, sem controle de plano).
> Sistema **novo**: `trivus-api` (FastAPI + Postgres, backend real) + `trivus-web` (Next 16, BFF com cookie httpOnly).
> Use a coluna **Testar** como checklist. **Δ** = diferença de comportamento a validar.

---

## 1. O que mudou na arquitetura (resumo)

| Tema | Antigo | Novo |
|---|---|---|
| Backend | Nenhum — browser fala direto com Supabase (anon key) | API FastAPI dedicada (hexagonal, 161 testes) |
| Auth | Caseira, hash `hashed_`, sessão em localStorage | JWT + argon2, **cookie httpOnly + BFF** (token nunca no browser) |
| Isolamento entre lojas | Supabase RLS | Guard de acesso por loja na API (corrigido no stress test) |
| Planos/cobrança | **Não existe** — todo mundo vê tudo | Ecossistema SaaS: empresas, planos, assinaturas, **feature gates** por loja |
| Marketing | Tela simples | Funil de custos CPL/CAC/ROAS + campanhas + **integração Meta (mock)** |
| Datas/dinheiro | strings soltas | validadas (nunca 500) |

---

## 2. DE-PARA de TELAS

> Legenda: ✅ equivalente pronto · 🟡 mudou (validar Δ) · 🆕 novo (não existe no antigo) · ⚠️ **lacuna** (existia no antigo, falta no novo)

| # | Tela ANTIGA (rota) | Tela NOVA (rota) | Status | Δ / o que testar |
|---|---|---|---|---|
| 1 | `/dashboard` | `/dashboard` (Visão geral) | 🟡 | KPIs, funil, série 12m. Δ: dados vêm da API (não Supabase direto); comparar números com o antigo p/ a mesma loja/período. |
| 2 | `/crm` | `/crm` (Kanban) | 🟡 | Δ: **auto-avanço só p/ frente** (antigo ia p/ trás tb); **coluna RESGATE nova**; carimbo de data compra/venda; filtro por coluna; **sem badge de "esfriando"** (antigo tinha cooling — ver §5). |
| 3 | `/leads` + `/leads/new` (tabela `leads` flat) | *(sem tela; CRM substitui)* | ⚠️/🟡 | O antigo tinha uma **lista de leads separada** (tabela `leads`). No novo o CRM (`crm_funnel_leads`) é o centro. **Decidir**: precisa da lista flat? |
| 4 | `/agenda` | `/agenda` | 🟡 | Lista + calendário; filtro por agendamento/comparecimento/fechamento. Δ: presets e paginação. |
| 5 | `/indicators` | `/lancamento` (Lançamento diário) | 🟡 | Upsert por loja+data+origem. Δ: campos novos `classified_leads`, `marketing_investment`. |
| 6 | `/marketing` + `/admin/marketing` | `/marketing` | 🟡 | Δ: **muito mais rico** — funil de custos CPL→CAC, sinaleiros, ROAS/ROI, por campanha. |
| 7 | *(não existe)* | `/campanhas` | 🆕 | CRUD de campanhas (entidade nova) + vínculo com leads. |
| 8 | `/reports` + `/admin/reports` | `/relatorios` | 🟡 | Meta×realizado por origem + custos. Δ: **custos gateados por plano** (Essencial não vê). |
| 9 | `/projections` + `/admin/projections` | `/projecoes` | 🟡 | Meta/Realizado/Projetando. |
| 10 | `/admin/goals` | `/metas` | 🟡 | Upsert por loja+ano+mês+origem (só admin edita). Δ: campo `marketing_investment_goal`. |
| 11 | `/action-plans` + `/admin/action-plans` | `/planos-acao` | 🟡 | Kanban a_fazer/em_andamento/concluído. |
| 12 | `/admin/stores` | `/lojas` | 🟡 | Flags CRM/webhook, token, criar loja clona funil. Δ: `company_id`, `require_campaign_on_lead`, `meta_ad_account_id`. |
| 13 | `/usuarios` + `/admin/users` | `/usuarios` | 🟡 | Portal + equipe; vincular lojas. Δ: papéis/menu_permissions. |
| 14 | `/admin/clients` | `/admin/empresas` | 🟡 | Δ: "clients" virou **empresas da holding** (companies), com assinatura. |
| 15 | `/admin/bulk-sends` (+new, +[id]/logs) | *(falta)* | ⚠️ **LACUNA** | **Disparos em massa**: backend existe (bulk_send + n8n), mas **não há tela no front novo**. Decidir se entra antes do go-live. |
| 16 | `/change-password` | *(falta)* | ⚠️ **LACUNA** | Trocar senha — não há tela no novo. |
| 17 | `/admin/crm` | *(admin inline em /crm + /admin/crm/templates na API)* | 🟡 | Templates de funil viraram rota admin da API. |
| — | *(não existe)* | `/ecossistema` | 🆕 | Vitrine de serviços + upsell. |
| — | *(não existe)* | `/admin/planos` | 🆕 | Planos SaaS (service_keys). |
| — | *(não existe)* | `/admin/servicos` | 🆕 | Catálogo de serviços (feature_keys). |
| — | *(não existe)* | `/admin/assinaturas` | 🆕 | Assinaturas (suspender/reativar/trial). |
| — | *(não existe)* | `/admin/interesses` | 🆕 | Kanban de interesses (upsell). |
| — | localStorage/login caseiro | `/login` (BFF cookie) | 🟡 | Δ: cookie httpOnly, proxy injeta token. |

---

## 3. DE-PARA de DADOS (tabelas)

| Tabela | Antigo | Novo | Δ |
|---|---|---|---|
| users | ✅ | ✅ | + argon2; `role`, `shop_role`, `menu_permissions`. |
| stores | ✅ | ✅ | + `company_id`, `require_campaign_on_lead`, `meta_ad_account_id`. |
| user_store_access | ✅ | ✅ | usado agora no guard de acesso e `/stores/mine`. |
| crm_funnels / crm_funnel_stages | ✅ | ✅ | templates + clone por loja. |
| crm_funnel_leads | ✅ | ✅ | + `campaign_id`, `data_comprado`; datas validadas. |
| crm_lead_stage_history | ✅ | ✅ | base das métricas de "alcançou etapa". |
| crm_stage_cooling_rules | ✅ | ✅ (tabela existe) | ⚠️ **sem UI de cooling no novo** (ver §5). |
| crm_activity_log | ✅ | ✅ | não exposto por API (interno). |
| leads (flat) | ✅ (tela /leads) | ✅ (tabela existe) | novo não tem tela dedicada. |
| daily_indicators | ✅ | ✅ | + `classified_leads`, `marketing_investment`. |
| goals | ✅ | ✅ | + `marketing_investment_goal`. |
| action_plans | ✅ | ✅ | igual. |
| bulk_sends / bulk_send_contacts | ✅ (tela) | ✅ (tabela) | ⚠️ **sem tela no novo**. |
| — | — | **marketing_campaigns** 🆕 | entidade campanha. |
| — | — | **campaign_daily_spend** 🆕 | gasto Meta por campanha/dia. |
| — | — | **companies, plans, subscriptions, services, store_services, service_interests, subscription_payments** 🆕 | camada SaaS/holding inteira (não existia). |

---

## 4. DE-PARA de FLUXOS-CHAVE

| Fluxo | Antigo | Novo | Testar (Δ) |
|---|---|---|---|
| Entrada de lead (WhatsApp) | webhook Supabase | webhook Z-API na API + round-robin SDR + auto-match campanha por `link_code` | Validar payload real CTWA com o Alexis. |
| Avançar etapa | valida campos obrigatórios (idênticos) + auto-avança p/ frente E p/ trás | mesmos campos; **auto-avanço só p/ frente** (preserva RESGATE) | Confirmar que salvar não rebaixa lead em RESGATE. |
| Fechar venda | ao arrastar p/ VENDIDOS, carimba fechou_negocio+data | **igual** (paridade restaurada) | Data retroativa editável. |
| Investimento marketing | manual | manual **ou automático via Meta** (fallback) | Sync Meta grava gasto → funil usa. |
| Ver telas/recursos | todo mundo vê tudo | **gate por plano** (assinatura∧plano∧serviço na loja) | Essencial não vê Marketing; suspensa bloqueia tudo. |
| Isolamento entre lojas | RLS Supabase | guard na API | client/shop_user não acessa loja alheia → 403. |

---

## 5. LACUNAS do novo vs antigo (decidir antes do go-live)

1. ⚠️ **Disparos em massa** — backend pronto (bulk_send + n8n), **sem tela** no front novo. O antigo tinha `/admin/bulk-sends` (criar, listar, logs). **Ação:** construir a tela ou adiar.
2. ⚠️ **Trocar senha** — antigo tinha `/change-password`; novo não. **Ação:** adicionar (rápido).
3. ⚠️ **Badge "lead esfriando" (cooling)** — antigo mostrava no card via `crm_stage_cooling_rules`; novo tem a tabela mas **sem GET de cooling e sem badge**. **Ação:** expor endpoint + badge, ou aceitar como corte.
4. 🟡 **Lista de leads flat (`/leads`)** — o CRM substitui, mas confirmar que ninguém dependia da lista simples.
5. 🟡 **Paginação de `/crm/leads`** — antigo paginava; novo carrega tudo (ok até médio volume).

---

## 6. ROADMAP DE TESTES — ponto a ponto

> Para CADA tela, rode como **admin**, **dono (client)** e **equipe (shop_user)**. Sempre: criar → editar → excluir → validar erro → conferir no banco → **comparar com o antigo** para a mesma loja/período.

### Pré (Fase 0)
- [ ] Staging (API+web+Postgres) separado de produção.
- [ ] Dados: `seed_demo` ou snapshot anonimizado do antigo.
- [ ] 1 usuário por papel; lojas nos planos Full/Performance/Essencial/**suspensa**.
- [ ] E2E: `cd trivus-web && npx playwright install chromium && npm run e2e` (9 testes já existem).

### Login / Auth
- [ ] Login válido/senha errada/campos faltando. Logout limpa cookie. Token expira (7d) → re-login.
- [ ] Multi-tenant: dono não acessa loja alheia (403). shop_user só vê os próprios leads. `/admin/*` bloqueado p/ não-admin.
- [ ] Feature gates: cada tela bloqueada mostra o upsell certo por plano.

### Dashboard
- [ ] KPIs, funil e série 12m batem com os leads do CRM. **Comparar totais com o dashboard antigo** (mesma loja/mês).

### CRM (o mais crítico)
- [ ] Criar lead → auto-posiciona; arrastar entre etapas; bloqueio por campos obrigatórios (mensagem por etapa **idêntica ao antigo**).
- [ ] Auto-avanço ao salvar (agendar/comparecer/comprar/fechar). RESGATE só por arrasto; valor pretendido no card.
- [ ] Carimbo automático de data (comprado/vendido) + edição retroativa.
- [ ] Filtro por coluna; filtro de período por data de cada coluna.
- [ ] **Δ vs antigo**: confirmar que as 7 regras de etapa e a validação em cascata batem 1:1 (já verificado no código; validar em tela).

### Agenda / Lançamento / Metas / Planos / Projeções / Relatórios
- [ ] Agenda: lista+calendário, filtros, presets, busca.
- [ ] Lançamento: upsert por loja+data+origem; investimento alimenta o Marketing.
- [ ] Metas: upsert (só admin); campo de investimento.
- [ ] Planos de ação: mover entre colunas.
- [ ] Projeções: mês/ano válidos.
- [ ] Relatórios: meta×realizado; **custos gateados** (Essencial não vê).

### Marketing / Campanhas (+ Meta)
- [ ] Funil de custos CPL→CAC + sinaleiros; ROAS/ROI batendo com receita das vendas do CRM.
- [ ] Campanhas: CRUD, vínculo com leads.
- [ ] **Meta**: setar `meta_campaign_id`/`meta_ad_account_id`, chamar `POST /integrations/meta/sync` (mock) → investimento passa a vir do gasto Meta (fallback pro manual).

### Ecossistema / Admin da holding (tudo 🆕 — sem antigo p/ comparar)
- [ ] Ecossistema: cards, "tenho interesse" registra.
- [ ] Lojas, Usuários (vincular lojas), Empresas, Planos (service_keys), Serviços (feature_keys), Assinaturas (suspender/reativar/trial expirado → bloqueia), Interesses (kanban).

### Integrações (Fase 4)
- [ ] Webhook Z-API cria lead + round-robin + auto-match campanha. **Validar payload real com o Alexis.**
- [ ] n8n (disparos + interesses), billing gateway, Meta real (quando houver token).
- [ ] Agente WhatsApp (docs/INTEGRACAO_AGENTE.md); ligar `zapi_webhook_enabled=false` na loja piloto.

### Não-funcional / Migração / Deploy
- [ ] Segurança (multi-tenant, injection, JWT, 4xx) — **já coberto pelo stress test**.
- [ ] Carga (50-100 simultâneos), paginação de leads, backup/restore.
- [ ] **Migração real (Plano 11)**: ETL do Supabase antigo → novo com string read-only; **validar paridade** (contagens de leads/lojas/usuários/metas batem antigo×novo); janela única + rollback.
- [ ] Deploy Coolify: secrets, migrations no boot, health, HTTPS, rollback.

### Go-live
- [ ] Tudo ✅ em staging; smoke test em produção (login/criar lead/dashboard); rotacionar segredos expostos; apagar `trivus-backend/`.

---

## Prioridade
1. **Fechar as lacunas** (§5): Disparos + trocar senha (as duas telas que existiam e sumiram).
2. **Migração (Plano 11)** e **Deploy Coolify** — sem isso não há produção.
3. **Mais E2E de front** (já temos 9; expandir p/ cada tela).
4. **Integrações** (Z-API/agente/Meta real).

> Complementa `docs/ROADMAP_TESTES.md` (visão por fases) com o de-para tela-a-tela e as lacunas concretas vs o sistema antigo.
