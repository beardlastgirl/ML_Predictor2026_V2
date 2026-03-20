# Logging and Generic Utilities

import glob
import os

def log_info(message):
    print(f"[INFO] {message}")

def log_ok(message):
    print(f"[OK] {message}")

def log_error(message):
    print(f"[ERROR] {message}")

def log_warning(message):
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
