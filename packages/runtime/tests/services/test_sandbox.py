import pytest

from aicp_runtime.services.sandbox import (
    Language,
    OperationType,
    SandboxConfig,
    SandboxResult,
    SandboxSecurityError,
    SandboxService,
)


class TestSandboxService:
    def test_python_execution(self):
        svc = SandboxService()
        config = SandboxConfig(
            operation_type=OperationType.CODE_EXECUTION,
            language=Language.PYTHON,
            code="print('hello')",
        )
        result = svc.run_sandboxed(config)
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_python_error(self):
        svc = SandboxService()
        config = SandboxConfig(
            operation_type=OperationType.CODE_EXECUTION,
            language=Language.PYTHON,
            code="raise ValueError('test')",
        )
        result = svc.run_sandboxed(config)
        assert result.exit_code != 0

    def test_python_timeout(self):
        svc = SandboxService()
        config = SandboxConfig(
            operation_type=OperationType.CODE_EXECUTION,
            language=Language.PYTHON,
            code="import time; time.sleep(10)",
            timeout_ms=2000,
        )
        result = svc.run_sandboxed(config)
        assert result.error == "timeout"

    def test_blocked_import(self):
        svc = SandboxService()
        config = SandboxConfig(
            operation_type=OperationType.CODE_EXECUTION,
            language=Language.PYTHON,
            code="import os; os.system('ls')",
        )
        with pytest.raises(SandboxSecurityError):
            svc.run_sandboxed(config)

    def test_validate_config_valid(self):
        svc = SandboxService()
        config = SandboxConfig(operation_type=OperationType.CODE_EXECUTION, timeout_ms=5000, memory_limit_mb=128)
        assert svc.validate_config(config) is True

    def test_validate_config_invalid_timeout(self):
        svc = SandboxService()
        config = SandboxConfig(operation_type=OperationType.CODE_EXECUTION, timeout_ms=5000)
        svc.validate_config(config) is False

    def test_get_running_count(self):
        svc = SandboxService()
        assert svc.get_running_count() == 0


class TestSandboxConfig:
    def test_default_values(self):
        config = SandboxConfig(operation_type=OperationType.CODE_EXECUTION)
        assert config.timeout_ms == 30000
        assert config.memory_limit_mb == 256
        assert config.network_enabled is False

    def test_custom_values(self):
        config = SandboxConfig(
            operation_type=OperationType.REGEX,
            language=Language.JAVASCRIPT,
            code=".*",
            timeout_ms=10000,
        )
        assert config.timeout_ms == 10000
        assert config.language == Language.JAVASCRIPT