# Integração de Cobrança — Framework de Pagamentos ↔ Trivus API

## Estado atual

**DESENVOLVIDA e DESLIGADA** (`BILLING_GATEWAY_ENABLED=false`). A cobrança é manual:
o admin cria/ativa/suspende assinaturas em `/admin/subscriptions`; trials expiram
sozinhos na leitura (`trialing` + `trial_ends_at` no passado = suspenso).

## Arquitetura

O backend **não** integra gateways diretamente. O framework de pagamentos da Trivus
(que já integra vários gateways) é quem cobra — e reporta cada evento para:

```
POST /integrations/billing/events
Header: x-billing-token: <BILLING_TOKEN>
```

## Contrato do evento (o framework adapta qualquer gateway para este formato)

```json
{
  "subscription_id": "<uuid da assinatura no Trivus API>",
  "event_type": "payment_confirmed | payment_failed | payment_overdue | payment_refunded",
  "external_id": "<id do pagamento no framework/gateway>",
  "gateway": "<nome do gateway que processou>",
  "amount": 500.00,
  "paid_at": "2026-07-10T12:00:00Z",
  "raw": { "...payload original do gateway (auditoria)..." }
}
```

## O que o backend faz com cada evento

1. **SEMPRE** persiste em `subscription_payments` (histórico completo + payload bruto).
2. Se a assinatura tem `billing_mode = "gateway"`:
   - `payment_confirmed` → status **active**
   - `payment_failed` / `payment_overdue` → status **suspended** (os usuários da
     empresa perdem acesso na hora — os gates leem o status na leitura)
   - `payment_refunded` → só registra (decisão manual do admin)
3. Assinaturas `billing_mode = "manual"` **nunca** têm o status alterado por eventos
   (o pagamento é registrado mesmo assim). Manual e gateway coexistem.

## Passo a passo para ATIVAR

1. Gere um token forte: `openssl rand -hex 32` → env `BILLING_TOKEN` (Railway + framework).
2. Configure o framework para POSTar os eventos na URL de produção com o header `x-billing-token`.
3. Mapeie os IDs: ao criar a cobrança no framework, guarde o `subscription_id` do
   Trivus API; opcionalmente preencha `gateway_customer_id`/`gateway_subscription_id`
   (campos já existem em `subscriptions`).
4. Mude as assinaturas desejadas para `billing_mode = "gateway"`.
5. Ligue `BILLING_GATEWAY_ENABLED=true` e teste em sandbox:
   - evento `payment_confirmed` → assinatura fica `active`;
   - evento `payment_overdue` → fica `suspended` e o acesso trava.

## Rollback

Desligue `BILLING_GATEWAY_ENABLED` (o endpoint passa a responder **409**) e volte
`billing_mode = "manual"` nas assinaturas afetadas. Nenhum dado é perdido — o
histórico fica em `subscription_payments`.
