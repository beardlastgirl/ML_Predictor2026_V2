"""
Scraper resilience utilities for ML_Predictor2026_V2

Provides decorator-based error handling, retry logic, and resource cleanup
for all web scrapers to ensure graceful degradation and proper error reporting.
"""

import functools
import time
import logging
from typing import Callable, Optional, Any, Tuple, List
from src.utils import log_info, log_ok, log_error, log_warning


class ScraperException(Exception):
    """Base exception for scraper errors."""
    pass


class CaptchaDetectedException(ScraperException):
    """Raised when CAPTCHA is detected."""
    pass


class ScraperTimeoutException(ScraperException):
    """Raised when scraper times out."""
    pass


class ScraperResourceError(ScraperException):
    """Raised when resources (browser, driver) fail."""
    pass


def detect_captcha_in_content(content: str) -> bool:
    """
    Detect common CAPTCHA indicators in page content.
    
    Args:
        content: HTML content or text response from page
    
    Returns:
        True if CAPTCHA detected, False otherwise
    """
    if not content:
        return False
    
    content_lower = str(content).lower()
    
    captcha_indicators = [
        "not a robot",
        "verify you are human",
        "recaptcha",
        "captcha",
        "challenge",
        "verify human",
        "verify yourself",
        "are you human",
    ]
    
    return any(indicator in content_lower for indicator in captcha_indicators)


