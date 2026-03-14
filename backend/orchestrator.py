"""
orchestrator.py

Orchestrates the 2-Pass learning → answering flow.
All SSE events are emitted as properly-formed strings using the sse() helper.

KEY ARCHITECTURE: 
  Pass A — run_agent_stream(learn_prompt)  → writes the skill, collects skill content
  Pass B — run_answer_stream(user_message, skill_content)  → tool-free LLM answers directly
  
Pass B uses a tool-free agent to prevent the LLM from calling write_new_skill
again instead of actually answering the user's question.
"""

import asyncio
import os
import sys
import pathlib
import json
import logging
from typing import AsyncGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("orchestrator")

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.skills_scanner import scan_skills
from backend.agent_runner import run_agent_stream, run_answer_stream
from backend.skill_matcher import find_best_skill


# ── SSE helpers ────────────────────────────────────────────────────────────────
def sse(event: str, data: str) -> str:
    """Returns a properly-formed SSE event string, supporting multiline data."""
    output = f"event: {event}\n"
    for line in data.splitlines():
        output += f"data: {line}\n"
    return output + "\n"


def sse_log(step: str, status: str, message: str) -> str:
    return sse("log", json.dumps({"step": step, "status": status, "message": message}))


# ── Main orchestrator ──────────────────────────────────────────────────────────
async def orchestrate_chat(user_message: str) -> AsyncGenerator[str, None]:
    """
    Orchestrates the chat flow:
    1. Scan existing skills.
    2. Check if any skill matches the user message.
    3. 2-Pass Flow:
       Pass A: Learn (trigger skill creation via write_new_skill tool)
       Pass B: Answer (tool-free agent with embedded skill content)
    """

    # ── Step 1: Scan ─────────────────────────────────────────────────────────
    yield sse_log("Scan", "info", "Checking local skill manifest...")
    skills = scan_skills()
    logger.info(f"O-LOG: Scanned {len(skills)} skills.")

    # ── Step 2: Match ─────────────────────────────────────────────────────────
    yield sse_log("Match", "info", "Evaluating intent against loaded skills...")
    matched_skill = await find_best_skill(user_message, skills)

    if matched_skill:
        # ── Known skill: directly answer using Pass B ─────────────────────
        skill_name = matched_skill.get('name', 'unknown')
        skill_path = matched_skill.get('path')
        skill_content = ""
        
        if skill_path:
            skill_file = pathlib.Path(skill_path) / "SKILL.md"
            if skill_file.exists():
                skill_content = skill_file.read_text(encoding="utf-8")

        yield sse_log("Match", "success", f"Active skill found: {skill_name}")
        yield sse_log("Agent", "info", f"Generating answer using skill: {skill_name}...")
        yield sse("thinking", "answering")
        yield sse("message", "") # Start the message bubble
        
        # Use tool-free runner for matched skills
        async for chunk in run_answer_stream(user_message, skill_content=skill_content):
            yield chunk

    else:
        # ── Step 3: 2-Pass Learning Loop ──────────────────────────────────
        yield sse_log("Gap", "warning", "Knowledge gap detected. Triggering Learning Pass.")
        yield sse("learning", "start")
        yield sse("message", "*🧠 Knowledge gap detected. Researching and creating a new skill now...*\n\n**Drafting Skill:** ")

        # ─────────────────────────────────────────────────────────────────
        # Pass A: Learn — write the skill via write_new_skill tool
        # ─────────────────────────────────────────────────────────────────
        learn_prompt = (
            f"You are a skill-writing agent. You have exactly TWO allowed actions and NO others.\n\n"
            f"STEP 1 — SEARCH (do this first, right now):\n"
            f"Call: web_search(query='{user_message} official documentation tutorial best practices')\n\n"
            f"STEP 2 — WRITE SKILL (do this immediately after step 1 returns):\n"
            f"After you receive the web_search results, you MUST call write_new_skill immediately.\n"
            f"DO NOT output any text, explanation, or markdown between these two steps.\n"
            f"DO NOT summarize the search results in text — put them in the skill instead.\n"
            f"DO NOT ask the user anything.\n"
            f"Your ONLY output after receiving web_search results is a write_new_skill tool call.\n\n"
            f"The write_new_skill call MUST use:\n"
            f"  skill_name: A short lowercase-hyphenated name, e.g. 'redis-streams'\n"
            f"  skill_md_content: A COMPLETE SKILL.md with this EXACT structure:\n\n"
            f"---\n"
            f"name: <skill-name>\n"
            f"description: >\n"
            f"  Technical reference for {user_message}. Use when the user asks about this topic.\n"
            f"metadata:\n"
            f"  version: '1.0'\n"
            f"  author: dev-assistant\n"
            f"---\n\n"
            f"## 1. Executive Summary\n"
            f"<What it is, what problem it solves, when to use it — from search results>\n\n"
            f"## 2. Technical Concepts & Architecture\n"
            f"<Core internals, terminology, data models — from search results>\n\n"
            f"## 3. Implementation & Quick Reference\n"
            f"<CLI commands, API endpoints, config in tables — from search results>\n\n"
            f"## 4. Practical Examples\n"
            f"<At least 3 distinct, complete code blocks>\n\n"
            f"## 5. Performance & Best Practices\n"
            f"<Production tips, optimization, security — from search results>\n\n"
            f"## 6. Diagnosis & Troubleshooting\n"
            f"<Known errors and how to fix them>\n\n"
            f"Populate every section with REAL content from web_search results. "
            f"Do NOT leave any placeholder text like '<...>' in the output."
        )


        yield sse_log("Learn", "info", "Pass A: Generating skill outline...")

        skill_was_created = False
        skill_name_created = None
        skill_content_learned = ""  # ← will hold the full SKILL.md content

        # Use gemini-2.5-flash for the learning pass (Pass A)
        async for chunk in run_agent_stream(learn_prompt, fresh_session=True, model_name="gemini-2.5-flash"):
            if chunk.startswith("event: skill_created"):
                logger.info("O-LOG: Detected skill_created event in Pass A.")
                skill_was_created = True
                # Extract skill name AND skill content from the event payload
                for line in chunk.strip().split("\n"):
                    if line.startswith("data: "):
                        raw = line[6:].strip()
                        try:
                            payload = json.loads(raw)
                            skill_name_created = payload.get("name", "new-skill")
                            skill_content_learned = payload.get("content", "")
                        except Exception:
                            skill_name_created = raw if raw not in ("[DONE]", "reload") else "new-skill"
                yield chunk  # Forward to frontend (triggers sidebar refresh)

            elif chunk.startswith("event: log"):
                yield chunk  # Forward log events

            elif chunk.startswith("data: "):
                if skill_was_created:
                    continue  # Mute the AI's "Tool successfully executed" confirmation text

                # Forward the agent's drafting text to the frontend so the user sees progress
                txt = chunk[6:].strip()
                if txt and txt != "[DONE]":
                    if any(kw in txt.lower() for kw in ["cannot", "sorry", "unable", "don't know"]):
                        yield sse_log("Learn", "warning", f"Agent note: {txt[:120]}")
                # Stream the actual text to the user
                yield chunk

        # ─────────────────────────────────────────────────────────────────
        # Pass B: Answer — use tool-free agent with skill content embedded
        # ─────────────────────────────────────────────────────────────────
        if skill_was_created:
            display_name = skill_name_created or "new-skill"
            yield sse_log("Ready", "success", f"Skill '{display_name}' written. Generating answer...")
            yield sse("skill_integrated", json.dumps({"name": display_name}))
            yield sse("thinking", "answering")

            # Separator shown in chat
            yield sse("message", f"\n\n---\n✅ **New skill created: `{display_name}`** — Response:\n")

            # Pass B: answer-only, tool-free agent with skill content as context
            # This prevents the agent from calling write_new_skill AGAIN
            async for chunk in run_answer_stream(user_message, skill_content=skill_content_learned):
                yield chunk

        else:
            yield sse_log("Fail", "error", "Learning pass completed without skill activation. Generating general response.")
            yield sse("learning", "failed")
            yield sse("message", "\n\n---\n*⚠️ Could not create a new skill. Providing a general response:*\n\n")

            # Fallback: use answer-only agent (also tool-free) for a clean response
            async for chunk in run_answer_stream(user_message):
                yield chunk

    yield sse_log("Done", "success", "Flow complete.")
    yield sse("done", "[DONE]")
