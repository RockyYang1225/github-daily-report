from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import List, Optional


class MailError(RuntimeError):
    """Raised when SMTP delivery fails."""


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str


@dataclass
class EmailMessagePayload:
    subject: str
    html: str
    sender: str
    recipients: List[str]


@dataclass
class MailResult:
    sent: bool
    message: str


def _build_message(payload: EmailMessagePayload) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = payload.subject
    message["From"] = payload.sender
    message["To"] = ", ".join(payload.recipients)
    message.set_content("This report requires an HTML-capable email client.")
    message.add_alternative(payload.html, subtype="html")
    return message


def send_report_email(
    payload: EmailMessagePayload,
    smtp_config: Optional[SmtpConfig],
    dry_run: bool = False,
) -> MailResult:
    if dry_run:
        return MailResult(sent=False, message="dry-run")
    if smtp_config is None:
        raise MailError("SMTP configuration is required when dry_run is false")

    message = _build_message(payload)
    try:
        if smtp_config.port == 465:
            with smtplib.SMTP_SSL(smtp_config.host, smtp_config.port) as smtp:
                smtp.login(smtp_config.username, smtp_config.password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(smtp_config.host, smtp_config.port) as smtp:
                smtp.starttls()
                smtp.login(smtp_config.username, smtp_config.password)
                smtp.send_message(message)
    except smtplib.SMTPException as exc:
        raise MailError(f"SMTP delivery failed: {exc}") from exc

    return MailResult(sent=True, message="sent")
