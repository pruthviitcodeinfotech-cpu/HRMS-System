"""Email transport (SMTP).

A deliberately small client: build a MIME message, hand it to ``smtplib``. It exists so
callers (today: the payslip-email job) never touch a socket or a header themselves.

Two behaviours are load-bearing:

* **Unconfigured is not an error.** With no ``SMTP_HOST`` — the default in development
  and in CI — :meth:`SmtpEmailClient.send` logs and returns ``False`` without raising.
  A background job that merely *wants* to notify someone must not crash, and must not
  be retried forever, because the deployment has no mail server. Callers check the
  return value.
* **A configured-but-failing server IS an error.** Once ``SMTP_HOST`` is set, a refused
  connection or a rejected recipient raises :class:`EmailDeliveryException`, so the
  calling job fails and arq retries it. Silently dropping mail from a *working*
  configuration is the failure mode this class is written to prevent.

``smtplib`` is blocking, so the send runs in a worker thread (``anyio.to_thread``) and
never stalls the event loop.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache

import anyio

from app.core.config.settings import Settings, get_settings
from app.core.exceptions.base import AppException
from app.core.logging import get_logger

_logger = get_logger("email")

#: Seconds to wait on the SMTP socket before giving up.
_SMTP_TIMEOUT = 15


class EmailDeliveryException(AppException):
    """SMTP is configured but the message could not be handed to the server."""

    code = "EMAIL_DELIVERY_FAILED"
    status_code = 502
    message = "The email could not be delivered."


@dataclass(frozen=True)
class EmailAttachment:
    """A file to attach: raw bytes plus the name and MIME type to advertise."""

    filename: str
    content: bytes
    content_type: str = "application/pdf"

    @property
    def maintype(self) -> str:
        """The MIME main type (e.g. ``application``)."""
        return self.content_type.split("/", 1)[0]

    @property
    def subtype(self) -> str:
        """The MIME subtype (e.g. ``pdf``)."""
        parts = self.content_type.split("/", 1)
        return parts[1] if len(parts) == 2 else "octet-stream"


class SmtpEmailClient:
    """Sends mail over SMTP using the ``SMTP_*`` settings."""

    def __init__(self, config: Settings) -> None:
        self._config = config

    @property
    def is_configured(self) -> bool:
        """True when a mail server is configured (``SMTP_HOST`` is set)."""
        return bool(self._config.smtp_host.strip())

    async def send(
        self,
        *,
        to: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
        attachments: list[EmailAttachment] | None = None,
    ) -> bool:
        """Send one message. Returns ``True`` if it was handed to the SMTP server.

        Returns ``False`` — without raising — when SMTP is not configured, or when
        ``to`` is empty: both mean "there is nobody/nowhere to deliver to", which is a
        no-op, not a failure.

        Raises:
            EmailDeliveryException: SMTP is configured but the server refused the
                message (connection, auth, or recipient failure).
        """
        recipient = (to or "").strip()
        if not recipient:
            _logger.warning("email_skipped_no_recipient", subject=subject)
            return False

        if not self.is_configured:
            _logger.warning(
                "email_skipped_smtp_not_configured",
                subject=subject,
                to=recipient,
                hint="set SMTP_HOST to enable outbound email",
            )
            return False

        message = self._build_message(
            to=recipient,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            attachments=attachments or [],
        )

        try:
            await anyio.to_thread.run_sync(self._send_sync, message)
        except OSError as exc:  # smtplib.SMTPException is an OSError subclass
            _logger.error(
                "email_delivery_failed", subject=subject, to=recipient, error=str(exc)
            )
            raise EmailDeliveryException() from exc

        _logger.info("email_sent", subject=subject, to=recipient)
        return True

    def _build_message(
        self,
        *,
        to: str,
        subject: str,
        text_body: str,
        html_body: str | None,
        attachments: list[EmailAttachment],
    ) -> EmailMessage:
        """Assemble the MIME message (plain text, optional HTML alternative)."""
        message = EmailMessage()
        message["From"] = self._config.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")
        for attachment in attachments:
            message.add_attachment(
                attachment.content,
                maintype=attachment.maintype,
                subtype=attachment.subtype,
                filename=attachment.filename,
            )
        return message

    def _send_sync(self, message: EmailMessage) -> None:
        """Blocking SMTP send (runs in a worker thread).

        STARTTLS is attempted on every server that advertises it — credentials must not
        cross the wire in clear text — and skipped on the ones that do not (a local relay
        such as MailHog), rather than failing the send.
        """
        config = self._config
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=_SMTP_TIMEOUT) as smtp:
            smtp.ehlo()
            if smtp.has_extn("starttls"):
                smtp.starttls()
                smtp.ehlo()
            if config.smtp_user:
                smtp.login(config.smtp_user, config.smtp_password)
            smtp.send_message(message)


@lru_cache(maxsize=1)
def get_email_client() -> SmtpEmailClient:
    """Return the process-wide email client."""
    return SmtpEmailClient(get_settings())
