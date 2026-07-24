# Plano 13 — Ajustes pós-reunião (visão macro por fases)

> **Para EXECUTAR, use `PLANO_13_BABY_STEPS.md`** — decomposição deste plano em
> micro-passos (S0.1…S7.2) para execução por IA, com verificação e commit por passo.
> O prompt da IA executora está em `PROMPT_EXECUTOR_PLANO13.md`. Este arquivo fica
> como referência da visão macro/estimativas.

> Plano de desenvolvimento derivado de `AJUSTES_POS_REUNIAO_CLIENTE.md` (decisões ✅) e
> `SPEC_MARKETING_RELATORIOS.md` (designs). Segue a estrutura real do projeto:
>
> - **API** `trivus-api` (branch `develop`): módulos hexagonais em
>   `src/modules/<mod>/{domain,application,infrastructure,interface}`, migrations Alembic em
>   `migrations/versions/`, testes em `tests/{unit,integration,e2e}`.
> - **Web** `trivus-web` (branch `release/new-web`): rotas em `src/app/(app)/<rota>/page.tsx`,
>   componentes em `src/components/`, utilitários em `src/lib/`.
>
> **Ritual de cada passo:** implementar → `uv run pytest && uv run ruff check . && uv run mypy src`
> (API) / `npm run lint && npm run build` (web) → commit convencional → push na branch certa
> (**NUNCA legacy/main/master**). Para testar no browser: `docker compose up -d --build api web`
> em `trivus-api/deploy/` (portas locais 3010 web / 3011 api / 5443 db) e rodar
> `uv run python -m scripts.seed_demo` se precisar de dados.
>
> Estimativa total: ~15-20 dias úteis de trabalho de agente, em 6 fases independentes.
> Cada fase termina com o sistema deployável (nada fica quebrado entre fases).

---

## FASE 1 — Visual rápido (front-only, ~1 dia)

### 1.1 Paleta nova
- `trivus-web/src/app/globals.css`: remapear tokens por tema (NÃO renomear classes):
  - dark: `--gold` → branco `#F4F6FA`, `--goldt` → branco suave; texto sobre `btn-gold` vira escuro.
  - light: `--gold` → azul da marca (referência: o azul do bg dark), `--goldt` → azul mais escuro.
- Conferir contraste em botões/chips/badges nos 2 temas e as cores de destaque nos gráficos Recharts.

### 1.2 Toast de validação do CRM (react-toastify)
- `npm i react-toastify`; `<ToastContainer position="top-right" autoClose={10000} theme="colored"/>` no layout do grupo `(app)`.
- Usar `toast.error(...)` nos erros da mutation `move` de `src/app/(app)/crm/page.tsx` e nas validações do `src/components/crm/lead-drawer.tsx`, nomeando card + campos: `"João Silva" não pode ir para AGENDADOS: falta data e horário.`
- O toast interno (`components/ui/toast.tsx`) permanece no resto do app.

### 1.3 Colunas do kanban com cor
- Em `crm/page.tsx`, derivar o fundo de cada coluna de `DOT_COLORS[i]` com ~8% de opacidade (`color-mix` ou rgba). Validar nos 2 temas.

### 1.4 Filtro por múltiplas colunas
- `stageFilter: string` → `stageFilters: string[]`; dropdown com checkboxes (padrão: todas); board filtra `stageFilters.length === 0 || stageFilters.includes(st.id)`.

### 1.5 Nomenclatura de origens + preview de total em Metas (parte front)
- Criar `src/lib/origin-labels.ts`: `ORIGIN_LABELS = { receptivo: "Marketing", prospeccao: "Prospecção Ativa", outros: "Outras Mídias" }` — aplicar em Metas, Lançamento, Relatórios, Projeções e Marketing (valores do banco intactos).
- Metas: linha "Total" readonly/opaca somando as 3 origens em tempo real.

**Aceite F1:** lint+build verdes; as 5 mudanças conferidas no browser nos 2 temas.
**Commit:** `feat(ui): paleta nova, toastify no CRM, colunas coloridas, filtro multi-coluna, rótulos de origem` → `release/new-web`.

