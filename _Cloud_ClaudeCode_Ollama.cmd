@echo off
cls
cd /d i:\Scripts\ML_Predictor2026_V2

:menu
cls
echo ===================================================
echo     ML Predictor 2026 - Interactive Launcher
echo ===================================================
echo  CLOUD MODEL OPTION (Free):
echo    1. Nemotron-3-super:cloud
echo.
echo  LOCAL MODEL OPTIONS (NVIDIA RTX 4060):
echo    2. Liquid AI LFM 2.5 (8B)
echo    3. DeepSeek-R1 Reasoning (7B)
echo    4. Alibaba Qwen 3.5 Coder (9B)
echo    5. Google Gemma 4 (e4b-it-q4_K_M)
echo.
echo  MANAGED ROUTING:
echo    6. Qwen 3.5 Cloud Router
echo    7. Exit
echo ===================================================
set /p choice="Select your operational runtime [1-7]: "

if "%choice%"=="1" goto launch_glm
if "%choice%"=="2" goto launch_lfm
if "%choice%"=="3" goto launch_deepseek
if "%choice%"=="4" goto launch_qwen_local
if "%choice%"=="5" goto launch_gemma
if "%choice%"=="6" goto launch_qwen_cloud
if "%choice%"=="7" goto exit
goto menu

:launch_glm
echo.
echo Launching Claude Code with Nemotron-3-super:cloud...
ollama launch claude --model nemotron-3-super:cloud
goto end

:launch_lfm
echo.
echo Launching Claude Code locally with lfm2.5:8b...
ollama launch claude --model lfm2.5:8b
goto end

:launch_deepseek
echo.
echo Launching Claude Code locally with deepseek-r1:7b...
ollama launch claude --model deepseek-r1:7b
goto end

:launch_qwen_local
echo.
echo Launching Claude Code locally with qwen3.5:9b...
ollama launch claude --model qwen3.5:9b
goto end

:launch_gemma
echo.
echo Launching Claude Code locally with gemma4:e4b-it-q4_K_M...
ollama launch claude --model gemma4:e4b-it-q4_K_M
goto end

:launch_qwen_cloud
echo.
echo Launching Claude Code with qwen3.5:cloud...
ollama launch claude --model qwen3.5:cloud
goto end

:exit
echo Exiting launcher...
goto end

:end
pause
