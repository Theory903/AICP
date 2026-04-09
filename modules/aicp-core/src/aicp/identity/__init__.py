"""
Identity and Trust Module
Module 2 - DID-based authentication and trust tiers
"""

from aicp.identity.did import (
    DIDDocument,
    DIDMethod,
    DIDRegistry,
    Identity,
    IdentityStatus,
    TrustEvaluator,
    TrustPolicy,
    TrustTier,
    VerifiableCredential,
    create_aicp_identity,
)

__all__ = [
    "TrustTier",
    "IdentityStatus",
    "DIDMethod",
    "DIDDocument",
    "VerifiableCredential",
    "Identity",
    "TrustPolicy",
    "TrustEvaluator",
    "DIDRegistry",
    "create_aicp_identity",
]
