"""
skill_writer.py

A tool that enables an ADK agent to write new Skills for itself.
The agent generates the SKILL.md content following the agentskills.io spec.
This tool handles the filesystem operations: validation, writing, and confirmation.
"""

import pathlib
import re

# The root skills directory, relative to this file's location
SKILLS_ROOT = pathlib.Path(__file__).parent.parent / "skills" / "generated"


def _is_valid_skill_name(name: str) -> bool:
    """
    Validates a skill name:
    - Max 64 characters
    - Lowercase letters, numbers, and hyphens only
    - Must not start or end with a hyphen
    - Must not contain consecutive hyphens
    """
    if not name or len(name) > 64:
        return False
    pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
    return bool(re.match(pattern, name)) and '--' not in name


def _sanitize_skill_name(name: str) -> str:
    """
    Attempt to auto-sanitize a skill name if it's close to valid.
    Lowercases, replaces spaces/underscores with hyphens, strips bad chars.
    """
    name = name.lower().strip()
    name = re.sub(r'[\s_]+', '-', name)          # spaces/underscores → hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)       # remove any other chars
    name = re.sub(r'-{2,}', '-', name)           # collapse consecutive hyphens
    name = name.strip('-')                         # remove leading/trailing hyphens
    return name[:64]                              # enforce max length


def write_new_skill(skill_name: str, skill_md_content: str) -> dict:
    """
    Writes a new Agent Skill to the skills/generated/ directory.

    ⚠️  IMPORTANT WORKFLOW — YOU MUST FOLLOW THIS ORDER:
    1. First call `web_search(query)` to gather real, up-to-date information
       about the topic. Use a specific query like:
       "Redis in-memory database key concepts tutorial best practices"
    2. Then call THIS tool with skill_md_content built from those search results.

    The skill_md_content MUST follow the agentskills.io specification:

    REQUIRED FRONTMATTER (YAML between --- delimiters):
      name:        lowercase-hyphenated skill name (matches directory name)
      description: 1-3 sentences describing what the skill does AND when to use it.
                   Include specific keywords for agent matching.
      metadata:
        version: "1.0"
        author: dev-assistant

    REQUIRED BODY (Markdown after frontmatter) — must include ALL of:
      ## 1. Executive Summary
        Deep overview of what the technology is and the problem it solves.
      ## 2. Technical Concepts & Architecture
        Breakdown of internals, terminology, and data models.
      ## 3. Implementation & Quick Reference
        Dense collection of CLI commands, API endpoints, or configuration in tables/lists.
      ## 4. Practical Examples
        At least 3 distinct code blocks in various contexts.
      ## 5. Performance & Best Practices
        Expert recommendations for production, optimization, and security.
      ## 6. Diagnosis & Troubleshooting
        Known failure modes and solutions.

    Example of a COMPLETE, RICH SKILL.md:

    ---
    name: redis-basics
    description: >
      Core Redis concepts, data structures, and commands. Use when the user
      asks about Redis, caching, pub/sub, in-memory storage, or key-value databases.
    metadata:
      version: "1.0"
      author: dev-assistant
    ---

    ## Overview
    Redis (Remote Dictionary Server) is an open-source, in-memory data structure
    store used as a database, cache, message broker, and streaming engine.
    ...

    ## Key Concepts
    - **Keys**: UTF-8 strings up to 512MB. Use colons as namespacing (user:1000)
    - **Strings**: binary-safe, max 512MB. Use SET/GET.
    ...

    ## Quick Reference
    | Command | Description |
    |---------|-------------|
    | SET key value | Set a string value |
    | GET key | Get value by key |
    ...

    Args:
        skill_name: The name for the new skill. Must be lowercase-with-hyphens.
                    Example: 'redis-basics', 'docker-workflow', 'sql-optimizer'
        skill_md_content: The complete SKILL.md content — frontmatter + rich body
                          filled with insights from the web_search results.

    Returns:
        dict with 'status' ('success' or 'error') and 'message' or 'error_message'.
    """

    # Auto-sanitize the skill name first
    original_name = skill_name
    skill_name = _sanitize_skill_name(skill_name)

    if not skill_name:
        return {
            "status": "error",
            "error_message": (
                f"Could not create a valid skill name from '{original_name}'. "
                "Please use a name like 'docker-workflow' or 'sql-basics'."
            )
        }

    if not _is_valid_skill_name(skill_name):
        return {
            "status": "error",
            "error_message": (
                f"Invalid skill name '{skill_name}'. Skill names must be "
                "lowercase letters, numbers, and hyphens only. "
                "Examples: 'docker-workflow', 'sql-optimizer', 'api-testing'"
            )
        }

    # Validate that content starts with YAML frontmatter
    content_stripped = skill_md_content.strip()
    if not content_stripped.startswith('---'):
        # Try to wrap bare content with frontmatter automatically
        skill_md_content = (
            f"---\nname: {skill_name}\ndescription: A skill about {skill_name.replace('-', ' ')}.\n---\n\n"
            + skill_md_content
        )

    # Ensure the name field in frontmatter references the (possibly sanitized) skill_name
    if f"name: {skill_name}" not in skill_md_content:
        # Try to fix it by replacing any name: line with the correct one
        skill_md_content = re.sub(
            r'^name:.*$',
            f'name: {skill_name}',
            skill_md_content,
            count=1,
            flags=re.MULTILINE
        )

    # Create the skill directory if needed
    skill_dir = SKILLS_ROOT / skill_name
    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {
            "status": "error",
            "error_message": f"Could not create skill directory: {e}"
        }

    skill_file = skill_dir / "SKILL.md"

    # If it already exists, overwrite (update) rather than error
    action = "updated" if skill_file.exists() else "written"

    try:
        skill_file.write_text(skill_md_content, encoding="utf-8")
    except OSError as e:
        return {
            "status": "error",
            "error_message": f"Could not write SKILL.md: {e}"
        }

    return {
        "status": "success",
        "message": (
            f"Skill '{skill_name}' {action} successfully at {skill_file}. "
            f"The skill is now active. Use the following instructions you just wrote "
            f"to answer the user's question now:\n\n{skill_md_content}"
        )
    }
