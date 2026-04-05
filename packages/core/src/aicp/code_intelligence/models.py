from enum import Enum
from uuid import uuid4
from typing import Any, List, Optional

from pydantic import BaseModel, Field

class SymbolKind(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    INTERFACE = "interface"
    CONSTANT = "constant"

class SymbolLocation(BaseModel):
    uri: str
    line: int
    character: int
    end_line: Optional[int] = None
    end_character: Optional[int] = None

class ASTNode(BaseModel):
    id: str = Field(default_factory=lambda: f"node_{uuid4().hex}") # Real ID set in indexer
    kind: SymbolKind
    name: str
    location: SymbolLocation
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)

class SymbolRelation(BaseModel):
    source_id: str
    target_id: str
    relation_type: str # "calls", "inherits", "references", "contains"


class LspServerConfig(BaseModel):
    command: list[str]
    language_id: str
    root_uri: str = ""


class CallEdge(BaseModel):
    caller_id: str
    callee_id: str
    call_site: SymbolLocation
    call_type: str = "direct"


class CodeIntelligenceConfig(BaseModel):
    enabled: bool = True
    index_path: str = ".aicp/index"
    max_file_size: int = 1_000_000
    workspace_root: str = "."
    token_budget: int = 8_000
    languages: list[str] = Field(default_factory=lambda: ["python"])
    lsp_servers: dict[str, LspServerConfig] = Field(default_factory=dict)


def __getattr__(name: str):
    if name == "CodeContext":
        from .code_context import CodeContext

        return CodeContext
    raise AttributeError(name)
