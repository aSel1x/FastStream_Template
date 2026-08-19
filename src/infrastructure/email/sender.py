from typing import final, override
from abc import ABC, abstractmethod

from infrastructure.email.config import EmailConfig


class EmailSenderInterface(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None: ...


@final
class SMTPSender(EmailSenderInterface):
    def __init__(self, config: EmailConfig) -> None:
        self._config = config

    @override
    async def send(self, to: str, subject: str, body: str) -> None:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg['From'] = self._config.from_addr
        msg['To'] = to
        msg['Subject'] = subject
        msg.set_content(body)
        msg.add_alternative(body, subtype='html')

        if self._config.use_tls:
            _ = await aiosmtplib.send(
                msg,
                hostname=self._config.host,
                port=self._config.port,
                username=self._config.username or None,
                password=self._config.password or None,
                use_tls=True,
            )
        else:
            _ = await aiosmtplib.send(
                msg,
                hostname=self._config.host,
                port=self._config.port,
                username=self._config.username or None,
                password=self._config.password or None,
                start_tls=False,
            )
