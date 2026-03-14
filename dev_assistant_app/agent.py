import pathlib
from google.adk.agents import LlmAgent
from google.genai import types as genai_types
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset
try:
    from tools.skill_writer import write_new_skill
    from tools.web_search_tool import web_search
except ImportError:
    from .tools.skill_writer import write_new_skill
    from .tools.web_search_tool import web_search

__all__ = ['get_agent']


# ── Helper: dynamically discover all skills in a folder ──────────────────────
def load_all_skills_from_dir(skills_dir: pathlib.Path) -> list:
    """
    Scans a directory for sub-folders that contain a SKILL.md file
    and loads each one as an ADK Skill.
    """
    skills = []
    if not skills_dir.exists():
        return skills
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            try:
                skills.append(load_skill_from_dir(skill_dir))
                print(f"  Loaded skill: {skill_dir.name}")
            except Exception as e:
                print(f"  Warning: could not load skill {skill_dir.name}: {e}")
    return skills


def get_agent():
    """
    Creates a fresh ADK Agent instance with the latest skills discovered on disk.
    """
    all_skills = []
    try:
        SKILLS_ROOT = pathlib.Path(__file__).parent / "skills"

        # Load specific hand-crafted skills
        for name in ["code-review", "git-workflow"]:
            skill_path = SKILLS_ROOT / name
            if (skill_path / "SKILL.md").exists():
                all_skills.append(load_skill_from_dir(skill_path))

        # Load any generated skills
        all_skills.extend(load_all_skills_from_dir(SKILLS_ROOT / "generated"))
    except Exception as e:
        print(f"Warning: Error loading skills: {e}")

    # Build the dynamic toolset
    dev_toolset = skill_toolset.SkillToolset(skills=all_skills)

    skill_names = ", ".join([s.name for s in all_skills]) if all_skills else "none"

    return LlmAgent(
        model="gemini-2.5-flash",
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0, max_output_tokens=8192
        ),
        name="dev_assistant",
        description="A software engineering assistant with extensible skills.",
        instruction=(
            f"You are a software engineering assistant with self-extending capabilities.\n\n"
            f"CURRENTLY LOADED SKILLS: {skill_names}\n\n"
            "=== MANDATORY SKILL-CREATION PROTOCOL ===\n"
            "If the user's question is about a topic NOT already in LOADED SKILLS, "
            "you are STRICTLY PROHIBITED from answering directly. You MUST execute "
            "ALL of the following steps IN ORDER before writing a single word of your answer:\n\n"
            "  STEP 1 → Call `web_search` with a focused query about the topic "
            "(e.g. 'Redis data structures tutorial best practices 2024').\n"
            "  STEP 2 → Call `write_new_skill` using the search results to build a "
            "complete SKILL.md (frontmatter + all 6 required sections).\n"
            "  STEP 3 → Only AFTER `write_new_skill` returns status='success', "
            "answer the user's question using the content you just wrote.\n\n"
            "NEVER skip STEP 1 or STEP 2. "
            "NEVER say 'I cannot create a skill' or give a general response without first attempting both tool calls. "
            "If `web_search` returns an error, still call `write_new_skill` with your "
            "own expert knowledge as the content.\n\n"
            "=== SKILL QUALITY REQUIREMENTS ===\n"
            "The skill_md_content passed to `write_new_skill` MUST:\n"
            "  • Start with valid YAML frontmatter (--- ... ---) containing name, description, and metadata.\n"
            "  • Include ALL 6 sections: Executive Summary, Technical Concepts & Architecture, "
            "Implementation & Quick Reference, Practical Examples (≥3 code blocks), "
            "Performance & Best Practices, Diagnosis & Troubleshooting.\n"
            "  • Be rich, dense, and production-ready — not a skeleton or placeholder.\n\n"
            "Always follow the latest technical standards and provide complete, professional-grade code examples."
        ),
        tools=[
            dev_toolset,
            web_search,
            write_new_skill,
        ],
    )
