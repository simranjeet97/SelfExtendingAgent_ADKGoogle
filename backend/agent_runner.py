"""
agent_runner.py

Wraps the ADK agent for use within FastAPI.
Provides async generators that yield SSE-formatted text chunks.

Two modes:
  run_agent_stream()   — Full agent with write_new_skill (for the learn pass)
  run_answer_stream()  — A direct LLM call with NO tools (for the answer pass)
                         to prevent the LLM from calling write_new_skill AGAIN
                         instead of just answering the question.
"""

import asyncio
import sys
import os
import pathlib
import json
import re
import logging
from typing import AsyncGenerator

logger = logging.getLogger("agent_runner")

# Ensure dev_assistant_app is importable
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT / "dev_assistant_app"))

# Load env vars
from dotenv import load_dotenv
load_dotenv(ROOT / "dev_assistant_app" / ".env")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent
from google.genai import types as genai_types

# Import the agent generator
from dev_assistant_app.agent import get_agent

APP_NAME = "dev_assistant_ui"
USER_ID  = "ui_user"

# Shared session service (in-memory)
session_service = InMemorySessionService()
_session_id: str | None = None


async def get_or_create_session() -> str:
    global _session_id
    if _session_id is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
        )
        _session_id = session.id
    return _session_id


# ── Pass A: Full agent with tools ─────────────────────────────────────────────
async def run_agent_stream(
    user_message: str, 
    fresh_session: bool = False,
    model_name: str | None = None
) -> AsyncGenerator[str, None]:
    """
    Sends user_message to a fresh ADK agent instance and yields SSE-formatted chunks.
    Re-instantiating the runner ensures the agent has the latest skills from disk.
    If fresh_session is True, a brand new session is created for this request.
    """
    if fresh_session:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
        )
        session_id = session.id
    else:
        session_id = await get_or_create_session()

    # Use a dedicated, minimal skill-writer agent for the learn pass.
    # This avoids conflicting instructions from the full dev_assistant agent.
    from dev_assistant_app.tools.skill_writer import write_new_skill
    from dev_assistant_app.tools.web_search_tool import web_search

    agent = LlmAgent(
        model=model_name or "gemini-2.5-flash",
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0, max_output_tokens=8192
        ),
        name="skill_writer_agent",
        description="A skill-writing agent that creates new skills from web research.",
        instruction=(
            "You are a skill-writing agent with exactly two allowed actions:\n"
            "1. Call web_search to get information about a topic.\n"
            "2. Immediately after receiving web_search results, call write_new_skill.\n"
            "You MUST NOT output any text between these two tool calls.\n"
            "You MUST NOT answer the user directly.\n"
            "Your ONLY job is: web_search → write_new_skill. Nothing else."
        ),
        tools=[web_search, write_new_skill],
    )

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=content,
        ):
            # ── Handle Output Parts ────────────────────────────────────────
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # 1. Handle Text
                    if hasattr(part, "text") and part.text:
                        txt = part.text.strip()
                        if not txt or "non-text parts" in txt.lower():
                            continue
                        # Yield using SSE multiline format
                        for line in part.text.splitlines():
                            yield f"data: {line}\n"
                        yield "\n"

                    # 2. Handle Tool Calls (Capture before execution)
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        logger.info(f"RUNNER: Detected function_call: {fc.name}")
                        
                        if fc.name == "write_new_skill":
                            args = fc.args or {}
                            skill_name = args.get("skill_name")
                            skill_md = args.get("skill_md_content")
                            
                            if skill_name and skill_md:
                                logger.info(f"RUNNER: Capturing skill '{skill_name}' from arguments.")
                                payload = json.dumps({
                                    "name": skill_name,
                                    "status": "success",
                                    "content": skill_md,
                                })
                                yield f"event: skill_created\ndata: {payload}\n\n"

            # ── Log Tool Responses ──────────────────────────────────────────
            try:
                for fr in (event.get_function_responses() or []):
                    logger.info(f"RUNNER: Tool result received for '{getattr(fr, 'name', '?')}'")
            except Exception:
                pass

    except Exception as e:
        logger.error(f"RUNNER: Exception during agent run: {e}", exc_info=True)
        payload = json.dumps({"step": "Agent", "status": "error", "message": f"Agent error: {str(e)}"})
        yield f"event: log\ndata: {payload}\n\n"

    yield "event: done\ndata: [DONE]\n\n"


# ── Pass B: Answer-only agent (NO tools) ──────────────────────────────────────
async def run_answer_stream(
    user_message: str,
    skill_content: str = "",
    session_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Answers the user's question directly using a tool-free LLM agent.
    Includes the skill content in context for immediate leverage.
    """
    if session_id is None:
        session_id = await get_or_create_session()

    if skill_content:
        prompt = (
            f"Use the following reference to answer the user's question.\n"
            f"--- START SKILL REFERENCE ---\n{skill_content}\n--- END SKILL REFERENCE ---\n\n"
            f"User Question: {user_message}\n\n"
            f"Instruction: Follow the 'Output format' and 'Your role' from the reference. Be concise."
        )
    else:
        prompt = f"User Question: {user_message}\n\nInstruction: Answer in Markdown."

    answer_agent = LlmAgent(
        model="gemini-2.5-flash",
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0.1, max_output_tokens=8192
        ),
        name="dev_assistant_answer",
        description="Answers questions based on skill context.",
        instruction=(
            "You are a professional assistant. Adopt the format and tone of the provided Skill Reference. "
            "Respond in clean Markdown. Minimize vertical whitespace."
        ),
        tools=[], 
    )

    runner = Runner(
        agent=answer_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        for line in part.text.splitlines():
                            yield f"data: {line}\n"
                        yield "\n"

    except Exception as e:
        logger.error(f"RUNNER(answer): Exception: {e}", exc_info=True)
        payload = json.dumps({"step": "Answer", "status": "error", "message": f"Answer error: {str(e)}"})
        yield f"event: log\ndata: {payload}\n\n"

    yield "event: done\ndata: [DONE]\n\n"
