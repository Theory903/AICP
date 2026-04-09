from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BookMetadata:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    language: str = ""
    subjects: list[str] = field(default_factory=list)
    identifier: str = ""
    publisher: str | None = None
    description: str | None = None


@dataclass
class ChapterContent:
    id: str
    href: str
    title: str
    content: str
    text: str
    order: int


@dataclass
class TOCEntry:
    title: str
    href: str
    file_href: str
    anchor: str | None
    children: list[TOCEntry] = field(default_factory=list)


@dataclass
class ParsedBook:
    metadata: BookMetadata
    spine: list[ChapterContent] = field(default_factory=list)
    toc: list[TOCEntry] = field(default_factory=list)
    images: dict[str, str] = field(default_factory=dict)


async def parse_epub(epub_path: str | Path) -> dict[str, Any]:
    path = Path(epub_path)
    return {
        "path": str(path),
        "exists": path.exists(),
        "metadata": None,
        "chapters": [],
        "images": {},
    }


async def process_epub(epub_path: str | Path) -> ParsedBook:
    path = Path(epub_path)
    if not path.exists():
        raise FileNotFoundError(f"EPUB not found: {path}")

    try:
        import ebooklib
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("ebooklib and beautifulsoup4 required: pip install ebooklib beautifulsoup4")

    book = ebooklib.epub.read_epub(str(path))

    metadata = BookMetadata(
        title=book.get_metadata("DC", "title") or "",
        authors=book.get_metadata("DC", "creator") or [],
        language=book.get_metadata("DC", "language") or "",
        subjects=book.get_metadata("DC", "subject") or [],
        identifier=book.get_metadata("DC", "identifier") or "",
        publisher=book.get_metadata("DC", "publisher"),
        description=book.get_metadata("DC", "description"),
    )

    spine_items = []
    for i, item in enumerate(book.spine):
        doc = book.get_item_with_id(item[0])
        if doc:
            soup = BeautifulSoup(doc.get_content(), "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            title = soup.title.string if soup.title else f"Chapter {i + 1}"

            spine_items.append(ChapterContent(
                id=item[0],
                href=doc.href,
                title=title or f"Chapter {i + 1}",
                content=str(soup),
                text=text,
                order=i,
            ))

    toc_items = []
    if book.toc:
        def parse_toc(items: list, base_href: str = "") -> list[TOCEntry]:
            entries = []
            for item in items:
                if hasattr(item, "href"):
                    href = item.href
                    anchor = None
                    if "#" in href:
                        href, anchor = href.split("#", 1)
                    entries.append(TOCEntry(
                        title=item.name,
                        href=item.href,
                        file_href=href,
                        anchor=anchor,
                        children=parse_toc(item.children, href) if hasattr(item, "children") else [],
                    ))
            return entries
        toc_items = parse_toc(book.toc)

    image_map = {}
    for item in book.items:
        if item.get_type() == 9:
            img_name = Path(item.href).name
            image_map[item.href] = img_name

    return ParsedBook(
        metadata=metadata,
        spine=spine_items,
        toc=toc_items,
        images=image_map,
    )


async def get_chapter_text(epub_path: str | Path, chapter_index: int) -> str:
    book = await process_epub(epub_path)
    if 0 <= chapter_index < len(book.spine):
        return book.spine[chapter_index].text
    return ""
