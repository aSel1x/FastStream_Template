# Architecture

This document covers the decisions you will trip over while working in this codebase — the
ones that are not obvious from reading a single file, and the ones you would otherwise have to
reverse-engineer.

## The dependency rule

```
presentation/    HTTP controllers, AMQP consumers, templates, middleware
      ↓
infrastructure/  SQLAlchemy, Hydra client, Redis, SMTP, RabbitMQ, DI wiring
      ↓
application/     Use cases, application services, ports
      ↓
domain/          Entities, value objects, domain events, domain ports
```

Every arrow points down and none point up. Two rules follow, and both are **enforced in CI** by
`import-linter` (`.importlinter`, run with `make layers`):

1. A layer may only import from the layers below it.
2. `domain/` and `application/` may not import a framework — no litestar, no sqlalchemy, no
   httpx, no redis, no prometheus. `domain/` additionally may not import pydantic.

This matters because the claim is easy to make and easy to break. It has already been broken
twice in this repository's history — an application use case caught an exception class from
`infrastructure.hydra`, and a logging formatter reached into `presentation` for a ContextVar —
and both times nothing noticed until the contract was added.

When you need something from a lower layer, define a **port** (a `Protocol`) in the layer that
needs it and implement it in `infrastructure/`. See `SecretCipherInterface`, `MetricsInterface`
and `TwoFactorChallengeStore` for recent examples of exactly that.

### Where ports live

- `domain/*/interfaces/` — ports the *domain* needs to express its own rules: repositories,
  password hashing, TOTP verification, secret encryption.
- `application/common/interfaces/` — ports the *application* needs to do its job: the unit of
  work, the cache, the rate limiter, metrics, the Hydra admin API.

The rule of thumb: if an entity or a domain service calls it, it belongs in `domain/`.

## Request lifecycle

```
HTTP request
  → RequestIDMiddleware        mints/propagates X-Request-ID into a ContextVar and the span
  → HTTPSRedirectMiddleware    (production only) refuses to reflect an untrusted Host
  → SecurityHeadersMiddleware  CSP, frame-ancestors, nosniff, HSTS
  → HydraIntrospectionMiddleware
        introspects the bearer token against Hydra, cached by sha256(token);
        rejects anything whose token_use is not an access token
  → guard                      require_admin / require_scope
  → controller                 maps the HTTP shape to an Input DTO
  → use case                   orchestrates, then commits the unit of work
        → application service  drives the aggregates
             → domain          decides
        → repository           persists
  → unit of work commit
        writes the outbox rows for every event the aggregates recorded,
        runs the audit handler, then commits the transaction
```

## Aggregate mutation

Entities are frozen dataclasses. A method that changes state returns a **new instance** and
records a domain event on it:

```python
def record_successful_login(self) -> Self:
    user = self._with(account_lock=self.account_lock.record_successful_login())
    user._record_event(UserAuthenticatedEvent(...))
    return user
```

`_with` delegates to `dataclasses.replace`, so a misspelled field name is a `TypeError` rather
than a silently ignored keyword. (It previously used `__new__` plus `object.__setattr__`, which
accepted `role._with(nmae=...)` and returned an object carrying the *old* name and a phantom
attribute.)

## Domain events

An aggregate records events; it never publishes them. Collection happens in one place:

```python
user = user.record_successful_login()
await self._user_repo.update(user)
self._uow.register(user)          # ← the service registers what it mutated
...
await self._uow.commit()          # ← the UoW drains every registered aggregate
```

Registering rather than pulling events at the call site is deliberate. When each use case
pulled events off the aggregates it happened to hold, everything a service mutated behind its
back was lost — every session revoked by a password change emitted nothing to the outbox and
nothing to the audit log. `tests/unit/test_event_collection.py` pins that behaviour.

### The outbox

`SQLAlchemyUoW.commit()` writes an `outbox_events` row per event **in the same transaction** as
the state change, so there is no window where one committed and the other did not. A separate
`outbox_worker` process relays them to a `domain_events` topic exchange.

Two properties worth knowing:

- **Secrets never reach the broker.** An event declares `sensitive_fields`; the publisher
  redacts those keys before publishing, and `mark_processed` strips them from the stored row.
  A password-reset token lives in the database only for as long as it takes the worker to
  render the email.
- **A poison message cannot block the queue.** Events publish individually; a failure
  increments `attempts`, sets `next_attempt_at` with exponential backoff, and dead-letters the
  event past `MAX_ATTEMPTS`.

## Persistence

SQLAlchemy **Core** (`Table` objects), not the ORM, with hand-written mapping functions per
aggregate. The trade: no identity map and no lazy loading to reason about, at the cost of
writing the mapping yourself. `OutboxEvent` is the one declarative model, because the outbox is
infrastructure's own bookkeeping rather than a domain aggregate.

`users` carries a `version` column and every update is conditional on it. Without it, two
concurrent requests could both spend the same 2FA recovery code, and parallel failed logins
lost increments of the lockout counter — defeating the only application-level brute-force
defence that is not per-IP.

## Two-factor authentication

A correct password alone yields nothing usable when the account has a second factor:

```
POST /v1/users/login          → { requires_two_factor: true, challenge_token: "..." }
POST /v1/auth/2fa/challenge   → { session_id, refresh_token }
```

The browser flow through Hydra uses the same `CompleteTwoFactorUseCase`, so the two entry
points cannot disagree about whether 2FA is enforced. Challenges are one-shot, expire in five
minutes, and are burned after five wrong codes. Accepted codes are remembered for two minutes,
because verifying a TOTP code does not consume it and its window is wide enough to replay.

## Adding a new aggregate

1. `domain/<context>/entities/` — the aggregate, its value objects, its events.
2. `domain/<context>/interfaces/persistence/` — the repository port.
3. `application/<context>/commands/` and `queries/` — one class per use case, each taking an
   Input dataclass and returning an Output dataclass.
4. `infrastructure/db/sqlalchemy/models/` and `repositories/` — the table and the mapping.
5. An Alembic migration: `make migration`, then read what it generated.
6. `infrastructure/di.py` — register the repository and every use case.
7. `presentation/http/controllers/` — the controller, and a Bruno request under `bruno/`.
8. Add the use case to `tests/e2e/test_di_graph.py`, which fails if a use case is registered
   but not constructible.

## Testing

- `tests/unit/` — domain and application, no I/O.
- `tests/e2e/` — the real Litestar app, the real DI graph, the real SQLAlchemy models, with
  the database session doubled. Not yet a real Postgres; that is the most valuable gap left.

`basedpyright` runs in `typeCheckingMode = "all"` over `src/` **and** `tests/` with zero errors
and three `pyright: ignore` comments in the whole repository. Tests run at a slightly relaxed
rule set (see `pyproject.toml`) because pytest fixtures and `MagicMock` are Unknown-typed by
construction; everything else stays on.

## Deliberate non-goals

Not implemented, and not planned unless someone needs them: SCIM provisioning, social/upstream
IdP federation, multi-tenancy, an admin web UI, WebAuthn/passkeys, and device flow. The
service is a login and consent provider for Ory Hydra, not an identity platform.
