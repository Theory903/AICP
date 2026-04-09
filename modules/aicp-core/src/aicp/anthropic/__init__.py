"""
AICP Anthropic Integration Module
Based on: https://github.com/anthropics/knowledge-work-plugins
"""

import json
from pathlib import Path
from typing import Optional

DEFAULT_STUDY_PATH = Path(__file__).parent.parent.parent.parent.parent / "ref" / "study"


class Skill:
    def __init__(
        self,
        name: str,
        description: str,
        content: str,
        path: Path | None = None,
    ):
        self.name = name
        self.description = description
        self.content = content
        self.path = path

    @classmethod
    def from_file(cls, path: Path) -> "Skill":
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                body = parts[2].strip()

                name = ""
                description = ""
                for line in frontmatter.split("\n"):
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()

                return cls(name=name, description=description, content=body, path=path)

        return cls(name=path.stem, description="", content=content, path=path)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "path": str(self.path) if self.path else None,
        }


class Plugin:
    def __init__(
        self,
        name: str,
        description: str,
        skills: list[Skill],
        connectors: dict[str, list[str]],
        path: Path | None = None,
    ):
        self.name = name
        self.description = description
        self.skills = skills
        self.connectors = connectors
        self.path = path

    @classmethod
    def from_directory(cls, path: Path) -> "Plugin":
        plugin_json = path / ".claude-plugin" / "plugin.json"
        name = path.name
        description = ""

        if plugin_json.exists():
            with open(plugin_json, encoding="utf-8") as f:
                data = json.load(f)
                description = data.get("description", "")

        skills = []
        skills_dir = path / "skills"
        if skills_dir.exists():
            for skill_file in skills_dir.rglob("SKILL.md"):
                skills.append(Skill.from_file(skill_file))

        connectors = {}
        mcp_json = path / ".mcp.json"
        if mcp_json.exists():
            with open(mcp_json, encoding="utf-8") as f:
                data = json.load(f)
                connectors = {k: [v.get("command", ""), v.get("args", [])]
                             for k, v in data.get("mcpServers", {}).items()}

        return cls(
            name=name,
            description=description,
            skills=skills,
            connectors=connectors,
            path=path,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "skills": [s.to_dict() for s in self.skills],
            "connectors": self.connectors,
            "path": str(self.path) if self.path else None,
        }


class SkillManager:
    def __init__(self, study_path: Path | None = None):
        self.study_path = study_path or DEFAULT_STUDY_PATH
        self.skills_path = self.study_path / "skills"
        self._skills_cache: dict[str, Skill] = {}

    def load_all_skills(self) -> dict[str, Skill]:
        if not self.skills_path.exists():
            return {}

        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skill = Skill.from_file(skill_file)
                self._skills_cache[skill.name] = skill

        return self._skills_cache

    def get_skill(self, name: str) -> Skill | None:
        if name in self._skills_cache:
            return self._skills_cache[name]

        skill_file = self.skills_path / name / "SKILL.md"
        if skill_file.exists():
            skill = Skill.from_file(skill_file)
            self._skills_cache[name] = skill
            return skill

        return None

    def list_skills(self) -> list[str]:
        if not self._skills_cache:
            self.load_all_skills()
        return list(self._skills_cache.keys())

    def get_skill_content(self, name: str) -> str | None:
        skill = self.get_skill(name)
        return skill.content if skill else None


class PluginManager:
    def __init__(self, study_path: Path | None = None):
        self.study_path = study_path or DEFAULT_STUDY_PATH
        self.plugins_path = self.study_path / "knowledge-work-plugins"
        self._plugins_cache: dict[str, Plugin] = {}

    def load_all_plugins(self) -> dict[str, Plugin]:
        if not self.plugins_path.exists():
            return {}

        for plugin_dir in self.plugins_path.iterdir():
            if not plugin_dir.is_dir():
                continue
            if plugin_dir.name.startswith("."):
                continue

            try:
                plugin = Plugin.from_directory(plugin_dir)
                self._plugins_cache[plugin.name] = plugin
            except Exception:
                continue

        return self._plugins_cache

    def get_plugin(self, name: str) -> Plugin | None:
        if name in self._plugins_cache:
            return self._plugins_cache[name]

        plugin_dir = self.plugins_path / name
        if plugin_dir.exists():
            try:
                plugin = Plugin.from_directory(plugin_dir)
                self._plugins_cache[name] = plugin
                return plugin
            except Exception:
                pass

        return None

    def list_plugins(self) -> list[str]:
        if not self._plugins_cache:
            self.load_all_plugins()
        return list(self._plugins_cache.keys())


def get_available_tools() -> dict[str, list[str]]:
    manager = PluginManager()
    manager.load_all_plugins()

    tools = {}
    for name, plugin in manager._plugins_cache.items():
        tools[name] = list(plugin.connectors.keys())

    return tools


__all__ = [
    "Skill",
    "Plugin",
    "SkillManager",
    "PluginManager",
    "get_available_tools",
    "DEFAULT_STUDY_PATH",
]
