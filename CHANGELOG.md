# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

A hardening and correctness pass over the whole service, following a full review. Everything
below is a behaviour change, not a refactor.

### Security

- **Two-factor authentication is now enforced on the direct API.** `POST /v1/users/login`
  previously returned `requires_two_factor: true` *alongside* a usable session and refresh
  token, with no endpoint to complete the second step — 2FA was advisory for every non-browser
  client. It now returns only a short-lived `challenge_token`, exchanged at
  `POST /v1/auth/2fa/challenge`. The browser flow uses the same use case.
- **Refresh tokens rotate**, and replaying one that was already exchanged revokes the session.
- **Token introspection checks `token_use`.** A Hydra *refresh* token was accepted as a bearer
  access token, because Hydra reports both as `active`.
- **Secrets are no longer stored in readable form.** Password-reset and email-verification
  tokens are stored as SHA-256 digests, recovery codes as digests, and the TOTP seed encrypted
  with `SECRET_ENCRYPTION_KEY`.
- **Secrets no longer reach the message broker.** Events declare `sensitive_fields`; those keys
  are redacted before publishing and stripped from the stored row once handled.
- **Scope guards on every state-changing endpoint.** Account deletion, password change, 2FA
  enable/disable and session revocation previously required no OAuth scope at all.
- **Rate limiting and lockout are keyed on `(client ip, identifier)`** and resolve the client IP
  from `X-Forwarded-For` only when the peer is a configured trusted proxy. Behind any reverse
  proxy, five bad passwords used to lock out every user at once.
- **The failed-login counter resets once the lockout window elapses.** One wrong password every
  fifteen minutes previously kept a known account locked out indefinitely.
- **Enrolling a second factor now requires confirming a code** before it becomes active.
- **TOTP codes cannot be replayed** within their validity window.
- Security response headers (CSP with `frame-ancestors 'none'`, HSTS, `nosniff`,
  `Referrer-Policy`); the consent screen was framable.
- The HTTPS redirect no longer reflects the `Host` header, which was an open redirect.
- Configuration fails closed: anything other than an explicit `ENV=development` is treated as
  production and requires real secrets and shared Redis-backed cache and limiter.
- The lockout response no longer discloses the account's internal UUID.

### Fixed

- **The outbox worker no longer wedges permanently.** It held one session for the life of the
  process and never rolled back, so the first database error left every subsequent statement
  failing while the container stayed "healthy". Session and transaction are now per batch.
- **The AMQP publisher no longer leaks a connection per batch** (~86 000 a day at the default
  poll interval).
- **Verification and password-reset emails link to routes that exist.** The links pointed at
  `/users/verify-email` and `/users/reset-password`, which were never routes; the real endpoints
  required a bearer token the recipient could not have. Both are now identified by the token
  alone and have unauthenticated landing pages.
- **`revoke_all_sessions` actually revokes refresh tokens.** Sessions were loaded without their
  tokens, so the revocation mapped over an empty collection.
- **Session-revocation events are no longer dropped** on password change, password reset and
  account deletion — they reached neither the outbox nor the audit log.
- **Concurrent updates cannot both spend the same recovery code.** `users` now carries a
  `version` column and every write is conditional on it.
- Passwords over 72 bytes returned a 500 (bcrypt raises rather than truncating); the limit is
  now enforced in bytes, and the alphabet restriction that rejected passphrases and non-Latin
  scripts is gone.
- A token whose subject is not a UUID returned a 500 instead of a 401.
- Soft-deleted users are excluded in SQL rather than only in the application layer.
- `IntegrityError` on registration surfaces as a conflict, not a 500.
- Emails render with autoescaping enabled.
- One unpublishable event no longer blocks the whole outbox: publishing is per event, with
  attempts, exponential backoff and dead-lettering.

### Added

- `GET /health/live` and `GET /health/ready` with real dependency checks; the previous endpoint
  reported `healthy` with everything down.
- `GET /health/metrics` — Prometheus counters for login outcomes, 2FA verifications, sessions
  and rate-limit rejections.
- Structured JSON logging correlated by `request_id`, `trace_id` and `span_id`.
- A maintenance worker that prunes expired sessions, processed outbox rows, old audit entries
  and long soft-deleted accounts. Nothing previously deleted anything on a schedule.
- `POST /v1/auth/2fa/confirm` to activate a pending enrolment.
- A single validated `Settings` object, read once at startup.
- `acr`/`amr` are passed to Hydra, so a relying party can tell whether a second factor was used.
- Dead-letter exchange and delivery limit on the AMQP queues.
- `ARCHITECTURE.md`, `SECURITY.md`, `CONTRIBUTING.md`.

### Changed

- **Breaking:** `POST /v1/auth/reset-password` no longer takes `user_id`; the token identifies
  the user. `POST /v1/auth/verify-email` is unauthenticated for the same reason.
- **Breaking:** `POST /v1/auth/refresh` returns a new `refresh_token` on every call.
- **Breaking:** requires Python 3.14.
- Domain events are collected by the unit of work through `uow.register(aggregate)` rather than
  pulled by each use case.
- `_with()` on entities delegates to `dataclasses.replace`, so a misspelled field is an error
  rather than a silently ignored keyword.
- The event registries are keyed on the event class, not on its name.
- The database engine is configured from settings, with `pool_pre_ping`, recycling and a
  server-side statement timeout; `POSTGRES_ECHO` now defaults to off.
- Indexes added on the outbox poll query, the token-hash lookups, non-leading foreign keys and
  the audit-log entity lookup.
- Docker images run as a non-root user, install from the lockfile, and carry a healthcheck.

### Tooling

- `ruff` runs 22 rule sets and `ruff format`; previously only the default four were active,
  leaving 578 violations invisible.
- `basedpyright` at `typeCheckingMode = "all"` now also covers `tests/`, which had been excluded
  and was hiding real type errors. Zero errors across the repository.
- `import-linter` enforces the dependency rule in CI. It had already been broken in both
  directions.
- CI split into lint, typecheck, test with coverage, dependency audit, Docker build, and an
  `alembic check` against a real Postgres.

## [2.1.0] and earlier

See the git history.
