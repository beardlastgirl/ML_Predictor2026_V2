$ErrorActionPreference = "Stop"

Write-Host "Updating tooling..."
python -m pip install -U pip pip-tools

Write-Host "Compiling requirements.txt from requirements.in..."
python -m piptools compile requirements.in -o requirements.txt

Write-Host "Compiling dev-requirements.txt from dev-requirements.in..."
python -m piptools compile dev-requirements.in -o dev-requirements.txt

Write-Host "Syncing environment to dev-requirements.txt..."
python -m piptools sync dev-requirements.txt

Write-Host "Running dependency checks..."
python -m pip check

Write-Host "Installing Playwright Chromium..."
python -m playwright install chromium

Write-Host "Done."