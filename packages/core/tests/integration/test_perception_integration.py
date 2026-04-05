import pytest
import asyncio
from aicp.perception.playwright_provider import PlaywrightPerceptionProvider
from aicp.perception.perception import SignalType, SignalExtractor

@pytest.mark.asyncio
async def test_perception_signal_extraction():
    provider = PlaywrightPerceptionProvider(headless=True)
    extractor = SignalExtractor()
    
    url = "data:text/html,<html><body><form id='test-form'><input type='text' id='name'></form></body></html>"
    
    try:
        tree = await provider.get_accessibility_tree(url)
        assert tree.element_count > 0
        
        signals = extractor.extract(tree, SignalType.ACCESSIBILITY_TREE)
        assert any(s.payload.get("type") == "forms_detected" for s in signals)
        
        snapshot = await provider.get_dom_snapshot(url)
        assert len(snapshot.forms) == 1
        
        dom_signals = extractor.extract(snapshot, SignalType.DOM_SNAPSHOT)
        assert any(s.payload.get("type") == "forms" for s in dom_signals)
    finally:
        await provider.stop()
