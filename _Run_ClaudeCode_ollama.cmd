@echo off
cls
cd /d i:\Scripts\ML_Predictor2026_V2

:: Recommended models:
::   minimax-m2.5:cloud 
::   glm-5:cloud 
::   kimi-k2.5:cloud

:: This is the best for programming
:: ollama launch claude --model minimax-m2.5:cloud
ollama launch claude --model qwen2.5-coder:7b
:: ollama launch claude --model gemma4:e4b-it-q4_K_M


