# Integração Meta Ads — Marketing API ↔ Trivus API

## O que resolve

O funil de custos (`GET /marketing/funnel`) usa o **investimento de marketing** do
período. Hoje ele vem de lançamentos manuais em `daily_indicators.marketing_investment`
(digitados à mão). Esta integração puxa o **gasto real** das campanhas direto da
Meta Ads e passa a alimentar o funil automaticamente — sem trocar nada para as
lojas que não usam Meta.

## Estado atual

**DESENVOLVIDA e DESLIGADA por flag** (`META_ENABLED=false`). Com a flag desligada,
o endpoint de sync funciona usando um **mock determinístico** (gasto sintético por
campanha/dia, sem rede) — dá para exercitar o fluxo ponta a ponta em dev/testes.
Com `META_ENABLED=true`, o mesmo endpoint chama a Graph API real.

## Arquitetura

```
POST /integrations/meta/sync            (protegido por header x-meta-token)
        │
        ▼
SyncMetaSpendUseCase
        │  agrupa campanhas por loja (cada loja = 1 ad account)
        ▼
MetaAdsClient  (interface / Protocol)
        ├── MockMetaClient   (META_ENABLED=false, default)
        └── HttpMetaClient   (META_ENABLED=true  -> graph.facebook.com)
        │
        ▼
campaign_daily_spend   (upsert por campaign_id + reference_date)
        │
        ▼
InvestmentReader -> GET /marketing/funnel   (investimento = SUM(spend))
```

- **Adapter atrás de uma interface** (`MetaAdsClient`): o resto do sistema não sabe
  se o gasto veio da rede ou do mock.
- O gasto fica em `campaign_daily_spend (store_id, campaign_id, reference_date,
  spend, impressions, clicks)`, uma linha por campanha/dia.

## Modelo de dados (migration `c7f4b2e918d5`)

- `marketing_campaigns.meta_campaign_id` — id da campanha na Meta.
- `stores.meta_ad_account_id` — ad account da loja (ex.: `act_1234567890`).
- Tabela `campaign_daily_spend` — gasto diário, `UNIQUE(campaign_id, reference_date)`
  (o sync é idempotente: re-sincronizar sobrescreve, não duplica).

## Variáveis de ambiente

| Env | Default | Para que serve |
|-----|---------|----------------|
| `META_ENABLED` | `false` | `true` = usa a Graph API real; `false` = mock |
| `META_ACCESS_TOKEN` | `""` | token do System User (só usado quando `META_ENABLED=true`) |
| `META_TOKEN` | `dev-meta-token` | segredo do header `x-meta-token` do endpoint de sync |

## Endpoint de sync

```
POST /integrations/meta/sync
Header: x-meta-token: <META_TOKEN>      (401 se faltar ou não bater)
Body (opcional):
{
  "store_id": "<uuid>",   // ausente = todas as lojas com campanhas Meta
  "since": "2026-07-01",  // ausente = janela padrão (últimos dias)
  "until": "2026-07-03"   // ausente = hoje
}
```

Para cada campanha com `meta_campaign_id` (da loja, ou de todas), chama o client
(mock ou HTTP conforme `META_ENABLED`) e faz upsert em `campaign_daily_spend`.
Campanhas cuja loja não tem `meta_ad_account_id` são puladas (contadas em
`skipped_no_ad_account`).

Resposta:

```json
{
  "rows_written": 3,
  "campaigns_synced": 1,
  "skipped_no_ad_account": 0,
  "since": "2026-07-01",
  "until": "2026-07-03"
}
```

O `HttpMetaClient` chama:

```
GET https://graph.facebook.com/v21.0/{ad_account}/insights
    ?level=campaign&time_increment=1
    &fields=campaign_id,spend,impressions,clicks
    &time_range={"since":"...","until":"..."}
Header: Authorization: Bearer <META_ACCESS_TOKEN>
```

## Como o investimento passa a ser automático

`InvestmentReader.total()` (usado pelo `/marketing/funnel` sem `campaign_id`):

1. Se **há linhas** em `campaign_daily_spend` para a loja no período → usa
   `SUM(spend)` dessas linhas (gasto real da Meta).
2. Senão → mantém o fallback atual: `SUM(daily_indicators.marketing_investment)`.

Ou seja: lojas com Meta sincronizada passam a ter o investimento vindo da fonte
real automaticamente; lojas sem Meta continuam exatamente como antes.

## O que precisa do lado da Meta (para ligar de verdade)

1. **Business Manager** com o ativo de anúncios (ad account) da loja.
2. **System User** (Business Settings → Users → System Users) com acesso ao ad
   account e um token de longa duração.
3. Permissão **`ads_read`** no token (suficiente para ler insights de gasto).
4. **App** no developer.facebook.com; para rodar além das lojas de teste e em
   escala, passar pelo **App Review** solicitando `ads_read`.
5. Guardar o `act_<id>` do ad account em cada loja (`stores.meta_ad_account_id`,
   via `PATCH /admin/stores/{id}`) e o `meta_campaign_id` em cada campanha
   (`PATCH /campaigns/{id}`).

## Passo a passo para ATIVAR

1. Preencha `meta_ad_account_id` das lojas e `meta_campaign_id` das campanhas.
2. Gere o token do System User com `ads_read` → env `META_ACCESS_TOKEN`.
3. Gere um segredo forte (`openssl rand -hex 32`) → env `META_TOKEN` (usado por
   quem dispara o sync, ex.: um cron/n8n).
4. Ligue `META_ENABLED=true`.
5. Dispare `POST /integrations/meta/sync` (idealmente agendado, 1x/dia) e confira
   o `/marketing/funnel` — o investimento deve refletir o gasto real.

## Rollback

Desligue `META_ENABLED` (volta ao mock; nenhuma chamada externa). Se quiser voltar
ao investimento manual, basta não sincronizar: sem linhas novas em
`campaign_daily_spend` no período, o funil usa o fallback de `daily_indicators`.
Os dados já gravados permanecem na tabela.
