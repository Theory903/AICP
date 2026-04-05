from __future__ import annotations

from pathlib import Path

import pytest

from aicp.code_intelligence.models import CodeIntelligenceConfig
from aicp_runtime.services.code_intelligence import CodeIntelligenceService


def _write_workspace_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "def helper():\n"
        "    return 1\n\n"
        "def use_helper():\n"
        "    return helper()\n",
        encoding="utf-8",
    )
    return file_path


@pytest.mark.asyncio
async def test_code_intelligence_service_builds_context_from_focus_files(tmp_path: Path) -> None:
    file_path = _write_workspace_file(tmp_path)
    service = CodeIntelligenceService(
        CodeIntelligenceConfig(workspace_root=str(tmp_path), languages=["python"])
    )

    context = await service.get_context([str(file_path)])

    symbols = context.find_symbol("helper")
    assert len(symbols) == 1
    assert symbols[0].location.uri == str(file_path)


@pytest.mark.asyncio
async def test_code_intelligence_service_finds_definitions_without_lsp(tmp_path: Path) -> None:
    file_path = _write_workspace_file(tmp_path)
    service = CodeIntelligenceService(
        CodeIntelligenceConfig(workspace_root=str(tmp_path), languages=["python"])
    )

    definitions = await service.find_definitions(str(file_path), line=5, character=11)

    assert len(definitions) == 1
    assert definitions[0].uri == str(file_path)
    assert definitions[0].line == 1


@pytest.mark.asyncio
async def test_code_intelligence_service_finds_references_without_lsp(tmp_path: Path) -> None:
    file_path = _write_workspace_file(tmp_path)
    service = CodeIntelligenceService(
        CodeIntelligenceConfig(workspace_root=str(tmp_path), languages=["python"])
    )

    references = await service.find_references(str(file_path), line=1, character=4)

    assert len(references) == 1
    assert references[0].uri == str(file_path)
    assert references[0].line == 5
