from fastapi import APIRouter
from typing import List
from aicp_runtime.services.code_intelligence import CodeIntelligenceService


def build_code_intelligence_router(service: CodeIntelligenceService) -> APIRouter:
    router = APIRouter(prefix="/v1/code-intelligence", tags=["Code Intelligence"])

    @router.get("/context")
    async def get_code_context(uris: List[str], depth: int = 2):
        return await service.get_context(uris, depth)

    @router.get("/definitions")
    async def get_definitions(uri: str, line: int, character: int):
        return await service.find_definitions(uri, line, character)

    @router.get("/references")
    async def get_references(uri: str, line: int, character: int):
        return await service.find_references(uri, line, character)

    return router
