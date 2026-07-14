# Contexto para o protótipo (Claude Design) — partes novas do Trivus

> **Cole este documento no chat do protótipo.** Ele descreve as duas áreas que ainda não existem no design:
> **(1) o módulo de Marketing novo** e **(2) a camada SaaS/Ecossistema** (admin da holding + bloqueios/upsell nas telas da loja).
> Os shapes de dados mostrados são os **reais da API já construída** — desenhar com eles garante que o protótipo vira código sem retrabalho.

---

## Contexto geral (relembrando o produto)

O Trivus é a plataforma da holding Trivus (consultoria + capacitação + agência de marketing) para **lojas/concessionárias de veículos**: CRM Kanban de leads, captação automática via WhatsApp, agenda, métricas/metas e agora **análise de marketing por custo** e **gestão de assinaturas SaaS**.

**Papéis:** `admin` (equipe Trivus — enxerga tudo, telas /admin), `client` (dono de loja — gestor), `shop_user` (colaborador: gerente/vendedor/sdr/administrativo).

**Identidade visual:** manter a existente no protótipo (dark/light, cards, sidebar por módulo).

---

# PARTE 1 — Módulo de Marketing (novo)

## 1.1 Nova tela: **Marketing** (substitui a antiga por completo)

Item de menu "Marketing". Filtros no topo: **loja** (se multi-loja), **período** (mês atual default) e **campanha** (dropdown "Todas as campanhas" + lista). A tela tem **3 seções empilhadas**:

### Seção 1 — Funil Receptivo Geral (com custos)

Um funil GRANDE (vertical ou horizontal, números legíveis — feedback do cliente: os atuais ficam pequenos demais). 6 etapas, cada uma exibindo: **quantidade**, **taxa de conversão da etapa anterior**, **custo unitário** (destaque em amarelo) e **sinaleiro** (bolinha verde/amarela/vermelha/cinza + % da meta).

Dados (GET /marketing/funnel):
```json
{
  "stages": [
    {"stage": "leads",      "label": "Leads",        "quantity": 200, "unit_cost": 50.0,  "conversion_from_previous": null, "goal": 180, "pct_of_goal": 111.1, "light": "green"},
    {"stage": "classified", "label": "Classificados","quantity": 160, "unit_cost": 62.5,  "conversion_from_previous": 80.0, "goal": null, "pct_of_goal": null, "light": "gray"},
    {"stage": "qualified",  "label": "Qualificados", "quantity": 112, "unit_cost": 89.3,  "conversion_from_previous": 70.0, "goal": 120, "pct_of_goal": 93.3, "light": "yellow"},
    {"stage": "scheduled",  "label": "Agendados",    "quantity": 56,  "unit_cost": 178.6, "conversion_from_previous": 50.0, "goal": 60,  "pct_of_goal": 93.3, "light": "yellow"},
    {"stage": "attended",   "label": "Comparecidos", "quantity": 40,  "unit_cost": 250.0, "conversion_from_previous": 71.4, "goal": 45,  "pct_of_goal": 88.9, "light": "yellow"},
    {"stage": "sales",      "label": "Vendas",       "quantity": 8,   "unit_cost": 1250.0,"conversion_from_previous": 20.0, "goal": 12,  "pct_of_goal": 66.7, "light": "red"}
  ],
  "investment": 10000.0, "investment_goal": 12000.0,
  "revenue": 125000.0, "roas": 12.5, "roi": 11.5
}
```
- Header da seção: cards pequenos com **Investimento no período** (R$ 10.000 / meta R$ 12.000), **Faturamento**, **ROAS 12,5x**, **ROI 11,5x**.
- Rótulos dos custos: "Custo por Lead (CPL)" na 1ª etapa e "CAC" na última; `unit_cost` nulo = "—".
- Sinaleiro: verde ≥100% da meta, amarelo ≥80%, vermelho <80%, cinza sem meta. Com campanha selecionada ou período >1 mês, tudo vem cinza (metas são mensais por loja).
- Ao selecionar uma campanha no filtro, a seção mostra só os leads daquela campanha e o investimento vira o **budget da campanha**.

### Seção 2 — Funil por Campanha

Um card por campanha ativa/encerrada no período, cada um com um funil compacto (mesmas 6 etapas, versão mini) + nome, período, budget e CAC. Dados (GET /marketing/by-campaign):
```json
[
  {"campaign": {"id": "c1", "name": "Carro Popular Julho", "started_at": "2026-07-01", "ended_at": null, "budget": 4000.0},
   "funnel": { "...mesmo shape da Seção 1, com investment = budget..." }}
]
```

