"""
Comprehensive tests for email_templates.py — 719 lines of pure functions.
All functions are pure: no I/O, no DB, no network.
"""
from datetime import datetime
from backend.core.utils.email_templates import (
    _t,
    get_email_header,
    get_email_footer,
    create_processing_started_email,
    create_data_ready_email,
    create_processing_error_email,
)


# ════════════════════════════════════════════════════════════════
# Translation helper _t
# ════════════════════════════════════════════════════════════════
class TestTranslationHelper:
    def test_t_english(self):
        val = _t("en", "location")
        assert isinstance(val, str)
        assert len(val) > 0

    def test_t_portuguese(self):
        val = _t("pt", "location")
        assert isinstance(val, str)
        assert len(val) > 0

    def test_t_unknown_key(self):
        val = _t("en", "nonexistent_key_xxx")
        assert isinstance(val, str)  # Returns key or fallback

    def test_t_unknown_lang_fallback(self):
        val = _t("fr", "location")
        assert isinstance(val, str)


# ════════════════════════════════════════════════════════════════
# Email header / footer
# ════════════════════════════════════════════════════════════════
class TestEmailHeaderFooter:
    def test_header_en(self):
        html = get_email_header("en")
        assert "EVAonline" in html
        assert "<" in html  # contains HTML tags

    def test_header_pt(self):
        html = get_email_header("pt")
        assert "EVAonline" in html

    def test_header_default(self):
        html = get_email_header()
        assert isinstance(html, str)
        assert len(html) > 50

    def test_footer_en(self):
        html = get_email_footer("en")
        assert "FAO-56" in html or "Penman" in html or "automated" in html.lower()

    def test_footer_pt(self):
        html = get_email_footer("pt")
        assert isinstance(html, str)
        assert len(html) > 20

    def test_footer_default(self):
        html = get_email_footer()
        assert isinstance(html, str)


