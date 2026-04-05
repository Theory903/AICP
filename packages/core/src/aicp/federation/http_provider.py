from datetime import datetime
from typing import Any, Optional

import httpx

from .federation import (
    CapabilityShare,
    CRDTRegistry,
    FederationNode,
    FederationProvider,
    RegistrySyncStrategy,
    WellKnownDiscovery,
)


class HttpFederationProvider(FederationProvider):
    def __init__(self, node_endpoint: Optional[str] = None, timeout: float = 10.0):
        self.node_endpoint = node_endpoint
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def discover_node(self, url: str) -> Optional[FederationNode]:
        base_url = url.rstrip("/")
        well_known_url = f"{base_url}/.well-known/aicp"

        try:
            response = await self._require_client().get(well_known_url)
            response.raise_for_status()
            data = response.json()
            discovery = WellKnownDiscovery(**data)

            return FederationNode(
                name=discovery.organization or "Unknown Org",
                endpoint=base_url,
                capabilities=[item["name"] for item in discovery.capabilities],
                metadata={"version": discovery.version, "contact": discovery.contact},
            )
        except Exception:
            return None

    async def register_capability(self, capability: CapabilityShare) -> dict[str, Any]:
        try:
            if not self.node_endpoint:
                raise ValueError("Node endpoint is required for capability registration")

            payload = self._model_dump(capability)
            response = await self._require_client().post(
                f"{self.node_endpoint.rstrip('/')}/v1/federation/register",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def sync_registry(self, strategy: RegistrySyncStrategy) -> CRDTRegistry:
        if not self.node_endpoint:
            return self._build_registry(
                id="default",
                name="default",
                node_id="local",
                entries={},
                vector_clock={},
                last_updated=datetime.now().isoformat(),
            )

        response = await self._require_client().get(
            f"{self.node_endpoint.rstrip('/')}/v1/federation/registry"
        )
        response.raise_for_status()
        payload = response.json()

        return self._build_registry(
            id=payload.get("id", "default"),
            name=payload.get("name", "default"),
            node_id=payload.get("node_id", "remote"),
            entries=payload.get("entries", {}),
            vector_clock=payload.get("vector_clock", {}),
            last_updated=payload.get("last_updated", datetime.now().isoformat()),
        )

    async def authenticate_did(self, did: str, challenge: str) -> bool:
        return did.startswith("did:aicp:")

    async def execute_remote_capability(
        self,
        node: FederationNode,
        capability_name: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        url = f"{node.endpoint.rstrip('/')}/v1/execute"
        try:
            payload = {
                "capability_name": capability_name,
                "arguments": arguments,
                "execution_mode": "sync",
            }
            response = await self._require_client().post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "status": "error",
                "error": f"Remote execution failed: {str(e)}",
            }

    async def close(self):
        if self.client is not None:
            await self.client.aclose()

    @staticmethod
    def _model_dump(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(exclude_none=True)
        if isinstance(value, dict):
            return value
        return vars(value)

    def _require_client(self) -> httpx.AsyncClient:
        return self.client

    @staticmethod
    def _build_registry(
        *,
        id: str,
        name: str,
        node_id: str,
        entries: dict[str, Any],
        vector_clock: dict[str, Any],
        last_updated: str,
    ) -> CRDTRegistry:
        payload = {
            "id": id,
            "name": name,
            "node_id": node_id,
            "entries": entries,
            "vector_clock": vector_clock,
            "last_updated": last_updated,
        }
        try:
            return CRDTRegistry(**payload)
        except Exception:
            return CRDTRegistry.model_construct(**payload)
