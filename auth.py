"""
auth.py — Secure user authentication: registration, login, and logout.
"""
import json
import bcrypt
import streamlit as st

import config

MIN_PASSWORD_LENGTH = 8


def _load_users() -> dict:
    """Load users from the JSON file, returning an empty dict on any error."""
    try:
        with open(config.USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_users(users: dict) -> None:
    """Persist the users dict to the JSON file."""
    with open(config.USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def register_user(username: str, password: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    try:
        if not username or not username.strip():
            return False, "Username is required."

        if len(password) < MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

        users = _load_users()

        if username in users:
            return False, "Username already exists."

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        users[username] = {"password_hash": password_hash.decode("utf-8")}
        _save_users(users)

        return True, "Registration successful."
    except Exception as e:
        return False, f"Registration failed: {e}"


def login_user(username: str, password: str) -> tuple[bool, str]:
    """Verify credentials. Returns (success, message)."""
    try:
        users = _load_users()

        user = users.get(username)
        if user is None or "password_hash" not in user:
            # Generic error — never reveal whether the username exists
            return False, "Invalid username or password."

        stored_hash = user["password_hash"].encode("utf-8")
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return True, "Login successful."

        return False, "Invalid username or password."
    except Exception as e:
        return False, f"Login failed: {e}"


def logout_user() -> None:
    """Clear Streamlit session state (remove 'user' key)."""
    st.session_state.pop("user", None)
