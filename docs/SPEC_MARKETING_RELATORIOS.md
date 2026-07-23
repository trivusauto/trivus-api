# Spec — Funil da Visão Geral, tela de MARKETING e tela de RELATÓRIOS

> Detalha (e substitui) os itens **2, 5 e 6** de `AJUSTES_POS_REUNIAO_CLIENTE.md`,
> com base nos 5 prints de design enviados pelo cliente em 23/07/2026.
> Como as imagens não acompanham este arquivo, cada design está **descrito por extenso** —
> implementar fielmente a partir das descrições.
>
> Contexto: `trivus-api` (FastAPI, branch **develop**) + `trivus-web` (Next 16, branch
> **release/new-web**). Push SÓ nessas branches. Gráficos com **Recharts** (já usado no projeto).
> Formatação BRL/pt-BR já existe (`BRL` em `src/lib/types.ts`).

---

## REGRA GLOBAL DE SEMÁFORO (veio do design — usar em todo o sistema)

O print do funil meta×realizado define os limiares oficiais:

| Cor | Critério |
|---|---|
| 🟢 verde | **≥ 95%** da meta |
| 🟡 dourado/âmbar | **80% a 95%** da meta |
| 🔴 vermelho | **< 80%** da meta |

Criar helper único no front (`src/lib/goal-status.ts`): `goalStatus(realizado, meta) → "green" | "amber" | "red"` e usar em Marketing, Relatórios, Projeções e Metas. (Substitui os limiares 100/80 sugeridos antes no doc de ajustes.)

---

# PARTE A — Visão Geral: Funil de Conversão (print 1)

**O que é:** o funil do dashboard vira um **funil visual de formato FIXO** — a forma nunca muda, só os números mudam.

