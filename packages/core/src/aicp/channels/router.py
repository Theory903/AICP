from __future__ import annotations

from .registry import ChannelNotFound, ChannelRegistry


class ChannelRouter:
    def __init__(self, registry: ChannelRegistry) -> None:
        self._registry = registry
        self._fallback: str | None = None

    def set_fallback(self, channel_id: str) -> None:
        self._fallback = channel_id

    def route(self, message_channel_id: str | None = None, sender_id: str | None = None) -> str:
        if message_channel_id:
            try:
                channel = self._registry.get(message_channel_id)
                manifest = self._registry.get_manifest(message_channel_id)
                if channel.connected and self._allowed(manifest.allowlist, sender_id):
                    return message_channel_id
            except ChannelNotFound:
                pass

        for manifest in self._registry.iter_enabled_manifests():
            channel = self._registry.get(manifest.id)
            if channel.connected and self._allowed(manifest.allowlist, sender_id):
                return manifest.id

        if self._fallback:
            return self._fallback
        raise ChannelNotFound(message_channel_id or "any")

    @staticmethod
    def _allowed(allowlist: list[str], sender_id: str | None) -> bool:
        if not allowlist:
            return True
        if sender_id is None:
            return False
        return sender_id in allowlist