---

## FASE 2 — Backend pequeno (~2 dias)

### 2.1 Migration: meta de classificados
- `migrations/versions/xxxx_add_classified_quantity_to_goals.py`: `goals.classified_quantity INTEGER NULL`.
- Módulo `goals`: ORM + schema + repo + router aceitam/retornam o campo. Front Metas: campo "Classificados" (com o total do 1.5).

### 2.2 Data de entrada na etapa no card (CRM 3.3)
- `crm/infrastructure/repositories.py` → `list_for_board`: incluir `stage_entered_at` por lead — subquery agregada em `crm_lead_stage_history` (MAX(entered_at) da etapa atual do lead), **uma query, sem N+1**.
- Front `crm/page.tsx`: trocar `daysSince(...)` por `fmtDay(stage_entered_at)` (dd/mm).
- Teste: `tests/e2e/test_crm_patches.py` (ou novo) — lead criado/movido retorna `stage_entered_at` coerente.

### 2.3 Funil da Visão Geral com CLASSIFICADOS + componente fixo (SPEC Parte A)
- API `metrics`: incluir CLASSIFICADOS na resposta do funil do dashboard e na lista de taxas (StageReachReader já lê `crm_lead_stage_history`).
- Web: criar `src/lib/goal-status.ts` (`goalStatus`: ≥95 green · 80–95 amber · <80 red) e `src/components/charts/fixed-funnel.tsx` (SVG de paths FIXOS, 6 trapézios 100→86→72→56→40→22→14, degradê azul, última faixa accent, texto central `Nome  Número`). Usar no dashboard.
- Teste API: funil retorna a etapa nova; taxas incluem Leads→Classificados.

### 2.4 Agenda: vendedor + modal
- API `agenda`: `GET /agenda` aceita `vendedor_id` (filtra `vendedor_id`/`agendado_por`); resposta inclui `vendedor_nome` (join com users, sem N+1).
- API `users`: liberar `GET /stores/{store_id}/team` para shop_user **gerente da própria loja** (guard `parent_store_id == store_id`; hoje `require_roles("admin","client")` em `users/interface/router.py`).
- Web agenda: dropdown "Vendedor" (usa a query de team), coluna "Vendedor" na lista, clique (lista ou item do calendário) abre o `LeadDrawer` do lead.
- Testes: filtro por vendedor; gerente lê team da própria loja (200) e de outra (403).

**Aceite F2:** suíte API verde (novos testes incluídos); telas conferidas.
**Commits:** um por item, API → `develop`, web → `release/new-web`.

---

## FASE 3 — Permissões (fazer TUDO junto e reescrever os testes, ~2-3 dias)

> Motivo de agrupar: 3.1-3.5 mudam a semântica de visibilidade/edição do CRM e o item 11 mexe
> em quem cria usuários — os testes de acesso são reescritos uma única vez.

### 3.1 Migration: flag de edição
- `users.can_edit_others_leads BOOLEAN NOT NULL DEFAULT false` (**default = restrito**; autorização é concedida).
- Expor no create/update de team user (`users` schemas/router/use case). O PRÓPRIO usuário nunca vê a flag na UI.

### 3.2 Leitura: todos da loja veem o quadro
- `crm/application/leads.py` (`ListLeadsUseCase`) + `list_for_board`: **remover** a restrição por `assigned_to` para shop_user (a regra do legado morre aqui, por decisão do cliente). Manter o param `assigned_to` como filtro opcional (agora útil para todos).
- Front: o filtro "Responsável" do CRM passa a aparecer para todos os papéis. Para os nomes: incluir `assigned_to_name` no payload de `list_for_board` (join com users) em vez de abrir o endpoint de team para todo mundo.

### 3.3 Escrita: guard central
- Novo helper em `crm/application` (ex. `edit_guard.py`): `assert_can_edit_lead(user, lead, users_repo)` → shop_user não-gerente sem flag e `assigned_to != user_id` e `vendedor_id != user_id` → `ForbiddenError("Este lead pertence a outro colaborador. Peça autorização ao gerente.")`.
- Aplicar nos endpoints de escrita do `crm/interface/router.py`: PATCH lead, `/stage`, `/agendamento`, `/compareceu`, `/fechamento`, DELETE.

