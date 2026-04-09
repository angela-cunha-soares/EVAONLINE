"""
Tests for rate_limiter middleware and API route helpers.

Covers:
- _get_key (pure key generation)
- _check_identifier_limit (mocked Redis)
- check_calculation_limit (mocked Redis)
- track_calculation (mocked Redis)
- get_remaining_calculations (mocked Redis)
"""

from unittest.mock import patch, MagicMock

from backend.api.middleware.rate_limiter import (
    _get_key,
    _check_identifier_limit,
    check_calculation_limit,
    track_calculation,
    get_remaining_calculations,
    CALC_LIMITS,
)


# ════════════════════════════════════════════════════════════════════
# _get_key — pure logic
# ════════════════════════════════════════════════════════════════════

class TestGetKey:

    def test_format(self):
        key = _get_key("192.168.1.1", "dashboard_current")
        assert key.startswith("calc_limit:192.168.1.1:dashboard_current:")
        # Date portion YYYY-MM-DD
        date_part = key.split(":")[-1]
        assert len(date_part) == 10
        assert "-" in date_part

    def test_different_modes(self):
        k1 = _get_key("ip", "dashboard_current")
        k2 = _get_key("ip", "historical_email")
        assert k1 != k2

    def test_different_identifiers(self):
        k1 = _get_key("ip1", "global")
        k2 = _get_key("ip2", "global")
        assert k1 != k2


# ════════════════════════════════════════════════════════════════════
# _check_identifier_limit — mocked Redis
# ════════════════════════════════════════════════════════════════════

class TestCheckIdentifierLimit:

    def test_within_limit_allowed(self):
        redis = MagicMock()
        redis.get.return_value = "5"  # Within limit
        allowed, msg = _check_identifier_limit(redis, "ip", "IP", "dashboard_current")
        assert allowed is True
        assert msg is None

    def test_mode_limit_exceeded(self):
        redis = MagicMock()
        redis.get.return_value = str(CALC_LIMITS["dashboard_current"])
        allowed, msg = _check_identifier_limit(redis, "ip", "IP", "dashboard_current")
        assert allowed is False
        assert "limit" in msg.lower()

    def test_global_limit_exceeded(self):
        redis = MagicMock()
        # Mode under limit but global over limit
        redis.get.side_effect = lambda k: (
            "5" if "dashboard" in k else str(CALC_LIMITS["global"])
        )
        allowed, msg = _check_identifier_limit(redis, "ip", "IP", "dashboard_current")
        assert allowed is False
        assert "limit" in msg.lower()

    def test_zero_usage(self):
        redis = MagicMock()
        redis.get.return_value = None  # No previous usage
        allowed, msg = _check_identifier_limit(redis, "ip", "IP", "dashboard_current")
        assert allowed is True


# ════════════════════════════════════════════════════════════════════
# check_calculation_limit — full function with mocked Redis
# ════════════════════════════════════════════════════════════════════

class TestCheckCalculationLimit:

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_allowed(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis
        
        allowed, msg = check_calculation_limit("192.168.1.1", "dashboard_current")
        assert allowed is True
        assert msg is None

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_ip_blocked(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(CALC_LIMITS["dashboard_current"])
        mock_get_redis.return_value = mock_redis
        
        allowed, msg = check_calculation_limit("192.168.1.1", "dashboard_current")
        assert allowed is False

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_visitor_id_checked(self, mock_get_redis):
        mock_redis = MagicMock()
        # IP is fine, visitor_id is over limit
        call_count = [0]
        def mock_get(key):
            call_count[0] += 1
            if "vid:" in key:
                return str(CALC_LIMITS["dashboard_current"])
            return "0"
        mock_redis.get = mock_get
        mock_get_redis.return_value = mock_redis
        
        allowed, msg = check_calculation_limit(
            "192.168.1.1", "dashboard_current", visitor_id="visitor_123"
        )
        assert allowed is False

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_redis_error_fails_open(self, mock_get_redis):
        """If Redis fails, allow the request (fail open)"""
        mock_get_redis.side_effect = Exception("Redis down")
        allowed, msg = check_calculation_limit("192.168.1.1")
        assert allowed is True
        assert msg is None


# ════════════════════════════════════════════════════════════════════
# track_calculation — mocked Redis
# ════════════════════════════════════════════════════════════════════

class TestTrackCalculation:

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_increments_counters(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        mock_get_redis.return_value = mock_redis
        
        result = track_calculation("192.168.1.1", "dashboard_current")
        assert result == 1
        assert mock_redis.incr.call_count >= 2  # Mode + global
        assert mock_redis.expire.call_count >= 2

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_tracks_visitor_id(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        mock_get_redis.return_value = mock_redis
        
        track_calculation("192.168.1.1", "dashboard_current", visitor_id="vis_123")
        # IP mode + IP global + visitor mode + visitor global = 4 incrs
        assert mock_redis.incr.call_count == 4

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_redis_error_returns_zero(self, mock_get_redis):
        mock_get_redis.side_effect = Exception("Redis down")
        result = track_calculation("192.168.1.1")
        assert result == 0


# ════════════════════════════════════════════════════════════════════
# get_remaining_calculations
# ════════════════════════════════════════════════════════════════════

class TestGetRemainingCalculations:

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_full_quota(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # No usage
        mock_get_redis.return_value = mock_redis
        
        result = get_remaining_calculations("192.168.1.1", "dashboard_current")
        assert result["mode_remaining"] == CALC_LIMITS["dashboard_current"]
        assert result["global_remaining"] == CALC_LIMITS["global"]

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_partial_usage(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "10"
        mock_get_redis.return_value = mock_redis
        
        result = get_remaining_calculations("192.168.1.1", "dashboard_current")
        assert result["mode_remaining"] == CALC_LIMITS["dashboard_current"] - 10
        assert result["mode_used"] == 10

    @patch("backend.api.middleware.rate_limiter._get_redis")
    def test_redis_error(self, mock_get_redis):
        mock_get_redis.side_effect = Exception("Redis down")
        result = get_remaining_calculations("192.168.1.1")
        assert result["mode_remaining"] == -1
        assert result["global_remaining"] == -1
