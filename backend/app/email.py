import smtplib
from email.message import EmailMessage

from .db import settings


def _send_email(recipient: str, subject: str, body: str) -> None:
    required = (
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.email_from,
    )
    if not all(required):
        raise RuntimeError("SMTP is not configured; email cannot be delivered")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from
    message["To"] = recipient
    message.set_content(body)

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)


def send_password_reset_email(recipient: str, token: str) -> None:
    """Send a one-time reset token. SMTP credentials are supplied only via environment."""
    _send_email(
        recipient,
        "VANTIQ password reset",
        "A password reset was requested for your VANTIQ account.\n\n"
        f"Your one-time reset token is: {token}\n\n"
        "Submit this token to POST /api/v1/auth/password-reset/confirm. "
        "The token expires in 30 minutes and can be used only once. "
        "If you did not request this, ignore this email.",
    )


def send_email_verification(recipient: str, token: str) -> None:
    """Send a one-time email verification token."""
    _send_email(
        recipient,
        "Verify your VANTIQ email",
        "Welcome to VANTIQ. Please verify your email address to activate your free account.\n\n"
        f"Your one-time verification token is: {token}\n\n"
        "Submit this token to POST /api/v1/auth/verify-email. "
        "The token expires in 24 hours and can be used only once. "
        "If you did not create this account, ignore this email.",
    )
