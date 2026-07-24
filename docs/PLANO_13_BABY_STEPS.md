# Plano 13 — BABY STEPS (roteiro de execução passo a passo)

> Decomposição executável do `PLANO_13_AJUSTES_POS_REUNIAO.md`. Regras de negócio em
> `AJUSTES_POS_REUNIAO_CLIENTE.md`; designs em `SPEC_MARKETING_RELATORIOS.md`.
> **Execute UM passo por vez, na ordem.** Cada passo: fazer → verificar → commitar → próximo.
> Nunca misture dois passos num commit. Nunca pule a verificação.

## Convenções deste arquivo

- **API** = repo `trivus-api` (branch `develop`) · **WEB** = repo `trivus-web` (branch `release/new-web`).
- **CHECK-API** = `uv run pytest -q && uv run ruff check . && uv run mypy src` (tudo verde).
- **CHECK-WEB** = `npm run lint && npm run build` (tudo verde).
- **DB local**: Postgres do compose em `localhost:5443` → para testes: `DATABASE_URL=postgresql+asyncpg://trivus:trivus@localhost:5443/trivus uv run pytest -q`. Migrations: `uv run alembic upgrade head` (mesma env var).
- **App local**: `cd trivus-api/deploy && docker compose up -d --build api web` → web http://localhost:3010, api http://localhost:3011. Seed: `uv run python -m scripts.seed_demo`. Logins: `admin@trivus.local/admin123`; donos `carlos|marina|rafael@trivus.local` e equipe (`gerente.gerente.<slug>@trivus.local` etc.) senha `demo123`.
- Antes de editar um arquivo pela primeira vez, **leia-o**. Se algo citado aqui não existir com o nome exato, procure o equivalente (grep) — os nomes de módulos são estáveis, os de funções podem variar.
- Se um passo ficar ambíguo ou impossível: **NÃO improvise.** Registre em `trivus-api/docs/DUVIDAS_PLANO13.md` (crie se não existir: número do passo + dúvida + o que você faria), pule para o próximo passo INDEPENDENTE e siga.

---

## ETAPA 0 — Preparação

**S0.1 — Baseline.** Leia os 3 docs citados no topo. Confirme as branches (`git branch --show-current`): API=`develop`, WEB=`release/new-web`. Rode CHECK-API e CHECK-WEB. Tudo verde? Siga. Algo vermelho? PARE e registre em DUVIDAS.
**S0.2 — Ambiente.** Suba o compose, rode `alembic upgrade head` e o seed. Faça login como admin em http://localhost:3010. Não commita nada.

---

## ETAPA 1 — Visual (WEB apenas)

**S1.1 — Paleta dark.** `src/app/globals.css`: no tema dark, troque o valor dos tokens dourados (`--gold`, `--goldt` e variações) por branco `#F4F6FA` / branco suave. NÃO renomeie classes/tokens. Ajuste a cor do TEXTO sobre `btn-gold` para escuro (contraste). Verificar: CHECK-WEB + abrir o app no tema dark (botões, chips, links legíveis). Commit: `feat(ui): paleta dark com destaque branco`.

**S1.2 — Paleta light.** Mesmo arquivo, tema light: troque os tokens dourados por azul (use o azul do fundo do tema dark como referência de matiz; `--goldt` num tom mais escuro para contraste de texto). Verificar: CHECK-WEB + app no tema light. Commit: `feat(ui): paleta light com destaque azul`.

**S1.3 — Toastify base.** `npm i react-toastify`. No layout do grupo `(app)` (`src/app/(app)/layout.tsx`), importe o CSS e monte `<ToastContainer position="top-right" autoClose={10000} theme="colored" />`. Verificar: CHECK-WEB. Commit: `feat(ui): react-toastify montado no layout`.

