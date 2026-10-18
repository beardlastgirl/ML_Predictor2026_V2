# ML_Predictor2026_V2 - Menu-driven Runner
# Run individual scripts or the complete pipeline

param(
    [string]$Option = "0"
)

$ErrorActionPreference = "Stop"

# ============================================
# Functions
# ============================================

function Test-Prerequisites {
    $dataDir = Join-Path $PSScriptRoot "data"
    $dataPath = Join-Path $dataDir "ARG.csv"
    $url = "https://football-data.co.uk/new/ARG.csv"
    $daysThreshold = 5

    # Ensure the data directory exists
    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    }

    $shouldDownload = $false

    # Check if file exists and its age
    if (-not (Test-Path $dataPath)) {
        Write-Host "[INFO] ARG.csv not found. Preparing to download..." -ForegroundColor Yellow
        $shouldDownload = $true
    }
    else {
        $fileAge = (Get-Date) - (Get-Item $dataPath).LastWriteTime
        if ($fileAge.Days -ge $daysThreshold) {
            Write-Host "[INFO] ARG.csv is older than $daysThreshold days (Age: $($fileAge.Days) days). Preparing to update..." -ForegroundColor Yellow
            $shouldDownload = $true
        }
        else {
            Write-Host "[INFO] ARG.csv is up to date (Age: $($fileAge.Days) days)." -ForegroundColor Green
        }
    }

    # Download if necessary
    if ($shouldDownload) {
        try {
            Write-Host "[INFO] Downloading ARG.csv from $url..." -ForegroundColor Cyan
            Invoke-WebRequest -Uri $url -OutFile $dataPath -UseBasicParsing
            Write-Host "[SUCCESS] ARG.csv downloaded successfully." -ForegroundColor Green
        }
        catch {
            Write-Host "[ERROR] Failed to download ARG.csv: $_" -ForegroundColor Red
            return $false
        }
    }

    # Check if Glossary.txt exists
    $glossaryPath = Join-Path $PSScriptRoot "Glossary.txt"
    if (-not (Test-Path $glossaryPath)) {
        $sourceGlossary = Join-Path $dataDir "Glossary.txt"
        if (Test-Path $sourceGlossary) {
            Write-Host "[INFO] Copying Glossary.txt from data folder..." -ForegroundColor Yellow
            Copy-Item $sourceGlossary $glossaryPath
        }
        else {
            Write-Host "[WARNING] Glossary.txt not found in data folder." -ForegroundColor Yellow
        }
    }
    
    return $true
}

function Enable-Venv {
    $venvPath = Join-Path $PSScriptRoot ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Yellow
        . "$venvPath"
    }
    else {
        Write-Host "[WARNING] Virtual environment not found, using system Python" -ForegroundColor Yellow
    }
}

function Invoke-Script {
    param(
        [string]$ScriptName,
        [string]$Description,
        [string]$ScriptArgs = ""
    )

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Running: $Description" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan

    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    if (-not (Test-Path $scriptPath)) {
        Write-Host "[ERROR] Script not found: $scriptPath" -ForegroundColor Red
        return $false
    }

    # Set working directory to project root so relative paths work
    Push-Location -Path $PSScriptRoot

    if ($ScriptArgs) {
        & python $scriptPath $ScriptArgs
    }
    else {
        & python $scriptPath
    }

    # Restore previous location
    Pop-Location

    $exitCode = $LASTEXITCODE

    if ($exitCode -eq 0) {
        Write-Host "[OK] Completed successfully" -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] Failed with exit code $exitCode" -ForegroundColor Red
    }

    return ($exitCode -eq 0)
}

function Show-Menu {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "ML_Predictor2026_V2 - Menu" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1 - Parse Reporte PDFs" -ForegroundColor White
    Write-Host "2 - Scrape FBref Stats" -ForegroundColor White
    Write-Host "3 - Scrape FootyStats (Playwright)" -ForegroundColor White
    Write-Host "4 - Scrape Sofascore (via Apify)" -ForegroundColor White
    Write-Host "5 - Scrape TyC Sports" -ForegroundColor White
    Write-Host "6 - Manual Scraper (CDP Connection)" -ForegroundColor White
    Write-Host "7 - Run Main Prediction Model" -ForegroundColor White
    Write-Host "8 - Run All Data Scrapers + Prediction" -ForegroundColor White
    Write-Host ""
    Write-Host "0 - Exit" -ForegroundColor Gray
    Write-Host ""
}

