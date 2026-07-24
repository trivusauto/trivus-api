# Fora do escopo do Plano 13 — para revisão do Giovani

Coisas que encontrei enquanto executava o baby steps e **decidi NÃO fazer**, porque
o passo não pedia. Nenhum item aqui foi alterado no código. Cada um traz o que é,
por que ficou de fora e o que eu faria.

> Diferente de `DUVIDAS_PLANO13.md`: lá ficam ambiguidades do plano que **travaram**
> um passo; aqui ficam melhorias/problemas que **não travaram** nada.

---

## 1. Layout dos filtros da Agenda empilha em largura total

**Onde:** `trivus-web/src/app/(app)/agenda/page.tsx` — cabeçalho de filtros.

**O que é:** os selects ("Data do agendamento", "Todos os vendedores") e o campo de
busca ocupam a linha inteira em vez de ficarem lado a lado. O container é
`flex flex-wrap` com um spacer `flex-1`, e a classe `.input` (que tem `width: 100%`)
vence o `w-auto` do Tailwind.

**Por que ficou de fora:** confirmei no container antigo (antes do S2.12) que **já era
assim** — não é regressão minha, e o S2.12 só pedia o dropdown, a coluna e o modal.

**O que eu faria:** trocar `.input` por uma variante sem `width: 100%` nesses selects,
ou dar `!w-auto`. É um ajuste de CSS de poucos minutos.

---

## 2. `/auth/me` não expõe `shop_role`

**Onde:** `trivus-api/src/modules/auth/` (resposta do `/auth/me`) e
`trivus-web/src/components/providers.tsx` (`useSession`).

**O que é:** o front não consegue distinguir um `shop_user` **gerente** de um SDR —
`/auth/me` devolve só `id/email/name/role/parent_store_id`. O próprio comentário no
`providers.tsx` já admite isso: *"shop_user gerente é resolvido pelo backend nos dados;
no front, gestor visual = admin/client"*.

**Impacto atual:** no S2.12 (dropdown de vendedor da Agenda) resolvi deixando a query
de equipe rodar para todos com `retry: false` — quem pode recebe 200 e vê o dropdown,
o SDR recebe 403 e não vê. Funciona e mantém o backend como fonte da verdade, mas gera
um request 403 na tela do SDR. O mesmo padrão deve aparecer no S3.5 e no S4.10.

**Por que ficou de fora:** mexer no contrato do `/auth/me` afeta auth, sessão e todas
as telas — nenhum passo do plano pediu.

**O que eu faria:** incluir `shop_role` (e talvez `can_edit_others_leads`) no `/auth/me`
e expor `isGerente` no `useSession`. Simplifica S3.5, S4.10, S4.15 e S5.5, que todos
precisam esconder coisas por papel.

---

## 3. Testes e2e sujam o banco local do seed

**Onde:** `trivus-api/tests/` + `deploy/docker-compose.yml` (Postgres :5443).

**O que é:** os e2e rodam contra o MESMO banco do seed de demonstração e criam lojas
de verdade. O seletor de loja do app hoje mostra "AP Store", "Classified Store",
"Goals Store", "Loja Patches"… várias duplicadas.

**Por que ficou de fora:** é infra de teste; nenhum passo do plano trata disso, e os
checks passam normalmente.

**O que eu faria:** banco separado para teste (`trivus_test`) ou transação com rollback
por teste. Enquanto isso, rodar `uv run python -m scripts.seed_demo` limpa a vitrine
antes de uma demo. (Vou rodar antes do smoke final do S7.1.)

---

## 5. Outros inserts com UNIQUE ainda podem virar 500

**Onde:** `trivus-api/src/modules/` — qualquer use case que insira em coluna `UNIQUE`
sem checar antes.

**O que é:** no S3.6 descobri que criar colaborador com e-mail repetido estourava
`IntegrityError` e virava **500**, violando a regra "input inválido → 4xx, nunca 500".
Corrigi **dentro do escopo** (o `CreateTeamUserUseCase` agora checa `get_by_email`
antes de inserir e levanta `DomainError`), o que também conserta o
`POST /stores/{id}/team` que já tinha o mesmo defeito.

**O que ficou de fora:** não auditei os **demais** inserts do sistema com constraint
UNIQUE (campanhas, templates de funil, empresas…). Podem ter o mesmo problema.

**O que eu faria:** um handler global de `IntegrityError` → 409 como rede de segurança,
somado à checagem explícita onde a mensagem para o usuário importa.

---

## 4. Lead nunca movido não tem histórico de etapa

**Onde:** `trivus-api/src/modules/crm/application/` — criação de lead.

**O que é:** `crm_lead_stage_history` só recebe registro **ao mover** o lead. Lead
recém-criado tem `stage_entered_at = null`.

**Por que ficou de fora:** gravar histórico na criação é mudança no `CreateLeadUseCase`,
e o S2.4 pedia só para expor o dado existente.

**Status:** contornado no front com fallback para `created_at` (S2.5). Detalhes e a
decisão pendente estão em `DUVIDAS_PLANO13.md`.
