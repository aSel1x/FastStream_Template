# Backend Template

**Ory Hydra doesn't ship a login UI. This is one — in Python.**

Hydra is an OpenID Certified® OAuth2 and OIDC server that deliberately does not handle
credentials. It delegates that to a *login and consent provider* you write yourself. Ory's own
reference implementations are Go and Node; this is a complete one in Python, with the parts a
real deployment needs already built.

[![CI](https://github.com/aSel1x/Backend_Template/actions/workflows/ci.yml/badge.svg)](https://github.com/aSel1x/Backend_Template/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![Litestar](https://img.shields.io/badge/litestar-2.x-202235.svg)](https://litestar.dev/)
[![Ory Hydra](https://img.shields.io/badge/ory%20hydra-v26-5528ff.svg)](https://www.ory.sh/hydra/)
[![basedpyright: all](https://img.shields.io/badge/basedpyright-all-1e824c.svg)](https://docs.basedpyright.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Status: a reference implementation you can run and fork**, not a product. It boots, the
> flows work end to end, and the architecture is worth copying. It has no production mileage,
> no load numbers and no Helm chart. Read [ARCHITECTURE.md](ARCHITECTURE.md) before building on
> it, and [SECURITY.md](SECURITY.md) for the threat-model boundaries.

## Why this rather than the alternatives

|                                   | This | Keycloak / Zitadel | FastAPI auth boilerplate |
|-----------------------------------|:----:|:------------------:|:------------------------:|
| Tokens issued by a certified OIDC server | ✅ Hydra | ✅ | ❌ hand-rolled JWT |
| Login/consent UI you own and can restyle | ✅ Jinja | ⚠️ theming SPI | ✅ |
| Written in the language of your team     | ✅ Python | ❌ Java / Go | ✅ |
| Token revocation, introspection, rotation | ✅ | ✅ | ❌ usually absent |
| Something to read and learn from          | ✅ ~12k lines | ❌ | ⚠️ varies |
| Runs the whole stack in one command       | ✅ | ⚠️ | ✅ |

Pick Keycloak if you want a finished product. Pick this if you have chosen Hydra and now need
the half Hydra deliberately leaves to you — or if you want a non-toy Python application built
on DDD and Clean Architecture to read.

## What's in it

- **The Hydra bridge** — login, consent and logout challenge handling, with styled pages, plus
  an admin API for OAuth2 client management.
- **Authentication** — registration, login, email verification, password reset, TOTP 2FA with
  recovery codes, refresh tokens with rotation and replay detection.
- **RBAC** — roles, permissions, assignment, an admin-guarded management API.
- **Sessions** — multi-device tracking, per-session and bulk revocation that also kills the
  Hydra-side grants.
- **Audit log** — every meaningful domain event recorded in the same transaction.
- **Transactional outbox** — events persisted with the state change that produced them, then
  relayed to RabbitMQ with retry, backoff and dead-lettering.
- **Operations** — real readiness probes, Prometheus metrics, structured JSON logs correlated
  by request and trace id, and a maintenance worker that keeps the tables from growing forever.

42 application endpoints, 33 use cases, 21 domain events, 296 tests.

## Quick start

```bash
git clone https://github.com/aSel1x/Backend_Template && cd Backend_Template
cp .env.dist .env          # then set the three change-me secrets
make build                 # postgres, redis, rabbitmq, hydra, api, workers
curl localhost:8000/health/ready
```

Generate the secrets with `openssl rand -hex 32`. The service refuses to start with the
placeholders outside development — see [Configuration](#configuration).

Then open the interactive API docs at <http://localhost:8000/schema>, or walk the whole OIDC
flow with the [Bruno](https://www.usebruno.com/) collection in `bruno/` — 37 requests
covering every endpoint, plus the login/consent dance. Pick the **Local** environment.

## The OIDC flow

This service is **not** the OAuth2 server. Hydra is. This is the app Hydra redirects to.

```mermaid
sequenceDiagram
    participant C as Client app
    participant H as Ory Hydra
    participant S as This service
    participant U as User

    C->>H: GET /oauth2/auth
    H->>S: redirect ?login_challenge=…
    S->>U: login form
    U->>S: username + password
    Note over S: credentials checked;<br/>if 2FA is on, a challenge is issued<br/>and no session exists yet
    U->>S: TOTP or recovery code
    S->>H: accept login (amr=[pwd,otp], acr=urn:acr:2fa)
    H->>S: redirect ?consent_challenge=…
    S->>U: consent screen
    U->>S: approve scopes
    S->>H: accept consent (+ id_token claims)
    H->>C: authorization code → access / refresh / ID tokens
```

`POST /v1/users/login` is a separate, direct API login for non-browser clients. It issues this
service's own session and refresh token rather than going through Hydra, and carries no OIDC
scopes or claims.

## Following one request

`POST /v1/users/login`, all the way down:

| Layer | File |
|---|---|
| Route, request/response schema | `presentation/http/controllers/user.py` |
| Client IP behind a trusted proxy | `presentation/http/client_ip.py` |
| Orchestration, rate limiting, 2FA branch | `application/user/commands/login.py` |
| Credential check, session creation | `application/user/services.py` |
| Lockout rules, the authentication event | `domain/user/entities/user.py` |
| Row mapping, optimistic locking | `infrastructure/db/sqlalchemy/repositories/user.py` |
| Outbox write + audit, then commit | `infrastructure/db/sqlalchemy/uow.py` |

## Configuration

Everything is read once, at startup, by `infrastructure/settings.py`, which **refuses to boot**
on a configuration that would fail later or fail silently. Outside `ENV=development` it
requires real secrets and a Redis-backed cache and limiter — the in-memory ones are per-process
and silently break pending 2FA challenges and rate limits across replicas.

`.env.dist` documents every variable. The ones that matter most:

| Variable | Why |
|---|---|
| `APP_SECRET_KEY` | Signs CSRF tokens. Random per process if unset, which breaks multi-worker. |
| `SECRET_ENCRYPTION_KEY` | Encrypts TOTP seeds at rest. **Changing it invalidates every enrolled second factor.** |
| `TRUSTED_PROXIES` | CIDRs allowed to set `X-Forwarded-For`. Empty means nothing is in front of the app. |
| `PUBLIC_HOST` | Where the HTTPS redirect sends browsers. Reflecting `Host` would be an open redirect. |
| `CACHE_BACKEND`, `RATE_LIMIT_BACKEND` | `redis` outside development. |

## Development

```bash
uv sync --group dev
make check        # lint + format + layers + types + tests, i.e. what CI runs
```

| Command | |
|---|---|
| `make build` / `start` / `stop` / `restart` | the docker stack |
| `make test` / `cov` | tests, with or without coverage |
| `make lint` / `format` / `typecheck` | ruff, ruff format, basedpyright |
| `make layers` | the dependency rule, via import-linter |
| `make migration` / `migrate` | generate / apply Alembic migrations |
| `make logs-api` / `logs-outbox` / … | tail a service |

Without Docker you still need Postgres, Redis, RabbitMQ and Hydra reachable — bring up just the
infrastructure with `docker compose up -d postgres redis rabbitmq hydra`, then:

```bash
POSTGRES_HOST=localhost uv run alembic -c alembic.ini upgrade head
POSTGRES_HOST=localhost uv run uvicorn presentation.http.app:get_litestar --factory --reload
```

## Layout

```
src/
  domain/          entities, value objects, events, domain ports — no framework imports
  application/     use cases (one class per command/query), services, ports
  infrastructure/  SQLAlchemy, Hydra, Redis, SMTP, RabbitMQ, DI, settings, observability
  presentation/
    http/          Litestar controllers, guards, middleware, Jinja templates
    amqp/          FastStream consumers
tests/
  unit/            domain and application, no I/O
  e2e/             the real app, the real DI graph, the real models
```

[ARCHITECTURE.md](ARCHITECTURE.md) explains the dependency rule, how aggregates mutate, how
domain events are collected, and how to add your own bounded context.

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The most useful
contributions right now are listed as good-first-issues: binding queues for the domain events
that do not yet have consumers, and a testcontainers harness so `tests/e2e/` runs against a
real Postgres.

## License

MIT — see [LICENSE](LICENSE).