### 3.4 Reescrever `tests/e2e/test_crm_visibility.py`
- Cenários novos: (a) sdr vê TODOS os leads da loja; (b) sdr sem flag não move/edita lead do colega (403) mas move o próprio; (c) sdr com flag move o do colega; (d) gerente/dono/admin sempre podem; (e) filtro `assigned_to` funciona para sdr; (f) multi-tenant continua (loja alheia 403).

### 3.5 Front CRM/Usuários
- Usuários: toggle "Pode editar leads de outros colaboradores" (visível só para admin/dono/gerente).
- CRM: sem permissão, card do colega com drag desabilitado + tooltip; drawer readonly.

### 3.6 Lojas/Empresas (item 11, decisões ✅)
- `POST /admin/stores` aceita `managers[]` (email/senha/nome) e cria loja+gerentes atomicamente (use case novo em `stores/application`); modal "Nova loja" ganha a seção Gerentes (1+).
- `POST /stores/{id}/team` também liberado para gerente da própria loja (mesmo guard do 2.4). Front esconde "Adicionar colaborador" para SDR/vendedor.
- **Loja sem empresa (Opção A):** no resolvedor de entitlements (`src/modules/ecosystem/`), `company_id IS NULL` → conjunto padrão completo de feature_keys (igual ao plano Full: união dos serviços de software). Remover o erro "Loja sem empresa vinculada (modo legado)" de `store_services.py`. Assinatura suspensa continua bloqueando lojas vinculadas.
- Testes: loja sem empresa acessa CRM/métricas/marketing; criação de loja com gerentes; gerente cria equipe; SDR não cria (403).

**Aceite F3:** suíte completa verde com os testes novos; roteiro manual: sdr vê tudo/não mexe no alheio; gerente concede a flag e o sdr passa a mexer.
**Commits:** API `feat(crm)!: visibilidade total na loja + edição por autorização` (mudança de comportamento — destacar no corpo) e `feat(stores): criação com gerentes + loja sem empresa (modo A)`; web correspondente.

---

## FASE 4 — Multi-loja + Marketing + Relatórios + Projeções (~5-6 dias, o maior bloco)

### 4.1 Infra multi-loja (pré-requisito comum)
- Helper em `src/shared/interface/store_access.py`: `require_store_ids_access` — aceita `store_ids` repetidos, valida TODOS contra `GetAccessibleStoreIdsUseCase`, 403 se algum fora do escopo; default = todas as lojas acessíveis quando omitido.
- `metrics/infrastructure/reader.py`: variantes agrupadas por `store_id` (uma query com `GROUP BY store_id`, nunca loop de queries).

### 4.2 Dashboard consolidado + comparação (item 1)
- `GET /metrics/dashboard` (e funil/série) com `store_ids` → `{consolidated, by_store[]}`. Ticket médio consolidado = Σ receita ÷ Σ fechamentos.
- Web: seletor multi-loja no dashboard (aparece com 2+ lojas; padrão "Todas"); KPIs consolidados; série 12m e gráficos com uma linha/barra por loja selecionada.
- Testes: dono com 2 lojas vê soma; id alheio → 403; shop_user segue mono-loja.

### 4.3 Séries de marketing (SPEC B2/B4)
- Novo `GET /metrics/marketing/series?store_id&from&to`: por dia `{date, leads, classificados, qualificados, agendados, comparecidos, vendas, investimento}` + agregados do período e do comparativo (janela anterior de mesma duração). Fontes: `daily_indicators` + CRM (mesma base do funil de custos). Uma query agrupada por data.
- Web Marketing: **12 KPI cards** (Leads, CPL, Classificados, Custo/Classificado, Qualificados, Custo/Qualificado, %Qualificados, Agendados, Comparecidos, Vendas, CAC, Investimento) com valor grande, badge de variação (custos: melhorar = cair → inverter cor), "X no período anterior" e sparkline de área; + os 2 gráficos de linha (Investido×Leads, Leads×Qualificados).

