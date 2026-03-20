# ML_Predictor2026_V2 - Menu-driven Runner
# Run individual scripts or the complete pipeline

param(
    [int]$Option = 0
)

$ErrorActionPreference = "Stop"

# ============================================
# Functions
# ============================================

function Test-Prerequisites {
    # Check if data directory exists
    $dataPath = Join-Path $PSScriptRoot "data\ARG.csv"
    if (-not (Test-Path $dataPath)) {
        Write-Host "[ERROR] data\ARG.csv not found. Please copy from ML_Predictor2026" -ForegroundColor Red
        return $false
    }

    # Check if Glossary.txt exists
    $glossaryPath = Join-Path $PSScriptRoot "Glossary.txt"
    if (-not (Test-Path $glossaryPath)) {
        $sourceGlossary = Join-Path $PSScriptRoot "data\Glossary.txt"
        if (Test-Path $sourceGlossary) {
            Write-Host "[INFO] Copying Glossary.txt from data folder..." -ForegroundColor Yellow
            Copy-Item $sourceGlossary $glossaryPath
        }
        else {
            Write-Host "[WARNING] Glossary.txt not found" -ForegroundColor Yellow
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

    if ($ScriptArgs) {
        Invoke-Expression "python `"$scriptPath`" $ScriptArgs"
    }
    else {
        & python "$scriptPath"
    }

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

# Show menu if no option specified
if ($Option -eq 0) {
    Show-Menu
    $Option = Read-Host "Select an option"

    if ([string]::IsNullOrWhiteSpace($Option)) {
        Write-Host "[INFO] No option selected, exiting." -ForegroundColor Yellow
        exit 0
    }
}

# Validate option
$Option = [int]$Option

if ($Option -lt 0 -or $Option -gt 8) {
    Write-Host "[ERROR] Invalid option: $Option" -ForegroundColor Red
    exit 1
}

# Check prerequisites
if (-not (Test-Prerequisites)) {
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
        Invoke-Script -ScriptName "parse_reporte_pdfs.py" -Description "Parse Reporte PDFs"

        Write-Host ""
        Write-Host "Step 2/5: Scraping FBref..." -ForegroundColor Yellow
        Invoke-Script -ScriptName "scrape_stats_enhanced.py" -Description "Scrape FBref Stats"

        Write-Host ""
        Write-Host "Step 3/5: Scraping FootyStats..." -ForegroundColor Yellow
        Invoke-Script -ScriptName "scrape_footystats.py" -Description "Scrape FootyStats" -ScriptArgs "--headless"

        Write-Host ""
        Write-Host "Step 4/5: Scraping Sofascore..." -ForegroundColor Yellow
        Invoke-Script -ScriptName "scrape_sofascore_apify.py" -Description "Scrape Sofascore"

        Write-Host ""
        Write-Host "Step 5/5: Running prediction model..." -ForegroundColor Yellow
        Invoke-Script -ScriptName "main.py" -Description "Run Main Prediction Model"

        # Show results
        $results = Get-ChildItem -Filter "Resultados_*.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
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
