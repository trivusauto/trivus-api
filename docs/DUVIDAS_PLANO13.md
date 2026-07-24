# Dúvidas e decisões do Plano 13

Registro de pontos em que o baby steps ficou ambíguo ou o código real divergiu do
esperado. Cada item traz o passo, o que travou e a decisão tomada para seguir.

---

## S2.4 / S2.5 — `stage_entered_at` de lead nunca movido

**O que aconteceu:** o baby steps assume que todo lead tem data de entrada na etapa
atual. Na prática, `crm_lead_stage_history` só recebe registro **ao mover** o lead —
um lead recém-criado (ou nunca movido) não tem histórico, então `stage_entered_at`
vem `null`.

**O que eu fiz:** mantive o backend fiel ao dado existente (`null` quando não há
histórico) e, no card do CRM (S2.5), fiz **fallback para `created_at`** — o lead está
naquela etapa desde que entrou no funil. O teste e2e cobre os dois casos.

**Precisa de decisão do Giovani:** se o correto for gravar histórico também na criação
do lead (passando a existir data para todo mundo), é uma mudança no `CreateLeadUseCase`
que está fora do escopo do S2.4. Enquanto isso, o fallback resolve a UI sem inventar dado.