# ════════════════════════════════════════════════════════════════
# create_processing_started_email
# ════════════════════════════════════════════════════════════════
class TestProcessingStartedEmail:
    def test_returns_subject_and_body(self):
        subject, body = create_processing_started_email(
            task_id="test-123",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-10",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        assert isinstance(subject, str)
        assert isinstance(body, str)
        assert len(subject) > 0
        assert len(body) > 100

    def test_contains_coordinates(self):
        _, body = create_processing_started_email(
            task_id="test-456",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-31",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        assert "-23.55" in body
        assert "-46.63" in body

    def test_contains_dates(self):
        _, body = create_processing_started_email(
            task_id="test-789",
            latitude=40.71,
            longitude=-74.01,
            start_date="2024-06-01",
            end_date="2024-06-30",
            started_at=datetime(2024, 6, 1, 8, 0, 0),
        )
        assert "2024-06-01" in body
        assert "2024-06-30" in body

    def test_portuguese(self):
        subject, body = create_processing_started_email(
            task_id="pt-test",
            latitude=38.72,
            longitude=-9.14,
            start_date="2024-03-01",
            end_date="2024-03-31",
            started_at=datetime(2024, 3, 1, 10, 0, 0),
            lang="pt",
        )
        assert isinstance(subject, str)
        assert isinstance(body, str)

    def test_file_format_csv(self):
        subject, body = create_processing_started_email(
            task_id="csv-test",
            latitude=-15.0,
            longitude=-47.0,
            start_date="2024-01-01",
            end_date="2024-01-10",
            started_at=datetime(2024, 1, 1, 0, 0, 0),
            file_format="csv",
        )
        assert "csv" in body.lower() or "CSV" in body

    def test_file_format_excel(self):
        subject, body = create_processing_started_email(
            task_id="xlsx-test",
            latitude=-15.0,
            longitude=-47.0,
            start_date="2024-01-01",
            end_date="2024-01-10",
            started_at=datetime(2024, 1, 1, 0, 0, 0),
            file_format="excel",
        )
        assert "excel" in body.lower() or "xlsx" in body.lower() or "Excel" in body


# ════════════════════════════════════════════════════════════════
# create_data_ready_email
# ════════════════════════════════════════════════════════════════
class TestDataReadyEmail:
    def test_returns_subject_and_body(self):
        subject, body = create_data_ready_email(
            task_id="ready-123",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-31",
            days_processed=31,
            processing_time_seconds=45.5,
            sources_used=["NASA POWER", "Open-Meteo"],
        )
        assert isinstance(subject, str)
        assert isinstance(body, str)
        assert len(body) > 200

    def test_contains_sources(self):
        _, body = create_data_ready_email(
            task_id="src-test",
            latitude=40.71,
            longitude=-74.01,
            start_date="2024-06-01",
            end_date="2024-06-30",
            days_processed=30,
            processing_time_seconds=120.0,
            sources_used=["NASA POWER", "Open-Meteo Archive"],
        )
        assert "NASA" in body or "POWER" in body

    def test_contains_days(self):
        _, body = create_data_ready_email(
            task_id="days-test",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-15",
            days_processed=15,
            processing_time_seconds=30.0,
            sources_used=["Open-Meteo"],
        )
        assert "15" in body

    def test_with_elevation(self):
        _, body = create_data_ready_email(
            task_id="elev-test",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-31",
            days_processed=31,
            processing_time_seconds=60.0,
            sources_used=["NASA POWER"],
            elevation=760.0,
        )
        assert "760" in body

    def test_with_summary_stats(self):
        _, body = create_data_ready_email(
            task_id="stats-test",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-07-01",
            end_date="2024-07-31",
            days_processed=31,
            processing_time_seconds=90.0,
            sources_used=["NASA POWER"],
            summary_stats={
                "et0_mean_mm_day": 4.5,
                "et0_max_mm_day": 7.2,
                "et0_min_mm_day": 2.1,
                "et0_total_mm": 139.5,
            },
        )
        assert isinstance(body, str)
        assert len(body) > 200  # Should have substantial HTML content

    def test_portuguese_lang(self):
        subject, body = create_data_ready_email(
            task_id="pt-ready",
            latitude=38.72,
            longitude=-9.14,
            start_date="2024-03-01",
            end_date="2024-03-31",
            days_processed=31,
            processing_time_seconds=60.0,
            sources_used=["Open-Meteo"],
            lang="pt",
        )
        assert isinstance(subject, str)
        assert isinstance(body, str)

    def test_csv_format(self):
        _, body = create_data_ready_email(
            task_id="csv-ready",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-10",
            days_processed=10,
            processing_time_seconds=30.0,
            sources_used=["NASA POWER"],
            file_format="csv",
        )
        assert "csv" in body.lower() or "CSV" in body

    def test_fast_processing_time(self):
        _, body = create_data_ready_email(
            task_id="fast",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-02",
            days_processed=2,
            processing_time_seconds=0.5,
            sources_used=["Open-Meteo Forecast"],
        )
        assert isinstance(body, str)


# ════════════════════════════════════════════════════════════════
# create_processing_error_email
# ════════════════════════════════════════════════════════════════
class TestProcessingErrorEmail:
    def test_returns_subject_and_body(self):
        subject, body = create_processing_error_email(
            task_id="err-123",
            latitude=-23.55,
            longitude=-46.63,
            start_date="2024-01-01",
            end_date="2024-01-31",
            error_message="Connection timeout reaching NASA POWER",
        )
        assert isinstance(subject, str)
        assert isinstance(body, str)
        assert len(body) > 100

    def test_contains_error_message(self):
        _, body = create_processing_error_email(
            task_id="err-456",
            latitude=40.71,
            longitude=-74.01,
            start_date="2024-06-01",
            end_date="2024-06-30",
            error_message="Data source unavailable: 503",
        )
        assert "503" in body or "unavailable" in body.lower()

    def test_contains_coordinates(self):
        _, body = create_processing_error_email(
            task_id="err-coords",
            latitude=-15.78,
            longitude=-47.93,
            start_date="2024-01-01",
            end_date="2024-01-10",
            error_message="Validation error",
        )
        assert "-15.78" in body
        assert "-47.93" in body

    def test_portuguese_lang(self):
        subject, body = create_processing_error_email(
            task_id="err-pt",
            latitude=38.72,
            longitude=-9.14,
            start_date="2024-03-01",
            end_date="2024-03-31",
            error_message="Erro de timeout",
            lang="pt",
        )
        assert isinstance(subject, str)
        assert isinstance(body, str)
