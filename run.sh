#!/bin/bash
# ──────────────────────────────────────────────────────────────────
# Self-Extending Agent UI — Startup Script
# Starts the FastAPI server at http://localhost:8000
# ──────────────────────────────────────────────────────────────────

set -e

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check Ollama is running

# Kill existing uvicorn on port 8000
echo "🧹  Cleaning up port 8000..."
lsof -i :8000 -t | xargs kill -9 2>/dev/null || true
sleep 2

# Set environment variables for Ollama
# Set your API keys in dev_assistant_app/.env instead of here
# export GEMINI_API_KEY="your-gemini-api-key-here"   # Set in .env
source dev_assistant_app/.env 2>/dev/null || true
export GEMINI_API_KEY="${GEMINI_API_KEY:-your-gemini-api-key-here}"

# Check if virtual environment exists
if [ -d ".venv" ]; then
  echo "🐍  Activating virtual environment..."
  source .venv/bin/activate
fi

# Install dependencies if needed
echo "📦  Installing/checking dependencies..."
pip3 install -q -r requirements.txt 2>/dev/null || pip install -q -r requirements.txt 2>/dev/null || true

# Find uvicorn
UVICORN_BIN=$(which uvicorn 2>/dev/null || echo "uvicorn")


echo ""
echo "🚀  Starting Self-Extending Agent UI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   UI:     http://localhost:8000"
echo "   Skills: Scanning from dev_assistant_app/skills/"
echo "   Model:  Gemini 2.5 Flash"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start the server
"$UVICORN_BIN" backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level warning
