from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class WikiConfig:
    wiki_path: Path
    raw_sources_path: Path
    schema_path: Path | None = None
    index_file: str = "index.md"
    log_file: str = "log.md"

    def __post_init__(self) -> None:
        self.wiki_path = Path(self.wiki_path)
        self.raw_sources_path = Path(self.raw_sources_path)
        self.wiki_path.mkdir(parents=True, exist_ok=True)
        self.raw_sources_path.mkdir(parents=True, exist_ok=True)


@dataclass
class WikiEntry:
    title: str
    content: str
    category: str
    sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class WikiManager:
    def __init__(self, config: WikiConfig) -> None:
        self.config = config

    def _get_entry_path(self, title: str) -> Path:
        safe_title = re.sub(r"[^\w\s-]", "", title).replace(" ", "-").lower()
        return self.config.wiki_path / f"{safe_title}.md"

    def _read_entry(self, title: str) -> WikiEntry | None:
        path = self._get_entry_path(title)
        if not path.exists():
            return None

        content = path.read_text()
        frontmatter = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                body = parts[2].strip()
                for line in fm_text.strip().split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        frontmatter[key.strip()] = val.strip()

        return WikiEntry(
            title=title,
            content=body,
            category=frontmatter.get("category", "general"),
            sources=json.loads(frontmatter.get("sources", "[]")),
            tags=json.loads(frontmatter.get("tags", "[]")),
            links=json.loads(frontmatter.get("links", "[]")),
            created_at=frontmatter.get("created_at", ""),
            updated_at=frontmatter.get("updated_at", ""),
        )

    def _write_entry(self, entry: WikiEntry) -> None:
        path = self._get_entry_path(entry.title)
        links = json.dumps(entry.links, indent=2)
        sources = json.dumps(entry.sources, indent=2)
        tags = json.dumps(entry.tags, indent=2)

        content = f"""---
title: {entry.title}
category: {entry.category}
sources: {sources}
tags: {tags}
links: {links}
created_at: {entry.created_at}
updated_at: {entry.updated_at}
---

{entry.content}
"""
        path.write_text(content)

    def _extract_links(self, content: str) -> list[str]:
        wiki_links = re.findall(r"\[\[([^\]]+)\]\]", content)
        http_links = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", content)
        return wiki_links + [l[1] for l in http_links]

    def _extract_tags(self, content: str) -> list[str]:
        tags = re.findall(r"#(\w+)", content)
        return list(set(tags))

    async def ingest(
        self,
        source_path: str | Path,
        summary: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")

        title = source.stem.replace("-", " ").replace("_", " ").title()

        entry = self._read_entry(title)
        now = datetime.now().isoformat()

        if entry:
            entry.content += f"\n\n## Update ({datetime.now().strftime('%Y-%m-%d')})\n{summary}"
            entry.updated_at = now
            entry.sources.append(str(source))
        else:
            entry = WikiEntry(
                title=title,
                content=summary or f"Content from {source.name}",
                category=category,
                sources=[str(source)],
            )

        entry.links = self._extract_links(entry.content)
        entry.tags = self._extract_tags(entry.content)

        self._write_entry(entry)

        await self._update_index()
        await self._append_log("ingest", f"Processed {source.name}", [title])

        return {
            "source": str(source),
            "pages_created": [title] if not self._read_entry(title) or entry.created_at == now else [],
            "pages_updated": [title] if entry.updated_at == now else [],
            "crosslinks_added": entry.links,
        }

    async def query(self, question: str) -> dict[str, Any]:
        keywords = question.lower().split()
        matches: list[WikiEntry] = []

        for md_file in self.config.wiki_path.glob("*.md"):
            entry = self._read_entry(md_file.stem)
            if entry:
                score = sum(1 for kw in keywords if kw in entry.title.lower() or kw in entry.content.lower())
                if score > 0:
                    matches.append(entry)

        matches.sort(key=lambda e: sum(1 for kw in keywords if kw in e.title.lower()), reverse=True)

        answer = f"Found {len(matches)} relevant pages:\n\n"
        for entry in matches[:5]:
            answer += f"- [[{entry.title}]] ({entry.category})\n"

        return {
            "question": question,
            "answer": answer,
            "sources": [e.title for e in matches[:5]],
        }

    async def lint(self) -> dict[str, Any]:
        orphans: list[str] = []
        broken_links: list[str] = []
        all_entries: dict[str, WikiEntry] = {}

        for md_file in self.config.wiki_path.glob("*.md"):
            entry = self._read_entry(md_file.stem)
            if entry:
                all_entries[entry.title] = entry

        for title, entry in all_entries.items():
            has_incoming = any(title in e.links for e in all_entries.values() if e.title != title)
            if not has_incoming:
                orphans.append(title)

            for link in entry.links:
                if link.startswith("http"):
                    continue
                if not any(link.lower() == e.title.lower() for e in all_entries.values()):
                    broken_links.append(f"{title} -> {link}")

        return {
            "orphans": orphans[:10],
            "broken_links": broken_links[:10],
            "contradictions": [],
            "stale_content": [],
        }

    async def _update_index(self) -> None:
        entries = []
        for md_file in self.config.wiki_path.glob("*.md"):
            entry = self._read_entry(md_file.stem)
            if entry:
                entries.append(entry)

        categories: dict[str, list[WikiEntry]] = {}
        for entry in entries:
            if entry.category not in categories:
                categories[entry.category] = []
            categories[entry.category].append(entry)

        lines = ["# Wiki Index\n"]
        lines.append(f"Total entries: {len(entries)}\n")

        for cat, cat_entries in sorted(categories.items()):
            lines.append(f"\n## {cat.title()}\n")
            for entry in sorted(cat_entries, key=lambda e: e.title):
                lines.append(f"- [[{entry.title}]] ({len(entry.sources)} sources)")

        (self.config.wiki_path / self.config.index_file).write_text("\n".join(lines))

    async def _append_log(self, action: str, description: str, affected: list[str]) -> None:
        log_path = self.config.wiki_path / self.config.log_file
        now = datetime.now().strftime("%Y-%m-%d")
        entry = f"\n## [{now}] {action} | {description}\n"
        entry += f"- Affected: {', '.join(affected)}\n"

        if log_path.exists():
            log_path.write_text(log_path.read_text() + entry)
        else:
            log_path.write_text(f"# Wiki Log\n{entry}")

    async def create_entity_page(
        self,
        name: str,
        entity_type: str,
        content: str,
        related: list[str] | None = None,
    ) -> str:
        entry = WikiEntry(
            title=name,
            content=content,
            category=entity_type,
            links=related or [],
        )
        self._write_entry(entry)
        return name
