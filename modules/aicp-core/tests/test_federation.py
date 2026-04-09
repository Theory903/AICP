import hashlib

import pytest
from pydantic import ValidationError

import aicp.federation.federation as federation_module
from aicp.federation.federation import (
    CapabilityMesh,
    CapabilityShare,
    CRDTRegistry,
    DIDAuthenticator,
    FederationNode,
    FederationService,
    WellKnownDiscovery,
)


def test_federation_node_defaults_and_validation() -> None:
    node = FederationNode(name="Example Org", endpoint="https://example.com")

    assert node.id
    assert node.capabilities == []
    assert node.metadata == {}
    assert node.trust_level == 0

    with pytest.raises(ValidationError):
        FederationNode(name="Example Org", endpoint="not-a-uri")

    with pytest.raises(ValidationError):
        FederationNode(
            name="Example Org",
            endpoint="https://example.com",
            trust_level=5,
        )


def test_well_known_discovery_to_response_dict() -> None:
    discovery = WellKnownDiscovery(
        url="https://example.com/.well-known/aicp",
        capabilities=[{"name": "notes.list"}],
        organization="Example Org",
        contact="ops@example.com",
    )

    assert discovery.to_response_dict() == {
        "url": "https://example.com/.well-known/aicp",
        "capabilities": [{"name": "notes.list"}],
        "version": "1.0",
        "organization": "Example Org",
        "contact": "ops@example.com",
    }


def test_crdt_registry_put_get_and_merge_prefers_newer_clock() -> None:
    local = CRDTRegistry(name="local", node_id="node-a")
    remote = CRDTRegistry(name="remote", node_id="node-b")

    local.put("capability", {"name": "notes.list"}, node_id="node-a")
    remote.put("capability", {"name": "notes.read"}, node_id="node-b")
    remote.put("capability", {"name": "notes.write"}, node_id="node-b")

    local.merge(remote)

    assert local.get("capability") == {"name": "notes.write"}
    assert local.vector_clock["node-a"] == 1
    assert local.vector_clock["node-b"] == 2


def test_did_authenticator_validates_and_authenticates() -> None:
    authenticator = DIDAuthenticator()
    did = "did:web:example.com"
    challenge = authenticator.create_challenge()
    signature = hashlib.sha256(f"{did}:{challenge}".encode()).hexdigest()

    assert authenticator.validate(did) is True
    assert authenticator.authenticate(did, challenge, signature) is True
    assert authenticator.validate("not-a-did") is False
    assert authenticator.authenticate(did, challenge, "bad-signature") is False


def test_capability_mesh_tracks_nodes_and_capabilities() -> None:
    mesh = CapabilityMesh()
    node = FederationNode(id="node-1", name="Remote", endpoint="https://remote.test")
    share = CapabilityShare(
        id="share-1",
        capability_name="notes.list",
        version="1.0.0",
        shared_by="node-1",
        shared_at="2026-04-05T10:00:00Z",
    )

    mesh.add_node(node)
    mesh.share_capability(share)

    assert mesh.get_node("node-1") == node
    assert mesh.list_nodes() == [node]
    assert mesh.find_capability("notes.list") == [(node, share)]

    mesh.remove_node("node-1")
    assert mesh.get_node("node-1") is None


def test_federation_service_discovers_remote_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "url": "https://remote.test/.well-known/aicp",
                "capabilities": [{"name": "notes.list"}, {"name": "notes.create"}],
                "version": "1.0",
                "organization": "Remote Org",
            }

    def mock_get(url: str, timeout: float) -> MockResponse:
        assert url == "https://remote.test/.well-known/aicp"
        assert timeout == 5.0
        return MockResponse()

    monkeypatch.setattr(federation_module.httpx, "get", mock_get)

    service = FederationService()

    assert service.discover_remote("https://remote.test") == ["notes.list", "notes.create"]


def test_federation_service_builds_well_known_response() -> None:
    service = FederationService()
    service.share_capability(
        CapabilityShare(
            id="share-1",
            capability_name="notes.list",
            version="1.0.0",
            shared_by=service.registry.node_id,
            shared_at="2026-04-05T10:00:00Z",
            access_policy="public",
        )
    )

    assert service.get_well_known_aicp("https://local.test") == {
        "url": "https://local.test/.well-known/aicp",
        "capabilities": [
            {
                "name": "notes.list",
                "version": "1.0.0",
                "shared_by": service.registry.node_id,
                "access_policy": "public",
                "rate_limit": None,
            }
        ],
        "version": "1.0",
        "organization": service.registry.name,
        "contact": None,
    }
