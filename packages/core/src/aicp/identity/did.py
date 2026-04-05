"""
Identity and Trust Module
Module 2 - DID-based authentication and trust tiers
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid
import hashlib
import json
from datetime import datetime, timedelta


class TrustTier(int, Enum):
    """Trust tier levels (0-4)"""
    ANONYMOUS = 0      # No identity, minimal trust
    IDENTIFIED = 1     # Basic identity, limited capabilities
    VERIFIED = 2       # Verified identity, moderate capabilities
    TRUSTED = 3       # High trust, most capabilities
    AUTONOMOUS = 4    # Full trust, all capabilities


class IdentityStatus(str, Enum):
    """Identity status"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class DIDMethod(str, Enum):
    """Supported DID methods"""
    AICP = "aicp"
    WEB = "web"
    KEY = "key"


class DIDDocument(BaseModel):
    """W3C DID Document"""
    id: str  # DID
    context: list[str] = Field(default_factory=lambda: ["https://www.w3.org/ns/did/v1"])
    verification_method: list[dict[str, Any]] = Field(default_factory=list)
    authentication: list[str] = Field(default_factory=list)
    service: list[dict[str, Any]] = Field(default_factory=list)
    created: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class VerifiableCredential(BaseModel):
    """Verifiable Credential"""
    id: str = Field(default_factory=lambda: f"vc_{uuid.uuid4().hex[:12]}")
    issuer: str
    subject: str
    credential_type: list[str] = Field(default_factory=list)
    claims: dict[str, Any] = Field(default_factory=dict)
    proof: Optional[dict[str, Any]] = None
    issued: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires: Optional[str] = None


class Identity(BaseModel):
    """Identity with DID"""
    id: str = Field(default_factory=lambda: f"id_{uuid.uuid4().hex[:8]}")
    did: str
    did_method: DIDMethod = DIDMethod.AICP
    display_name: str
    trust_tier: TrustTier = TrustTier.ANONYMOUS
    status: IdentityStatus = IdentityStatus.PENDING
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    credentials: list[VerifiableCredential] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_authenticated: Optional[str] = None

    class Config:
        use_enum_values = True


class TrustPolicy(BaseModel):
    """Trust policy for capability access"""
    name: str
    description: Optional[str] = None
    min_tier: TrustTier = TrustTier.ANONYMOUS
    requires_capabilities: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    rate_limit: Optional[int] = None  # requests per minute


class TrustEvaluator:
    """Evaluates trust for capability access"""

    def __init__(self):
        self._identities: dict[str, Identity] = {}
        self._policies: dict[str, TrustPolicy] = {}
        self._default_policies: dict[str, TrustPolicy] = {}

    def register_identity(self, identity: Identity) -> Identity:
        """Register a new identity"""
        self._identities[identity.id] = identity
        return identity

    def get_identity(self, identity_id: str) -> Optional[Identity]:
        """Get identity by ID"""
        return self._identities.get(identity_id)

    def get_identity_by_did(self, did: str) -> Optional[Identity]:
        """Get identity by DID"""
        for identity in self._identities.values():
            if identity.did == did:
                return identity
        return None

    def add_policy(self, policy: TrustPolicy):
        """Add a trust policy"""
        self._policies[policy.name] = policy

    def set_default_policy(self, capability: str, policy: TrustPolicy):
        """Set default policy for a capability"""
        self._default_policies[capability] = policy

    def evaluate(self, identity_id: str, capability: str) -> dict[str, Any]:
        """Evaluate trust for identity accessing capability"""
        identity = self._identities.get(identity_id)
        if not identity:
            return {
                "allowed": False,
                "reason": "Identity not found",
                "trust_tier": 0
            }

        # Get applicable policy
        policy = self._default_policies.get(capability)
        
        # Check trust tier
        tier_requirement = policy.min_tier if policy else TrustTier.ANONYMOUS
        
        if identity.trust_tier < tier_requirement:
            return {
                "allowed": False,
                "reason": f"Trust tier {identity.trust_tier.value} below required {tier_requirement.value}",
                "trust_tier": identity.trust_tier.value,
                "required_tier": tier_requirement.value
            }

        # Check required capabilities
        if policy and policy.requires_capabilities:
            missing = [c for c in policy.requires_capabilities if c not in identity.capabilities]
            if missing:
                return {
                    "allowed": False,
                    "reason": f"Missing capabilities: {missing}",
                    "trust_tier": identity.trust_tier.value,
                    "missing_capabilities": missing
                }

        return {
            "allowed": True,
            "trust_tier": identity.trust_tier.value,
            "requires_approval": policy.requires_approval if policy else False,
            "rate_limit": policy.rate_limit if policy else None
        }

    def promote_tier(self, identity_id: str, new_tier: TrustTier, reason: str = "") -> bool:
        """Promote identity to higher trust tier"""
        identity = self._identities.get(identity_id)
        if not identity:
            return False
        
        if new_tier > identity.trust_tier:
            identity.trust_tier = new_tier
            identity.metadata["promotion"] = {
                "from": identity.trust_tier.value,
                "to": new_tier.value,
                "reason": reason,
                "at": datetime.utcnow().isoformat()
            }
            return True
        return False

    def add_credential(self, identity_id: str, credential: VerifiableCredential) -> bool:
        """Add verifiable credential to identity"""
        identity = self._identities.get(identity_id)
        if not identity:
            return False
        identity.credentials.append(credential)
        return True


class DIDRegistry:
    """DID registration and resolution"""

    def __init__(self):
        self._documents: dict[str, DIDDocument] = {}

    def create(self, method: DIDMethod, public_key: str, service_endpoint: Optional[str] = None) -> tuple[DIDDocument, str]:
        """Create a new DID"""
        # Generate DID based on method
        did = f"did:{method.value}:{hashlib.sha256(public_key.encode()).hexdigest()[:16]}"
        
        doc = DIDDocument(
            id=did,
            verification_method=[{
                "id": f"{did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "public_key_multibase": public_key
            }],
            authentication=[f"{did}#key-1"]
        )
        
        if service_endpoint:
            doc.service.append({
                "id": f"{did}#service-1",
                "type": "AgentService",
                "service_endpoint": service_endpoint
            })
        
        self._documents[did] = doc
        return doc, did

    def resolve(self, did: str) -> Optional[DIDDocument]:
        """Resolve DID to document"""
        return self._documents.get(did)

    def update(self, did: str, updates: dict[str, Any]) -> bool:
        """Update DID document"""
        doc = self._documents.get(did)
        if not doc:
            return False
        
        for key, value in updates.items():
            if hasattr(doc, key):
                setattr(doc, key, value)
        
        doc.updated = datetime.utcnow().isoformat()
        return True

    def deactivate(self, did: str) -> bool:
        """Deactivate a DID"""
        if did in self._documents:
            # Mark as deactivated by adding to metadata
            doc = self._documents[did]
            doc.service = []  # Remove services
            return True
        return False


def create_aicp_identity(display_name: str, trust_tier: TrustTier = TrustTier.ANONYMOUS) -> tuple[Identity, str]:
    """Helper to create a new AICP identity"""
    # Generate a simple key for demo
    key = hashlib.sha256(f"{display_name}{uuid.uuid4()}".encode()).hexdigest()
    
    registry = DIDRegistry()
    doc, did = registry.create(DIDMethod.AICP, key)
    
    identity = Identity(
        did=did,
        display_name=display_name,
        trust_tier=trust_tier,
        status=IdentityStatus.ACTIVE
    )
    
    return identity, did