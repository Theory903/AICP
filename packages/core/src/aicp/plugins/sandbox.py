from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SandboxPolicy:
    allowed_permissions: set[str] = field(default_factory=set)
    allow_bundled_plugins: bool = True

    def permits(self, permission: str) -> bool:
        if not self.allowed_permissions:
            return True
        return permission in self.allowed_permissions


class PluginSandbox:
    def __init__(self, policy: SandboxPolicy | None = None) -> None:
        self.policy = policy or SandboxPolicy()

    def validate_permissions(self, permissions: list[str], *, bundled: bool = False) -> None:
        if bundled and self.policy.allow_bundled_plugins:
            return
        denied = [permission for permission in permissions if not self.policy.permits(permission)]
        if denied:
            raise PermissionError(f"Plugin permissions denied: {', '.join(sorted(denied))}")
