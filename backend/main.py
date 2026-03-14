"""
main.py — FastAPI server for the Self-Extending Agent UI

Endpoints:
  GET  /              → serves frontend/index.html
  GET  /static/*      → serves frontend static files
  GET  /api/health    → health check
  GET  /api/skills    → list all loaded skills
  POST /api/chat      → streams agent response via SSE
"""

import asyncio
import os
import sys
import pathlib
import warnings
from typing import AsyncGenerator

# Silencing Pydantic and ADK experimental warnings for a cleaner console
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*EXPERIMENTAL.*feature SKILL_TOOLSET.*", category=UserWarning)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is importable
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT / "dev_assistant_app"))

from dotenv import load_dotenv
load_dotenv(ROOT / "dev_assistant_app" / ".env")

from backend.skills_scanner import scan_skills

app = FastAPI(title="Self-Extending Agent UI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = ROOT / "frontend"

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main UI."""
    html_file = FRONTEND_DIR / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": "gemini-2.5-flash"}


@app.get("/api/skills")
async def list_skills():
    """Return all skills (builtin + generated) with metadata."""
    skills = scan_skills()
    return JSONResponse(content={"skills": skills})


@app.post("/api/chat")
async def chat_stream(request: Request):
    """
    Accepts JSON body: {"message": "..."}
    Returns Server-Sent Events stream of agent response.
    """
    body = await request.json()
    user_message = body.get("message", "").strip()
    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    from backend.orchestrator import orchestrate_chat
    return StreamingResponse(
        orchestrate_chat(user_message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
