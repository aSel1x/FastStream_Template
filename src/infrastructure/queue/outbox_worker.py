import asyncio
import logging
import signal
from pathlib import Path
from typing import final
from uuid import UUID

from domain.common.json_value import JsonValue
from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent
from infrastructure.db.sqlalchemy.repositories.outbox import OutboxRepository
from infrastructure.email import EmailConfig, EmailSenderInterface
from infrastructure.queue.config import RabbitMQConfig
from infrastructure.queue.event_publisher import EventPublisherAMQP

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / 'presentation/http/templates/email'


@final
class OutboxWorker:
    def __init__(
        self,
        outbox_repo: OutboxRepository,
        publisher: EventPublisherAMQP,
        email_sender: EmailSenderInterface | None = None,
        email_config: EmailConfig | None = None,
        batch_size: int = 100,
        poll_interval: float = 1.0,
    ) -> None:
        self._outbox_repo = outbox_repo
        self._publisher = publisher
        self._email_sender = email_sender
        self._email_config = email_config
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._running = False

    async def start(self) -> None:
        self._running = True
        logger.info('Outbox worker started')

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error('Error processing outbox batch: %s', e)

            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info('Outbox worker stopped')

    async def _process_batch(self) -> None:
        events = await self._outbox_repo.get_unprocessed(self._batch_size)

        if not events:
            return

        event_ids: list[UUID] = [event.id for event in events]

        try:
            await self._publisher.publish_outbox(events)
        except Exception as e:
            logger.error('Failed to publish outbox events: %s', e)
            return

        await self._outbox_repo.mark_processed(event_ids)
        logger.info('Processed %d outbox events', len(events))

        if self._email_sender and self._email_config:
            for event in events:
                try:
                    await self._handle_email_event(event)
                except Exception as e:
                    logger.error('Failed to send email for outbox event %s: %s', event.id, e)

    async def _handle_email_event(self, event: OutboxEvent) -> None:
        if not self._email_sender or not self._email_config:
            return
        sender: EmailSenderInterface = self._email_sender
        config: EmailConfig = self._email_config

        event_type = event.event_type
        if event_type == 'EmailVerificationRequestedEvent':
            await self._send_verification_email(event.payload, sender, config)
        elif event_type == 'PasswordResetRequestedEvent':
            await self._send_reset_email(event.payload, sender, config)

    async def _send_verification_email(
        self, payload: dict[str, JsonValue], sender: EmailSenderInterface, config: EmailConfig,
    ) -> None:
        from jinja2 import Environment, FileSystemLoader

        email = payload.get('email')
        token = payload.get('verification_token')
        if not isinstance(email, str) or not isinstance(token, str):
            return

        verification_url = f'{config.app_base_url}/users/verify-email?token={token}'

        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        template = env.get_template('verify.html')
        body = template.render(
            verification_url=verification_url,
            expires_in_hours=24,
        )

        await sender.send(
            to=email,
            subject='Verify your email',
            body=body,
        )
        logger.info('Sent verification email to %s', email)

    async def _send_reset_email(
        self, payload: dict[str, JsonValue], sender: EmailSenderInterface, config: EmailConfig,
    ) -> None:
        from jinja2 import Environment, FileSystemLoader

        email = payload.get('email')
        token = payload.get('reset_token')
        if not isinstance(email, str) or not isinstance(token, str):
            return

        reset_url = f'{config.app_base_url}/users/reset-password?token={token}'

        env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        template = env.get_template('reset_password.html')
        body = template.render(
            reset_url=reset_url,
            expires_in_hours=1,
        )

        await sender.send(
            to=email,
            subject='Reset your password',
            body=body,
        )
        logger.info('Sent password reset email to %s', email)


class OutboxProcessor:
    @staticmethod
    async def run(
        database_url: str,
        rabbitmq_config: RabbitMQConfig,
        email_sender: EmailSenderInterface | None = None,
        email_config: EmailConfig | None = None,
        batch_size: int = 100,
        poll_interval: float = 1.0,
    ) -> None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        engine = create_async_engine(database_url, echo=False)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with session_factory() as session:
            outbox_repo = OutboxRepository(session)
            worker = OutboxWorker(
                outbox_repo=outbox_repo,
                publisher=EventPublisherAMQP(rabbitmq_config),
                email_sender=email_sender,
                email_config=email_config,
                batch_size=batch_size,
                poll_interval=poll_interval,
            )
            await worker.start()


async def main() -> None:
    import logging

    from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
    from infrastructure.email import EmailConfig, SMTPSender

    logging.basicConfig(level=logging.INFO)

    db_config = SQLAlchemyConfig.from_environ()
    rabbitmq_config = RabbitMQConfig.from_environ()
    email_config = EmailConfig.from_environ()

    await OutboxProcessor.run(
        database_url=db_config.full_url,
        rabbitmq_config=rabbitmq_config,
        email_sender=SMTPSender(email_config),
        email_config=email_config,
    )


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
