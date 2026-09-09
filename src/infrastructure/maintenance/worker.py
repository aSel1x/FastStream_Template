"""The janitor.

Every table in this service grew without bound: sessions were never deleted once expired,
processed outbox rows were never pruned (the repository method existed and had no callers),
audit entries were kept forever, and a soft-deleted account held its username and email
hostage for good.

Each job is independent and idempotent, so one failing job does not stop the others, and a
run that dies halfway can simply be repeated.
"""

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import final

from sqlalchemy import Text, delete, func, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.db.sqlalchemy.models.audit import AUDIT_LOGS_TABLE
from infrastructure.db.sqlalchemy.models.session import SESSIONS_TABLE
from infrastructure.db.sqlalchemy.repositories.outbox import OutboxRepository
from infrastructure.maintenance.config import MaintenanceConfig

logger = logging.getLogger(__name__)

type Job = Callable[[AsyncSession, datetime], Awaitable[int]]


def _rows_affected(result: object) -> int:
    """`Session.execute` is typed as returning `Result`, which has no rowcount."""
    return result.rowcount if isinstance(result, CursorResult) else 0


@final
class MaintenanceWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        config: MaintenanceConfig,
    ) -> None:
        self._session_factory = session_factory
        self._config = config
        self._stopping = asyncio.Event()

    def _jobs(self) -> dict[str, Job]:
        return {
            'expired_sessions': self._purge_expired_sessions,
            'processed_outbox': self._prune_outbox,
            'old_audit_entries': self._prune_audit_log,
            'deleted_users': self._anonymise_deleted_users,
        }

    async def start(self) -> None:
        logger.info('Maintenance worker started', extra={'dry_run': self._config.dry_run})

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._stopping.set)

        while not self._stopping.is_set():
            _ = await self.run_once()
            try:
                _ = await asyncio.wait_for(
                    self._stopping.wait(), timeout=self._config.interval_seconds
                )
            except TimeoutError:
                continue

        logger.info('Maintenance worker stopped')

    def stop(self) -> None:
        self._stopping.set()

    async def run_once(self) -> dict[str, int]:
        """Run every job once. Returns rows affected per job."""
        now = datetime.now(UTC)
        results: dict[str, int] = {}
        for name, job in self._jobs().items():
            try:
                async with self._session_factory() as session, session.begin():
                    affected = await job(session, now)
                    if self._config.dry_run:
                        await session.rollback()
                    results[name] = affected
            except Exception:
                # One job failing must not stop the rest; the next run retries it.
                logger.exception('Maintenance job failed', extra={'job': name})
                results[name] = -1
        logger.info('Maintenance run finished', extra={'results': results})
        return results

    async def _purge_expired_sessions(self, session: AsyncSession, now: datetime) -> int:
        cutoff = now - timedelta(days=self._config.session_grace_days)
        # refresh_tokens.session_id cascades, so the tokens go with the sessions.
        result = await session.execute(
            delete(SESSIONS_TABLE).where(SESSIONS_TABLE.c.expires_at < cutoff)
        )
        return _rows_affected(result)

    async def _prune_outbox(self, session: AsyncSession, now: datetime) -> int:
        cutoff = now - timedelta(days=self._config.outbox_retention_days)
        return await OutboxRepository(session).delete_processed_older_than(cutoff)

    async def _prune_audit_log(self, session: AsyncSession, now: datetime) -> int:
        cutoff = now - timedelta(days=self._config.audit_retention_days)
        result = await session.execute(
            delete(AUDIT_LOGS_TABLE).where(AUDIT_LOGS_TABLE.c.timestamp < cutoff)
        )
        return _rows_affected(result)

    async def _anonymise_deleted_users(self, session: AsyncSession, now: datetime) -> int:
        """Strip personal data from long soft-deleted accounts.

        Anonymised rather than deleted: audit entries and role assignments reference the id,
        and a hard delete would either cascade them away or fail. The username and email are
        released so they can be registered again.
        """
        from infrastructure.db.sqlalchemy.models.user import USERS_TABLE

        cutoff = now - timedelta(days=self._config.deleted_user_retention_days)
        result = await session.execute(
            update(USERS_TABLE)
            .where(
                USERS_TABLE.c.deleted_at.isnot(None),
                USERS_TABLE.c.deleted_at < cutoff,
                USERS_TABLE.c.email.isnot(None),
            )
            .values(
                # A stable, non-identifying placeholder that keeps the unique constraint
                # satisfied while releasing the original username.
                username=func.concat(
                    'deleted_', func.replace(USERS_TABLE.c.id.cast(Text), '-', '')
                ),
                email=None,
                hashed_password=b'',
                two_factor_secret=None,
                two_factor_backup_codes=None,
                email_verification_token_hash=None,
                password_reset_token_hash=None,
            )
        )
        return _rows_affected(result)


async def run_worker(database_url: str, config: MaintenanceConfig) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True, pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        await MaintenanceWorker(session_factory, config).start()
    finally:
        await engine.dispose()


async def main() -> None:
    from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
    from infrastructure.observability.logging import configure_logging

    configure_logging()
    await run_worker(SQLAlchemyConfig.from_environ().full_url, MaintenanceConfig.from_environ())


if __name__ == '__main__':
    asyncio.run(main())
