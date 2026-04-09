import os
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class OperationType(str, Enum):
    CODE_EXECUTION = "code_execution"
    REGEX = "regex"
    EVAL = "eval"
    DYNAMIC_IMPORT = "dynamic_import"


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"


class SandboxError(AicpError):
    pass


class SandboxTimeoutError(SandboxError):
    pass


class SandboxResourceError(SandboxError):
    pass


class SandboxSecurityError(SandboxError):
    pass


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    error: Optional[str] = None


class SandboxConfig(BaseModel):
    operation_type: OperationType
    language: Language = Language.PYTHON
    code: Optional[str] = None
    timeout_ms: int = Field(default=30000, ge=1000, le=60000)
    memory_limit_mb: int = Field(default=256, ge=64, le=1024)
    cpu_limit: float = Field(default=0.5, ge=0.1, le=2.0)
    disk_limit_mb: int = Field(default=50, ge=10, le=200)
    network_enabled: bool = False


BLOCKED_IMPORTS = {
    "python": {
        "os",
        "sys",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "ftplib",
        "telnetlib",
    },
    "javascript": {
        "child_process",
        "fs",
        "net",
        "http",
        "https",
        "dns",
        "eval",
        "Function",
    },
}


class SandboxService:
    def __init__(self, image: str = "python:3.11-sandbox"):
        self._image = image

    def _validate_code(self, code: str, language: Language) -> None:
        if language == Language.PYTHON:
            for blocked in BLOCKED_IMPORTS["python"]:
                if f"import {blocked}" in code or f"from {blocked} import" in code:
                    raise SandboxSecurityError(f"Blocked import: {blocked}")
        else:
            for blocked in BLOCKED_IMPORTS["javascript"]:
                if blocked in code:
                    raise SandboxSecurityError(f"Blocked keyword: {blocked}")

    def _execute_python(self, config: SandboxConfig) -> SandboxResult:
        import time

        start = time.perf_counter()
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(config.code or "")
                temp_path = f.name
            try:
                result = subprocess.run(
                    ["python", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=config.timeout_ms / 1000,
                )
                elapsed = int((time.perf_counter() - start) * 1000)
                return SandboxResult(
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    execution_time_ms=elapsed,
                )
            finally:
                os.unlink(temp_path)
        except subprocess.TimeoutExpired:
            elapsed = int((time.perf_counter() - start) * 1000)
            return SandboxResult(
                stdout="",
                stderr="Execution timed out",
                exit_code=-1,
                execution_time_ms=elapsed,
                error="timeout",
            )
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=elapsed,
                error="execution_error",
            )

    def _execute_javascript(self, config: SandboxConfig) -> SandboxResult:
        import time

        start = time.perf_counter()
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
                f.write(config.code or "")
                temp_path = f.name
            try:
                result = subprocess.run(
                    ["node", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=config.timeout_ms / 1000,
                )
                elapsed = int((time.perf_counter() - start) * 1000)
                return SandboxResult(
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    execution_time_ms=elapsed,
                )
            finally:
                os.unlink(temp_path)
        except subprocess.TimeoutExpired:
            elapsed = int((time.perf_counter() - start) * 1000)
            return SandboxResult(
                stdout="",
                stderr="Execution timed out",
                exit_code=-1,
                execution_time_ms=elapsed,
                error="timeout",
            )
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            return SandboxResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=elapsed,
                error="execution_error",
            )

    def run_sandboxed(self, config: SandboxConfig) -> SandboxResult:
        if config.code:
            self._validate_code(config.code, config.language)
        if config.language == Language.PYTHON:
            return self._execute_python(config)
        return self._execute_javascript(config)

    def validate_config(self, config: SandboxConfig) -> bool:
        if config.timeout_ms < 1000 or config.timeout_ms > 60000:
            return False
        if config.memory_limit_mb < 64 or config.memory_limit_mb > 1024:
            return False
        return True

    def get_running_count(self) -> int:
        return 0
