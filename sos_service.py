"""
sos_service.py — SOS alerting and evidence logging.
"""
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.text import MIMEText

import config
import contact_manager

logger = logging.getLogger(__name__)


def log_sos_event(username: str, lat: float, lon: float) -> None:
    """Append SOS event to the evidence log file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"SOS | user={username} | timestamp={timestamp} | lat={lat} | lon={lon}\n"
    try:
        with open(config.EVIDENCE_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as exc:
        logger.error("log_sos_event failed: %s", exc)


def trigger_sos(username: str, lat: float, lon: float) -> dict:
    """
    Send SOS email alerts to all contacts with an email address.

    Returns:
        {notified: [...], failed: [...]} on normal execution.
        Adds a 'warning' key when no contacts exist or none have email addresses.
    Never raises exceptions to the caller.
    """
    try:
        contacts = contact_manager.get_contacts(username)

        email_contacts = [c for c in contacts if c.get("email", "").strip()]

        if not contacts:
            log_sos_event(username, lat, lon)
            return {
                "notified": [],
                "failed": [],
                "warning": "No contacts registered. Please add emergency contacts before using SOS.",
            }

        if not email_contacts:
            log_sos_event(username, lat, lon)
            return {
                "notified": [],
                "failed": [],
                "warning": "No contacts have email addresses. Please add email addresses to your contacts.",
            }

        notified = []
        failed = []

        subject = "🚨 SOS Alert"
        body = (
            f"Emergency SOS alert from {username}!\n\n"
            f"Location: lat={lat}, lon={lon}\n"
            f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n"
            "Please contact them immediately or alert emergency services."
        )

        for contact in email_contacts:
            email = contact["email"].strip()
            name = contact.get("name", email)
            try:
                msg = MIMEText(body)
                msg["Subject"] = subject
                msg["From"] = config.SMTP_USER
                msg["To"] = email

                context = ssl.create_default_context()
                with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(config.SMTP_USER, config.SMTP_PASSWORD)
                    server.sendmail(config.SMTP_USER, [email], msg.as_string())

                notified.append(name)
                logger.info("SOS email sent to %s (%s)", name, email)

            except Exception as exc:
                logger.error("Failed to send SOS email to %s (%s): %s", name, email, exc)
                failed.append(name)

    except Exception as exc:
        logger.error("trigger_sos encountered an unexpected error: %s", exc)
        notified = []
        failed = []

    finally:
        log_sos_event(username, lat, lon)

    return {"notified": notified, "failed": failed}
