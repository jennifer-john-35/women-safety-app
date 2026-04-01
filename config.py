"""
config.py — Load all environment variables via python-dotenv and expose as constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# File paths
USERS_FILE: str = os.getenv("USERS_FILE", "users.json")
INCIDENTS_FILE: str = os.getenv("INCIDENTS_FILE", "incidents.json")
HOTSPOTS_FILE: str = os.getenv("HOTSPOTS_FILE", "hotspots.json")
CONTACTS_FILE: str = os.getenv("CONTACTS_FILE", "contacts.json")
EVIDENCE_LOG: str = os.getenv("EVIDENCE_LOG", "evidence_log.txt")

# Model paths
MODEL_PATH: str = os.getenv("MODEL_PATH", "model.joblib")
SCALER_PATH: str = os.getenv("SCALER_PATH", "scaler.joblib")

# SMTP credentials
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
