# Backend Template

A reference User Identity microservice: Clean Architecture / DDD, [Litestar](https://litestar.dev/),
SQLAlchemy, and [Ory Hydra](https://www.ory.sh/hydra/) as the OIDC/OAuth2 provider — with RBAC,
2FA, sessions, an audit log, and a transactional outbox over RabbitMQ.

## Features

- **Authentication** — username/password registration and login, email verification, password
  reset, TOTP-based 2FA with backup codes, refresh tokens.
- **OIDC / OAuth2** — Ory Hydra is the actual token issuer; this service implements the
  login/consent/logout bridge Hydra delegates to, plus an admin API for managing OAuth clients.
- **RBAC** — roles, permissions, role assignment, admin-guarded management API.
- **Sessions** — multi-device session tracking with per-session and bulk revocation.
- **Audit log** — every meaningful domain event (login, lockout, role changes, ...) is recorded.
- **Transactional outbox** — domain events are persisted in the same transaction as the state
  change that produced them, then relayed to RabbitMQ by a separate outbox worker — no dual-write
  problem.
- **Rate limiting** — login, registration, and password-reset endpoints are rate-limited (Redis or
  in-memory backend).

## Architecture

Four layers, each only depending on the ones "below" it:

```
presentation/    Litestar HTTP controllers + FastStream AMQP consumers. Talks to application/
                 through use cases (commands/queries) via dishka dependency injection.
application/     Use cases (one class per command/query) orchestrating domain objects through
                 ports (Protocol interfaces) — never touches infrastructure directly.
domain/          Entities, value objects, domain events, domain services. Pure Python — no
                 framework, database, or HTTP imports.
infrastructure/  SQLAlchemy repositories, the Hydra HTTP client, Redis cache/rate-limiter, SMTP
                 sender, RabbitMQ publisher — the concrete implementations of application's ports.
```

Dependencies point inward only: `presentation → application → domain`, with `infrastructure`
plugged in at the edges via `infrastructure/di.py` (a [dishka](https://github.com/reagento/dishka)
provider). `domain/` has zero framework imports — it's tested and reasoned about independent of
Litestar, SQLAlchemy, or anything else.

### OIDC login/consent flow

This service is **not** an OAuth2/OIDC server itself — Ory Hydra is. This service is Hydra's
*login and consent provider*: when a client starts an OAuth2 flow, Hydra redirects the browser
here to authenticate the user and collect consent, then resumes the flow itself.

```
Client app → Hydra /oauth2/auth → redirects to → this service's /auth/login (login_challenge)
                                                       ↓ (credential check, optional 2FA)
                                                   accepts the challenge via Hydra's admin API
                                                       ↓
                                  Hydra → redirects to → this service's /auth/consent (consent_challenge)
                                                       ↓ (user approves requested scopes)
                                                   accepts the challenge via Hydra's admin API
                                                       ↓
                                  Hydra issues the actual access/refresh/ID tokens → redirects back to client
```

`POST /v1/users/login` is a separate, direct API login for non-browser clients (mobile apps,
service-to-service) — it issues this service's own session + refresh token rather than going
through Hydra, and does not carry OIDC scopes/claims.

### Events: outbox → RabbitMQ

Every domain event is written to an `outbox_events` table in the same transaction as the change
that raised it. A separate `outbox_worker` process polls that table and relays events to a
`domain_events` topic exchange in RabbitMQ, then marks them processed. Only 4 event types
currently have a bound queue (`presentation/amqp/consumers/`) as a worked example — the rest are
still published to the exchange and are there for you to bind a queue to when you need them; see
`domain/user/events.py` for the full list.

## Quick start

```bash
cp .env.dist .env        # edit values — at minimum change the two "change-me" secrets
make build                # docker compose build + up (Postgres, Redis, RabbitMQ, Hydra, API, ...)
```

The API is then at `http://localhost:8000`, with interactive docs at `http://localhost:8000/schema`.
Ory Hydra's public endpoint is at `http://localhost:4444`.

### Local development without Docker

```bash
uv sync --group dev
POSTGRES_HOST=localhost uv run alembic -c alembic.ini upgrade head
uv run uvicorn presentation.http.app:get_litestar --factory --reload
```

This still requires Postgres, Redis, RabbitMQ, and Hydra to be reachable (e.g. run just the
infra services from `docker-compose.yaml`: `docker-compose up postgres redis rabbitmq hydra`).

### Trying it out by hand

The `bruno/` directory is a click-through [Bruno](https://www.usebruno.com/) collection covering
every endpoint, including the Hydra OIDC login/consent dance (open Bruno, open the folder, pick the
**Local** environment) — see its root Docs tab for the walkthrough. No curl, no hand-written JSON.

## `make` commands

| Command | Description |
|---|---|
| `make build` | Build images and start every service |
| `make start` / `make stop` / `make restart` | Start / stop / restart the stack |
| `make logs-api` / `logs-queue` / `logs-outbox` / `logs-rabbitmq` / `logs-redis` / `logs-hydra` | Tail a service's logs |
| `make migration` | Generate an Alembic migration from the current models (`alembic revision --autogenerate`) |
| `make rabbitmq-ui` | Open the RabbitMQ management UI |

## Testing

```bash
uv run ruff check .        # lint
uv run basedpyright        # type check
uv run pytest tests        # unit + e2e tests
```

## Project layout

```
src/
  domain/            Entities, value objects, domain events — per bounded context (user, audit)
  application/        Use cases (commands/queries), application services, ports (interfaces)
  infrastructure/     SQLAlchemy, Hydra client, Redis, SMTP, RabbitMQ — port implementations + DI
  presentation/
    http/              Litestar controllers, guards, middleware, Jinja templates (login/consent)
    amqp/               FastStream consumers for the domain-event exchange
tests/
  unit/                Domain and application-layer tests (no I/O)
  e2e/                 Tests that exercise the real Litestar app / SQLAlchemy models
```

## License

MIT — see [LICENSE](LICENSE).
