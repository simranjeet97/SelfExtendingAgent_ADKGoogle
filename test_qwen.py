import asyncio
import os
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT / "dev_assistant_app"))

from dotenv import load_dotenv
load_dotenv(ROOT / "dev_assistant_app" / ".env")

from google.adk.agents import LlmAgent
from google.genai import types as genai_types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

async def main():
    skill_file = ROOT / "dev_assistant_app" / "skills" / "git-workflow" / "SKILL.md"
    skill_content = skill_file.read_text(encoding="utf-8")
    
    user_message = "What is the branching strategy and when should I rebase instead of merge?"
    
    prompt = (
        f"Use the following reference to answer the user's question.\n"
        f"--- START SKILL REFERENCE ---\n{skill_content}\n--- END SKILL REFERENCE ---\n\n"
        f"User Question: {user_message}\n\n"
        f"Instruction: Follow the 'Output format' and 'Your role' from the reference. Be concise."
    )
    
    answer_agent = LlmAgent(
        model="ollama/qwen2.5:3b",
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0.3, max_output_tokens=8192
        ),
        name="test_qwen_agent",
        description="Answers questions based on skill context.",
        instruction=(
            "You are a professional assistant. Adopt the format and tone of the provided Skill Reference. "
            "Respond in clean Markdown. Minimize vertical whitespace."
        ),
        tools=[],
    )
    
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name="test_app", user_id="test_user")
    
    runner = Runner(
        agent=answer_agent,
        app_name="test_app",
        session_service=session_service,
    )
    
    content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
    
    print(f"--- Asking Qwen ---\nUser: {user_message}\n-------------------")
    
    try:
        async for event in runner.run_async(
            user_id="test_user",
            session_id=session.id,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)
    except Exception as e:
        print(f"\nError: {e}")
    print("\n--- Done ---")

if __name__ == "__main__":
    asyncio.run(main())
