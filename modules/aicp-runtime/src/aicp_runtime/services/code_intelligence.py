from __future__ import annotations

import ast
import asyncio
import os
import re
from pathlib import Path
from typing import Any

from aicp.code_intelligence.ast_indexer import ASTIndexer
from aicp.code_intelligence.code_context import CodeContext
from aicp.code_intelligence.models import CodeIntelligenceConfig, SymbolLocation
from aicp.code_intelligence.symbol_graph import SymbolGraph


class CodeIntelligenceService:
    def __init__(self, config: CodeIntelligenceConfig) -> None:
        self.config = config
        self.indexer = ASTIndexer()
        self.graph = SymbolGraph()
        self.lsp_bridge: Any = None
        self._initialized = False
        self._indexed_files: set[str] = set()

    async def initialize(self) -> None:
        if self._initialized:
            return

        if self.lsp_bridge:
            for lang, lsp_cfg in self.config.lsp_servers.items():
                await self.lsp_bridge.register_client(lang, lsp_cfg)
            await self.lsp_bridge.start_all()

        await self._index_workspace()
        self._initialized = True

    async def _index_workspace(self) -> None:
        if "python" not in self.config.languages:
            return

        workspace_root = Path(self.config.workspace_root)
        if not workspace_root.exists():
            return

        for root, _, files in os.walk(workspace_root):
            for file_name in files:
                if not file_name.endswith(".py"):
                    continue
                await self._ensure_indexed(str(Path(root) / file_name))

    async def _ensure_indexed(self, file_path: str) -> None:
        normalized = str(Path(file_path).resolve())
        if normalized in self._indexed_files:
            return

        nodes = await asyncio.to_thread(self.indexer.index_file, normalized)
        for node in nodes:
            self.graph.add_node(node)
        self._indexed_files.add(normalized)

    async def get_context(self, focus_uris: list[str], depth: int = 2) -> CodeContext:
        del depth
        if not self._initialized:
            await self.initialize()

        for uri in focus_uris:
            await self._ensure_indexed(uri)

        return CodeContext(graph=self.graph, token_budget=self.config.token_budget)

    async def find_definitions(
        self, uri: str, line: int, character: int
    ) -> list[SymbolLocation]:
        if not self._initialized:
            await self.initialize()

        await self._ensure_indexed(uri)

        if self.lsp_bridge:
            definitions = await self.lsp_bridge.go_to_definition(
                self._get_lang_from_uri(uri), uri, line, character
            )
            if definitions:
                return definitions

        symbol_name = self._symbol_at_position(uri, line, character)
        if not symbol_name:
            return []

        definitions: list[SymbolLocation] = []
        for node in self.graph.get_definitions(symbol_name):
            if node.location not in definitions:
                definitions.append(node.location)
        return definitions

    async def find_references(
        self, uri: str, line: int, character: int
    ) -> list[SymbolLocation]:
        if not self._initialized:
            await self.initialize()

        await self._ensure_indexed(uri)

        if self.lsp_bridge:
            references = await self.lsp_bridge.find_references(
                self._get_lang_from_uri(uri), uri, line, character
            )
            if references:
                return references

        symbol_name = self._symbol_at_position(uri, line, character)
        if not symbol_name:
            return []

        return await asyncio.to_thread(self._find_python_references, symbol_name)

    def _symbol_at_position(self, uri: str, line: int, character: int) -> str | None:
        path = Path(uri)
        if not path.exists():
            return None

        lines = path.read_text(encoding="utf-8").splitlines()
        if line < 1 or line > len(lines):
            return None

        current_line = lines[line - 1]
        if character < 0:
            return None

        for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", current_line):
            if match.start() <= character < match.end():
                return match.group(0)
        return None

    def _find_python_references(self, symbol_name: str) -> list[SymbolLocation]:
        references: list[SymbolLocation] = []
        for file_path in sorted(self._indexed_files):
            path = Path(file_path)
            if path.suffix != ".py" or not path.exists():
                continue

            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError, OSError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == symbol_name:
                    if isinstance(node.ctx, ast.Load):
                        references.append(
                            SymbolLocation(
                                uri=file_path,
                                line=node.lineno,
                                character=node.col_offset,
                                end_line=getattr(node, "end_lineno", node.lineno),
                                end_character=getattr(
                                    node,
                                    "end_col_offset",
                                    node.col_offset + len(symbol_name),
                                ),
                            )
                        )
        return references

    def _get_lang_from_uri(self, uri: str) -> str:
        if uri.endswith(".py"):
            return "python"
        if uri.endswith(".ts") or uri.endswith(".tsx"):
            return "typescript"
        return "unknown"

    async def shutdown(self) -> None:
        if self.lsp_bridge:
            await self.lsp_bridge.stop_all()
