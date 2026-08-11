"""
Unit tests for the result-file storage (expiring download links).

Covers: save_result, resolve, delete, cleanup_expired, filename/extension
handling and email normalization. Redis is faked; files use a tmp dir.
"""

from unittest.mock import patch

import pytest

from backend.infrastructure.storage import result_files as rf


class FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, ex=None):
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)
        return 1

    def exists(self, key):
        return 1 if key in self.store else 0


class _Settings:
    def __init__(self, tmp):
        self.RESULTS_STORAGE_DIR = str(tmp)
        self.DOWNLOAD_TTL_HOURS = 48

        class _R:
            redis_url = "redis://x"

        self.redis = _R()


@pytest.fixture
def env(tmp_path):
    fake = FakeRedis()
    settings = _Settings(tmp_path)
    with patch.object(rf, "_redis", return_value=fake), patch.object(
        rf, "get_settings", return_value=settings
    ):
        yield fake, tmp_path


def test_save_and_resolve(env):
    _fake, tmp = env
    token = rf.save_result(b"date,eto\n1990-01-01,4.2\n", "res.csv", "  User@X.com ")
    assert token and len(token) > 20

    meta = rf.resolve(token)
    assert meta is not None
    assert meta["filename"] == "res.csv"
    assert meta["email"] == "user@x.com"  # normalized
    assert meta["size"] == 24
    assert meta["path"].endswith(".csv")
    assert (tmp / f"{token}.csv").exists()


def test_resolve_invalid_token_returns_none(env):
    assert rf.resolve("does-not-exist") is None
    assert rf.resolve("") is None


def test_resolve_expired_metadata_returns_none(env):
    fake, _tmp = env
    token = rf.save_result(b"x", "a.csv", "a@b.com")
    fake.store.clear()  # simulate Redis TTL expiry
    assert rf.resolve(token) is None


def test_delete_removes_file_and_metadata(env):
    _fake, _tmp = env
    token = rf.save_result(b"x", "a.xlsx", "a@b.com")
    path = rf.resolve(token)["path"]
    assert rf.delete(token) is True
    import os

    assert not os.path.exists(path)
    assert rf.resolve(token) is None


def test_cleanup_removes_orphan_files(env):
    fake, tmp = env
    token = rf.save_result(b"x", "a.csv", "a@b.com")
    path = tmp / f"{token}.csv"
    assert path.exists()
    fake.store.clear()  # metadata gone, file orphaned
    removed = rf.cleanup_expired()
    assert removed == 1
    assert not path.exists()


def test_cleanup_keeps_live_files(env):
    _fake, tmp = env
    token = rf.save_result(b"x", "a.csv", "a@b.com")
    removed = rf.cleanup_expired()
    assert removed == 0
    assert (tmp / f"{token}.csv").exists()


def test_safe_extension_fallback():
    assert rf._safe_ext("file.csv") == ".csv"
    assert rf._safe_ext("file.xlsx") == ".xlsx"
    assert rf._safe_ext("noext") == ".dat"
    assert rf._safe_ext("weird.<script>") == ".dat"