**S1.4 — Toastify no CRM.** Em `src/app/(app)/crm/page.tsx` (mutation `move`) e `src/components/crm/lead-drawer.tsx` (validações): troque a notificação de erro de movimentação por `toast.error(...)` do react-toastify, nomeando o lead e os campos: `"<nome>" não pode ir para <ETAPA>: falta <campos>.` O toast interno (`components/ui/toast.tsx`) continua no resto do app. Verificar: CHECK-WEB + arrastar um card incompleto → toast vermelho no topo-direita por 10s. Commit: `feat(crm): toast de validação com react-toastify`.

**S1.5 — Colunas coloridas.** `crm/page.tsx`: fundo de cada coluna = `DOT_COLORS[i]` com ~8% de opacidade (ex.: `color-mix(in srgb, <cor> 8%, transparent)` via style). Conferir nos 2 temas. Verificar: CHECK-WEB. Commit: `feat(crm): fundo colorido por coluna`.

**S1.6 — Filtro multi-colunas.** `crm/page.tsx`: estado `stageFilter: string` vira `stageFilters: string[]`; troque o `<select>` por um dropdown de checkboxes (popover simples). Board: `stages.filter(st => stageFilters.length === 0 || stageFilters.includes(st.id))`. Verificar: CHECK-WEB + selecionar 2-3 colunas. Commit: `feat(crm): filtro por múltiplas colunas`.

**S1.7 — Rótulos de origem.** Crie `src/lib/origin-labels.ts`: `export const ORIGIN_LABELS: Record<string,string> = { receptivo: "Marketing", prospeccao: "Prospecção Ativa", outros: "Outras Mídias" }`. Substitua os rótulos EXIBIDOS (nunca os valores enviados à API) em: Metas, Lançamento, Relatórios, Projeções, Marketing (grep por "receptivo"/"Receptivo" em `src/app/(app)/`). Verificar: CHECK-WEB + conferir as 5 telas. Commit: `feat(ui): rótulos de origem centralizados`.

**S1.8 — Total nas Metas.** `src/app/(app)/metas/page.tsx`: linha "Total" readonly com estilo opaco somando, por métrica, os valores das 3 origens em tempo real. Verificar: CHECK-WEB. Commit: `feat(metas): linha de total somando as origens`.

---

## ETAPA 2 — Backend pequeno

**S2.1 — Migration classified em goals.** API: nova migration Alembic seguindo o padrão de `migrations/versions/` (`op.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS classified_quantity int")`). Rode `alembic upgrade head`. Verificar: CHECK-API. Commit: `feat(goals): migration classified_quantity`.

**S2.2 — Goals expõe classified.** Módulo `src/modules/goals/` (ORM, schema, repo, router): aceitar/retornar `classified_quantity` no upsert e no GET. Teste e2e: upsert com o campo → GET devolve. Verificar: CHECK-API. Commit: `feat(goals): meta de classificados`.

**S2.3 — Metas front: campo Classificados.** WEB `metas/page.tsx`: campo "Classificados" entre Leads e Qualificados (entra no Total do S1.8). Verificar: CHECK-WEB. Commit: `feat(metas): campo classificados`.

**S2.4 — stage_entered_at no board.** API `crm/infrastructure/repositories.py` → `list_for_board`: adicionar `stage_entered_at` por lead via UMA subquery agregada (MAX(`entered_at`) em `crm_lead_stage_history` onde `stage_id` = etapa atual do lead) — join, sem loop. Teste e2e: criar lead → mover → `stage_entered_at` muda. Verificar: CHECK-API. Commit: `feat(crm): data de entrada na etapa no payload do board`.

**S2.5 — Card mostra dd/mm.** WEB `crm/page.tsx`: no card, trocar `daysSince(...)` por `fmtDay(lead.stage_entered_at)` (helper existe; adicione o campo ao tipo `Lead` em `src/lib/types.ts`). Verificar: CHECK-WEB. Commit: `feat(crm): card exibe data de entrada na etapa`.