### 4.4 Funil Meta × Realizado (SPEC B1 ⭐)
- Estender o endpoint do funil de custos: por etapa `{stage, meta, realizado, pct_meta, custo_unit, conv_prev_pct}` — metas de `goals` origem `receptivo` (com `classified_quantity` da F2), meta proporcional ao período, custo = investimento ÷ realizado da etapa.
- Web: componente com os DOIS meio-funis SVG fixos (cinza espelhado META à esquerda; azul REALIZADO·CUSTO à direita, VENDAS em accent), centro com bolinha `goalStatus` + `↓ X% da etapa anterior`, chips "% da meta" e custo; legenda ≥95/80–95/<80; nota "prospecção ativa não entra no cálculo de custo"; **filtro de etapas** (checkboxes) com recálculo do ↓% entre visíveis.

### 4.5 Relatórios → Painel Executivo (SPEC Parte C)
- Novo `GET /metrics/executive?store_ids&year&month` → blocos prontos: `dias{uteis,trabalhados,restantes}` (dia útil seg-sáb), `kpis` (faturamento/meta/projeção/lucro projetado/ticket/fechamentos/conversão/margem), `by_store[]` (tabela C3), dados dos 6 gráficos (C4, incl. comprados×vendidos), `gauge` (% meta), `ritmo` (média atual/necessária, forecast = min(99%, projeção÷meta)), `resumo[]` (bullets calculados), `tops` (3 destaques + 3 atenção). Divisões protegidas (nunca 500).
- Web `/relatorios`: reconstruir como o painel (C1 cabeçalho → C2 8 KPIs → C3 tabela com heatmap → C4 grade 2×3 de gráficos → C5 rodapé com gauge (PieChart semicircular + agulha SVG), ritmo, resumo executivo e TOP 3s).
- Escopo: dono/admin multi-loja; gerente = própria loja com a tabela **por vendedor** (usa as regras de atribuição da F5.2); SDR → versão "meus números".
- Testes e2e: papéis (SDR bloqueado do executivo), loja vazia, mês sem meta, ids alheios 403.

### 4.6 Projeções (item 7)
- API `metrics/projections`: incluir `classified`; separar por origem (receptivo/prospeccao/outros) + total; aceitar `store_ids` e `user_id` (shop_user comum: `user_id` FORÇADO ao próprio no backend).
- Web: semáforo `goalStatus` em cores fortes; 3 blocos por origem (rótulos `ORIGIN_LABELS`) + total; seletor de lojas (dono) e de colaborador (gerente); SDR vê os próprios.

**Aceite F4:** suíte verde; conferência manual com `seed_demo` (dono AutoStar compara Matriz×Filial; Essencial continua gateado; SDR só vê o dele).
**Commits:** por sub-item (4.1+4.2 juntos; 4.3+4.4; 4.5; 4.6), sempre API→develop e web→release/new-web.

---

## FASE 5 — Features novas (~4-5 dias)

### 5.1 Planos de Ação como roadmap (item 9)
- Migrations: `action_plans.due_date DATE NULL`, `action_plans.responsible_ids JSONB NULL`; tabela nova `action_plan_steps (id, plan_id FK ON DELETE CASCADE, title, description, due_date, done BOOL DEFAULT false, sort_order INT)`.
- Módulo `action_plans`: ORM/repos + CRUD aninhado `GET/POST/PATCH/DELETE /action-plans/{id}/steps`; response do plano inclui steps ordenados + nomes dos responsáveis.
- Web `/planos-acao`: card com badge de prazo (≤7 dias amarelo · vencido vermelho · concluído neutro) e progresso `X/Y etapas`; modal com prazo, multi-seleção de responsáveis (equipe da loja) e lista de etapas (checkbox, título, descrição, prazo).
- Testes: CRUD de steps, cascade no delete, papéis.

