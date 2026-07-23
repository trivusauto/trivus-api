# Ajustes pós-reunião com o cliente — spec detalhada para implementação

> Documento para a sessão de IA que vai implementar. Contexto: monorepo `trivus-api`
> (FastAPI + Postgres, branch **develop**) + `trivus-web` (Next 16 App Router, branch
> **release/new-web**). Push SEMPRE nessas branches — NUNCA em legacy/main/master.
> Sistema legado para referência de paridade: pasta `trivus/` (Next 14 + Supabase).
> Rode `npm run lint && npm run build` no web e `uv run pytest && uv run ruff check . && uv run mypy src` na api antes de cada commit.
>
> Legenda de esforço: 🟢 pequeno (horas) · 🟡 médio (1-2 dias) · 🔴 grande (3+ dias).
> Itens marcados ⚠️ DECISÃO precisam de resposta do Giovani antes de codar.
> Itens marcados 📎 ASSET dependem de material que o cliente ainda vai mandar.
>
> **ATUALIZAÇÃO 23/07:** os assets dos itens 2, 5 e 6 CHEGARAM. Os itens 2, 5 e 6 estão
> agora detalhados em **`docs/SPEC_MARKETING_RELATORIOS.md`** (funil fixo da Visão Geral,
> tela de Marketing com funil meta×realizado/KPIs/linhas, e Relatórios como Painel
> Executivo multi-loja). Aquele doc também fixa o semáforo oficial: ≥95% verde ·
> 80–95% âmbar · <80% vermelho (substitui os limiares sugeridos nos itens 7 e 13.4).

---

## 0. Paleta de cores (global) — 🟢 viável, impacto visual amplo

**O que o cliente quer:**
- **Modo escuro:** manter o fundo azul atual, mas trocar o **dourado** de destaque por **branco**.
- **Modo claro:** manter o fundo em tons de branco, e trocar o dourado/laranja da fonte e destaques por **azul**.

**Como fazer:** os destaques são tokens CSS (`gold`, `goldt`, `btn-gold` etc.) em `trivus-web/src/app/globals.css`. NÃO renomear classes — apenas remapear os valores dos tokens por tema:
- tema dark: `--gold` → branco (ex.: `#F4F6FA`), `--goldt` → branco suave; garantir contraste do texto sobre `btn-gold` (texto do botão vira escuro).
- tema light: `--gold` → azul da marca (usar o azul do fundo dark como referência), `--goldt` → azul mais escuro para texto.

**Impacto:** afeta TODAS as telas (botões, chips, links, sinaleiros que usam dourado). Revisar contraste (WCAG AA) especialmente em botões e badges. Verificar gráficos (Recharts) que usam a cor de destaque.

---

## 1. Visão Geral (Dashboard) — visão consolidada + comparação entre lojas — 🔴 viável

**O que o cliente quer:** o dono da empresa (nível mais alto) deve poder ver os dados de **todas as suas lojas juntas** (leads, rentabilidade, ticket médio, funil, série 12m) e **comparar lojas** (selecionar uma ou mais para exibir lado a lado nos gráficos).

**Como fazer:**
1. **Backend:** os endpoints de métricas (módulo `src/modules/metrics/`) hoje recebem `store_id` único. Aceitar `store_ids` múltiplos (query param repetido). Regras:
   - validar cada id contra as lojas acessíveis do usuário (`GetAccessibleStoreIdsUseCase` — já existe em `src/modules/stores/application/get_accessible_stores.py`); id fora do escopo → 403.
   - resposta em dois formatos: `consolidated` (soma/média de tudo) e `by_store` (mesmas métricas por loja, para os gráficos comparativos).
2. **Front:** no dashboard, quando o usuário tem 2+ lojas (`stores` da sessão), mostrar um seletor multi-loja ("Todas as lojas" por padrão + checkboxes por loja). KPIs mostram o consolidado; gráficos ganham uma série por loja selecionada (linha/barra por loja, com legenda).
3. shop_user (1 loja) não vê o seletor — tela igual à atual.

**Impacto:** mexe nas queries do `metrics/infrastructure/reader.py` (agrupar por store_id). Cuidado com performance. Ticket médio consolidado = receita total ÷ fechamentos totais (não média das médias).

---

## 2. Funil de conversão — incluir CLASSIFICADOS + imagem do design — 🟢/🟡 viável · 📎 ASSET

