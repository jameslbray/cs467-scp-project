import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from services.db_init.app.models import BlacklistedToken


def cleanup_expired_tokens(db: Session):
    """Remove expired tokens from the blacklist."""
    now = datetime.now()
    expired_tokens = (
        db.query(BlacklistedToken)
        .filter(BlacklistedToken.expires_at < now)
        .all()
    )

    for token in expired_tokens:
        db.delete(token)

    db.commit()
    return len(expired_tokens)


def send_email(
    to_email: str,
    subject: str,
    content: str,
    html_content: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    attachments: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send an email using configured SMTP settings from environment variables.

    Args:
        to_email: Recipient email address
        subject: Email subject
        content: Plain text content
        html_content: Optional HTML content
        cc: Optional CC recipients
        bcc: Optional BCC recipients
        attachments: Optional dict of attachments {filename: file_data}

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Create message
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("SMTP_USER", "default@example.com")
    msg["To"] = to_email

    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    # Set content
    if html_content:
        msg.set_content(content)  # Plain text version
        msg.add_alternative(html_content, subtype="html")
    else:
        msg.set_content(content)

    # Add attachments if any
    if attachments:
        for filename, file_data in attachments.items():
            # This is simplified - you'd need to handle file types properly
            msg.add_attachment(file_data, filename=filename)

    # Send email
    try:
        host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        port = int(os.environ.get("SMTP_PORT", "465"))

        # Choose connection method based on port
        if port == 465:
            smtp_class = smtplib.SMTP_SSL
        else:
            smtp_class = smtplib.SMTP

        with smtp_class(host, port) as smtp:
            # Start TLS if not using SSL and port is 587
            if smtp_class == smtplib.SMTP and port == 587:
                smtp.starttls()

            # Login and send
            smtp.login(
                os.environ.get("SMTP_USER", ""),
                os.environ.get("SMTP_PASSWORD", ""),
            )
            smtp.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# Example usage for password reset
def send_reset_email(to_email: str, reset_url: str) -> bool:
    subject = "Password Reset Request"
    plain_content = f"Click the link to reset your password: {reset_url}"
    html_content = f"""
    <html>
        <body>
            <h1>Password Reset</h1>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
        </body>
    </html>
    """

    return send_email(to_email, subject, plain_content, html_content)
