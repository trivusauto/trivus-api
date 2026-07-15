# Deploy — stack completa (banco + API + front)

Orquestração Docker Compose que sobe os três serviços juntos: PostgreSQL, a
**trivus-api** e a **trivus-web**. Complementa o deploy no Coolify (ver
[../docs/DEPLOY_COOLIFY.md](../docs/DEPLOY_COOLIFY.md)), que trata cada serviço
como recurso separado.

> Requer o repositório **trivus-web** clonado como irmão de `trivus-api`
> (`../../trivus-web`), pois o compose faz o build do front a partir dali.

## Local (valores direto no compose, sem `.env`)

```bash
cd deploy
docker compose up -d --build
```

- Front: http://localhost:3000 — login `admin@trivus.local` / `admin123`
- API:   http://localhost:3001
- Banco: `localhost:5433` (trivus / trivus / trivus)

A API roda `alembic upgrade head` + `seed_admin` no boot. Para popular um
cenário realista de demonstração:

```bash
docker compose exec api uv run python -m scripts.seed_demo
```

Derrubar: `docker compose down` (dados persistem no volume) ou
`docker compose down -v` (apaga o banco).

## Produção self-hosted (segredos via env)

```bash
cd deploy
cp .env.prod.example .env.prod   # preencha as senhas/segredos
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

O compose de produção não expõe a porta do banco e não roda o seed automático.
