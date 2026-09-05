"""Shared pytest configuration and fixtures."""

import os
from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from infrastructure.db.memory.uow import InMemoryUoW

# A deterministic, development-shaped environment for every test. Without ENV the app boots in
# its fail-closed production mode and refuses to start without a real APP_SECRET_KEY.
_TEST_ENV = {
    'ENV': 'development',
    'APP_SECRET_KEY': 'test-secret-key-that-is-at-least-32-chars-long',
    'SECRET_ENCRYPTION_KEY': 'test-encryption-key-that-is-at-least-32-chars',
    'POSTGRES_ECHO': 'false',
    'CACHE_BACKEND': 'memory',
    'RATE_LIMIT_BACKEND': 'memory',
}


@pytest.fixture(autouse=True, scope='session')
def _test_environment() -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in _TEST_ENV}
    os.environ.update(_TEST_ENV)
    yield
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def uow() -> InMemoryUoW:
    """A real unit of work rather than a mock.

    It records what was committed, so a test can assert on the events an operation emitted
    instead of on which methods happened to be called.
    """
    from infrastructure.db.memory.uow import InMemoryUoW

    return InMemoryUoW()
