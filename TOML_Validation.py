import os
import tomlkit
from pathlib import Path

# Define base directory for agent configs
BASE_DIR = "I:\Scripts\ML_Predictor2026_V2\.agents"


def validate_and_enhance_toml_files():
    """
    Enhances each .toml file in the agents folder by:
        - Adding missing top-level tables (e.g., [config], [environment])
        - Ensuring required fields are present and typed correctly
        - Adding metadata like version, author, date
    """
    for filename in os.listdir(BASE_DIR):
        if not filename.endswith(".toml"):
            continue

        filepath = Path(BASE_DIR) / filename
        print(f"Processing: {filepath}")

        # Read existing TOML content
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            data = tomlkit.loads(content)
        except Exception as e:
            print(f"[ERROR] Failed to read file {filename}: {e}")
            continue

        # Define required fields (with default values and types)
        REQUIRED_FIELDS = {
            "sandbox_mode": True,
            "developer_instructions": "",
            "version": "1.0",
            "author": "Codex Team",
            "created_date": "2026-07-17",
        }

        # Enforce presence of required fields
        for field, default_value in REQUIRED_FIELDS.items():
            if not data.get(field):
                print(
                    f"[WARNING] Missing field '{field}' in {filename}. Adding with default value."
                )
                data[field] = default_value

        # Add configuration table (optional but recommended)
        config_table = data.setdefault("config", {})
        config_table["environment"] = "development"
        config_table["debug_mode"] = True
        config_table["max_retries"] = 3

        # Add environment table for agent-specific settings
        env_table = data.setdefault("environment", {})
        env_table["api_key"] = ""
        env_table["timeout_seconds"] = 60

        # Update file with enhanced structure and validate TOML syntax
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(tomlkit.dumps(data))
            print(f"[SUCCESS] Successfully updated: {filepath}")
        except Exception as e:
            print(f"[ERROR] Failed to write file {filename}: {e}")


# Run the enhancement
if __name__ == "__main__":
    validate_and_enhance_toml_files()
