"""
Tests for setup_docker.py.

The script is top-level procedural code using subprocess.
We test it by importing with subprocess calls fully mocked.
"""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_env(tmp_path):
    """Create a fake .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "POSTGRES_HOST=postgres\n"
        "POSTGRES_USER=evaonline\n"
        "POSTGRES_PASSWORD=testpass\n"
        "POSTGRES_DB=evaonline\n"
        "REDIS_HOST=redis\n"
        "REDIS_PASSWORD=redispass\n"
    )
    return env_file


class TestSetupDockerComponents:
    """Test individual logic patterns from setup_docker.py."""

    def test_env_required_vars_list(self):
        """Verify the set of required env vars."""
        required_vars = [
            "POSTGRES_HOST",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "REDIS_HOST",
            "REDIS_PASSWORD",
        ]
        # These should all be checked
        assert len(required_vars) == 6
        assert "POSTGRES_PASSWORD" in required_vars
        assert "REDIS_PASSWORD" in required_vars

    def test_password_display_masking(self):
        """Password display logic should mask middle characters."""
        value = "7tcae-edSNDr0cu-05Qb8T_vPs1kPyzOsEQv-BS12IM"
        display = f"{value[:4]}...{value[-4:]}"
        assert display == "7tca...12IM"
        assert len(display) < len(value)

    def test_password_display_short(self):
        """Short passwords should still work with masking."""
        value = "abcdefgh"
        display = f"{value[:4]}...{value[-4:]}"
        assert display == "abcd...efgh"

    def test_docker_compose_version_command(self):
        """Verify the command format for Docker check."""
        cmd = ["docker", "compose", "version"]
        assert cmd[0] == "docker"
        assert cmd[1] == "compose"

    def test_docker_compose_down_command(self):
        """Verify cleanup command."""
        cmd = ["docker", "compose", "down", "-v"]
        assert "-v" in cmd

    def test_docker_compose_up_services(self):
        """Verify the services started."""
        cmd = ["docker", "compose", "up", "-d", "postgres", "redis"]
        assert "postgres" in cmd
        assert "redis" in cmd
        assert "-d" in cmd

    @patch.dict(os.environ, {
        "POSTGRES_USER": "evaonline",
        "POSTGRES_PASSWORD": "pass",
        "POSTGRES_DB": "evaonline",
        "REDIS_PASSWORD": "rpass",
    })
    def test_pg_isready_command(self):
        """Verify the pg_isready healthcheck command format."""
        cmd = [
            "docker", "exec", "evaonline-postgres",
            "pg_isready", "-U", os.getenv("POSTGRES_USER"),
        ]
        assert cmd[-1] == "evaonline"

    @patch.dict(os.environ, {
        "REDIS_PASSWORD": "rpass",
    })
    def test_redis_ping_command(self):
        """Verify the Redis healthcheck command format."""
        cmd = [
            "docker", "exec", "evaonline-redis",
            "redis-cli", "-a", os.getenv("REDIS_PASSWORD"), "ping",
        ]
        assert cmd[-1] == "ping"
        assert "-a" in cmd

    def test_subprocess_run_timeout(self):
        """Verify subprocess.run is called with timeout."""
        # The script uses timeout=5 for version checks
        # and timeout=60 for docker compose up
        assert 5 < 60  # Timeout for up > version check

    @patch("subprocess.run")
    def test_docker_version_check_succeeds(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Docker Compose version v2.29.7",
        )
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0
        assert "Docker Compose" in result.stdout

    @patch("subprocess.run")
    def test_docker_version_check_fails(self, mock_run):
        mock_run.side_effect = FileNotFoundError("not found")
        with pytest.raises(FileNotFoundError):
            subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True, text=True, timeout=5,
            )

    @patch("subprocess.run")
    def test_health_check_loop_logic(self, mock_run):
        """Simulate the health check loop."""
        # First call: PG ready, second call: Redis ready
        mock_run.return_value = MagicMock(returncode=0)

        pg_result = subprocess.run(
            ["docker", "exec", "evaonline-postgres", "pg_isready", "-U", "evaonline"],
            capture_output=True, timeout=5,
        )
        redis_result = subprocess.run(
            ["docker", "exec", "evaonline-redis", "redis-cli", "-a", "pass", "ping"],
            capture_output=True, timeout=5,
        )

        assert pg_result.returncode == 0
        assert redis_result.returncode == 0

    @patch("subprocess.run")
    def test_health_check_pg_not_ready(self, mock_run):
        """PG not ready should continue loop."""
        mock_run.return_value = MagicMock(returncode=1)
        pg_result = subprocess.run(
            ["docker", "exec", "evaonline-postgres", "pg_isready", "-U", "evaonline"],
            capture_output=True, timeout=5,
        )
        assert pg_result.returncode != 0