### Seção 3 — Comparação entre campanhas

Gráfico de barras com seletor de métrica: **Leads | Vendas | CAC | ROAS** por campanha (uma barra por campanha, dados derivados da Seção 2). Campanha nova cadastrada = barra nova automática.

## 1.2 Nova tela: **Campanhas** (cadastro)

Lista + formulário. Campos: **nome***, **início*** (data), **fim** (vazio = ativa, badge "Ativa"), **budget** (R$), **código do link** (`link_code` — texto curto usado pra identificar a campanha automaticamente nos leads que chegam pelo WhatsApp; tooltip explicando). Quem usa: pré-vendas/admin da loja. Ações: criar, editar, encerrar (setar fim).

## 1.3 Mudanças em telas existentes

**Relatórios:** (a) nova linha **CLASSIFICADOS** entre Leads e Qualificados; (b) **coluna de custos** ao lado das quantidades, células com fundo amarelo claro (CPL, custo/classificado, custo/qualificado, custo/agendado, custo/atendido, CAC) — a coluna inteira pode vir nula (sem permissão → ver Parte 2); (c) **filtro por campanha** (dropdown); (d) na comparação com metas, nova linha **Meta Investimento vs Real Investimento**.

**Projeções:** cada indicador (leads, qualificados, agendados, comparecimentos, conversões, receita) vira um card com o trio **Meta / Realizado / Projetando** + **% da meta em destaque** + sinaleiro. Header: dias úteis (totais/decorridos/restantes). Shape:
```json
{"working_days": {"total": 26, "elapsed": 13, "remaining": 13},
 "metrics": [{"key": "conversions", "goal": 12, "actual": 8, "projected": 16.0, "pct_of_goal": 133.3, "light": "green"}]}
```

**CRM (card/modal do lead):** o campo de origem passa a se chamar **"Campanha de Marketing"**; ao escolher "receptivo", abre um segundo select com as campanhas cadastradas da loja (preenchido automático quando o lead veio de anúncio; manual como fallback). Se a loja exigir campanha (flag), lead receptivo **sem campanha não avança de etapa** — o modal de mover mostra o erro "Preencha a campanha de marketing do lead antes de avançar."

**Lançamento diário (modo indicadores):** dois campos novos no formulário: **Classificados** (número) e **Investimento em marketing do dia** (R$, separado das despesas operacionais).

---

# PARTE 2 — SaaS / Ecossistema

Duas frentes: **(A) telas novas do admin da holding** e **(B) o comportamento de bloqueio/upsell nas telas da loja**.

## 2A. Admin da holding (menu "Ecossistema" na área /admin)

### Tela: Empresas
Lista (nome, CNPJ, responsável, nº de lojas, plano atual, status da assinatura com badge) + form (nome*, CNPJ, responsável). Detalhe da empresa: lojas vinculadas (vincular/desvincular loja) + assinatura atual + histórico.

### Tela: Planos
Lista + form: **key*** (slug, imutável após criar), **nome***, **serviços incluídos** (multi-select do catálogo), **máx. de lojas** (vazio = ilimitado), **preço/mês** (informativo — cobrança é manual na v1).
Exemplos pra mock: `saas_starter` (CRM+Agenda, 1 loja, R$ 297), `saas_pro` (+Métricas+Marketing+Disparos, 3 lojas, R$ 597), `consultoria_full` (tudo + serviços humanos, ilimitado).

### Tela: Catálogo de Serviços
O coração do modelo. Lista + form: **key*** (imutável), **nome***, **tipo*** (`software` | `humano`), **o que é** (curto), **o que faz** (detalhe), **pitch de venda** (copy que aparece no card de upsell), **feature keys** (multi-select de uma lista fechada — só para tipo software; humanos não desbloqueiam nada, só aparecem no catálogo), ordem, ativo.
Aviso na edição: "Alterar as feature keys muda o acesso de todos os assinantes imediatamente." Desativar é bloqueado se o serviço estiver em algum plano.

Lista de feature keys (picklist, com rótulo e grão):
```
crm.kanban (tela) · crm.activity_log (área) · agenda (tela) · webhook.zapi (módulo)
metrics.dashboard (tela) · metrics.reports (tela) · metrics.reports.costs (área: coluna de custos)
metrics.marketing (tela) · metrics.projections (tela) · metrics.team (tela)
marketing.campaigns (tela) · bulk_send (módulo) · indicators (tela) · goals (tela) · action_plans (tela)
```

