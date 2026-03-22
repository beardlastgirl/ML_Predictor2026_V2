"""
Tests for scraper utilities including resilience and error handling.
"""

import pytest
import time
from src.scraper_utils import (
    detect_captcha_in_content,
    ScraperException,
    CaptchaDetectedException,
    ScraperTimeoutException,
    resilient_scraper,
    validate_scraper_output,
    ScraperHealthMonitor,
)


# ==============================================
# CAPTCHA Detection Tests
# ==============================================

def test_detect_captcha_basic():
    """Test CAPTCHA detection with basic indicators."""
    assert detect_captcha_in_content("Please verify you are not a robot")
    assert detect_captcha_in_content("reCAPTCHA challenge")
    assert detect_captcha_in_content("verify you are human")
    assert not detect_captcha_in_content("Normal page content")


def test_detect_captcha_case_insensitive():
    """Test CAPTCHA detection is case-insensitive."""
    assert detect_captcha_in_content("NOT A ROBOT")
    assert detect_captcha_in_content("ReCapTCha")
    assert detect_captcha_in_content("Verify Human")


def test_detect_captcha_empty():
    """Test CAPTCHA detection with empty/None input."""
    assert not detect_captcha_in_content("")
    assert not detect_captcha_in_content(None)


# ==============================================
# Resilient Scraper Decorator Tests
# ==============================================

def test_resilient_scraper_success_first_try():
    """Test resilient scraper succeeds on first attempt."""
    call_count = 0
    
    @resilient_scraper(max_retries=3)
    def successful_scraper():
        nonlocal call_count
        call_count += 1
        return {"status": "success"}
    
    result = successful_scraper()
    assert result["status"] == "success"
    assert call_count == 1


def test_resilient_scraper_retry_then_success():
    """Test resilient scraper retries then succeeds."""
    call_count = 0
    
    @resilient_scraper(max_retries=3, backoff_factor=0.1)
    def flaky_scraper():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ScraperTimeoutException("Timeout on attempt")
        return {"status": "success"}
    
    result = flaky_scraper()
    assert result["status"] == "success"
    assert call_count == 3


def test_resilient_scraper_exhaust_retries():
    """Test resilient scraper fails after exhausting retries."""
    call_count = 0
    
    @resilient_scraper(max_retries=2, backoff_factor=0.01)
    def always_fails():
        nonlocal call_count
        call_count += 1
        raise ScraperException("Always fails")
    
    with pytest.raises(ScraperException):
        always_fails()
    
    assert call_count == 2


def test_resilient_scraper_captcha_detection():
    """Test resilient scraper handles CAPTCHA detection."""
    call_count = 0
    
    @resilient_scraper(max_retries=2, backoff_factor=0.01)
    def captcha_scraper():
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            raise CaptchaDetectedException("CAPTCHA found")
        return {"data": "success"}
    
    result = captcha_scraper()
    assert result["data"] == "success"
    assert call_count == 2


# ==============================================
# Scraper Output Validation Tests
# ==============================================

def test_validate_scraper_output_dict():
    """Test validation of dictionary output."""
    data = {"key": "value", "count": 10}
    assert validate_scraper_output(data, dict, min_size=0)


def test_validate_scraper_output_list():
    """Test validation of list output."""
    data = [1, 2, 3, 4, 5]
    assert validate_scraper_output(data, list, min_size=5)


def test_validate_scraper_output_wrong_type():
    """Test validation rejects wrong type."""
    data = [1, 2, 3]
    with pytest.raises(ValueError, match="Expected dict"):
        validate_scraper_output(data, dict)


def test_validate_scraper_output_too_small():
    """Test validation rejects undersized output."""
    data = [1, 2]
    with pytest.raises(ValueError, match="at least 5"):
        validate_scraper_output(data, list, min_size=5)


# ==============================================
# Health Monitor Tests
# ==============================================

def test_health_monitor_record_run():
    """Test health monitor records runs."""
    monitor = ScraperHealthMonitor()
    
    monitor.record_run("test_scraper", True, 1.5)
    monitor.record_run("test_scraper", True, 1.2)
    monitor.record_run("test_scraper", False, 2.1, error="Timeout")
    
    health = monitor.get_health("test_scraper", window_size=10)
    assert health['success_rate'] == pytest.approx(2/3, abs=0.01)
    assert health['avg_duration'] == pytest.approx((1.5 + 1.2 + 2.1) / 3, abs=0.01)
    assert health['total_runs'] == 3


def test_health_monitor_multiple_scrapers():
    """Test health monitor tracks multiple scrapers."""
    monitor = ScraperHealthMonitor()
    
    monitor.record_run("scraper_a", True, 1.0)
    monitor.record_run("scraper_a", True, 1.1)
    monitor.record_run("scraper_b", True, 2.0)
    monitor.record_run("scraper_b", False, 2.5)
    
    health_a = monitor.get_health("scraper_a")
    health_b = monitor.get_health("scraper_b")
    
    assert health_a['success_rate'] == 1.0
    assert health_b['success_rate'] == 0.5


def test_health_monitor_report_generation():
    """Test health monitor generates readable report."""
    monitor = ScraperHealthMonitor()
    
    monitor.record_run("scraper_x", True, 1.5)
    monitor.record_run("scraper_x", False, 2.0)
    
    report = monitor.generate_report()
    assert "SCRAPER HEALTH REPORT" in report
    assert "scraper_x" in report
    assert "50.0%" in report  # 50% success rate


def test_health_monitor_unknown_scraper():
    """Test health monitor handles unknown scrapers gracefully."""
    monitor = ScraperHealthMonitor()
    
    health = monitor.get_health("never_run", window_size=10)
    assert health['success_rate'] == 0
    assert health['total_runs'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