### 5.2 Tela Desempenho de Colaboradores (item 10)
- API: `GET /metrics/team-performance?store_id&from&to` — **portar 1:1** `trivus/lib/crmTeamMetrics.js` (`buildCrmTeamPerformanceData`): Leads→`assigned_to` por criação; Agendamentos→`vendedor_id||agendado_por` pela data de marcação; Comparecimentos→`vendedor_id` por `data_compareceu`; Fechamentos+receita/rentabilidade→`vendedor_id` pela data de fechamento. Resposta por usuário: contadores + `receita, rentabilidade, ticket_medio, share_faturamento_pct` + rankings prontos (top3_vendas, top3_sdrs, mais_fechou).
- Web: rota nova `src/app/(app)/desempenho/page.tsx` + item no nav (`src/lib/nav.ts`, featureKey do serviço metrics, papel de gestão): pódio TOP 3 vendas e TOP 3 SDRs, tabela por cargo (rótulos de `shop_role_labels` da loja), rosca de participação no faturamento (PieChart innerRadius) e radar comparando até 5 colaboradores (RadarChart), filtro de período; dono também filtra loja. SDR não acessa.
- Testes: agregações conferidas contra o seed, papéis.

**Aceite F5:** suíte verde; desempenho confere com os leads do seed; plano de ação com etapas funcionando ponta a ponta.

---

## FASE 6 — Meta Ads: ativar a conexão + funil de mídia (SPEC B3, ~1 dia de código)

### ⚠️ O QUE JÁ EXISTE (NÃO REIMPLEMENTAR — conferido no código em 23/07)

O módulo `src/modules/integrations/meta/` está **completo e hexagonal**:

| Peça | Arquivo | Estado |
|---|---|---|
| Porta (interface) | `domain/client.py` — `MetaAdsClient`, `DailyInsight` | ✅ pronto |
| **Cliente REAL da Graph API** | `infrastructure/http_client.py` — `GET /v21.0/{ad_account}/insights` com `level=campaign`, `time_increment=1`, `fields=campaign_id,spend,impressions,clicks`, token no header | ✅ pronto |
| Cliente mock determinístico | `infrastructure/mock_client.py` | ✅ pronto |
| Chaveamento real×mock | `interface/deps.py` — HTTP se `META_ENABLED=true`, senão mock | ✅ pronto |
| Endpoint de sync | `interface/router.py` — `POST /integrations/meta/sync` (protegido por `require_meta_token`) | ✅ pronto |
| Use case | `application/sync.py` — agrupa por loja, chama o client, faz upsert | ✅ pronto |
| Migration `c7f4b2e918d5` | `marketing_campaigns.meta_campaign_id`, `stores.meta_ad_account_id`, tabela `campaign_daily_spend (spend, **impressions**, **clicks**)` + UNIQUE(campaign_id, reference_date) | ✅ aplicada |
| Env vars | `.env.example`: `META_ENABLED=false`, `META_ACCESS_TOKEN=` | ✅ documentadas |

**As colunas `impressions` e `clicks` JÁ EXISTEM e o client real JÁ as busca** — NÃO criar migration para isso.

### O QUE FALTA (o trabalho real desta fase)

**6.1 UI para preencher os IDs da Meta (não existe no front — bloqueia tudo)**
- Tela **Lojas** (`src/app/(app)/lojas/page.tsx`): campo "ID da conta de anúncios Meta" (`meta_ad_account_id`, formato `act_123456789`). O backend já aceita (o campo está em `_UPDATABLE` de `stores/infrastructure/repository.py`).
- Tela **Campanhas** (`src/app/(app)/campanhas/page.tsx`): campo "ID da campanha na Meta" (`meta_campaign_id`) no create/edit; conferir se o schema da API já expõe e adicionar se faltar.
- Sem esses dois IDs preenchidos, o sync não tem o que buscar.

**6.2 Agendamento do sync (hoje é manual)**
- `POST /integrations/meta/sync` só roda se alguém chamar. Configurar **n8n (ou cron do Coolify)** para chamar 1×/dia de madrugada, com o header do token (`require_meta_token`).
- Opcional: botão "Sincronizar agora" na tela de Marketing/Lojas para o admin forçar.

