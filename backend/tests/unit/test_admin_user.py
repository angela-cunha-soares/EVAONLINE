"""Tests for backend/database/models/admin_user.py."""

import pytest
from unittest.mock import patch, MagicMock


class TestAdminUser:
    def _make_user(self, **kwargs):
        from backend.database.models.admin_user import AdminUser
        return AdminUser(**kwargs)

    def test_validate_username_valid(self):
        user = self._make_user(
            username="test_user",
            email="test@example.com",
            password_hash="fakehash",
            role="DEVELOPER",
        )
        assert user.username == "test_user"

    def test_validate_username_too_short(self):
        with pytest.raises(ValueError, match="at least 3 characters"):
            self._make_user(
                username="ab",
                email="test@example.com",
                password_hash="fakehash",
            )

    def test_validate_username_invalid_chars(self):
        with pytest.raises(ValueError, match="letters, numbers"):
            self._make_user(
                username="user@name",
                email="test@example.com",
                password_hash="fakehash",
            )

    def test_validate_username_lowered(self):
        user = self._make_user(
            username="TestUser",
            email="test@example.com",
            password_hash="fakehash",
        )
        assert user.username == "testuser"

    def test_validate_email_valid(self):
        user = self._make_user(
            username="testuser",
            email="User@Example.COM",
            password_hash="fakehash",
        )
        assert user.email == "user@example.com"

    def test_validate_email_invalid(self):
        with pytest.raises(ValueError, match="Invalid email"):
            self._make_user(
                username="testuser",
                email="not-an-email",
                password_hash="fakehash",
            )

    def test_validate_role_valid(self):
        user = self._make_user(
            username="testuser",
            email="test@example.com",
            password_hash="fakehash",
            role="ADMIN",
        )
        assert user.role == "ADMIN"

    def test_validate_role_invalid(self):
        with pytest.raises(ValueError, match="Role must be one of"):
            self._make_user(
                username="testuser",
                email="test@example.com",
                password_hash="fakehash",
                role="INVALID",
            )

    def test_set_password_and_verify(self):
        user = self._make_user(
            username="testuser",
            email="test@example.com",
            password_hash="fakehash",
        )
        user.set_password("secure_password_123")
        assert user.password_hash != "fakehash"
        assert user.verify_password("secure_password_123") is True
        assert user.verify_password("wrong_password") is False

    def test_set_password_too_short(self):
        user = self._make_user(
            username="testuser",
            email="test@example.com",
            password_hash="fakehash",
        )
        with pytest.raises(ValueError, match="at least 8 characters"):
            user.set_password("short")

    def test_verify_password_invalid_hash(self):
        user = self._make_user(
            username="testuser",
            email="test@example.com",
            password_hash="not_a_valid_bcrypt_hash",
        )
        assert user.verify_password("any_password") is False

    def test_generate_api_token(self):
        user = self._make_user(
            username="testuser",
            email="test@example.com",
            password_hash="fakehash",
        )
        token = user.generate_api_token()
        assert isinstance(token, str)
        assert len(token) > 20
        assert user.api_token == token

    def test_repr(self):
        user = self._make_user(
            username="testuser",
            email="test@example.com",
            password_hash="fakehash",
            role="ADMIN",
        )
        assert "testuser" in repr(user)
        assert "ADMIN" in repr(user)
