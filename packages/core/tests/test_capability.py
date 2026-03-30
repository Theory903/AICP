"""Tests for capability models."""

from aicp.capability import (
    Capability,
    CapabilityKind,
    InputSchema,
    OutputSchema,
    ProviderInfo,
)


class TestCapability:
    """Tests for Capability model."""

    def test_valid_capability(self):
        """Test creating a valid capability."""
        capability = Capability(
            name="payments.transfer",
            description="Transfer money to a recipient",
            kind=CapabilityKind.ACTION,
            input_schema=InputSchema(
                type="object", properties={"amount": {"type": "number"}}, required=["amount"]
            ),
            output_schema=OutputSchema(
                type="object", properties={"transaction_id": {"type": "string"}}
            ),
            tags=["payments", "money"],
        )
        assert capability.name == "payments.transfer"
        assert capability.kind == "action"

    def test_capability_names(self):
        """Test various valid capability names."""
        names = [
            "payments.transfer",
            "orders.create",
            "user_get",
            "my-capability",
            "api/v1_test",
        ]
        for name in names:
            cap = Capability(
                name=name,
                kind=CapabilityKind.ACTION,
            )
            assert cap.name == name

    def test_capability_kind_enum(self):
        """Test capability kind values."""
        assert CapabilityKind.ACTION == "action"
        assert CapabilityKind.QUERY == "query"
        assert CapabilityKind.WORKFLOW == "workflow"
        assert CapabilityKind.ASYNC_ACTION == "async_action"
        assert CapabilityKind.BATCH_ACTION == "batch_action"

    def test_capability_supports_structured_provider_info(self):
        """Test provider metadata uses a nested provider object."""
        capability = Capability(
            name="payments.transfer",
            kind=CapabilityKind.ACTION,
            provider=ProviderInfo(name="banking_api", type="http"),
        )

        assert capability.provider is not None
        assert capability.provider.name == "banking_api"
        assert capability.provider.type == "http"
