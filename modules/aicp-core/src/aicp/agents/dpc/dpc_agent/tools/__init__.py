"""
DPC Agent Tools - Plugin architecture with sandbox constraints.

Tools are auto-discovered from modules that export get_tools().
All file operations are sandboxed to ~/.dpc/agent/.
"""

from .registry import ToolContext, ToolEntry, ToolRegistry

__all__ = ["ToolRegistry", "ToolContext", "ToolEntry"]