**O que o cliente quer:**
- O funil de conversão e as taxas de conversão do dashboard devem incluir a etapa **CLASSIFICADOS** (hoje pula direto de recebidos para qualificados).
- Usar a **imagem de funil do design** como fundo fixo (a arte não muda; só os números mudam por cima).

**Como fazer:** o backend já mede "alcançou etapa" via `crm_lead_stage_history` (StageReachReader) — incluir CLASSIFICADOS na sequência do funil e nas taxas etapa-a-etapa. No front, montar o componente com a imagem fixa posicionada e os valores sobrepostos por etapa.

**Pendência:** 📎 falta o print/arquivo do design do funil. Implementar a lógica já com CLASSIFICADOS e deixar a imagem por último.

---

## 3. CRM / Kanban

### 3.1 Toast de campos faltando (react-toastify) — 🟢 viável
Hoje, ao mover um card sem os campos obrigatórios, aparece uma mensagem discreta no canto inferior. Trocar por **react-toastify**:
- posição **top-right**, tema **erro (vermelho)**, duração **10 segundos**, fechável.
- mensagem nomeando o card e os campos: ex. `"João Silva" não pode ir para AGENDADOS: falta data e horário do agendamento.`
- instalar `react-toastify`, montar o `<ToastContainer/>` no layout do app e usar nos erros de movimentação do CRM (mutation `move` em `src/app/(app)/crm/page.tsx` e nas validações do `lead-drawer.tsx`). O toast interno atual (`components/ui/toast.tsx`) continua nos demais lugares por enquanto — migrar só o CRM primeiro.

### 3.2 Cor de fundo por coluna — 🟢 viável
Cada coluna do kanban ganha um fundo levemente diferente (tint sutil) para separação visual sem precisar ler. Usar uma paleta fixa por índice de etapa (já existe `DOT_COLORS` no `crm/page.tsx` — derivar o fundo com a mesma cor a ~6-10% de opacidade). Garantir que funciona nos dois temas.

### 3.3 Data no card em vez de "há X dias" — 🟡 viável
Hoje o card mostra há quantos dias está na etapa (ex. `25d`). Trocar por **data (dd/mm)** em que o lead **entrou na etapa atual**.
- Backend: `GET /crm/leads` deve incluir `stage_entered_at` (buscar em `crm_lead_stage_history` o `entered_at` mais recente da etapa atual — join agregado, não N+1).
- Front: exibir `dd/mm` no card (helper `fmtDay` já existe).

### 3.4 Filtro por MÚLTIPLAS colunas — 🟢 viável
Hoje o filtro de coluna seleciona 1 coluna. Trocar por multi-seleção (ex.: ver só RECEBIDOS + CLASSIFICADOS + QUALIFICADOS). Front-only: trocar o `<select>` de `stageFilter` por um dropdown com checkboxes; estado vira `string[]`; board renderiza `stages.filter(st => sel.length === 0 || sel.includes(st.id))`.

### 3.5 Permissão de edição: ver tudo × mexer só no seu — 🟡 viável · ⚠️ DECISÃO
**O que o cliente quer:** usuário comum (SDR/vendedor) **vê o kanban inteiro**, mas uma **flag por usuário** (controlada pelo admin/gerente; o usuário não vê a flag) define se ele pode mexer nos cards dos colegas:
- flag **ativa** (restrito): vê tudo, mas só move/edita os cards atribuídos a ele;
- flag **desativada**: vê tudo e mexe em qualquer card.

**Como fazer:**
1. Migration: coluna `restrict_edit_to_own_leads BOOLEAN DEFAULT false` em `users`.
2. Backend: nos endpoints de escrita de lead (`PATCH /crm/leads/{id}`, `/stage`, `/agendamento`, `/compareceu`, `/fechamento`, `DELETE`) — se o usuário é shop_user com a flag ativa e `lead.assigned_to != user_id` (e `vendedor_id != user_id`), retornar 403 com mensagem amigável ("Este lead pertence a outro colaborador.").
3. Visibilidade de leitura: **todo shop_user passa a ver o quadro inteiro** (remover o filtro por `assigned_to` do `list_for_board`).
4. UI de gestão: na tela **Usuários**, o admin/dono/gerente vê o toggle "Pode editar leads de outros colaboradores" ao criar/editar membro da equipe.
5. Front CRM: com a flag ativa, cards de outros ficam com drag desabilitado + tooltip; drawer abre em modo leitura.

