"""Discovery service for runtime responses."""

from aicp.interfaces.capability_provider import CapabilityProvider


class DiscoveryService:
    """Builds discovery payloads from a capability provider."""

    def __init__(self, capability_provider: CapabilityProvider):
        self._provider = capability_provider

    async def discover(self) -> dict:
        capabilities = await self._provider.discover()
        return {
            "capabilities": [cap.model_dump(exclude_none=True, mode="json") for cap in capabilities],
            "metadata": {
                "provider_name": self._provider.provider_name,
                "provider_type": self._provider.provider_type,
                "capability_count": len(capabilities),
            },
        }
