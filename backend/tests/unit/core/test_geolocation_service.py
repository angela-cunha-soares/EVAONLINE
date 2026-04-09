"""
Tests for GeolocationService — pure-logic static methods.

Covers:
- _detect_climate_region (bounding-box classification)
- _parse_user_agent (device/browser/OS detection)
- generate_visitor_id, generate_session_id (uniqueness)
"""

from backend.core.analytics.geolocation_service import GeolocationService


class TestDetectClimateRegion:
    """_detect_climate_region: lat/lon → 'usa' | 'nordic' | 'global'"""

    def test_usa_continental(self):
        assert GeolocationService._detect_climate_region(37.0, -100.0) == "usa"

    def test_usa_corner_nw(self):
        assert GeolocationService._detect_climate_region(49.0, -125.0) == "usa"

    def test_usa_corner_se(self):
        assert GeolocationService._detect_climate_region(24.0, -66.0) == "usa"

    def test_nordic_oslo(self):
        assert GeolocationService._detect_climate_region(59.91, 10.75) == "nordic"

    def test_nordic_corner_sw(self):
        assert GeolocationService._detect_climate_region(54.0, 4.0) == "nordic"

    def test_nordic_corner_ne(self):
        assert GeolocationService._detect_climate_region(71.5, 32.0) == "nordic"

    def test_brazil_global(self):
        assert GeolocationService._detect_climate_region(-15.79, -47.88) == "global"

    def test_japan_global(self):
        assert GeolocationService._detect_climate_region(35.68, 139.69) == "global"

    def test_antarctica_global(self):
        assert GeolocationService._detect_climate_region(-80.0, 0.0) == "global"

    def test_boundary_outside_usa_south(self):
        # Just below USA south boundary (lat 24)
        assert GeolocationService._detect_climate_region(23.9, -100.0) == "global"

    def test_boundary_outside_nordic_east(self):
        # Just east of Nordic boundary (lon 32)
        assert GeolocationService._detect_climate_region(60.0, 32.1) == "global"


class TestParseUserAgent:
    """_parse_user_agent: UA string → {device_type, browser, os}"""

    def test_desktop_chrome_windows(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "desktop"
        assert result["browser"] == "chrome"
        assert result["os"] == "windows"

    def test_mobile_android_chrome(self):
        ua = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0 Mobile"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "mobile"
        assert result["browser"] == "chrome"
        # Source checks 'Linux' before 'Android' so Linux-based Android UAs → 'linux'
        assert result["os"] == "linux"

    def test_tablet_ipad(self):
        ua = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) Safari/604.1"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "tablet"
        assert result["browser"] == "safari"
        assert result["os"] == "macos"

    def test_desktop_firefox_linux(self):
        ua = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "desktop"
        assert result["browser"] == "firefox"
        assert result["os"] == "linux"

    def test_desktop_edge_windows(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Edg/120.0"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "desktop"
        assert result["browser"] == "edge"
        assert result["os"] == "windows"

    def test_mobile_iphone(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/21A329"
        result = GeolocationService._parse_user_agent(ua)
        assert result["device_type"] == "mobile"
        assert result["browser"] == "other"
        # Source checks 'Mac' before 'iPhone' so Mac OS X-based iPhone UAs → 'macos'
        assert result["os"] == "macos"

    def test_unknown_agent(self):
        result = GeolocationService._parse_user_agent("Unknown")
        assert result["device_type"] == "desktop"
        assert result["browser"] == "other"
        assert result["os"] == "other"


class TestGenerateIds:
    """Visitor and session ID generation — format and uniqueness."""

    def test_visitor_id_format(self):
        vid = GeolocationService.generate_visitor_id()
        assert vid.startswith("visitor_")
        assert len(vid) == 20  # "visitor_" + 12 hex chars

    def test_visitor_id_unique(self):
        ids = {GeolocationService.generate_visitor_id() for _ in range(200)}
        assert len(ids) == 200

    def test_session_id_format(self):
        sid = GeolocationService.generate_session_id()
        assert sid.startswith("sess_")
        assert len(sid) == 21  # "sess_" + 16 hex chars

    def test_session_id_unique(self):
        ids = {GeolocationService.generate_session_id() for _ in range(200)}
        assert len(ids) == 200
