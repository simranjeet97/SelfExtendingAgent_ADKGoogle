"""
skills_scanner.py

Scans the skills/ directory and returns structured metadata for each skill.
Used by the /api/skills endpoint.
"""

import pathlib
import re
from typing import Optional
import datetime


SKILLS_ROOT = pathlib.Path(__file__).parent.parent / "dev_assistant_app" / "skills"


def _parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter fields from a SKILL.md file."""
    meta = {"name": "", "description": ""}
    if not content.strip().startswith("---"):
        return meta

    # Find closing ---
    end = content.find("---", 3)
    if end == -1:
        return meta

    front = content[3:end].strip()

    # Extract name
    name_match = re.search(r"^name:\s*(.+)$", front, re.MULTILINE)
    if name_match:
        meta["name"] = name_match.group(1).strip().strip('"\'')

    # Extract description (handles multi-line "> " yaml block)
    desc_match = re.search(r"^description:\s*>?\s*\n?((?:[ \t]+.+\n?)+)", front, re.MULTILINE)
    if desc_match:
        raw = desc_match.group(1)
        meta["description"] = " ".join(line.strip() for line in raw.strip().splitlines())
    else:
        # Inline description
        inline_match = re.search(r"^description:\s*(.+)$", front, re.MULTILINE)
        if inline_match:
            meta["description"] = inline_match.group(1).strip().strip('"\'')

    # Extract version
    ver_match = re.search(r"version:\s*[\"']?([^\"'\n]+)[\"']?", front)
    if ver_match:
        meta["version"] = ver_match.group(1).strip()

    return meta


def scan_skills() -> list[dict]:
    """
    Scans skills/ directory and returns a list of skill dicts with:
    - name, description, type (builtin | generated), path, created_at
    """
    results = []

    builtin_dirs = [
        (SKILLS_ROOT / "code-review", "builtin"),
        (SKILLS_ROOT / "git-workflow", "builtin"),
    ]
    for skill_dir, skill_type in builtin_dirs:
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8")
            meta = _parse_frontmatter(content)
            stat = skill_file.stat()
            results.append({
                "name": meta.get("name") or skill_dir.name,
                "description": meta.get("description", ""),
                "type": skill_type,
                "path": str(skill_dir),
                "created_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "version": meta.get("version", "1.0"),
            })

    # Scan generated skills
    generated_root = SKILLS_ROOT / "generated"
    if generated_root.exists():
        for skill_dir in sorted(generated_root.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_dir.is_dir() and skill_file.exists():
                content = skill_file.read_text(encoding="utf-8")
                meta = _parse_frontmatter(content)
                stat = skill_file.stat()
                results.append({
                    "name": meta.get("name") or skill_dir.name,
                    "description": meta.get("description", ""),
                    "type": "generated",
                    "path": str(skill_dir),
                    "created_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "version": meta.get("version", "1.0"),
                })

    return results
