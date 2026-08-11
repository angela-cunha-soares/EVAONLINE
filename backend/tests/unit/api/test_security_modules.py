"""
Unit tests for the abuse-protection / verification modules:
proof_of_work, internal_auth, pending_request, email_verification,
abuse_monitor, and the global daily cap in rate_limiter.

Redis and settings are faked so these run without external services.
"""

import hashlib
from unittest.mock import patch

import pytest

from backend.api.security import (
    abuse_monitor,
    email_verification,
    internal_auth,
    pending_request,
    proof_of_work,
)


class FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = str(value)
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)
        return 1

    def incr(self, key):
        self.store[key] = str(int(self.store.get(key, 0)) + 1)
        return int(self.store[key])

    def expire(self, key, ttl):
        return True

    def exists(self, key):
        return 1 if key in self.store else 0


class _Settings:
    ENVIRONMENT = "development"
    SECRET_KEY = "unit-test-secret"
    INTERNAL_API_TOKEN = ""
    POW_DIFFICULTY_BITS = 8
    ABUSE_ALERT_THRESHOLD = 2
    ALERT_WEBHOOK_URL = ""
    PUBLIC_BASE_URL = "https://evaonline.app.br"

    class redis:
        redis_url = "redis://x"


# ----------------------------------------------------------------------
# proof_of_work
# ----------------------------------------------------------------------
def _solve_pow(challenge, difficulty_bits=8):
    i = 0
    while True:
        digest = hashlib.sha256(f"{challenge}:{i}".encode()).digest()
        if proof_of_work._leading_zero_bits(digest) >= difficulty_bits:
            return str(i)
        i += 1


def test_pow_accepts_valid_solution():
    with patch.object(proof_of_work, "get_settings", return_value=_Settings()):
        subject = "visitor-123"
        challenge = proof_of_work.make_challenge(subject)
        nonce = _solve_pow(challenge, 8)
        assert proof_of_work.verify_solution(subject, nonce, 8) is True


def test_pow_rejects_bad_nonce_and_wrong_subject():
    with patch.object(proof_of_work, "get_settings", return_value=_Settings()):
        subject = "visitor-123"
        challenge = proof_of_work.make_challenge(subject)
        nonce = _solve_pow(challenge, 8)
        assert proof_of_work.verify_solution(subject, "0", 8) is False
        assert proof_of_work.verify_solution("other", nonce, 8) is False
        assert proof_of_work.verify_solution(subject, "", 8) is False


# ----------------------------------------------------------------------
# internal_auth
# ----------------------------------------------------------------------
def test_internal_token_derived_from_secret():
    with patch.object(internal_auth, "get_settings", return_value=_Settings()):
        token = internal_auth.get_internal_token()
        assert token and len(token) == 64  # sha256 hex


def test_internal_auth_noop_outside_production():
    s = _Settings()
    s.ENVIRONMENT = "development"
    with patch.object(internal_auth, "get_settings", return_value=s):
        assert internal_auth.verify_internal_token("") is None


def test_internal_auth_enforced_in_production():
    from fastapi import HTTPException

    s = _Settings()
    s.ENVIRONMENT = "production"
    with patch.object(internal_auth, "get_settings", return_value=s):
        token = internal_auth.get_internal_token()
        with pytest.raises(HTTPException) as exc:
            internal_auth.verify_internal_token("")
        assert exc.value.status_code == 403
        assert internal_auth.verify_internal_token(token) is None


# ----------------------------------------------------------------------
# pending_request
# ----------------------------------------------------------------------
def test_pending_save_and_consume_is_one_time():
    fake = FakeRedis()
    with patch.object(pending_request, "_redis", return_value=fake):
        params = {"lat": 1, "lon": 2, "email": "a@b.com"}
        assert pending_request.save("tok", params) is True
        assert pending_request.consume("tok") == params
        assert pending_request.consume("tok") is None  # one-time


# ----------------------------------------------------------------------
# email_verification
# ----------------------------------------------------------------------
def test_email_verification_flow():
    import sys
    import types

    fake = FakeRedis()
    sent = []

    def fake_send(to, subject, body, from_email=None):
        sent.append((to, subject, body))
        return True

    # Inject a lightweight email_utils so send_verification's lazy import
    # doesn't pull the full (heavy) module chain.
    fake_email_utils = types.ModuleType("backend.core.utils.email_utils")
    fake_email_utils.send_email = fake_send

    with patch.dict(
        sys.modules, {"backend.core.utils.email_utils": fake_email_utils}
    ), patch.object(
        email_verification, "_redis", return_value=fake
    ), patch.object(
        email_verification, "get_settings", return_value=_Settings()
    ), patch.object(
        pending_request, "_redis", return_value=fake
    ):
        email = "user@example.com"
        assert email_verification.is_verified(email) is False

        job = {"lat": -22.3, "email": email, "mode": "HISTORICAL_EMAIL"}
        assert email_verification.send_verification(email, "pt", pending=job) is True
        assert len(sent) == 1

        token = [
            k.split("email_verify_token:")[1]
            for k in fake.store
            if k.startswith("email_verify_token:")
        ][0]

        assert email_verification.confirm_token(token) == email
        assert email_verification.is_verified(email) is True
        # pending job recoverable for enqueue
        assert pending_request.consume(token) == job
        # invalid token
        assert email_verification.confirm_token("bad") is None


def test_email_verification_ttl_is_30_days():
    assert email_verification.VERIFIED_TTL == 86400 * 30


# ----------------------------------------------------------------------
# abuse_monitor
# ----------------------------------------------------------------------
def test_abuse_monitor_alerts_once_at_threshold():
    fake = FakeRedis()
    with patch.object(abuse_monitor, "_redis", return_value=fake), patch.object(
        abuse_monitor, "get_settings", return_value=_Settings()
    ):
        for _ in range(3):
            abuse_monitor.record_block("email", "a@b.com", "historical_email")
        alert_keys = [k for k in fake.store if k.startswith("abuse_alert:")]
        assert len(alert_keys) == 1  # deduped alert


# ----------------------------------------------------------------------
# global daily cap (rate_limiter)
# ----------------------------------------------------------------------
def test_global_daily_cap_blocks_when_reached():
    from backend.api.middleware import rate_limiter

    fake = FakeRedis()

    class _Cap:
        GLOBAL_DAILY_CALC_CAP = 3

    with patch.object(rate_limiter, "_get_redis", return_value=fake), patch.object(
        rate_limiter, "settings", _Cap()
    ):
        allowed = 0
        for _ in range(6):
            ok, _msg = rate_limiter.check_global_daily_cap()
            if ok:
                allowed += 1
                rate_limiter.track_global_calculation()
            else:
                break
        assert allowed == 3