**6.3 Consumir impressions/clicks no funil de mídia (SPEC B3)**
- API: expor impressões/cliques agregados do período no endpoint de marketing (a fonte `campaign_daily_spend` já tem os dados).
- Web Marketing: card "Funil de Marketing" (Impressões → Cliques → Leads → Leads Qualificados via `fixed-funnel` sem accent) + lista de taxas ao lado; loja sem Meta → estado vazio "Conecte a Meta Ads para ver impressões e cliques". ("Sessões"/GA fora de escopo.)
- Teste: sync mock grava impressions/clicks; endpoint agrega; loja sem Meta → payload vazio limpo.

**6.4 Ativação em produção (não é código — é do Giovani/cliente, roda em paralelo)**
Ver `docs/INTEGRACAO_META.md`. Caminho crítico de PRAZO (semanas):
1. Business Manager da Trivus verificado (CNPJ);
2. App tipo *Business* + produto *Marketing API*;
3. Contas de anúncio dos clientes compartilhadas com o BM da Trivus;
4. **System User** com permissão `ads_read` → gerar token (não expira);
5. **App Review / Advanced Access** para ler contas de vários clientes em escala;
6. Setar `META_ENABLED=true` + `META_ACCESS_TOKEN=<token>` nos secrets do Coolify e reiniciar.

> Enquanto 6.4 não sai, **tudo funciona com o mock** (`META_ENABLED=false`): dá para
> desenvolver, testar e demonstrar o funil de mídia ponta a ponta sem token da Meta.

---

## Regras transversais (valem para TODAS as fases)

1. **Branches:** API → `develop` · Web → `release/new-web`. NUNCA legacy/main/master.
2. **Qualidade:** nenhum commit com pytest/ruff/mypy ou lint/build vermelhos. Endpoints novos SEMPRE com validação de acesso (store/papel) e teste e2e de 403.
3. **Sem N+1** nas agregações novas (uma query com GROUP BY; conferir com o seed ~250 leads).
4. **Erros de input → 4xx** (nunca 500): datas/dinheiro validados como já é padrão (`_coerce_dates`).
5. **Semáforo:** usar SEMPRE `goalStatus` (≥95/80–95/<80). **Origens:** usar SEMPRE `ORIGIN_LABELS`.
6. **Migrations:** uma por mudança, nome descritivo; `alembic upgrade head` roda no boot do container.
7. Ao final de cada fase: rebuild dos containers (`deploy/`, portas 3010/3011/5443) e smoke test manual com os usuários do seed (`admin@trivus.local/admin123`, donos e equipe `demo123`).
8. Docs vivos: se um comportamento divergir do previsto, atualizar este plano e o doc de origem no mesmo commit.

## Mapa de dependências entre fases

```
F1 (visual) ─────────────────────────┐
F2 (backend pequeno) ── 2.1 goals ───┼──► F4 (usa classified + goalStatus + fixed-funnel)
F3 (permissões) ─────────────────────┤
F4 (multi-loja/mkt/rel/proj) ────────┼──► F5.2 (desempenho reusa agregações por usuário)
F5 (planos de ação + desempenho)     │
F6 (Meta) — independente, só precisa do módulo integrations/meta existente
```
Obs.: se preferir, implementar o backend da F5.2 (agregação por usuário) ANTES de 4.5 e reusar na tabela por vendedor do gerente.

## Checklist de entrega final
- [ ] F1 visual (paleta, toastify, colunas, multi-filtro, rótulos)
- [ ] F2 (classified em goals, data na etapa, funil c/ classificados, agenda vendedor+modal)
- [ ] F3 (flag de edição, visibilidade total, loja+gerentes, loja sem empresa)
- [ ] F4 (dashboard multi-loja, marketing B1/B2/B4, painel executivo, projeções)
- [ ] F5 (planos de ação roadmap, tela desempenho)
- [ ] F6 (impressões/cliques Meta)
- [ ] Suíte completa verde + smoke test com seed em cada papel
