# setup_venv.ps1 - Ensure virtual environment exists and is ready
$ErrorActionPreference = "Stop"

# Determine script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Ensure virtual environment exists
$VenvPath = Join-Path $ScriptDir ".venv"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

if (-not (Test-Path $VenvPath)) {
    Write-Output "[WARN] .venv not found. Creating virtual environment..."
    try {
        python -m venv $VenvPath
        Write-Output "[OK] Virtual environment created."
    } catch {
        Write-Output "[ERROR] Failed to create virtual environment. Ensure Python is installed and on PATH."
        Write-Output $_.Exception.Message
        exit 1
    }
}

if (Test-Path $ActivateScript) {
    Write-Output "[INFO] Virtual environment exists at $VenvPath"
} else {
    Write-Output "[ERROR] Virtual environment activation script not found at $ActivateScript"
    exit 1
}

# Install dependencies if needed
$Requirements = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $Requirements) {
    Write-Output "[INFO] Installing dependencies..."
    & $ActivateScript
    python -m pip install --upgrade pip
    pip install -r $Requirements
    Write-Output "[OK] Dependencies installed."
} else {
    Write-Output "[WARN] requirements.txt not found."
}

Write-Output "[OK] Setup complete. Virtual environment is ready."
