@echo off
cls
cd /d "%~dp0"

:: This is the best for programming
ollama launch claude --model gemma4:31b-cloud
:: ollama launch claude --model ornith-agent:latest