def resilient_scraper(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    timeout: int = 30,
    fallback_source: Optional[str] = None,
    resource_cleanup: Optional[Callable] = None,
):
    """
    Decorator for resilient web scrapers with retry logic and error handling.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (2.0 = double wait each retry)
        timeout: Timeout in seconds per scraper attempt
        fallback_source: Name of fallback scraper to use on failure
        resource_cleanup: Optional cleanup function (e.g., browser.quit())
    
    Usage:
        @resilient_scraper(max_retries=3, fallback_source='footystats')
        def scrape_fbref_stats():
            # Scraping logic here
            return data
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            """Wrapped function with retry logic and error handling."""
            
            scraper_name = func.__name__
            attempt = 0
            last_error = None
            
            while attempt < max_retries:
                attempt += 1
                try:
                    log_info(f"[{scraper_name}] Attempt {attempt}/{max_retries}...")
                    
                    # Execute the scraper
                    result = func(*args, **kwargs)
                    
                    log_ok(f"[{scraper_name}] Success on attempt {attempt}")
                    return result
                
                except CaptchaDetectedException as e:
                    last_error = e
                    log_error(f"[{scraper_name}] CAPTCHA detected on attempt {attempt}")
                    if attempt < max_retries:
                        wait_time = int(backoff_factor ** attempt)
                        log_warning(f"[{scraper_name}] Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                
                except ScraperTimeoutException as e:
                    last_error = e
                    log_error(f"[{scraper_name}] Timeout on attempt {attempt}")
                    if attempt < max_retries:
                        wait_time = int(backoff_factor ** attempt)
                        log_warning(f"[{scraper_name}] Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                
                except ScraperResourceError as e:
                    last_error = e
                    log_error(f"[{scraper_name}] Resource error on attempt {attempt}: {e}")
                    if resource_cleanup:
                        try:
                            log_info(f"[{scraper_name}] Cleaning up resources...")
                            resource_cleanup()
                        except Exception as cleanup_error:
                            log_error(f"[{scraper_name}] Cleanup failed: {cleanup_error}")
                    
                    if attempt < max_retries:
                        wait_time = int(backoff_factor ** attempt)
                        log_warning(f"[{scraper_name}] Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                
                except Exception as e:
                    last_error = e
                    log_error(f"[{scraper_name}] Unexpected error on attempt {attempt}: {e}")
                    if attempt < max_retries:
                        wait_time = int(backoff_factor ** attempt)
                        log_warning(f"[{scraper_name}] Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                
                finally:
                    # Ensure cleanup happens after each attempt
                    if resource_cleanup and attempt == max_retries:
                        try:
                            log_info(f"[{scraper_name}] Final cleanup after {attempt} attempts")
                            resource_cleanup()
                        except Exception as cleanup_error:
                            log_error(f"[{scraper_name}] Final cleanup failed: {cleanup_error}")
            
            # All retries exhausted
            if fallback_source:
                log_warning(f"[{scraper_name}] All {max_retries} retries exhausted. "
                          f"Trying fallback: {fallback_source}")
                raise ScraperException(f"Scraper failed after {max_retries} attempts. "
                                     f"Consider using fallback: {fallback_source}")
            else:
                raise ScraperException(f"Scraper {scraper_name} failed after {max_retries} attempts: {last_error}")
        
        return wrapper
    
    return decorator


def validate_scraper_output(data: Any, expected_type: type, min_size: int = 0) -> bool:
    """
    Validate scraper output meets minimum requirements.
    
    Args:
        data: Output data from scraper
        expected_type: Expected data type (dict, list, pd.DataFrame)
        min_size: Minimum size/length expected
    
    Returns:
        True if valid, False otherwise
    
    Raises:
        ValueError: If data is invalid
    """
    if not isinstance(data, expected_type):
        raise ValueError(f"Expected {expected_type.__name__}, got {type(data).__name__}")
    
    if hasattr(data, '__len__'):
        if len(data) < min_size:
            raise ValueError(f"Expected at least {min_size} items, got {len(data)}")
    
    return True


def log_scraper_context(scraper_name: str, context: dict) -> None:
    """
    Log contextual information about a scraper for debugging.
    
    Args:
        scraper_name: Name of the scraper
        context: Dictionary with context info (url, team, date, etc.)
    """
    context_str = ", ".join(f"{k}={v}" for k, v in context.items())
    log_info(f"[{scraper_name}] Context: {context_str}")


class ScraperSession:
    """Context manager for scraper resource cleanup."""
    
    def __init__(self, scraper_name: str, resource: Any):
        self.scraper_name = scraper_name
        self.resource = resource
    
    def __enter__(self):
        log_info(f"[{self.scraper_name}] Opening resource...")
        return self.resource
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            log_error(f"[{self.scraper_name}] Exception in context: {exc_val}")
        
        try:
            # Try common cleanup methods
            if hasattr(self.resource, 'quit'):
                self.resource.quit()
            elif hasattr(self.resource, 'close'):
                self.resource.close()
            elif hasattr(self.resource, 'cleanup'):
                self.resource.cleanup()
            
            log_ok(f"[{self.scraper_name}] Resource cleaned up")
        except Exception as e:
            log_error(f"[{self.scraper_name}] Cleanup failed: {e}")
        
        return False  # Don't suppress exceptions


class ScraperHealthMonitor:
    """Track scraper health metrics for monitoring."""
    
    def __init__(self):
        self.runs: dict = {}  # scraper_name -> list of run results
    
    def record_run(self, scraper_name: str, success: bool, duration: float, error: Optional[str] = None):
        """Record a scraper run."""
        if scraper_name not in self.runs:
            self.runs[scraper_name] = []
        
        self.runs[scraper_name].append({
            'success': success,
            'duration': duration,
            'error': error,
            'timestamp': time.time()
        })
    
    def get_health(self, scraper_name: str, window_size: int = 10) -> dict:
        """Get health metrics for a scraper."""
        if scraper_name not in self.runs:
            return {'success_rate': 0, 'avg_duration': 0, 'total_runs': 0}
        
        recent_runs = self.runs[scraper_name][-window_size:]
        successes = sum(1 for r in recent_runs if r['success'])
        total = len(recent_runs)
        avg_duration = sum(r['duration'] for r in recent_runs) / total if total > 0 else 0
        
        return {
            'scraper': scraper_name,
            'success_rate': successes / total if total > 0 else 0,
            'avg_duration': avg_duration,
            'total_runs': len(self.runs[scraper_name]),
            'recent_window': window_size
        }
    
    def generate_report(self) -> str:
        """Generate health report for all scrapers."""
        lines = []
        lines.append("=" * 60)
        lines.append("SCRAPER HEALTH REPORT")
        lines.append("=" * 60)
        
        for scraper_name in self.runs:
            health = self.get_health(scraper_name)
            success_pct = health['success_rate'] * 100
            lines.append(f"{scraper_name}:")
            lines.append(f"  Success Rate: {success_pct:.1f}% ({int(health['success_rate'] * health['recent_window'])}/{health['recent_window']})")
            lines.append(f"  Avg Duration: {health['avg_duration']:.2f}s")
            lines.append(f"  Total Runs: {health['total_runs']}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Global health monitor instance
_health_monitor = ScraperHealthMonitor()


def get_health_monitor() -> ScraperHealthMonitor:
    """Get global health monitor instance."""
    return _health_monitor
