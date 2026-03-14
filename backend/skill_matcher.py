import json
import logging
from google.adk.agents import LlmAgent
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# Create a shared session service since the runner requires one
_matcher_session_service = InMemorySessionService()

logger = logging.getLogger("skill_matcher")

async def find_best_skill(user_message: str, available_skills: list) -> dict | None:
    """
    Uses the Qwen LLM to decide which of the available skills best answers the user's message.
    Returns the selected skill dict, or None if no skill is a good match.
    """
    if not available_skills:
        return None

    # Format the skills list for the prompt
    skills_text = ""
    for i, s in enumerate(available_skills):
        name = s.get('name', f'skill_{i}')
        desc = s.get('description', 'No description.')
        skills_text += f"- **{name}**: {desc}\n"

    prompt = (
        "Role: Semantic Intent Router\n"
        "Task: Match the [USER REQUEST] below to exactly ONE skill from the [MANIFEST].\n\n"
        "MANIFEST:\n"
        f"{skills_text}\n"
        "ROUTING RULES:\n"
        "1. MATCH ONLY if the skill's description or name explicitly covers the core technical intent of the request.\n"
        "2. DISAMBIGUATION: If multiple skills overlap, pick the most specific one. If none cover >80% of the intent, choose 'NONE'.\n"
        "3. LEARNING TRIGGER: If the request is about a new technical topic, tool, or library NOT in the manifest, output 'NONE'.\n"
        "4. OUTPUT FORMAT: Output ONLY the raw skill name (e.g., 'git-workflow') or the word 'NONE'. Do not use quotes, punctuation, or conversational filler.\n\n"
        f"[USER REQUEST]: \"{user_message}\"\n\n"
        "SELECTED SKILL:"
    )

    try:
        # Create an ADK minimalist LlmAgent for the matching call
        matcher_agent = LlmAgent(
            model="gemini-2.5-flash",
            generate_content_config=genai_types.GenerateContentConfig(
                temperature=0.0, max_output_tokens=50
            ),
            name="skill_matcher",
            instruction=(
                "You are a routing agent. Output ONLY the exact name of the best matching skill. "
                "Do not write anything else. If there is no good match, output exactly NONE."
            )
        )

        session = await _matcher_session_service.create_session(app_name="matcher", user_id="system")
        runner = Runner(agent=matcher_agent, app_name="matcher", session_service=_matcher_session_service)
        
        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=prompt)]
        )

        text = ""
        async for event in runner.run_async(user_id="system", session_id=session.id, new_message=content):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        text += part.text
        
        text = text.strip()
        
        # Clean up any markdown formatting the model might sneak in
        text = text.replace("`", "").replace("*", "").replace("\"", "").replace("'", "")
        text = text.strip()

        logger.info(f"LLM Matcher replied: '{text}' for query: '{user_message}'")

        if text.upper() == "NONE":
            return None

        # Compare output against available skill names
        for s in available_skills:
            if s.get('name', '').lower() == text.lower():
                return s
        
        logger.warning(f"LLM Matcher returned unknown skill: '{text}'")
        return None

    except Exception as e:
        logger.error(f"Error in LLM skill matcher: {e}", exc_info=True)
        # Fallback to static matching on error
        msg_lower = user_message.lower()
        for s in available_skills:
            name = s.get('name', '').lower()
            keywords = [kw for kw in name.split('-') if len(kw) > 3]
            if any(kw in msg_lower for kw in keywords) or name in msg_lower:
                return s
        return None
