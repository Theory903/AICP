import requests
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class Capability:
    name: str
    description: str
    kind: str
    input_schema: dict
    output_schema: dict


@dataclass
class ExecutionResult:
    execution_id: str
    capability_name: str
    status: str
    data: Optional[Any] = None
    error: Optional[str] = None
    policy_result: Optional[dict] = None


@dataclass
class Policy:
    name: str
    effect: str
    conditions: Optional[dict] = None


class AicpClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"
        self.session.headers["Content-Type"] = "application/json"

    def list_capabilities(self) -> list[Capability]:
        resp = self.session.get(f"{self.base_url}/v1/capabilities")
        resp.raise_for_status()
        data = resp.json()
        return [Capability(**c) for c in data.get("capabilities", [])]

    def get_capability(self, name: str) -> Optional[Capability]:
        caps = self.list_capabilities()
        for c in caps:
            if c.name == name:
                return c
        return None

    def execute(self, capability: str, arguments: Optional[dict] = None) -> ExecutionResult:
        payload = {"capability": capability, "arguments": arguments or {}}
        resp = self.session.post(f"{self.base_url}/v1/execute", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ExecutionResult(**data)

    def list_policies(self) -> list[Policy]:
        resp = self.session.get(f"{self.base_url}/v1/policies")
        resp.raise_for_status()
        data = resp.json()
        return [Policy(**p) for p in data.get("policies", [])]

    def get_policy(self, name: str) -> Optional[Policy]:
        policies = self.list_policies()
        for p in policies:
            if p.name == name:
                return p
        return None

    def list_workflows(self) -> list[dict]:
        resp = self.session.get(f"{self.base_url}/v1/workflows")
        resp.raise_for_status()
        return resp.json().get("workflows", [])

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        resp = self.session.get(f"{self.base_url}/v1/workflows/{workflow_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def create_workflow(self, definition: dict) -> dict:
        resp = self.session.post(f"{self.base_url}/v1/workflows", json={"definition": definition})
        resp.raise_for_status()
        return resp.json()

    def list_approvals(self) -> list[dict]:
        resp = self.session.get(f"{self.base_url}/v1/approvals")
        resp.raise_for_status()
        return resp.json().get("approvals", [])

    def get_approval(self, approval_id: str) -> Optional[dict]:
        resp = self.session.get(f"{self.base_url}/v1/approvals/{approval_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def approve(self, approval_id: str, reason: Optional[str] = None) -> dict:
        resp = self.session.post(
            f"{self.base_url}/v1/approvals/{approval_id}/decide",
            json={"decision": "approve", "reason": reason}
        )
        resp.raise_for_status()
        return resp.json()

    def deny(self, approval_id: str, reason: str) -> dict:
        resp = self.session.post(
            f"{self.base_url}/v1/approvals/{approval_id}/decide",
            json={"decision": "deny", "reason": reason}
        )
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict:
        resp = self.session.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()


__all__ = ["AicpClient", "Capability", "ExecutionResult", "Policy"]