**⚠️ IMPACTO IMPORTANTE:** isso **substitui** a regra de visibilidade atual (que espelha o legado: SDR só vê os próprios leads — implementada em `ListLeadsUseCase`/`list_for_board` e travada por `tests/e2e/test_crm_visibility.py`). Os testes devem ser **reescritos** para a nova regra (todos veem; escrita restrita pela flag). Confirmar com o cliente que todo SDR pode VER os leads dos colegas — é mudança de privacidade interna. `can_see_unassigned_leads` continua existindo para o round-robin do webhook.

---

## 4. Agenda — 🟡 viável

**O que o cliente quer:**
1. **Filtro por vendedor** (usuário) na tela.
2. Na visualização em **lista**, uma coluna **"Vendedor"**.
3. Ao clicar num item (linha da lista ou info no card do dia no calendário), abrir uma **modal com os dados do agendamento** — igual ao drawer do CRM.

**Como fazer:**
- Backend (`src/modules/agenda/`): `GET /agenda` aceitar `vendedor_id` opcional (filtra por `vendedor_id`/`agendado_por`); resposta incluir `vendedor_nome` (join com users — evitar N+1).
- Front: dropdown de vendedor (mesma query de equipe `GET /stores/{id}/team` usada no CRM; para gerente ver a equipe, liberar esse endpoint para shop_user gerente da própria loja — guard `parent_store_id == store_id`); coluna Vendedor na lista; clique abre modal reaproveitando o `LeadDrawer` existente (`components/crm/lead-drawer.tsx`) em modo leitura/edição conforme a permissão do 3.5.

---

## 5. Marketing — 🟡 viável · 📎 ASSET

**O que o cliente quer:**
1. **Filtrar as etapas do funil de custos** — ex.: às vezes só quer ver "quantos chegaram × quantos fecharam", sem as etapas intermediárias.
2. Tomar como base o **print da planilha** que o cliente usa (referência de layout/métricas).

**Como fazer:** no funil de custos (CPL→CAC) do front, um seletor de etapas visíveis (checkboxes: Leads, Classificados, Qualificados, Agendados, Comparecimentos, Fechamentos). O cálculo continua o mesmo; o filtro oculta etapas da visualização e recalcula a taxa "ponta a ponta" entre as etapas visíveis adjacentes. Sem mudança de backend.

**Pendência:** 📎 print da planilha do cliente — necessário antes de redesenhar a tela. O cliente avisou que Marketing e Relatórios são as telas que mais precisam melhorar.

---

## 6. Relatórios — 🔴 viável (reformulação)

**O que o cliente quer:**
1. Relatório separado por origem, com nomenclatura nova: **Marketing** (receptivo), **Prospecção Ativa** (prospecção) e **Outras Mídias** (outros) — e o **total = soma das três**.
2. Incluir indicadores como **ticket médio**, rentabilidade etc. por origem e no total.
3. **Escopo por papel:**
   - SDR/vendedor logado vê **apenas os próprios números**;
   - gerente da loja filtra **por funcionário**;
   - dono de empresa vê **várias lojas e compara** entre elas.

**Como fazer:**
- Backend: relatório meta×realizado já é por origem — adicionar bloco "total" agregado e ticket médio (receita ÷ fechamentos). Aceitar `store_ids` múltiplos (mesma infra do item 1) e `user_id` opcional (gerente filtrando por funcionário; para shop_user comum, forçar `user_id = ele mesmo` NO BACKEND, nunca confiar no front).
- Front: abas/seções Marketing / Prospecção Ativa / Outras Mídias / Total; seletor de funcionário (gerente+) e de lojas (dono/admin).
- A parte de **desempenho de colaboradores** que existia em relatórios no legado vira a tela nova do item 10 (colocar um link daqui para lá).

---

## 7. Projeções — 🔴 viável

**O que o cliente quer:**
1. **Semáforo de cores mais chamativo**: métrica batendo a meta = **verde**; perto de bater = **amarelo**; longe = **vermelho**.
2. Incluir **CLASSIFICADOS** (hoje falta).
3. Os **3 funis separados por origem** (Marketing / Prospecção Ativa / Outras Mídias) — e talvez o funil visual do marketing aqui também.
4. **SDR vê as próprias projeções** (só os números dele: leads que pegou, agendou, compareceu, vendeu…).
5. **Comparação entre lojas** para o dono (e por funcionário dentro de uma loja quando cabível).

