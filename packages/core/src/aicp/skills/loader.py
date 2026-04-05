from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SkillManifest:
    name: str
    description: str
    allowed_tools: list[str]
    when_to_use: str
    arguments: list[str]
    context: str
    effort: str

    @staticmethod
    def parse(content: str) -> "SkillManifest":
        parts = content.split("---")
        if len(parts) < 3:
            raise ValueError("Invalid skill format: missing YAML frontmatter")
        data = yaml.safe_load(parts[1])
        return SkillManifest(
            name=data.get("name", ""),
            description=data.get("description", ""),
            allowed_tools=data.get("allowed-tools", []),
            when_to_use=data.get("when_to_use", ""),
            arguments=data.get("arguments", []),
            context=data.get("context", "inline"),
            effort=data.get("effort", "medium"),
        )


class SkillLoader:
    def __init__(self, skills_dirs: list[Path]):
        self.skills_dirs = skills_dirs

    def discover_skills(self) -> list[SkillManifest]:
        skills = []
        for dir_path in self.skills_dirs:
            if dir_path.exists():
                for skill_file in dir_path.glob("*/SKILL.md"):
                    try:
                        content = skill_file.read_text()
                        skill = SkillManifest.parse(content)
                        skills.append(skill)
                    except Exception:
                        continue
        return skills

    def load_skill(self, name: str) -> Optional[tuple[SkillManifest, Path]]:
        for dir_path in self.skills_dirs:
            if not dir_path.exists():
                continue
            skill_path = dir_path / name / "SKILL.md"
            if skill_path.exists():
                try:
                    content = skill_path.read_text()
                    manifest = SkillManifest.parse(content)
                    return (manifest, skill_path)
                except Exception:
                    continue
            for entry in dir_path.iterdir():
                if entry.is_dir() and entry.name.lower() == name.lower():
                    skill_file = entry / "SKILL.md"
                    if skill_file.exists():
                        try:
                            content = skill_file.read_text()
                            manifest = SkillManifest.parse(content)
                            return (manifest, skill_file)
                        except Exception:
                            continue
        return None