### Tela: Assinaturas
Lista (empresa, plano, status badge: `trialing` azul c/ "expira em X dias", `active` verde, `suspended` laranja, `canceled` cinza) + criar (empresa*, plano*, status inicial `active` ou `trialing` — trial exige data de expiração) + ações: **trocar plano** (é assim que SaaS vira consultoria), **suspender/reativar**, **cancelar**, notas. Trial vencido aparece automaticamente como suspenso.

### Na tela de detalhe da Loja (admin): seção "Serviços"
Toggles por serviço, limitados ao plano da empresa (modelo híbrido: contrata-se por empresa, liga-se por loja). Serviço fora do plano aparece desabilitado com hint "não incluso no plano X". Toggle falha se a loja não tem empresa vinculada.

### Tela: Interesses (fila do comercial)
Kanban ou lista com filtro por status: **novo → contatado → convertido / descartado**. Cada card: serviço desejado, empresa, loja, quem clicou, quando, campo de notas. (O clique do cliente também dispara notificação automática ao comercial via n8n.)

## 2B. Comportamento nas telas da loja (bloqueio + upsell)

**A regra:** ao entrar/trocar de loja, o front recebe a lista de recursos liberados:
```json
GET /ecosystem/my-entitlements?store_id=...  →  {"feature_keys": ["crm.kanban", "agenda", "metrics.dashboard"]}
```
- **Menu/telas:** itens cujა key não está na lista **não somem** — aparecem com um **cadeado** e levam à tela de upsell (decisão de UX: mostrar o que existe vende mais que esconder).
- **Tela bloqueada:** em vez do conteúdo, um **card de upsell** centralizado: ícone de cadeado, nome do serviço que desbloqueia, "o que é", pitch de venda e botão **"Quero conhecer"**. Os dados do card vêm do catálogo:
```json
GET /ecosystem/services?store_id=... →
{"services": [{"key": "metricas_avancadas", "name": "Métricas Avançadas", "type": "software",
   "what_it_is": "Análise completa do seu funil", "upsell_pitch": "Descubra quanto custa cada venda...",
   "unlocked": false}],
 "locked_unlockers": {"metrics.marketing": {"service_key": "metricas_avancadas", "name": "Métricas Avançadas", "upsell_pitch": "..."}}}
```
- **Card/área bloqueada dentro de tela liberada** (ex.: a coluna de custos do relatório sem `metrics.reports.costs`): a API já devolve o dado nulo; no lugar, renderizar uma versão mini do card de upsell ("🔒 Custos por etapa — disponível no serviço X · Quero conhecer").
- **Clique em "Quero conhecer":** `POST /ecosystem/interests {store_id, service_key}` → toast "Interesse registrado! Nosso time entrará em contato." (botão vira "Interesse enviado ✓", desabilitado).
- **Erro 403 padronizado:** qualquer chamada pode retornar `{"error": "feature_locked", "feature_key": "..."}` — tratar igual (render do card correspondente).
- **Serviços humanos** (Consultoria, Capacitação, Agência) aparecem numa tela/área "**Ecossistema Trivus**" no menu da loja: vitrine de cards com o que a empresa já tem (badge "Contratado") e o que não tem (pitch + Quero conhecer).
- **Assinatura suspensa/trial expirado:** tudo bloqueado → tela cheia "Sua assinatura está suspensa — fale com a Trivus" (sem cards individuais).
- **Trial ativo:** banner discreto no topo "Período de teste — expira em X dias".

---

## Estados e enums pra usar nos mocks

| Coisa | Valores |
|---|---|
| Sinaleiro `light` | `green` · `yellow` · `red` · `gray` |
| Status assinatura | `trialing` · `active` · `suspended` · `canceled` |
| Status interesse | `novo` · `contatado` · `convertido` · `descartado` |
| Tipo de serviço | `software` · `humano` |
| Origem do lead (`funil`) | `receptivo` · `prospeccao_ativa` · outros |
| Etapas do funil de custos | leads → classified → qualified → scheduled → attended → sales |
| Papéis | `admin` · `client` · `shop_user` (gerente/vendedor/sdr/administrativo) |

## O que NÃO desenhar (fora de escopo da v1)

- Checkout/pagamento self-service (cobrança é manual; a integração com o gateway existe mas está desligada).
- Metas por campanha (descartado — meta é mensal geral).
- Dashboard: sem mudanças nesta entrega.

---

> **Depois do design aprovado:** trazemos o protótipo para o projeto real e geramos o front consumindo a API
> (`docs/API_REFERENCE.md` + `/openapi.json` têm todos os contratos — os shapes acima já são os finais).