**Como fazer:**
- Backend `metrics/projections`: incluir `classified` na projeção (fonte: `daily_indicators.classified_leads` + meta do item 8); separar resposta por origem + total; aceitar `store_ids` múltiplos e `user_id` (mesmas regras de escopo do item 6 — SDR forçado a si mesmo no backend).
- Front: badge semáforo por métrica — regra sugerida (confirmar): projetado ≥100% da meta = verde; 80-99% = amarelo; <80% = vermelho. Usar tons fortes (não os tints atuais).
- Reaproveitar o componente de funil do item 2 se couber.

---

## 8. Metas — 🟡 viável (com migration)

**O que o cliente quer:**
1. Incluir **CLASSIFICADOS** como meta (hoje não existe o campo).
2. Nomenclatura nova em toda a UI: `receptivo` → **Marketing**, `prospeccao` → **Prospecção Ativa**, `outros` → **Outras Mídias**.
3. Um **preview do total**: ao preencher (ex.) 100 leads Marketing + 50 Prospecção Ativa + 50 Outras Mídias, mostrar um campo mais opaco/readonly com o total (200) somando as três origens — para cada métrica.

**Como fazer:**
- Migration: `classified_quantity INTEGER NULL` na tabela `goals` (o realizado já existe em `daily_indicators.classified_leads`).
- Nomenclatura: **manter os valores do banco** (`receptivo/prospeccao/outros`) e trocar SÓ os rótulos no front — criar um mapa único `ORIGIN_LABELS` em `src/lib/` e usar em TODAS as telas (Metas, Lançamento, Relatórios, Projeções, Marketing). Zero risco de quebrar dados.
- Preview: linha "Total" readonly (estilo opaco) que soma as 3 origens em tempo real no formulário.

---

## 9. Planos de Ação — 🔴 viável (com migrations)

**O que o cliente quer:** transformar o plano de ação num mini-roadmap:
- **Prazo** (data limite) do plano;
- **Responsáveis** (um ou mais usuários);
- **Etapas** com título, descrição e **prazo próprio** (sub-datas) — para acompanhar como roadmap;
- **Semáforo por prazo**: chegando perto do prazo → **amarelo**; passou do prazo → **vermelho**.

**Como fazer:**
- Migrations: em `action_plans` adicionar `due_date DATE NULL` e `responsible_ids JSONB NULL` (lista de user_ids); nova tabela `action_plan_steps` (`id, plan_id FK cascade, title, description, due_date, done BOOLEAN DEFAULT false, sort_order`).
- Backend: CRUD de steps aninhado no plano (`GET/POST/PATCH/DELETE /action-plans/{id}/steps`); response do plano inclui steps + nomes dos responsáveis.
- Front: card do plano mostra prazo com badge (regra sugerida — confirmar: ≤7 dias do prazo = amarelo; vencido = vermelho; concluído ignora); modal de edição ganha campos de prazo, seletor de responsáveis (equipe da loja) e a lista de etapas com checkbox + prazo por etapa (estilo roadmap com barra de progresso X/Y).

---

## 10. Tela nova: Desempenho de Colaboradores — 🔴 viável (port do legado)

**O que o cliente quer:** tela de mensuração de performance por colaborador, dividida por cargo:
- **SDR/pré-venda:** quem mais agendou, quem mais prospectou, ranking de comparecimento;
- **Comercial/vendedor:** quantos leads atendeu, quantos fechamentos, rentabilidade gerada e ticket médio gerado;
- Destaques: **TOP 3 vendas**, **quem mais fechou**, **TOP 3 SDRs**;
- Objetivo: enxergar os 20% que trazem 80% do resultado (Pareto);
- Visual: considerar **gráfico de radar (teia)** e **rosca** (ex.: "João responde por 50% do faturamento; Marcos por 10%").

**Referência no legado (JÁ MAPEADA — portar esta lógica):** `trivus/lib/crmTeamMetrics.js` → `buildCrmTeamPerformanceData` + componente `trivus/components/reports/TeamPerformanceSection.js`. Regras de atribuição do legado:
- **Leads pegos** → `assigned_to`, contando pela data de criação no período;
- **Agendamentos** → `vendedor_id || agendado_por`, pela data de **marcação** do agendamento;
- **Comparecimentos** → `vendedor_id`, pela `data_compareceu`;
- **Fechamentos + receita/rentabilidade** → `vendedor_id`, pela data de fechamento.

