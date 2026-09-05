## What and why

<!-- What problem does this solve? Link the issue if there is one. -->

## How you know it works

<!-- The test you added, or the manual check you ran. -->

## Checklist

- [ ] `make check` passes (lint, format, layers, types, tests)
- [ ] Behaviour changes are covered by a test
- [ ] A new use case is registered in `infrastructure/di.py` and listed in `tests/e2e/test_di_graph.py`
- [ ] A new endpoint has a request in `bruno/`
- [ ] A schema change has a migration, and `alembic check` is clean
- [ ] Breaking changes are noted in `CHANGELOG.md`
