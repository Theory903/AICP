from __future__ import annotations

from .base import BaseChannel, ChannelError
from .manifest import ChannelManifest, ChannelType


class ChannelNotFoundError(ChannelError):
    def __init__(self, channel_id: str) -> None:
        self.channel_id = channel_id
        super().__init__(f"Channel not found: {channel_id}")


ChannelNotFound = ChannelNotFoundError


class ChannelRegistry:
    def __init__(self) -> None:
        self._channels: dict[str, BaseChannel] = {}
        self._manifests: dict[str, ChannelManifest] = {}

    def register(self, manifest: ChannelManifest, channel: BaseChannel) -> None:
        self._manifests[manifest.id] = manifest
        self._channels[manifest.id] = channel

    def get(self, channel_id: str) -> BaseChannel:
        if channel_id not in self._channels:
            raise ChannelNotFoundError(channel_id)
        return self._channels[channel_id]

    def get_manifest(self, channel_id: str) -> ChannelManifest:
        if channel_id not in self._manifests:
            raise ChannelNotFoundError(channel_id)
        return self._manifests[channel_id]

    def list_all(self) -> list[str]:
        return sorted(self._channels)

    def list_by_type(self, channel_type: ChannelType) -> list[str]:
        return [
            channel_id
            for channel_id, manifest in sorted(self._manifests.items())
            if manifest.channel_type == channel_type
        ]

    def list_enabled(self) -> list[str]:
        return [
            channel_id
            for channel_id, manifest in sorted(self._manifests.items())
            if manifest.enabled
        ]

    def iter_enabled_manifests(self) -> list[ChannelManifest]:
        return sorted(
            (manifest for manifest in self._manifests.values() if manifest.enabled),
            key=lambda manifest: (manifest.priority, manifest.id),
        )

    def remove(self, channel_id: str) -> None:
        self._channels.pop(channel_id, None)
        self._manifests.pop(channel_id, None)
