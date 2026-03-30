@echo off
cls
cd /d i:\Scripts\ML_Predictor2026_V2

:: Recommended models:
::   minimax-m2.5:cloud 
::   glm-5:cloud 
::   kimi-k2.5:cloud

:: This is the best for programming
:: ollama launch claude --model minimax-m2.5:cloud
ollama launch claude --model qwen3.5:cloud
