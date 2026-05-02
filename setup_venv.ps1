# setup_venv.ps1 - Ensure virtual environment exists and is ready
$ErrorActionPreference = "Stop"

# Determine script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Ensure virtual environment exists
$VenvPath = Join-Path $ScriptDir ".venv"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

# Check if the activation script exists. If not, recreate the virtual environment.
if (-not (Test-Path $ActivateScript)) {
    Write-Output "[WARN] Virtual environment activation script not found. Recreating virtual environment..."
    # If the .venv directory exists but is incomplete, remove it before recreating
    if (Test-Path $VenvPath) {
        Write-Output "[INFO] Removing incomplete .venv directory..."
        Remove-Item -Path $VenvPath -Recurse -Force
    }
    try {
        python -m venv $VenvPath
        Write-Output "[OK] Virtual environment created."
    } catch {
        Write-Output "[ERROR] Failed to create virtual environment. Ensure Python is installed and on PATH."
        Write-Output $_.Exception.Message
        exit 1
    }
} else {
    Write-Output "[INFO] Virtual environment and activation script found at $VenvPath"
}

# Install dependencies if needed
$RequirementsIn = Join-Path $ScriptDir "requirements.in"
$RequirementsTxt = Join-Path $ScriptDir "requirements.txt"

if (Test-Path $RequirementsIn) {
    Write-Output "[INFO] Activating virtual environment to install pip-tools and compile requirements..."
    & $ActivateScript
    python -m pip install --upgrade pip

    # Install pip-tools to compile requirements
    Write-Output "[INFO] Installing pip-tools..."
    pip install pip-tools
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install pip-tools."
        exit 1
    }

    # Compile requirements.txt from requirements.in
    Write-Output "[INFO] Compiling requirements.txt from requirements.in..."
    pip-compile --output-file=$RequirementsTxt $RequirementsIn
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to compile requirements.txt."
        exit 1
    }

    Write-Output "[INFO] Installing compiled dependencies..."
    pip install -r $RequirementsTxt
    Write-Output "[OK] Dependencies installed."
} else {
    Write-Output "[WARN] requirements.in not found. Skipping dependency installation."
}

Write-Output "[OK] Setup complete. Virtual environment is ready."