# ============================================
# Main
# ============================================

# Check prerequisites
if (-not (Test-Prerequisites)) {
    exit 1
}

# Show menu if no option specified
if ($Option -eq 0) {
    Show-Menu

    do {
        $menuInput = Read-Host "Select an option"

        if ([string]::IsNullOrWhiteSpace($menuInput)) {
            Write-Host "[INFO] No option selected, exiting." -ForegroundColor Yellow
            exit 0
        }
    } while ($menuInput -notmatch '^\d+$')

    $Option = [int]$menuInput
}

# Validate option
if ($Option -notmatch '^\d+$') {
    Write-Host "[ERROR] Invalid option: $Option" -ForegroundColor Red
    exit 1
}
$Option = [int]$Option

if ($Option -lt 0 -or $Option -gt 8) {
    Write-Host "[ERROR] Invalid option: $Option" -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Enable-Venv

# Execute selected option
switch ($Option) {
    1 {
        # Parse Reporte PDFs
        Invoke-Script -ScriptName "parse_reporte_pdfs.py" -Description "Parse Reporte PDFs"
    }
    2 {
        # Scrape FBref
        Invoke-Script -ScriptName "scrape_stats_enhanced.py" -Description "Scrape FBref Stats"
    }
    3 {
        # Scrape FootyStats
        Invoke-Script -ScriptName "scrape_footystats.py" -Description "Scrape FootyStats (Playwright)" -ScriptArgs "--headless"
    }
    4 {
        # Scrape Sofascore via Apify
        Invoke-Script -ScriptName "scrape_sofascore_apify.py" -Description "Scrape Sofascore (via Apify)"
    }
    5 {
        # Scrape TyC
        Invoke-Script -ScriptName "scrape_tyc.py" -Description "Scrape TyC Sports"
    }
    6 {
        # Manual Scraper
        Write-Host ""
        Write-Host "Ensure Chrome is running with remote debugging on port 9222" -ForegroundColor Cyan
        Invoke-Script -ScriptName "scrape_stats_manual.py" -Description "Manual Browser Scraper"
    }
    7 {
        # Run Main
        Invoke-Script -ScriptName "main.py" -Description "Run Main Prediction Model"
    }
    8 {
        # Run All
        Write-Host ""
        Write-Host "Running all data scrapers followed by prediction..." -ForegroundColor Cyan

        Write-Host ""
        Write-Host "Step 1/5: Parsing Reporte PDFs..." -ForegroundColor Yellow
        if (-not (Invoke-Script -ScriptName "parse_reporte_pdfs.py" -Description "Parse Reporte PDFs")) { exit 1 }

        Write-Host ""
        Write-Host "Step 2/5: Scraping FBref..." -ForegroundColor Yellow
        if (-not (Invoke-Script -ScriptName "scrape_stats_enhanced.py" -Description "Scrape FBref Stats")) { exit 1 }

        Write-Host ""
        Write-Host "Step 3/5: Scraping FootyStats..." -ForegroundColor Yellow
        if (-not (Invoke-Script -ScriptName "scrape_footystats.py" -Description "Scrape FootyStats" -ScriptArgs "--headless")) { exit 1 }

        Write-Host ""
        Write-Host "Step 4/5: Scraping Sofascore..." -ForegroundColor Yellow
        if (-not (Invoke-Script -ScriptName "scrape_sofascore_apify.py" -Description "Scrape Sofascore")) { exit 1 }

        Write-Host ""
        Write-Host "Step 5/5: Running prediction model..." -ForegroundColor Yellow
        if (-not (Invoke-Script -ScriptName "main.py" -Description "Run Main Prediction Model")) { exit 1 }

        # Show results
        $results = Get-ChildItem -Path $PSScriptRoot -Filter "Resultados_*.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($results) {
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Cyan
            Write-Host "Results saved to: $($results.Name)" -ForegroundColor Cyan
            Write-Host "========================================" -ForegroundColor Cyan
            Get-Content $results.FullName | Select-Object -First 35
        }
    }

    0 {
        Write-Host "[INFO] Exiting." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
