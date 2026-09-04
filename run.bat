@echo off
cd /d "%~dp0"
echo Starting PhenoGlobe on http://localhost:8000
start "" http://localhost:8000
rem Optional: set ANTHROPIC_API_KEY=... (or GEMINI_API_KEY=...) before running for the vision-LLM population refiner
.venv\Scripts\python -m uvicorn main:app --port 8000
