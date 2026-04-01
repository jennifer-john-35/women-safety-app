"""
contact_manager.py — Per-user emergency contact management.
"""
import json
import logging
import re

import config

logger = logging.getLogger(__name__)

# Regex for basic email validation
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_all() -> dict:
    """Load the full contacts dict from disk; return {} on any error."""
    try:
        with open(config.CONTACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Expect a plain dict mapping username -> list[dict]
        if isinstance(data, dict):
            return data
        return {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("Could not read contacts file: %s", exc)
        return {}


def _save_all(data: dict) -> None:
    """Persist the full contacts dict to disk."""
    with open(config.CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def add_contact(username: str, name: str, phone: str, email: str) -> tuple[bool, str]:
    """
    Validate and save a new contact for *username*.

    Validation rules:
    - At least one of phone or email must be non-empty.
    - If email is non-empty it must match a valid email format.

    Returns (True, success_message) or (False, error_message).
    Never raises an exception to the caller.
    """
    try:
        phone = (phone or "").strip()
        email = (email or "").strip()

        if not phone and not email:
            return False, "At least one of phone or email is required"

        if email and not _EMAIL_RE.match(email):
            return False, "Invalid email format"

        contact = {"name": (name or "").strip(), "phone": phone, "email": email}

        data = _load_all()
        user_contacts = data.get(username, [])
        user_contacts.append(contact)
        data[username] = user_contacts
        _save_all(data)

        return True, "Contact added successfully."

    except Exception as exc:
        logger.error("add_contact failed: %s", exc)
        return False, f"Failed to add contact: {exc}"


def get_contacts(username: str) -> list[dict]:
    """
    Return all contacts for *username*.

    Never raises an exception to the caller.
    """
    try:
        data = _load_all()
        return list(data.get(username, []))
    except Exception as exc:
        logger.error("get_contacts failed: %s", exc)
        return []


def delete_contact(username: str, contact_index: int) -> tuple[bool, str]:
    """
    Remove the contact at *contact_index* from *username*'s contact list.

    Returns (True, success_message) or (False, "Contact not found") for an
    out-of-range index.
    Never raises an exception to the caller.
    """
    try:
        data = _load_all()
        user_contacts = data.get(username, [])

        if contact_index < 0 or contact_index >= len(user_contacts):
            return False, "Contact not found"

        user_contacts.pop(contact_index)
        data[username] = user_contacts
        _save_all(data)

        return True, "Contact deleted successfully."

    except Exception as exc:
        logger.error("delete_contact failed: %s", exc)
        return False, f"Failed to delete contact: {exc}"
