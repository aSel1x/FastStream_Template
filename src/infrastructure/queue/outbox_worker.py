import asyncio
import logging
import signal
from pathlib import Path
from typing import final

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domain.common.json_value import JsonValue
from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent
from infrastructure.db.sqlalchemy.repositories.outbox import OutboxRepository
from infrastructure.email import EmailConfig, EmailSenderInterface
from infrastructure.queue.config import RabbitMQConfig
from infrastructure.queue.event_publisher import EventPublisherAMQP

logger = logging.getLogger(__name__)

# Beside the sender, not under presentation/: the outbox worker is not an HTTP concern,
# and infrastructure reaching into the presentation tree is the dependency rule backwards.
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / 'email/templates'

# Built once. Autoescape is not jinja2's default, and these templates interpolate a URL that
# carries a user-supplied token.
_TEMPLATES = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml']),
)

_EMAIL_TEMPLATES: dict[str, tuple[str, str, str, int]] = {
    # event_type -> (token payload key, template, subject, link expiry in hours)
    'EmailVerificationRequestedEvent': (
        'verification_token',
        'verify.html',
        'Verify your email',
        24,
    ),
    'PasswordResetRequestedEvent': (
        'reset_token',
        'reset_password.html',
        'Reset your password',
        1,
    ),
}

_EMAIL_PATHS: dict[str, str] = {
    'EmailVerificationRequestedEvent': '/v1/auth/verify-email',
    'PasswordResetRequestedEvent': '/v1/auth/reset-password',
}


@final
class OutboxWorker:
    """Relays the transactional outbox to RabbitMQ.

    Each poll runs in its own session and its own transaction: a session held for the whole
    process cannot recover from a single database error, and a transaction left open by an
    early return pins `FOR UPDATE` locks and the vacuum horizon indefinitely.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: EventPublisherAMQP,
        email_sender: EmailSenderInterface | None = None,
        email_config: EmailConfig | None = None,
        batch_size: int = 100,
        poll_interval: float = 1.0,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher
        self._email_sender = email_sender
        self._email_config = email_config
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        logger.info('Outbox worker started')

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._stopping.set)

        consecutive_failures = 0
        while not self._stopping.is_set():
            try:
                await self._process_batch()
                consecutive_failures = 0
            except Exception:
                consecutive_failures += 1
                logger.exception(
                    'Outbox batch failed (%d consecutive)',
                    consecutive_failures,
                )

            # Back off when the database or broker is down instead of hammering it at 1 Hz.
            backoff: int = min(1 << consecutive_failures, 30)
            delay: float = self._poll_interval * backoff
            try:
                _ = await asyncio.wait_for(self._stopping.wait(), timeout=delay)
            except TimeoutError:
                continue

        await self._publisher.close()
        logger.info('Outbox worker stopped')

    def stop(self) -> None:
        self._stopping.set()

    async def _process_batch(self) -> None:
        # A fresh session per batch: a poisoned connection cannot outlive one iteration.
        async with self._session_factory() as session, session.begin():
            repo = OutboxRepository(session)
            events = await repo.get_unprocessed(self._batch_size)
            if not events:
                return

            failures = await self._publisher.publish_outbox(events)
            failed_ids = {failure.event_id for failure in failures}
            errors = {failure.event_id: failure.error for failure in failures}

            published = [event for event in events if event.id not in failed_ids]

            # Send before marking processed: an email dropped after the row is committed as
            # done can never be retried, and there is no resend endpoint to fall back on.
            await self._send_emails(published)

            await repo.mark_processed(published)
            for event in events:
                if event.id in failed_ids:
                    await repo.reschedule(event, errors[event.id])

            if published:
                logger.info('Relayed %d outbox events', len(published))
            if failures:
                logger.warning('%d outbox events deferred for retry', len(failures))

    async def _send_emails(self, events: list[OutboxEvent]) -> None:
        if self._email_sender is None or self._email_config is None:
            return
        for event in events:
            if event.event_type not in _EMAIL_TEMPLATES:
                continue
            try:
                await self._send_email(event, self._email_sender, self._email_config)
            except Exception:
                # One bad address must not fail the batch; the event is still relayed.
                logger.exception('Failed to send email for outbox event %s', event.id)

    async def _send_email(
        self,
        event: OutboxEvent,
        sender: EmailSenderInterface,
        config: EmailConfig,
    ) -> None:
        token_key, template_name, subject, expires_in_hours = _EMAIL_TEMPLATES[event.event_type]
        payload: dict[str, JsonValue] = event.payload

        recipient = payload.get('email')
        token = payload.get(token_key)
        if not isinstance(recipient, str) or not recipient or not isinstance(token, str):
            logger.warning('Outbox event %s has no usable email payload', event.id)
            return

        url = f'{config.app_base_url}{_EMAIL_PATHS[event.event_type]}?token={token}'
        body = _TEMPLATES.get_template(template_name).render(
            action_url=url,
            expires_in_hours=expires_in_hours,
        )
        await sender.send(to=recipient, subject=subject, body=body)
        logger.info('Sent %s email for outbox event %s', event.event_type, event.id)


async def run_worker(
    database_url: str,
    rabbitmq_config: RabbitMQConfig,
    email_sender: EmailSenderInterface | None = None,
    email_config: EmailConfig | None = None,
    batch_size: int = 100,
    poll_interval: float = 1.0,
) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    publisher = EventPublisherAMQP(rabbitmq_config)
    worker = OutboxWorker(
        session_factory=session_factory,
        publisher=publisher,
        email_sender=email_sender,
        email_config=email_config,
        batch_size=batch_size,
        poll_interval=poll_interval,
    )
    try:
        await worker.start()
    finally:
        await engine.dispose()


async def main() -> None:
    from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
    from infrastructure.email import SMTPSender

    logging.basicConfig(level=logging.INFO)

    db_config = SQLAlchemyConfig.from_environ()
    rabbitmq_config = RabbitMQConfig.from_environ()
    email_config = EmailConfig.from_environ()

    await run_worker(
        database_url=db_config.full_url,
        rabbitmq_config=rabbitmq_config,
        email_sender=SMTPSender(email_config),
        email_config=email_config,
    )


if __name__ == '__main__':
    asyncio.run(main())
