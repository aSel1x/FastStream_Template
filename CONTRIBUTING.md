# Contributing

## Setup

```bash
uv sync --group dev
cp .env.dist .env
make check          # lint + format + layers + types + tests
```

`make check` is exactly what CI runs. If it passes locally it passes there.

You need Python 3.14 (`.python-version` pins it; `uv` will fetch it). Running the app needs
Postgres, Redis, RabbitMQ and Hydra — `make build` brings all of them up.

## The rules that are actually enforced

1. **The dependency rule.** `presentation → infrastructure → application → domain`, and
   `domain/`/`application/` import no framework. `import-linter` fails the build otherwise.
   If you need something from a lower layer, define a `Protocol` port and implement it in
   `infrastructure/`.
2. **`basedpyright` at `typeCheckingMode = "all"`, zero errors**, over `src/` and `tests/`.
   There are three `pyright: ignore` comments in the whole repository; adding a fourth needs a
   comment explaining why the type system is wrong rather than the code.
3. **`ruff check` and `ruff format`**, with the rule set in `pyproject.toml`.

## Where things go

| You are adding | It goes in |
|---|---|
| A rule about what is valid | `domain/` — an entity method or a value object |
| A step-by-step operation | `application/<context>/commands/` or `queries/`, one class per use case |
| A way to talk to the outside world | a `Protocol` in the layer that needs it, implemented in `infrastructure/` |
| An endpoint | `presentation/http/controllers/` **and** a request in `bruno/` |

Every use case takes an Input dataclass and returns an Output dataclass, and must be registered
in `infrastructure/di.py` **and** listed in `tests/e2e/test_di_graph.py` — that test fails if a
use case is registered but not constructible.

[ARCHITECTURE.md](ARCHITECTURE.md) walks through adding a whole bounded context.

## Database changes

```bash
make migration      # alembic revision --autogenerate
```

Read what it generated — autogenerate misses index and server-default changes routinely. CI
runs `alembic check` against a real Postgres and fails if the models and migrations disagree.

## Tests

- `tests/unit/` — domain and application, no I/O.
- `tests/e2e/` — the real app and DI graph, database session doubled.

Write the test that fails for the reason you care about. `tests/unit/test_event_collection.py`
and `tests/unit/test_two_factor_enforcement.py` are the style to copy: each one pins a specific
behaviour that used to be wrong, and says so in the assertion message.

## Commits and pull requests

Conventional-ish subject lines (`fix:`, `feat:`, `refactor:`, `docs:`), imperative mood,
explaining *why* in the body when the change is not obvious.

A pull request should say what problem it solves and how you know it works. If it changes
behaviour, it changes a test.

## Good first issues

- Bind queues for the domain events that have no consumer yet — see `domain/user/events.py`
  for the full list and `presentation/amqp/consumers/user.py` for the pattern.
- A testcontainers harness so `tests/e2e/` runs against a real Postgres instead of a doubled
  session. This is the most valuable gap in the suite.
- A `create-superuser` CLI, so bootstrapping the first admin does not mean registering over
  HTTP and pasting a UUID into `.env`.
