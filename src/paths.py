from pathlib import Path
import os

# The project root is one level above the 'src' directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Repository-owned directories
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

# Ensure essential directories exist
for directory in [OUTPUT_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Machine-specific paths (with environment variable overrides)
CHROME_BINARY = Path(
    os.getenv(
        "ML_PREDICTOR_CHROME_BINARY",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )
)

CHROME_DEBUG_DIR = Path(
    os.getenv(
        "ML_PREDICTOR_CHROME_DEBUG_DIR",
        str(OUTPUT_DIR / "chrome_debug"),
    )
)
# Ensure Chrome debug directory exists
CHROME_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
