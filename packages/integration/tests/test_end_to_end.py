import pytest


def test_oauth_pkce_generation():
    from aicp.auth.oauth import PKCEPair
    
    pkce = PKCEPair.generate()
    assert len(pkce.verifier) > 40
    assert len(pkce.challenge) > 40
    assert pkce.verifier != pkce.challenge


def test_oauth_service_initialization():
    from aicp.auth.oauth import OAuth2Service
    
    service = OAuth2Service(
        client_id="test-client",
        auth_url="https://auth.example.com/authorize",
        token_url="https://auth.example.com/token"
    )
    assert service.client_id == "test-client"


def test_token_manager_store_and_check():
    from aicp.auth.token_manager import TokenManager
    
    manager = TokenManager()
    manager.store_tokens(access_token="token123", refresh_token="refresh456", expires_in=3600)
    
    assert manager.get_access_token() == "token123"
    assert manager.get_refresh_token() == "refresh456"
    assert manager.is_valid() is True
    assert manager.should_refresh() is False


def test_skill_manifest_parse():
    from aicp.skills.loader import SkillManifest
    
    manifest_text = """---
name: test-skill
description: Test skill description
allowed-tools: [Bash, ReadFile]
when_to_use: Testing
arguments: [arg1]
context: inline
effort: low
---
# Test"""
    
    skill = SkillManifest.parse(manifest_text)
    assert skill.name == "test-skill"
    assert skill.context == "inline"


def test_plugin_manifest_validation():
    from aicp.plugins.manifest import PluginManifest
    
    data = {
        "id": "test-plugin",
        "name": "test-plugin",
        "version": "1.0.0",
        "description": "Test plugin",
        "author": "test-author",
        "plugin_type": "provider",
    }
    
    manifest = PluginManifest.model_validate(data)
    assert manifest.name == "test-plugin"
    assert manifest.version == "1.0.0"
    assert manifest.author == "test-author"


def test_session_storage_save_load():
    import tempfile
    from aicp_runtime.services.session_storage import JSONLSessionStorage
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JSONLSessionStorage(tmpdir)
        session_id = "test-session-123"
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        storage.save(session_id, messages)
        loaded = storage.load(session_id)
        
        assert len(loaded) == 2
        assert loaded[0]["content"] == "Hello"


def test_hook_registry_trigger():
    import asyncio
    from aicp.plugins.hooks import HookRegistry, HookContext
    from aicp.plugins.manifest import HookType
    
    registry = HookRegistry()
    triggered = []
    
    def handler(ctx: HookContext) -> None:
        triggered.append(ctx.payload)
    
    registry.register(HookType.POST_CAPABILITY, "test-plugin", handler)
    asyncio.run(registry.emit(HookType.POST_CAPABILITY, payload={"query": "test"}))
    
    assert len(triggered) == 1
    assert triggered[0]["query"] == "test"