**S2.6 — Funil com CLASSIFICADOS.** API módulo `metrics`: incluir a etapa CLASSIFICADOS no funil do dashboard e na lista de taxas (fonte: StageReachReader / `crm_lead_stage_history`; grep "QUALIFICADOS" no módulo para achar a sequência). Teste: resposta contém a etapa e a taxa Leads→Classificados. Verificar: CHECK-API. Commit: `feat(metrics): classificados no funil e taxas`.

**S2.7 — goalStatus helper.** WEB: crie `src/lib/goal-status.ts`: `goalStatus(realizado: number, meta: number): "green"|"amber"|"red"` — meta inválida/ausente (`<=0`) → `"amber"`; senão pct = realizado/meta: `>=0.95` green, `>=0.80` amber, senão red. Verificar: CHECK-WEB. Commit: `feat(ui): helper goalStatus (95/80)`.

**S2.8 — Componente fixed-funnel.** WEB: crie `src/components/charts/fixed-funnel.tsx` — SVG com 6 trapézios de larguras FIXAS (topo→base por faixa: 100→86, 86→72, 72→56, 56→40, 40→22, 22→14 em % do viewBox; alturas iguais), degradê de azul (topo ~#33517E clareando), última faixa em cor de destaque quando `accentLast`, texto central `label  value` (value bold; branco nas faixas escuras). Props: `steps: {label: string; value: number}[]`, `accentLast?: boolean`. Verificar: CHECK-WEB. Commit: `feat(charts): funil SVG de forma fixa`.

**S2.9 — Dashboard usa o funil fixo.** WEB `dashboard/page.tsx`: substituir o funil atual pelo `FixedFunnel` com as 6 etapas (Leads, Classificados, Qualificados, Agendados, Comparecidos, Vendas — dados do S2.6). Painel de taxas continua ao lado. Verificar: CHECK-WEB + visual conferido (funil azul, Vendas em destaque). Commit: `feat(dashboard): funil de conversão fixo com classificados`.

**S2.10 — Agenda backend: vendedor.** API `src/modules/agenda/`: `GET /agenda` aceita `vendedor_id` opcional (filtra `vendedor_id` OU `agendado_por`); cada item da resposta ganha `vendedor_nome` (join com users — sem N+1). Teste e2e. Verificar: CHECK-API. Commit: `feat(agenda): filtro por vendedor + nome no payload`.

**S2.11 — Team GET para gerente.** API `src/modules/users/interface/router.py`: `GET /stores/{store_id}/team` — além de admin/client, permitir shop_user com `shop_role == "gerente"` E `parent_store_id == store_id` (buscar o user no repo para checar o shop_role; senão 403). Teste e2e: gerente lê a própria loja (200) e outra (403). Verificar: CHECK-API. Commit: `feat(users): gerente lê a equipe da própria loja`.

**S2.12 — Agenda front.** WEB `agenda/page.tsx`: (a) dropdown "Vendedor" (query `GET /stores/{storeId}/team`, visível para dono/admin/gerente) passando `vendedor_id` à API; (b) coluna "Vendedor" na visão lista; (c) clique na linha (lista) ou no item do dia (calendário) abre o `LeadDrawer` daquele lead. Verificar: CHECK-WEB + testar no app. Commit: `feat(agenda): filtro por vendedor, coluna e modal de detalhes`.

---

## ETAPA 3 — Permissões (CRM + lojas/empresas)

**S3.1 — Migration flag de edição.** API: migration `users.can_edit_others_leads BOOLEAN NOT NULL DEFAULT false`. `alembic upgrade head`. Verificar: CHECK-API. Commit: `feat(users): migration can_edit_others_leads`.

**S3.2 — Users expõe a flag.** Módulo `users`: create/update de team user aceita `can_edit_others_leads`; GET do team retorna. Entidade `User` do auth (`auth/domain/entities.py` + repository) carrega o campo. Teste. Verificar: CHECK-API. Commit: `feat(users): flag can_edit_others_leads no CRUD de equipe`.

**S3.3 — Leitura liberada + nome do responsável.** API `crm/application/leads.py` (`ListLeadsUseCase`): REMOVER a restrição de leitura por papel — todo usuário com acesso à loja vê TODOS os leads (o param `assigned_to` continua como filtro opcional). Em `list_for_board`, incluir `assigned_to_name` (join com users, sem N+1). ATENÇÃO: `tests/e2e/test_crm_visibility.py` vai quebrar — ajuste-o NESTE MESMO passo para a nova regra de leitura. Verificar: CHECK-API. Commit: `feat(crm)!: leitura do board liberada para toda a equipe da loja`.

**S3.4 — Guard de escrita.** API: crie `crm/application/edit_guard.py` com `async def assert_can_edit_lead(user, lead, users_repo)`: se `user.role == "shop_user"` e o user (buscado no repo) NÃO é gerente e NÃO tem `can_edit_others_leads` e `lead["assigned_to"] != user.user_id` e `lead["vendedor_id"] != user.user_id` → `ForbiddenError("Este lead pertence a outro colaborador. Peça autorização ao gerente.")`. Aplique no router do CRM em: PATCH `/crm/leads/{id}`, `/stage`, `/agendamento`, `/compareceu`, `/fechamento`, DELETE. Testes e2e novos em `test_crm_visibility.py`: sdr sem flag não move lead do colega (403) mas move o próprio; sdr com flag move; gerente sempre move. Verificar: CHECK-API. Commit: `feat(crm): edição de leads de terceiros exige autorização`.

**S3.5 — Front: toggle + UX de bloqueio.** WEB: (a) `usuarios/page.tsx`: checkbox "Pode editar leads de outros colaboradores" no form de equipe (visível só para admin/dono/gerente); (b) `crm/page.tsx`: exibir o filtro "Responsável" para TODOS os papéis usando `assigned_to_name` do payload; 403 no move/patch → toast de erro com a mensagem da API. Verificar: CHECK-WEB + roteiro manual (sdr vê tudo, não move o alheio; gerente concede flag; sdr passa a mover). Commit: `feat(crm/usuarios): flag de edição + board visível para todos`.

**S3.6 — Loja + gerentes (backend).** API `stores`: `POST /admin/stores` aceita `managers: [{email, password, name}]` opcional; use case cria loja e, na mesma sessão, cria cada gerente via a lógica de create team user (`shop_role="gerente"`). Teste: criar loja com 2 gerentes → team tem os 2. Verificar: CHECK-API. Commit: `feat(stores): criação de loja com gerentes`.

**S3.7 — Loja + gerentes (front) + POST team p/ gerente + esconder botão.** WEB `lojas/page.tsx`: seção "Gerentes" no modal de nova loja (lista dinâmica nome/email/senha, mínimo 1, validado no front). API: `POST /stores/{id}/team` liberado para gerente da própria loja (mesmo guard do S2.11) + teste. WEB `usuarios/page.tsx`: esconder "Adicionar colaborador" quando o logado é shop_user não-gerente. Verificar: CHECK-API + CHECK-WEB. Commits: API `feat(users): gerente cria equipe da própria loja`; WEB `feat(lojas/usuarios): gerentes na criação + botão oculto p/ SDR`.

**S3.8 — Loja sem empresa (Opção A).** API `src/modules/ecosystem/`: no resolvedor de entitlements/feature_keys da loja, quando `company_id IS NULL` → retornar a UNIÃO das feature_keys de TODOS os serviços de software ativos (equivalente ao Full), ignorando assinatura. Em `application/store_services.py`: remover o raise "Loja sem empresa vinculada (modo legado)". Testes: loja sem empresa acessa `/crm/leads`, `/metrics/*`, `/campaigns` (200); loja de empresa SUSPENSA continua bloqueada. Verificar: CHECK-API. Commit: `feat(ecosystem): loja sem empresa opera com acesso padrão completo`.

---

## ETAPA 4 — Multi-loja, Marketing, Relatórios, Projeções

**S4.1 — Helper store_ids.** API `src/shared/interface/store_access.py`: adicionar `require_store_ids_access` — lê `store_ids` (query repetida); vazio → todas as lojas acessíveis do usuário; valida TODAS via `GetAccessibleStoreIdsUseCase` (qualquer uma fora → 403); retorna a lista efetiva. Teste. Verificar: CHECK-API. Commit: `feat(shared): validação de múltiplas lojas`.

**S4.2 — Dashboard multi-loja (backend).** API `metrics`: os endpoints do dashboard (KPIs, funil, série 12m — INSPECIONE `metrics/interface/router.py` para os nomes reais) ganham variante `store_ids` retornando `{consolidated, by_store: [{store_id, store_name, ...}]}`. MANTENHA `store_id` single funcionando (compat). Consolidado: somas; ticket médio = Σreceita/Σfechamentos. Reader: uma query com GROUP BY store_id. Testes: dono 2 lojas = soma; id alheio 403. Verificar: CHECK-API. Commit: `feat(metrics): dashboard consolidado por múltiplas lojas`.

**S4.3 — Dashboard multi-loja (front).** WEB `dashboard/page.tsx`: com `stores.length > 1`, seletor multi-loja (checkboxes, padrão todas); KPIs usam `consolidated`; série e gráficos plotam uma série por loja (legenda = nome). Com 1 loja: igual hoje. Verificar: CHECK-WEB + login carlos. Commit: `feat(dashboard): comparação entre lojas`.

**S4.4 — Séries de marketing (backend).** API: novo `GET /metrics/marketing/series?store_id&from&to` → `{days: [{date, leads, classificados, qualificados, agendados, comparecidos, vendas, investimento}], totals, previous_totals}` (previous = janela anterior de mesma duração). Fontes: `daily_indicators` + o InvestmentReader que o marketing já usa. Guard `require_store_access`. Teste e2e. Verificar: CHECK-API. Commit: `feat(metrics): série diária de marketing com comparativo`.

**S4.5 — KPI cards (front).** WEB `marketing/page.tsx`: grade de 12 cards (Leads, CPL, Classificados, Custo/Classificado, Qualificados, Custo/Qualificado, % Qualificados, Agendados, Comparecidos, Vendas, CAC, Investimento): valor grande, badge de variação vs `previous_totals` (**custos: cair = verde**; sem base = "N/A"), "X no período anterior", sparkline de área da série. Verificar: CHECK-WEB. Commit: `feat(marketing): cards de KPI com sparkline e comparativo`.

**S4.6 — Gráficos de linha (front).** WEB `marketing/page.tsx`: dois LineCharts — "Investido vs Leads" e "Leads vs Leads Qualificados" (série do S4.4; pontos, tooltip dd/mm/aa, legenda). Verificar: CHECK-WEB. Commit: `feat(marketing): gráficos diários investido×leads`.

**S4.7 — Funil meta×realizado (backend).** API (onde vive o funil de custos hoje — grep "CPL"/"cpl"/"cost"): estender a resposta por etapa para `{stage, meta, realizado, pct_meta, custo_unit, conv_prev_pct}`. Metas: `goals` origem `receptivo` (com classified), proporcional ao período (meta × dias_do_período ÷ dias_do_mês). Custo: investimento ÷ realizado (null se 0). Teste e2e. Verificar: CHECK-API. Commit: `feat(marketing): funil de custos com meta, % e conversão por etapa`.

**S4.8 — Funil meta×realizado (front).** WEB `marketing/page.tsx`: card "Funil receptivo geral" conforme SPEC B1 — meio-funil cinza espelhado (META, números à esquerda), centro (bolinha `goalStatus` + nome CAPS + `↓ X% da etapa anterior`), meio-funil azul (REALIZADO · CUSTO: número bold + chip "% da meta" + chip "R$ custo"), legenda ≥95/80–95/<80, nota "prospecção ativa não entra no cálculo de custo", rodapé explicativo. Meio-funis em SVG fixo. Checkboxes de etapas visíveis (o ↓% recalcula entre visíveis adjacentes — no front). Verificar: CHECK-WEB + comparar com o design. Commit: `feat(marketing): funil meta×realizado com semáforo e filtro de etapas`.

**S4.9 — Projeções (backend).** API `metrics/projections`: incluir `classified`; separar por origem + `total`; aceitar `store_ids` (S4.1) e `user_id` — **shop_user comum: IGNORAR o user_id recebido e forçar o próprio** (gerente pode passar qualquer um da própria loja). Regras de atribuição por usuário: leads=`assigned_to` (created_at); agendamentos=`vendedor_id`||`agendado_por` (data_marcacao); comparecimentos/fechamentos=`vendedor_id`. Testes: sdr recebe só o próprio mesmo passando id alheio. Verificar: CHECK-API. Commit: `feat(metrics): projeções por origem, loja e colaborador`.

**S4.10 — Projeções (front).** WEB `projecoes/page.tsx`: semáforo `goalStatus` em cores FORTES; blocos por origem (ORIGIN_LABELS) + total; seletor de lojas (dono/admin), de colaborador (gerente); shop_user comum vê só os próprios. Verificar: CHECK-WEB + conferir como carlos, gerente e sdr. Commit: `feat(projecoes): semáforo forte, origens e escopo por papel`.

**S4.11 — Executive (backend, números).** API: novo `GET /metrics/executive?store_ids&year&month` (guard S4.1): `dias {uteis, trabalhados, restantes}` (útil = seg-sáb; trabalhados = úteis decorridos se mês corrente, senão todos), `kpis {faturamento, meta, pct_meta, projecao, pct_projecao, lucro_projetado, margem_media, ticket_medio, fechamentos, conversao}`, `by_store [{store_id, nome, faturamento, meta, pct_meta, ticket_medio, lucro_projetado, margem, status}]`. Fórmulas: projeção = faturamento/trabalhados×úteis (0 se trabalhados=0); margem = Σrentabilidade/Σreceita; lucro_projetado = projeção×margem; conversão = fechamentos/Σleads (daily_indicators). Fontes: `crm_funnel_leads` (por `data_fechou_negocio` no mês), `goals.profitability_goal`. Divisões protegidas (nunca 500). Teste e2e. Verificar: CHECK-API. Commit: `feat(metrics): endpoint executivo (kpis + por loja)`.

**S4.12 — Executive (backend, análises).** Mesmo endpoint: `charts {faturamento_meta, ranking, ticket_medio, comprados_vendidos (contagens por data_comprado/data_fechou_negocio no mês), lucro_projetado, margem}`, `gauge {pct_meta}`, `ritmo {media_diaria_atual, media_diaria_necessaria, forecast_pct: min(99, round(projecao/meta*100))}`, `resumo: [strings]` ("X% da meta atingida", "Projeção: R$ Y", "Unidade destaque: Z", "Unidade que exige atenção: W", "Necessário ~R$ V/dia"), `tops {destaques: top3 faturamento, atencao: bottom3 margem}`. Teste. Verificar: CHECK-API. Commit: `feat(metrics): executivo com gráficos, gauge, ritmo, resumo e tops`.

**S4.13 — Painel Executivo (front, estrutura).** WEB `relatorios/page.tsx`: REESCREVER como o painel: cabeçalho (título + seletor mês/ano + 3 mini-infos de dias), 8 KPI cards (com barras de % e mini-donut de margem), tabela por unidade com heatmap no % Meta e linha TOTAL. Dono/admin: seletor multi-loja. Verificar: CHECK-WEB + conferir com o print da planilha. Commit: `feat(relatorios): painel executivo — cabeçalho, kpis e tabela`.

**S4.14 — Painel Executivo (front, gráficos).** Mesma tela: 6 gráficos Recharts (faturamento×meta + linha tracejada de projeção; ranking horizontal; ticket médio; comprados×vendidos; lucro projetado; donut de margem com lista). Verificar: CHECK-WEB. Commit: `feat(relatorios): grade de gráficos do executivo`.

**S4.15 — Painel Executivo (front, rodapé + escopo).** Mesma tela: gauge semicircular (PieChart 180° + agulha SVG girada pelo pct), ritmo (média atual/necessária/forecast), resumo executivo (bullets do backend), TOP 3 destaques/atenção. **SDR/vendedor não vê o painel** — mostrar versão "meus números" (KPIs próprios via projeções com escopo próprio). Verificar: CHECK-WEB + testar como sdr. Commit: `feat(relatorios): gauge, ritmo, resumo e tops + versão restrita p/ SDR`.

---

## ETAPA 5 — Features novas

**S5.1 — Migrations plano de ação.** API: migration única — `action_plans.due_date DATE NULL`, `action_plans.responsible_ids JSONB NULL`, e `CREATE TABLE action_plan_steps (id uuid PK DEFAULT gen_random_uuid(), plan_id uuid NOT NULL REFERENCES action_plans(id) ON DELETE CASCADE, title text NOT NULL, description text, due_date date, done boolean NOT NULL DEFAULT false, sort_order int NOT NULL DEFAULT 0)`. Verificar: CHECK-API + upgrade head. Commit: `feat(action-plans): migrations prazo, responsáveis e etapas`.

**S5.2 — Steps CRUD (backend).** Módulo `action_plans`: ORM do step; `GET/POST /action-plans/{id}/steps`, `PATCH/DELETE /action-plans/{id}/steps/{step_id}`; o list de planos inclui `due_date`, `responsible_ids`, `responsible_names` (join users) e `steps` ordenados. Testes: CRUD + cascade. Verificar: CHECK-API. Commit: `feat(action-plans): etapas com prazo (CRUD)`.

**S5.3 — Planos de ação (front).** WEB `planos-acao/page.tsx`: badge de prazo no card (sem prazo = nada; concluído = neutro; vencido = vermelho; ≤7 dias = amarelo) + progresso "X/Y etapas"; modal com data limite, multi-seleção de responsáveis (GET team) e lista de etapas (título, descrição, prazo, done, adicionar/remover). Verificar: CHECK-WEB + fluxo completo. Commit: `feat(planos-acao): roadmap com prazo, responsáveis e etapas`.

**S5.4 — Team performance (backend).** API `metrics`: novo `GET /metrics/team-performance?store_id&from&to` (gerente/dono/admin; shop_user comum → 403). Agregação por usuário sobre `crm_funnel_leads` — REGRAS EXATAS (portadas de `trivus/lib/crmTeamMetrics.js` do legado): leads → `assigned_to` pela `created_at`; agendamentos → `vendedor_id` OU (se null) `agendado_por`, pela `data_marcacao_agendamento`; comparecimentos → `vendedor_id`, pela `data_compareceu` (com `compareceu_agendamento=true`); fechamentos/receita/rentabilidade → `vendedor_id`, pela `data_fechou_negocio` (com `fechou_negocio=true`). Resposta: `users: [{user_id, nome, shop_role, leads, agendamentos, comparecimentos, fechamentos, receita, rentabilidade, ticket_medio, share_faturamento_pct}]` + `rankings {top3_vendas, top3_sdrs (por agendamentos), mais_fechou}`. Teste e2e com leads criados no próprio teste. Verificar: CHECK-API. Commit: `feat(metrics): desempenho por colaborador`.

**S5.5 — Tela Desempenho (front).** WEB: nova rota `src/app/(app)/desempenho/page.tsx` + entrada no nav (`src/lib/nav.ts`, featureKey `metrics.team`, oculta para shop_user comum): pódio TOP 3 vendas + TOP 3 SDRs, tabela por cargo (rótulos de cargo da loja), rosca de participação no faturamento (PieChart innerRadius, % por vendedor), radar comparando até 5 colaboradores (RadarChart, eixos normalizados), filtro de período. Verificar: CHECK-WEB + números vs seed. Commit: `feat(desempenho): tela de performance da equipe`.

**S5.6 — Executivo por vendedor (gerente).** API: `GET /metrics/executive` chamado por gerente (loja única) inclui `by_user` reutilizando a agregação do S5.4 (mesmas colunas, por vendedor). WEB `relatorios`: para gerente, a tabela mostra vendedores. Teste papel. Verificar: CHECK-API + CHECK-WEB. Commit: `feat(relatorios): tabela executiva por vendedor para o gerente`.

---

## ETAPA 6 — Meta Ads

> ⚠️ O backend da Meta JÁ ESTÁ PRONTO (client real busca spend+impressions+clicks; colunas existem — migration `c7f4b2e918d5`). NÃO criar migrations nem reimplementar `integrations/meta`.

**S6.1 — UI dos IDs.** WEB: `lojas/page.tsx` — campo "Conta de anúncios Meta (act_...)" editando `meta_ad_account_id` (backend já aceita). `campanhas/page.tsx` — campo "ID da campanha na Meta" (`meta_campaign_id`); CONFIRA se os schemas do módulo `campaigns` da API expõem o campo (grep `meta_campaign_id`); se não, adicione ao schema/repo (SEM migration — a coluna existe). Verificar: CHECK-API (se tocou) + CHECK-WEB + salvar no app. Commit(s): `feat(lojas/campanhas): campos de vínculo com a Meta`.

**S6.2 — Agregado de mídia (backend).** API: expor impressões/cliques agregados do período (soma de `campaign_daily_spend.impressions/clicks` das campanhas da loja) num endpoint de marketing existente (ou no `/metrics/marketing/series`). Teste: rodar o sync mock (`POST /integrations/meta/sync` com o token de teste) → agregado retorna números. Verificar: CHECK-API. Commit: `feat(marketing): impressões e cliques agregados`.

**S6.3 — Funil de mídia (front).** WEB `marketing/page.tsx`: card "Funil de Marketing" — `FixedFunnel` (sem accent) com Impressões → Cliques → Leads → Leads Qualificados + lista "Taxa de Conversão por Etapa" ao lado. Impressões/cliques null/0 (Meta não conectada) → estado vazio "Conecte a Meta Ads para ver impressões e cliques." Verificar: CHECK-WEB. Commit: `feat(marketing): funil de mídia (Meta)`.

**S6.4 — Sync agendado (config, não código).** Documentar em `docs/INTEGRACAO_META.md` (seção nova) o job diário: n8n/cron chamando `POST /integrations/meta/sync` com o header do token às 04:00. NÃO implementar scheduler na API. Commit: `docs: agendamento do sync da Meta`.

---

## Encerramento

**S7.1 — Rebuild + smoke final.** `docker compose up -d --build api web`; seed; roteiro: admin (tudo), carlos (multi-loja/comparação), gerente (executivo por vendedor, desempenho, concede flag), sdr (vê tudo no CRM, não move alheio, projeções próprias, sem tela executiva). Registrar resultado em `docs/DUVIDAS_PLANO13.md`.
**S7.2 — Checklist.** Marcar o checklist do `PLANO_13_AJUSTES_POS_REUNIAO.md` e listar os itens pendentes de `DUVIDAS_PLANO13.md` para o Giovani.