**Descrição do design (print 1):**
- Funil simétrico vertical, 6 faixas empilhadas que afunilam até um "bico" estreito na base.
- Ordem das faixas: **Leads** · **Classificados** · **Qualificados** · **Agendados** · **Comparecidos** · **Vendas**.
- Cores: degradê de azul — topo azul-escuro (~#33517E), clareando faixa a faixa (azul-acinzentado → azul-claro → cinza-azulado), e a última faixa (**Vendas**) na **cor de destaque** (hoje dourado; seguir a paleta nova do item 0 do doc de ajustes).
- Texto centralizado em cada faixa: `Nome  Número` (nome peso normal, número **bold**); branco nas faixas escuras, escuro nas claras.
- Card branco arredondado, título "Funil de Conversão"; ao lado direito permanece o painel "Taxa de conversão por etapa" que já existe.

**Implementação:**
- Componente novo `src/components/charts/fixed-funnel.tsx`: **SVG desenhado à mão com paths fixos** (NÃO usar FunnelChart proporcional — o cliente quer a forma sempre idêntica). Props: `steps: {label: string, value: number}[]`, `accentLast?: boolean`. Reutilizável (Marketing também usa).
- Forma: 6 trapézios empilhados; larguras sugeridas (% do viewBox, topo→base de cada faixa): 100→86 · 86→72 · 72→56 · 56→40 · 40→22 · 22→14; alturas iguais.
- **Backend:** incluir **CLASSIFICADOS** no funil do dashboard (dado vem do `crm_lead_stage_history` via StageReachReader) e na lista de taxas (Leads→Classificados, Classificados→Qualificados, …).
- "Comparecidos" = `compareceu_agendamento=true` no período (como o "atendidos" atual); "Vendas" = fechamentos.

---

# PARTE B — Tela de MARKETING (prints 2, 3 e 4)

A tela passa a ter 4 blocos, nesta ordem:

## B1. Funil Meta × Realizado ("Funil receptivo geral") — print 2 ⭐ peça central

**Descrição do design:**
- Card largo. Título "**Funil receptivo geral**" + nota pequena "· prospecção ativa não entra no cálculo de custo". Canto superior direito: legenda `● ≥95% da meta  ● 80–95%  ● <80%`.
- **Três colunas alinhadas por faixa:**
  1. **Esquerda — META:** meio-funil **espelhado** (afunila da esquerda para o centro), **cinza-claro**, rótulo "META" no topo, números da meta por etapa alinhados à esquerda (ex.: 250, 200, 150, 95, 80, 25).
  2. **Centro — etapas:** cada linha tem a **bolinha do semáforo** (cor pelo % da meta da etapa) + nome em CAPS bold (LEADS, CLASSIFICADOS, QUALIFICADOS, AGENDADOS, COMPARECIDOS, VENDAS) e, abaixo, em texto menor cinza: `↓ X% da etapa anterior` (conversão do REALIZADO vs etapa anterior; a 1ª etapa não tem).
  3. **Direita — REALIZADO · CUSTO:** meio-funil **azul-escuro** (afunila do centro para a direita; VENDAS na cor de destaque), rótulo "REALIZADO · CUSTO", e por faixa: **número realizado bold grande** + **chip "% da meta"** (fundo suave verde/âmbar/vermelho, ex. `96% da meta`) + **chip de custo por unidade** (ex. `R$ 47,50`).
- Rodapé: "Lado esquerdo: meta mensal por etapa · lado direito: realizado no período, com custo por unidade em destaque."
- **As formas dos dois meio-funis são FIXAS** — só números, chips e bolinhas mudam.

**Dados/cálculos:**
- Metas por etapa: `goals` da origem `receptivo` (leads_quantity, **classified_quantity → exige a migration do item 8 do doc de ajustes**, qualified_quantity, scheduled_quantity, attended_quantity, conversions_quantity). Meta proporcional quando o período não é o mês cheio (meta × dias_do_período ÷ dias_do_mês).
- Realizado por etapa: mesma fonte do funil de custos atual.
- Custo por unidade: `investimento ÷ quantidade realizada da etapa` (lógica CPL→CAC atual estendida às 6 etapas; custo/venda = CAC).
- % da meta → semáforo global (≥95/80–95/<80).
- Endpoint: **estender** a resposta do funil de custos existente para `{stage, meta, realizado, pct_meta, custo_unit, conv_prev_pct}[]` — não criar endpoint novo se o atual comportar.
- **Filtro de etapas (pedido da reunião):** checkboxes acima do card para ocultar etapas intermediárias (ex.: só LEADS×VENDAS); o `↓ %` recalcula entre as etapas visíveis adjacentes. Front-only.

## B2. Cards de KPI com sparkline e comparativo — print 3 (parte de cima)

**Descrição do design:** grade de cards (3 por linha). Cada card:
- Título pequeno (ex. "Leads Qualificados", "Custo por Lead Qualificado", "% Leads Qualificados").
- **Valor grande bold** (número, R$ ou %).
- Badge de variação vs período anterior: verde ↑ melhorou, vermelho ↓ piorou, cinza "N/A" sem base — **para métricas de CUSTO, melhorar = cair (inverter)**.
- Linha: "`<valor>` no período anterior".
- Legenda: `● Período de análise  ● Período comparativo`.
- **Sparkline de área** (área azul-clara) com a série diária do período.

**KPIs (12 cards):** Leads · CPL · Classificados · Custo/Classificado · Qualificados · Custo/Qualificado · % Qualificados (qualificados÷leads) · Agendados · Comparecidos · Vendas · CAC · Investimento total.

**Backend novo:** `GET /metrics/marketing/series?store_id&from&to` → por dia `{date, leads, classificados, qualificados, agendados, comparecidos, vendas, investimento}` + agregado do **período comparativo** (janela imediatamente anterior de mesma duração). Fontes: `daily_indicators` (contagens + marketing_investment), cruzando com CRM como o funil de custos já faz. Uma query agrupada por data — sem N+1.

## B3. Funil de mídia (Impressões → Cliques → Leads → Qualificados) — print 3 (baixo) · ⚠️ depende da Meta

**Descrição do design:** card "Funil de Marketing": funil invertido azul com **Impressões → Cliques → Sessões → Leads → Leads Qualificados** e, à direita, a lista "Taxa de Conversão por Etapa" (`Impressões → Cliques  X%  533.362/1.593`, …).

**Viabilidade honesta:**
- **Impressões/Cliques:** só via **Meta Ads** (Graph API insights: `impressions`, `clicks`). O adapter mock `src/modules/integrations/meta/` já existe — adicionar os 2 campos ao sync junto do `spend` (migration: `impressions INT NULL`, `clicks INT NULL` em `campaign_daily_spend`).
- **Sessões:** viria do Google Analytics — **fora de escopo agora** (omitir a faixa).
- Sem Meta conectada: estado vazio amigável ("Conecte a Meta Ads para ver impressões e cliques"). Com Meta: Impressões → Cliques → Leads → Leads Qualificados + taxas ao lado.
- Reutilizar o `fixed-funnel` (sem accent na última faixa).

## B4. Gráficos de linha diários — print 4

Dois cards lado a lado (Recharts LineChart, pontos, tooltip com data dd/mm/aa, legenda embaixo):
1. **"Investido vs Leads"** — `investimento` (azul) × `leads gerados` (teal), por dia.
2. **"Leads vs Leads Qualificados"** — `leads` (azul) × `qualificados` (teal), por dia.

Dados: o MESMO endpoint do B2 — não criar outro.

---

# PARTE C — Tela de RELATÓRIOS: Painel Executivo multi-loja (print 5, a planilha)

**O que é:** Relatórios vira um **"Business Performance — Painel Executivo de Indicadores e Resultados"**, replicando a planilha mensal do cliente. **Inerentemente multi-loja** (dono/admin comparando unidades). Seletor de mês/ano no topo.

## C1. Cabeçalho
- Título "Business Performance" + mês/ano (ex. JULHO/2026).
- Três mini-infos: **Dias úteis do mês** · **Dias trabalhados** (úteis decorridos) · **Dias restantes**. Dia útil = **segunda a sábado** (lojas abrem sábado); constante configurável no backend.

## C2. Faixa de KPIs (8 cards)
| Card | Cálculo | Extra |
|---|---|---|
| **Faturamento** | Σ receita dos fechamentos do mês (lojas selecionadas) | "% da meta" + barra de progresso |
| **Meta mensal** | Σ meta de faturamento (profitability_goal) das lojas | barra 100% |
| **Projeção mensal** | (faturamento ÷ dias trabalhados) × dias úteis | "% da meta" projetado |
| **Lucro projetado** | projeção × margem média atual | "% margem" |
| **Ticket médio geral** | faturamento ÷ fechamentos | — |
| **Fechamentos** | contagem de vendas do mês | — |
| **Conversão** | fechamentos ÷ leads do mês (%) | — |
| **Margem média** | Σ rentabilidade ÷ Σ receita (%) | mini-donut |

## C3. Tabela por unidade (loja)
Colunas: **Unidade · Faturamento · Meta · % Meta · Ticket Médio · Lucro Projetado · Margem · ●** (semáforo).
- Célula **% Meta** com fundo heatmap (vermelho→amarelo→verde pelo semáforo global).
- Linha final **TOTAL** em bold.
- Lucro projetado da loja = projeção da loja × margem da loja; margem = rentabilidade ÷ receita.

## C4. Grade de 6 gráficos (Recharts)
1. **Faturamento × Meta por loja** — barras agrupadas (faturamento azul, meta na cor de destaque) + **linha tracejada verde de projeção**.
2. **Ranking de faturamento** — barras horizontais ordenadas, valor na ponta.
3. **Ticket médio por loja** — barras verticais ordenadas.
4. **Comprados × Vendidos por loja** — barras agrupadas (na planilha "Conversão (vendidos x fechados)"; no nosso domínio = contagens de VEICULOS COMPRADOS × VEICULOS VENDIDOS no mês).
5. **Lucro projetado por loja** — barras verticais.
6. **Margem (%)** — donut central com a margem média + lista loja→% com bolinhas coloridas.

## C5. Rodapé analítico (4 blocos)
1. **Gauge "Desempenho da meta"** — velocímetro semicircular (arco vermelho→amarelo→verde + ponteiro) com o **% da meta atingida** em destaque. Implementar com PieChart semicircular do Recharts + agulha SVG (não instalar lib nova).
2. **Ritmo:** *média diária atual* (faturamento ÷ dias trabalhados) · *média diária necessária* ((meta − faturamento) ÷ dias restantes) · *forecast* = min(99%, projeção ÷ meta) exibido como "probabilidade de bater a meta".
3. **Resumo executivo (gerado por cálculo, sem IA):** bullets — "X% da meta atingida" · "Projeção de fechamento: R$ Y" · "Unidade destaque: <maior % meta>" · "Unidade que exige atenção: <menor % meta>" · "Necessário faturar ~R$ Z/dia para atingir a meta".
4. **TOP 3 destaques** (maiores faturamentos, com margem) e **TOP 3 pontos de atenção** (menores margens/% meta) — listas com posições 1/2/3.

## C6. Escopo por papel
- **dono/admin:** painel completo multi-loja (seletor de lojas; padrão = todas as acessíveis).
- **gerente (shop_user):** mesmo painel restrito à própria loja — a tabela C3 vira "por vendedor" (mesmas colunas por colaborador, com as regras de atribuição do item 10 do doc de ajustes).
- **SDR/vendedor:** não vê o painel executivo; vê a versão "meus números" (item 6 do doc de ajustes).
- Faixa "Novidades" da planilha: **fora de escopo** (era manual).

## C7. Backend novo
`GET /metrics/executive?store_ids=<repetido>&year&month` → JSON com todos os blocos prontos (kpis, byStore[], charts, gauge, resumo, tops):
- validar `store_ids` contra `GetAccessibleStoreIdsUseCase` → 403 fora do escopo;
- uma passada agregada por loja (sem N+1); fontes: `crm_funnel_leads` (receita/rentabilidade/fechamentos/comprados/vendidos por `data_fechou_negocio`/`data_comprado`), `goals` (metas), `daily_indicators` (leads p/ conversão);
- divisões protegidas (loja sem venda → ticket médio null, nunca 500);
- testes e2e: papel×escopo (SDR 403; gerente restrito à própria loja), loja vazia, mês sem meta.

---

## Ordem de implementação (só desta spec)

| Passo | Entrega |
|---|---|
| 1 | Helper `goalStatus` + componente `fixed-funnel` + funil da Visão Geral com CLASSIFICADOS (Parte A) |
| 2 | Migration `classified_quantity` em goals (pré-requisito) + B1 Funil Meta×Realizado |
| 3 | Endpoint `/metrics/marketing/series` + B2 (KPI cards) + B4 (linhas) |
| 4 | Endpoint `/metrics/executive` + Parte C (Relatórios) — maior bloco |
| 5 | B3 (Impressões/Cliques) — junto da frente Meta Ads (migration impressions/clicks) |

## Decisões já tomadas por este doc (não perguntar de novo)
- Semáforo oficial: **≥95 verde · 80–95 âmbar · <80 vermelho** (veio do design).
- Funis são SVG de forma FIXA (não proporcionais aos valores).
- "Sessões" (GA) fora de escopo; Impressões/Cliques só com Meta conectada.
- Dia útil = seg-sáb. Forecast = min(99%, projeção÷meta).
- "Conversão (vendidos×fechados)" da planilha = Comprados × Vendidos do CRM.
