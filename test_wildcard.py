import asyncio
from aicp.implementations.policy import DefaultPolicyEngine
from aicp.interfaces.policy_engine import Policy, PolicyEffect, PolicySubject

async def test_wildcard():
    engine = DefaultPolicyEngine()
    policy = Policy(
        name="wildcard_deny",
        description="Deny all articles",
        effect=PolicyEffect.DENY,
        subject=PolicySubject(capability_name="articles.*")
    )
    await engine.add_policy(policy)
    
    # Test match
    dec1 = await engine.evaluate("articles.create", {}, {"kind": "action"})
    print(f"articles.create: {dec1.effect} - {dec1.reason}")
    
    # Test no match
    dec2 = await engine.evaluate("users.login", {}, {"kind": "action"})
    print(f"users.login: {dec2.effect} - {dec2.reason}")

if __name__ == "__main__":
    asyncio.run(test_wildcard())
