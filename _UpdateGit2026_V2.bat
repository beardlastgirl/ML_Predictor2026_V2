@echo off
setlocal enabledelayedexpansion

:: Navigate to the project directory
cd /d I:\Scripts\ML_Predictor2026_V2

echo ========================================
echo   ML_Predictor2026_V2 - GIT UPDATE TOOL
echo ========================================

:: 0. Refuse to stage if any sensitive-looking file is present in the working tree
set "SENSITIVE="
for /f "usebackq delims=" %%L in (`git status --porcelain ^| findstr /I /C:".env" /C:".pem" /C:".key" /C:".p12" /C:".pfx" /C:"id_rsa" /C:".git-credentials" ^| findstr /V /I /C:".env.example"`) do set "SENSITIVE=%%L"
if defined SENSITIVE (
    echo.
    echo [ABORT] Sensitive-looking file detected in working tree: %SENSITIVE%
    echo         Nothing was staged. Remove it or add it to .gitignore first.
    pause
    exit /b 1
)

:: 1. Stage and Commit Local Changes First
echo [1/3] Staging local changes...
git add .

:: Check if there are changes to commit
git diff --cached --quiet
if %ERRORLEVEL% equ 0 (
    echo [INFO] No local changes to commit.
) else (
    set /p commit_msg="Enter commit message (or press Enter for default 'Update'): "
    if "!commit_msg!"=="" set commit_msg=Update %date% %time%
    echo [INFO] Committing with message: "!commit_msg!"
    git commit -m "!commit_msg!"
)

echo.
:: 2. Pull latest changes
echo [2/3] Fetching and merging remote changes...
:: --no-rebase ensures we use merge, --no-edit avoids the editor
git pull origin main --no-rebase --no-edit
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Pull/Merge failed. Likely a conflict that needs manual resolving.
    echo.
    echo TIPS TO RESOLVE:
    echo 1. If you want to FORCE your local files to GitHub (overwriting remote):
    echo    Run: git push origin main --force
    echo.
    echo 2. If you want to DISCARD your local changes and match GitHub:
    echo    Run: git reset --hard origin/main
    echo.
    pause
    exit /b %ERRORLEVEL%
)

:: 3. Push changes
echo.
echo [3/3] Pushing to GitHub...
git push origin main
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Push failed. 
    echo Check internet or try: git push origin main --force
) else (
    echo.
    echo ========================================
    echo   UPDATE COMPLETED SUCCESSFULLY!
    echo ========================================
)

pause
