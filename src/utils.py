# Logging and Generic Utilities

import glob
import os

def log_info(message):
    """Print an informational message to stdout.

    Kept deliberately minimal so logs are portable across environments.
    """
    print(f"[INFO] {message}")

def log_ok(message):
    """Print a success message to stdout."""
    print(f"[OK] {message}")

def log_error(message):
    """Print an error message to stdout."""
    print(f"[ERROR] {message}")

def log_warning(message):
    """Print a warning message to stdout."""
    print(f"[WARNING] {message}")

def find_latest_file(pattern):
    """Return the path to the most recently modified file matching pattern."""
    files = glob.glob(pattern)
    if not files:
        log_error(f"No files match the pattern {pattern}")
        raise FileNotFoundError(f"No files match the pattern {pattern}")
    latest = max(files, key=os.path.getmtime)
    log_info(f"Latest file found: {latest}")
    return latest
