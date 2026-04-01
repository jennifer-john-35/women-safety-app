"""
tests/test_contact_manager.py — Unit and property-based tests for contact_manager.py

Properties covered:
  P16: Contact add round-trip (Validates: Requirements 6.1, 6.4)
  P17: Contact requires at least one of phone or email (Validates: Requirements 6.2)
  P18: Invalid email format is rejected (Validates: Requirements 6.3)
  P19: Contact deletion removes exactly one contact (Validates: Requirements 6.5)
  P20: Contact data is scoped per user (Validates: Requirements 6.6)
"""
import contextlib
import json
import os
import tempfile

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

import config
import contact_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_contacts_file(tmp_path, monkeypatch):
    """Redirect CONTACTS_FILE to a fresh temp file for every test."""
    contacts_path = str(tmp_path / "contacts.json")
    monkeypatch.setattr(config, "CONTACTS_FILE", contacts_path)
    yield contacts_path


@contextlib.contextmanager
def _temp_contacts():
    """Context manager that redirects CONTACTS_FILE to a fresh temp file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name
    original = config.CONTACTS_FILE
    config.CONTACTS_FILE = tmp_path
    try:
        yield tmp_path
    finally:
        config.CONTACTS_FILE = original
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestAddContact:
    def test_add_with_phone_only(self):
        ok, msg = contact_manager.add_contact("alice", "Bob", "1234567890", "")
        assert ok is True
        contacts = contact_manager.get_contacts("alice")
        assert len(contacts) == 1
        assert contacts[0]["phone"] == "1234567890"

    def test_add_with_email_only(self):
        ok, msg = contact_manager.add_contact("alice", "Carol", "", "carol@example.com")
        assert ok is True
        contacts = contact_manager.get_contacts("alice")
        assert contacts[0]["email"] == "carol@example.com"

    def test_add_with_both_phone_and_email(self):
        ok, msg = contact_manager.add_contact("alice", "Dave", "9999", "dave@x.com")
        assert ok is True

    def test_add_fails_when_both_empty(self):
        ok, msg = contact_manager.add_contact("alice", "Eve", "", "")
        assert ok is False
        assert "phone or email" in msg.lower()
        assert contact_manager.get_contacts("alice") == []

    def test_add_fails_invalid_email_no_at(self):
        ok, msg = contact_manager.add_contact("alice", "Frank", "", "notanemail")
        assert ok is False
        assert "email" in msg.lower()

    def test_add_fails_invalid_email_no_domain(self):
        ok, msg = contact_manager.add_contact("alice", "Grace", "", "grace@")
        assert ok is False

    def test_add_valid_email_accepted(self):
        ok, msg = contact_manager.add_contact("alice", "Heidi", "", "heidi@example.org")
        assert ok is True

    def test_contacts_scoped_per_user(self):
        contact_manager.add_contact("alice", "A-Contact", "111", "")
        contact_manager.add_contact("bob", "B-Contact", "222", "")
        assert len(contact_manager.get_contacts("alice")) == 1
        assert contact_manager.get_contacts("alice")[0]["name"] == "A-Contact"
        assert len(contact_manager.get_contacts("bob")) == 1
        assert contact_manager.get_contacts("bob")[0]["name"] == "B-Contact"


class TestGetContacts:
    def test_returns_empty_list_for_unknown_user(self):
        result = contact_manager.get_contacts("nobody")
        assert result == []

    def test_returns_list_of_dicts(self):
        contact_manager.add_contact("alice", "X", "123", "")
        result = contact_manager.get_contacts("alice")
        assert isinstance(result, list)
        assert all(isinstance(c, dict) for c in result)


class TestDeleteContact:
    def test_delete_valid_index(self):
        contact_manager.add_contact("alice", "A", "1", "")
        contact_manager.add_contact("alice", "B", "2", "")
        ok, msg = contact_manager.delete_contact("alice", 0)
        assert ok is True
        contacts = contact_manager.get_contacts("alice")
        assert len(contacts) == 1
        assert contacts[0]["name"] == "B"

    def test_delete_out_of_range_returns_false(self):
        contact_manager.add_contact("alice", "A", "1", "")
        ok, msg = contact_manager.delete_contact("alice", 5)
        assert ok is False
        assert msg == "Contact not found"

    def test_delete_negative_index_returns_false(self):
        contact_manager.add_contact("alice", "A", "1", "")
        ok, msg = contact_manager.delete_contact("alice", -1)
        assert ok is False
        assert msg == "Contact not found"

    def test_delete_from_empty_list_returns_false(self):
        ok, msg = contact_manager.delete_contact("alice", 0)
        assert ok is False
        assert msg == "Contact not found"


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

# Strategies
_username = st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")))
_name = st.text(min_size=1, max_size=50)
_phone = st.one_of(st.just(""), st.text(min_size=1, max_size=15, alphabet="0123456789+"))
_valid_email = st.emails()
_invalid_email = st.one_of(
    st.text(min_size=1, max_size=30).filter(lambda s: "@" not in s and s.strip() != ""),
    st.just("missing@"),
    st.just("@nodomain.com"),
    st.just("no-at-sign"),
)


# Feature: ai-women-safety-system, Property 16: Contact add round-trip
@given(username=_username, name=_name, phone=_phone, email=_valid_email)
@settings(max_examples=100)
def test_p16_add_contact_round_trip(username, name, phone, email):
    """
    For any valid contact (name, phone, email), after add_contact returns success,
    get_contacts must return a list containing an entry with the same name, phone, email.

    Validates: Requirements 6.1, 6.4
    """
    with _temp_contacts():
        ok, _ = contact_manager.add_contact(username, name, phone, email)
        assert ok is True
        contacts = contact_manager.get_contacts(username)
        assert any(
            c["name"] == name.strip() and c["phone"] == phone.strip() and c["email"] == email.strip()
            for c in contacts
        )


# Feature: ai-women-safety-system, Property 17: Contact requires at least one of phone or email
@given(username=_username, name=_name)
@settings(max_examples=100)
def test_p17_contact_requires_phone_or_email(username, name):
    """
    For any contact where both phone and email are empty strings, add_contact must
    return failure and must not write the contact to storage.

    Validates: Requirements 6.2
    """
    with _temp_contacts():
        before = contact_manager.get_contacts(username)
        ok, msg = contact_manager.add_contact(username, name, "", "")
        assert ok is False
        after = contact_manager.get_contacts(username)
        assert len(after) == len(before)


# Feature: ai-women-safety-system, Property 18: Invalid email format is rejected
@given(username=_username, name=_name, invalid_email=_invalid_email)
@settings(max_examples=100)
def test_p18_invalid_email_rejected(username, name, invalid_email):
    """
    For any string that does not match a valid email format, add_contact must return
    failure and must not write the contact to storage.

    Validates: Requirements 6.3
    """
    with _temp_contacts():
        before = contact_manager.get_contacts(username)
        ok, msg = contact_manager.add_contact(username, name, "", invalid_email)
        assert ok is False
        after = contact_manager.get_contacts(username)
        assert len(after) == len(before)


# Feature: ai-women-safety-system, Property 19: Contact deletion removes exactly one contact
@given(
    username=_username,
    contacts=st.lists(
        st.tuples(_name, st.text(min_size=1, max_size=10, alphabet="0123456789"), st.just("")),
        min_size=1,
        max_size=10,
    ),
    index=st.integers(min_value=0),
)
@settings(max_examples=100)
def test_p19_delete_removes_exactly_one(username, contacts, index):
    """
    For any user with a non-empty contact list, deleting a contact at a valid index
    must result in the contact list being shorter by exactly one.

    Validates: Requirements 6.5
    """
    with _temp_contacts():
        for name, phone, email in contacts:
            contact_manager.add_contact(username, name, phone, email)

        before = contact_manager.get_contacts(username)
        valid_index = index % len(before)

        ok, _ = contact_manager.delete_contact(username, valid_index)
        assert ok is True

        after = contact_manager.get_contacts(username)
        assert len(after) == len(before) - 1


# Feature: ai-women-safety-system, Property 20: Contact data is scoped per user
@given(
    user_a=_username,
    user_b=_username,
    name=_name,
    phone=st.text(min_size=1, max_size=10, alphabet="0123456789"),
)
@settings(max_examples=100)
def test_p20_contacts_scoped_per_user(user_a, user_b, name, phone):
    """
    For any two distinct usernames A and B, get_contacts(A) must never return any
    contact that was added via add_contact(B, ...), and vice versa.

    Validates: Requirements 6.6
    """
    assume(user_a != user_b)

    with _temp_contacts():
        contact_manager.add_contact(user_a, name, phone, "")

        contacts_b = contact_manager.get_contacts(user_b)
        assert not any(c["name"] == name.strip() and c["phone"] == phone.strip() for c in contacts_b)
