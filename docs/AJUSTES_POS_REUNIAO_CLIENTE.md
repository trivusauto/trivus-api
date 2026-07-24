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

### 3.5 Permissão de edição: todos VEEM, editar os dos colegas exige autorização — 🟡 viável · ✅ DECIDIDO (23/07)
**Regra confirmada pelo Giovani:** TODO usuário da loja (SDR/vendedor/etc.) **vê o kanban inteiro**. Por padrão, cada um **só pode mover/editar os próprios cards**. Para mexer nos cards dos colegas, precisa de **autorização concedida por um usuário superior** (admin Trivus, dono ou gerente da loja) — uma flag por usuário que o próprio usuário NÃO vê.

**Como fazer:**
1. Migration: coluna `can_edit_others_leads BOOLEAN DEFAULT false` em `users` (**default = restrito**; a autorização é concedida, não retirada).
2. Backend: nos endpoints de escrita de lead (`PATCH /crm/leads/{id}`, `/stage`, `/agendamento`, `/compareceu`, `/fechamento`, `DELETE`) — se o usuário é shop_user comum (não gerente) SEM a flag e `lead.assigned_to != user_id` (e `vendedor_id != user_id`), retornar 403 amigável ("Este lead pertence a outro colaborador. Peça autorização ao gerente."). Gerente, dono e admin sempre editam tudo.
3. Visibilidade de leitura: **todo shop_user passa a ver o quadro inteiro** (remover o filtro por `assigned_to` do `list_for_board`).
4. UI de gestão: na tela **Usuários**, admin/dono/gerente veem o toggle "Pode editar leads de outros colaboradores" ao criar/editar membro da equipe. O próprio usuário nunca vê essa flag.
5. Front CRM: sem a flag, cards dos colegas ficam com drag desabilitado + tooltip explicando; drawer abre em modo leitura.

**Impacto:** substitui a regra de visibilidade atual (legado: SDR só via os próprios — `ListLeadsUseCase`/`list_for_board`). **Reescrever `tests/e2e/test_crm_visibility.py`** para a nova regra: leitura liberada para toda a equipe da loja; escrita restrita pela flag (default restrito). `can_see_unassigned_leads` continua existindo para o round-robin do webhook. O filtro "Responsável" do quadro passa a valer para todos (todos agora veem o quadro inteiro).

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

## 11. Usuários / Lojas / Empresas — 🟡 viável · ✅ DECIDIDO (23/07)

**O que o cliente quer (novo modelo mental — a LOJA é o centro):**
1. Admin da Trivus cria a **loja** e, **no mesmo fluxo, os gerentes** dela (1+, junto da criação).
2. **Gerentes criam os demais usuários** da própria loja.
3. **Empresa é opcional**: só o admin cria empresas; uma empresa pode ter N lojas (franquia), e **uma loja pode existir sem empresa**.
4. **SDR não vê** a opção "Adicionar colaborador" (só dono da empresa e gerente da loja adicionam).

**Como fazer:**
- Criação de loja + gerentes: no front, o modal "Nova loja" (admin) ganha a seção "Gerentes" (nome/email/senha, 1+ obrigatório). Backend: preferível `POST /admin/stores` aceitar `managers[]` (atômico); alternativa aceitável: fluxo em sequência (POST loja → POST team com `shop_role=gerente`) com validação no front.
- Gerente criar equipe: abrir `POST /stores/{store_id}/team` (e o GET) para shop_user com `shop_role=gerente` **da própria loja** (guard: `user.parent_store_id == store_id`). Hoje é `require_roles("admin","client")` em `src/modules/users/interface/router.py`.
- SDR sem botão: front esconde por papel; backend segue bloqueando.
- Loja sem empresa — ✅ **DECIDIDO (Opção A): a loja funciona NORMALMENTE sem empresa vinculada.**
  - ⚠️ **AVISO REGISTRADO (Giovani, 24/07): acesso completo ≠ gratuidade.** Loja sem empresa **SERÁ COBRADA** — a frente financeira (cobrança/billing) será implementada no futuro e deverá alcançar também as lojas sem empresa vinculada. Este item deve constar como requisito quando a frente de cobrança for planejada.
  - `stores.company_id` já é nullable; o que muda é o resolvedor de entitlements (`src/modules/ecosystem/`): quando `company_id IS NULL`, retornar o **conjunto padrão completo** de feature_keys (equivalente ao plano Full — todos os serviços de software), até a loja ser vinculada a uma empresa. A partir do vínculo, passa a valer o plano da assinatura da empresa (inclusive suspensão).
  - Ajustar `store_services.py`: habilitar/desabilitar serviço numa loja sem empresa deixa de lançar o erro "Loja sem empresa vinculada (modo legado)".
  - Testes: loja sem empresa acessa CRM/métricas/marketing normalmente; loja vinculada a assinatura suspensa continua toda bloqueada (regra atual mantida).

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
2. ✅ ~~Privacidade do CRM (3.5)~~ — **DECIDIDO 23/07:** todos da loja VEEM o quadro inteiro; editar cards dos colegas exige a flag `can_edit_others_leads`, concedida por admin/dono/gerente (default = restrito).
3. ✅ ~~Loja sem empresa (11)~~ — **DECIDIDO 23/07: Opção A** — a loja funciona normalmente sem empresa (entitlements padrão completos até vincular).
4. ✅ ~~Limiares dos semáforos~~ — fixados pelo design em `SPEC_MARKETING_RELATORIOS.md`: **≥95% verde · 80–95% âmbar · <80% vermelho** (vale para Marketing, Relatórios, Projeções e Metas). Plano de ação segue: ≤7 dias do prazo = amarelo · vencido = vermelho.