**Como fazer:**
- Backend: `GET /metrics/team-performance?store_id&from&to` (módulo metrics) devolvendo por usuário: `leads, agendamentos, comparecimentos, fechamentos, receita, rentabilidade, ticket_medio, share_faturamento_pct` + rankings prontos. Uma query agregada sobre `crm_funnel_leads` + join `users` (portar as regras acima 1:1).
- Front: nova rota `/desempenho` (feature key do serviço `metrics`): pódio TOP 3 vendas e TOP 3 SDRs, tabela por cargo, rosca de participação no faturamento (Recharts PieChart com innerRadius) e radar comparando até ~5 colaboradores (RadarChart), com filtro de período e — para dono — de loja.
- Acesso: gerente/dono/admin. SDR não acessa (os números individuais dele aparecem em Projeções/Relatórios, itens 6-7).

---

## 11. Usuários / Lojas / Empresas — 🟡 viável · ⚠️ DECISÃO

**O que o cliente quer (novo modelo mental — a LOJA é o centro):**
1. Admin da Trivus cria a **loja** e, **no mesmo fluxo, os gerentes** dela (1+, junto da criação).
2. **Gerentes criam os demais usuários** da própria loja.
3. **Empresa é opcional**: só o admin cria empresas; uma empresa pode ter N lojas (franquia), e **uma loja pode existir sem empresa**.
4. **SDR não vê** a opção "Adicionar colaborador" (só dono da empresa e gerente da loja adicionam).

**Como fazer:**
- Criação de loja + gerentes: no front, o modal "Nova loja" (admin) ganha a seção "Gerentes" (nome/email/senha, 1+ obrigatório). Backend: preferível `POST /admin/stores` aceitar `managers[]` (atômico); alternativa aceitável: fluxo em sequência (POST loja → POST team com `shop_role=gerente`) com validação no front.
- Gerente criar equipe: abrir `POST /stores/{store_id}/team` (e o GET) para shop_user com `shop_role=gerente` **da própria loja** (guard: `user.parent_store_id == store_id`). Hoje é `require_roles("admin","client")` em `src/modules/users/interface/router.py`.
- SDR sem botão: front esconde por papel; backend segue bloqueando.
- Loja sem empresa: `stores.company_id` **já é nullable**. PORÉM ⚠️: os gates exigem empresa+assinatura para habilitar serviços (`store_services.py` lança "Loja sem empresa vinculada (modo legado)"). **DECISÃO NECESSÁRIA — o que uma loja sem empresa enxerga?**
  - Opção A (recomendada): loja sem empresa opera em "modo legado" com acesso a um conjunto padrão (ex.: equivalente ao plano Full) até ser vinculada;
  - Opção B: loja sem empresa fica só com CRM;
  - Opção C: como hoje (tudo bloqueado até vincular) — contradiz o pedido do cliente.

---

## 12. Ordem de implementação sugerida (fases)

| Fase | Itens | Por quê |
|---|---|---|
| 1 | 0 (paleta) · 3.1 · 3.2 · 3.4 · 8 (nomenclatura+preview) | Rápidos, alto impacto visual, sem migration arriscada |
| 2 | 3.3 · 4 (agenda) · 2 (funil c/ classificados, sem a arte) · 8 (migration classificados) | Backend pequeno |
| 3 | 3.5 (flag de edição) · 11 (lojas/gerentes) | Mudam permissões — fazer juntos e reescrever os testes de visibilidade |
| 4 | 1 (dashboard multi-loja) · 6 · 7 (relatórios/projeções por origem+escopo) | Compartilham a infra `store_ids`/`user_id` |
| 5 | 9 (planos de ação) · 10 (desempenho) | Features novas maiores |
| 6 | 5 (marketing) + arte do funil | Depende dos 📎 assets do cliente |

## 13. Pendências para o Giovani resolver antes/durante

1. ~~📎 Print do design do funil (item 2) e print da planilha do marketing (item 5)~~ — **RECEBIDOS 23/07**; ver `SPEC_MARKETING_RELATORIOS.md`.
2. ⚠️ Confirmar a mudança de privacidade do CRM (3.5): todo SDR passa a VER os leads dos colegas (hoje não vê) — ok?
3. ⚠️ Decidir o comportamento da loja sem empresa (11): opção A, B ou C.
4. Confirmar os limiares dos semáforos (7 e 9): projeções ≥100% verde / 80-99% amarelo / <80% vermelho; plano de ação ≤7 dias amarelo / vencido vermelho.
