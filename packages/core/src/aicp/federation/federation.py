from abc import ABC, abstractmethod
from dataclasses import field
import datetime
import hashlib
import hmac
from typing import Optional, List, Dict, Any, Literal
from urllib.parse import urlparse
import uuid

import httpx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, RootModel, field_validator
from pydantic.dataclasses import dataclass


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime.datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def _validate_uri(value: str) -> str:
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("must be a valid URI")
    return value


class DiscoveryProtocol(RootModel[Literal["well_known", "dns_sd", "manual"]]):
    root: Literal["well_known", "dns_sd", "manual"]


class RegistrySyncStrategy(RootModel[Literal["crdt", "snapshot", "delta"]]):
    root: Literal["crdt", "snapshot", "delta"]


class FederationNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    endpoint: str
    did: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    trust_level: int = Field(default=0, ge=0, le=4)
    last_seen: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("endpoint")
    @classmethod
    def _validate_endpoint(cls, value: str) -> str:
        return _validate_uri(value)

    @field_validator("last_seen")
    @classmethod
    def _validate_last_seen(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        _parse_datetime(value)
        return value


class CapabilityShare(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    capability_name: str
    version: str
    shared_by: str
    shared_at: str
    access_policy: str = "public"
    rate_limit: Optional[Dict[str, Any]] = None

    @field_validator("shared_at")
    @classmethod
    def _validate_shared_at(cls, value: str) -> str:
        _parse_datetime(value)
        return value


@dataclass(config=ConfigDict(extra="forbid"))
class CrossOrgCapability:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    local_name: str = ""
    remote_name: str = ""
    remote_org: str = ""
    endpoint: str = ""
    schema: Dict[str, Any] = field(default_factory=dict)
    shared: bool = False
    rate_limit: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        self.endpoint = _validate_uri(self.endpoint)


class CRDTRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str
    node_id: str
    entries: Dict[str, Any] = Field(default_factory=dict)
    vector_clock: Dict[str, int] = Field(default_factory=dict)
    last_updated: str = Field(default_factory=_utc_now)

    _entry_versions: Dict[str, Dict[str, Any]] = PrivateAttr(default_factory=dict)

    @field_validator("last_updated")
    @classmethod
    def _validate_last_updated(cls, value: str) -> str:
        _parse_datetime(value)
        return value

    def _record_key(self, key: str, record: Any) -> tuple[int, datetime.datetime]:
        metadata = self._entry_versions.get(key)
        if metadata is not None:
            clock = int(metadata.get("clock", 0))
            timestamp = _parse_datetime(str(metadata.get("timestamp", self.last_updated)))
            return (clock, timestamp)

        fallback_clock = int(self.vector_clock.get(self.node_id, max(self.vector_clock.values(), default=0)))
        timestamp = _parse_datetime(self.last_updated)
        return (fallback_clock, timestamp)

    @staticmethod
    def _build_record_metadata(node_id: str, clock: int, timestamp: str) -> Dict[str, Any]:
        return {
            "node_id": node_id,
            "clock": clock,
            "timestamp": timestamp,
        }

    def put(self, key: str, value: Any, node_id: str) -> None:
        next_clock = int(self.vector_clock.get(node_id, 0)) + 1
        timestamp = _utc_now()
        self.vector_clock[node_id] = next_clock
        self.entries[key] = value
        self._entry_versions[key] = self._build_record_metadata(
            node_id=node_id,
            clock=next_clock,
            timestamp=timestamp,
        )
        self.last_updated = timestamp

    def get(self, key: str) -> Any:
        return self.entries.get(key)

    def add_entry(self, key: str, value: Any) -> None:
        self.put(key, value, self.node_id)

    def get_entry(self, key: str) -> Any:
        return self.get(key)

    def merge(self, other: "CRDTRegistry") -> "CRDTRegistry":
        for node_id, clock in other.vector_clock.items():
            self.vector_clock[node_id] = max(int(self.vector_clock.get(node_id, 0)), int(clock))

        all_keys = set(self.entries.keys()) | set(other.entries.keys())
        for key in all_keys:
            local_record = self.entries.get(key)
            remote_record = other.entries.get(key)
            if local_record is None:
                self.entries[key] = remote_record
                self._entry_versions[key] = other._entry_versions.get(
                    key,
                    self._build_record_metadata(
                        node_id=other.node_id,
                        clock=int(other.vector_clock.get(other.node_id, max(other.vector_clock.values(), default=0))),
                        timestamp=other.last_updated,
                    ),
                )
                continue
            if remote_record is None:
                continue
            if other._record_key(key, remote_record) > self._record_key(key, local_record):
                self.entries[key] = remote_record
                self._entry_versions[key] = other._entry_versions.get(
                    key,
                    self._build_record_metadata(
                        node_id=other.node_id,
                        clock=int(other.vector_clock.get(other.node_id, max(other.vector_clock.values(), default=0))),
                        timestamp=other.last_updated,
                    ),
                )

        if _parse_datetime(other.last_updated) > _parse_datetime(self.last_updated):
            self.last_updated = other.last_updated
        return self


class WellKnownDiscovery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    capabilities: List[Dict[str, Any]]
    version: str = "1.0"
    organization: Optional[str] = None
    contact: Optional[str] = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return _validate_uri(value)

    def to_response_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class FederationProvider(ABC):
    @abstractmethod
    async def discover_node(self, url: str) -> Optional[FederationNode]:
        raise NotImplementedError

    @abstractmethod
    async def register_capability(self, capability: CapabilityShare) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def sync_registry(self, strategy: RegistrySyncStrategy) -> CRDTRegistry:
        raise NotImplementedError

    @abstractmethod
    async def authenticate_did(self, did: str, challenge: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def execute_remote_capability(
        self,
        node: FederationNode,
        capability_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NotImplementedError


@dataclass(config=ConfigDict(extra="forbid"))
class DIDAuthenticator:
    trusted_methods: List[str] = field(
        default_factory=lambda: ["did:aicp:", "did:web:", "did:key:"]
    )

    def validate(self, did: str) -> bool:
        if not isinstance(did, str) or not did.startswith("did:"):
            return False
        if not any(did.startswith(method) for method in self.trusted_methods):
            return False
        parts = did.split(":")
        return len(parts) >= 3 and all(part != "" for part in parts[:3])

    def authenticate(self, did: str, challenge: str, signature: str) -> bool:
        if not self.validate(did):
            return False
        if not challenge or not signature:
            return False
        expected_signature = hashlib.sha256(f"{did}:{challenge}".encode("utf-8")).hexdigest()
        return hmac.compare_digest(signature, expected_signature)

    def create_challenge(self) -> str:
        return uuid.uuid4().hex


class CapabilityMesh(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: Dict[str, FederationNode] = Field(default_factory=dict)
    shares: Dict[str, CapabilityShare] = Field(default_factory=dict)

    def add_node(self, node: FederationNode) -> None:
        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)
        self.shares = {
            share_id: share
            for share_id, share in self.shares.items()
            if share.shared_by != node_id
        }

    def get_node(self, node_id: str) -> Optional[FederationNode]:
        return self.nodes.get(node_id)

    def list_nodes(self) -> List[FederationNode]:
        return list(self.nodes.values())

    def share_capability(self, share: CapabilityShare) -> None:
        self.shares[share.id] = share

    def find_capability(self, name: str) -> List[tuple[FederationNode, CapabilityShare]]:
        matches: List[tuple[FederationNode, CapabilityShare]] = []
        for share in self.shares.values():
            if share.capability_name != name:
                continue
            node = self.nodes.get(share.shared_by)
            if node is not None:
                matches.append((node, share))
        return matches


class FederationService(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mesh: CapabilityMesh = Field(default_factory=CapabilityMesh)
    registry: CRDTRegistry = Field(
        default_factory=lambda: CRDTRegistry(name="default", node_id="local")
    )
    authenticator: DIDAuthenticator = Field(default_factory=DIDAuthenticator)

    def discover_remote(self, endpoint: str) -> List[str]:
        well_known_url = f"{endpoint.rstrip('/')}/.well-known/aicp"
        try:
            response = httpx.get(well_known_url, timeout=5.0)
            response.raise_for_status()
            discovery = WellKnownDiscovery(**response.json())
            capabilities = []
            for capability in discovery.capabilities:
                name = capability.get("name")
                if isinstance(name, str) and name:
                    capabilities.append(name)
            return capabilities
        except Exception:
            return []

    def share_capability(self, share: CapabilityShare) -> None:
        self.mesh.share_capability(share)
        self.registry.put(
            key=share.capability_name,
            value=share.model_dump(),
            node_id=share.shared_by,
        )

    def get_well_known_aicp(self, host: str) -> Dict[str, Any]:
        discovery = WellKnownDiscovery(
            url=f"{host.rstrip('/')}/.well-known/aicp",
            capabilities=[
                {
                    "name": share.capability_name,
                    "version": share.version,
                    "shared_by": share.shared_by,
                    "access_policy": share.access_policy,
                    "rate_limit": share.rate_limit,
                }
                for share in self.mesh.shares.values()
            ],
            version="1.0",
            organization=self.registry.name,
            contact=None,
        )
        return discovery.to_response_dict()
