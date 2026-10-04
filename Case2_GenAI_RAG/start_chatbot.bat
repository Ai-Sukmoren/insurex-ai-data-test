@echo off
REM Starts the InsureX web chatbot (Ollama must be running).
cd /d "%~dp0"
if not exist "data\faiss_index\index.faiss" .venv\Scripts\python.exe main.py ingest
if not exist "frontend\dist\index.html" (
  where npm >nul 2>nul && (pushd frontend & call npm install & call npm run build & popd)
)
start "" http://127.0.0.1:8000
.venv\Scripts\python.exe main.py serve
