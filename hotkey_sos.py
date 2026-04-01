"""
hotkey_sos.py — Background hotkey listener for instant SOS triggering.

Runs silently in the background. Press Ctrl+Shift+S at any time to send
an SOS alert to all registered emergency contacts — no need to open the app.

Usage:
    python hotkey_sos.py --user <your_username>

The script reads contacts and SMTP config from the same .env and JSON files
used by the main app, so no extra setup is needed.
"""
import argparse
import json
import logging
import sys
import time

import keyboard  # pip install keyboard

import sos_service
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("hotkey_sos.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

HOTKEY = "ctrl+shift+s"


def _get_default_user() -> str:
    """Return the first username found in users.json, or empty string."""
    try:
        with open(config.USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        if users:
            return next(iter(users))
    except Exception:
        pass
    return ""


def fire_sos(username: str) -> None:
    """Trigger SOS and print result to console."""
    logger.info("🚨 Hotkey detected! Firing SOS for user: %s", username)
    print(f"\n🚨 SOS TRIGGERED for {username}! Sending alerts...\n")

    result = sos_service.trigger_sos(username, lat=0.0, lon=0.0)

    if "warning" in result:
        print(f"⚠️  Warning: {result['warning']}")
        logger.warning(result["warning"])
    else:
        if result["notified"]:
            print("✅ Alerts sent to: " + ", ".join(result["notified"]))
            logger.info("Notified: %s", result["notified"])
        if result["failed"]:
            print("❌ Failed to notify: " + ", ".join(result["failed"]))
            logger.error("Failed: %s", result["failed"])
        if not result["notified"] and not result["failed"]:
            print("ℹ️  SOS logged. No contacts with email addresses found.")

    print("\nListening for hotkey again...\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Background SOS hotkey listener")
    parser.add_argument(
        "--user",
        type=str,
        default="",
        help="Username whose contacts will receive the SOS alert",
    )
    args = parser.parse_args()

    username = args.user.strip() or _get_default_user()

    if not username:
        print("❌ No username found. Run with: python hotkey_sos.py --user <your_username>")
        sys.exit(1)

    print(f"✅ SOS hotkey listener started for user: {username}")
    print(f"   Press  {HOTKEY.upper()}  at any time to send an emergency alert.")
    print("   Press  Ctrl+C  to stop.\n")
    logger.info("Hotkey listener started for user '%s' — hotkey: %s", username, HOTKEY)

    keyboard.add_hotkey(HOTKEY, fire_sos, args=(username,))

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\nSOS listener stopped.")
        logger.info("Hotkey listener stopped by user.")


if __name__ == "__main__":
    main()
