import smtplib
from email.message import EmailMessage

from .db import settings


def send_password_reset_email(recipient: str, token: str) -> None:
    """Send a one-time reset token. SMTP credentials are supplied only via environment."""
    required = (
        settings.smtp_host,
        settings.smtp_username,
        settings.smtp_password,
        settings.email_from,
    )
    if not all(required):
        raise RuntimeError("SMTP is not configured; password reset email cannot be delivered")

    message = EmailMessage()
    message["Subject"] = "VANTIQ password reset"
    message["From"] = settings.email_from
    message["To"] = recipient
    message.set_content(
        "A password reset was requested for your VANTIQ account.\n\n"
        f"Your one-time reset token is: {token}\n\n"
        "Enter this token in POST /api/v1/auth/password-reset/confirm in the VANTIQ API docs. "
        "The token expires in 30 minutes and can be used only once. "
        "If you did not request this, ignore this email."
    )

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
