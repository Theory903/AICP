"""Tests for the 5-layer Memory System (TDD — tests first)."""

from __future__ import annotations

import pytest

from aicp_runtime.memory.store import (
    WorkingMemory,
    EpisodicMemory,
    SemanticMemory,
    ProceduralMemory,
    MetaMemory,
    MemoryStore,
    MemorySnapshot,
)


# ---------------------------------------------------------------------------
# WorkingMemory
# ---------------------------------------------------------------------------


class TestWorkingMemory:
    def test_set_and_get(self):
        wm = WorkingMemory()
        wm.set("current_step", "checkout")
        assert wm.get("current_step") == "checkout"

    def test_get_missing_returns_default(self):
        wm = WorkingMemory()
        assert wm.get("missing") is None
        assert wm.get("missing", "fallback") == "fallback"

    def test_delete_removes_key(self):
        wm = WorkingMemory()
        wm.set("key", "value")
        wm.delete("key")
        assert wm.get("key") is None

    def test_clear_empties_memory(self):
        wm = WorkingMemory()
        wm.set("a", 1)
        wm.set("b", 2)
        wm.clear()
        assert wm.to_dict() == {}

    def test_to_dict(self):
        wm = WorkingMemory()
        wm.set("x", 42)
        assert wm.to_dict() == {"x": 42}

    def test_from_dict_roundtrip(self):
        wm = WorkingMemory.from_dict({"foo": "bar"})
        assert wm.get("foo") == "bar"


# ---------------------------------------------------------------------------
# EpisodicMemory
# ---------------------------------------------------------------------------


class TestEpisodicMemory:
    def test_append_and_retrieve(self):
        em = EpisodicMemory()
        em.append("session_started", data={"goal": "checkout"})
        events = em.all()
        assert len(events) == 1
        assert events[0].event == "session_started"
        assert events[0].data["goal"] == "checkout"
        assert events[0].timestamp is not None

    def test_multiple_events_ordered(self):
        em = EpisodicMemory()
        em.append("step_1")
        em.append("step_2")
        events = em.all()
        assert [e.event for e in events] == ["step_1", "step_2"]

    def test_to_dict_list(self):
        em = EpisodicMemory()
        em.append("capability_executed", data={"cap": "cart.add_item"})
        result = em.to_list()
        assert len(result) == 1
        assert result[0]["event"] == "capability_executed"
        assert "timestamp" in result[0]

    def test_from_list_roundtrip(self):
        original = EpisodicMemory()
        original.append("test_event", data={"x": 1})
        restored = EpisodicMemory.from_list(original.to_list())
        assert len(restored.all()) == 1
        assert restored.all()[0].event == "test_event"


# ---------------------------------------------------------------------------
# SemanticMemory
# ---------------------------------------------------------------------------


class TestSemanticMemory:
    def test_set_and_get_fact(self):
        sm = SemanticMemory()
        sm.set("preferred_restaurant", "Tacos El Rey")
        assert sm.get("preferred_restaurant") == "Tacos El Rey"

    def test_update_fact(self):
        sm = SemanticMemory()
        sm.set("count", 1)
        sm.set("count", 2)
        assert sm.get("count") == 2

    def test_keys(self):
        sm = SemanticMemory()
        sm.set("a", 1)
        sm.set("b", 2)
        assert set(sm.keys()) == {"a", "b"}

    def test_to_dict(self):
        sm = SemanticMemory()
        sm.set("dietary_restrictions", ["gluten-free"])
        d = sm.to_dict()
        assert d["dietary_restrictions"] == ["gluten-free"]

    def test_from_dict_roundtrip(self):
        sm = SemanticMemory.from_dict({"restaurant": "Tacos El Rey"})
        assert sm.get("restaurant") == "Tacos El Rey"


# ---------------------------------------------------------------------------
# ProceduralMemory
# ---------------------------------------------------------------------------


class TestProceduralMemory:
    def test_add_pattern(self):
        pm = ProceduralMemory()
        pm.add_pattern("cart.add -> checkout", confidence=0.85)
        patterns = pm.all()
        assert len(patterns) == 1
        assert patterns[0].pattern == "cart.add -> checkout"
        assert patterns[0].confidence == 0.85

    def test_pattern_confidence_clamped(self):
        pm = ProceduralMemory()
        with pytest.raises(ValueError, match="confidence"):
            pm.add_pattern("bad pattern", confidence=1.5)

    def test_best_pattern_returns_highest_confidence(self):
        pm = ProceduralMemory()
        pm.add_pattern("a", confidence=0.5)
        pm.add_pattern("b", confidence=0.9)
        pm.add_pattern("c", confidence=0.7)
        best = pm.best()
        assert best is not None
        assert best.pattern == "b"

    def test_to_list(self):
        pm = ProceduralMemory()
        pm.add_pattern("flow", confidence=0.8)
        result = pm.to_list()
        assert len(result) == 1
        assert result[0]["pattern"] == "flow"
        assert result[0]["confidence"] == 0.8

    def test_from_list_roundtrip(self):
        pm = ProceduralMemory()
        pm.add_pattern("p1", confidence=0.6)
        restored = ProceduralMemory.from_list(pm.to_list())
        assert len(restored.all()) == 1


# ---------------------------------------------------------------------------
# MetaMemory
# ---------------------------------------------------------------------------


class TestMetaMemory:
    def test_defaults(self):
        mm = MetaMemory()
        assert mm.token_budget_remaining == 0
        assert mm.capability_coverage == []
        assert mm.preference_weights == {}

    def test_set_token_budget(self):
        mm = MetaMemory(token_budget_remaining=50000)
        assert mm.token_budget_remaining == 50000

    def test_add_capability_coverage(self):
        mm = MetaMemory()
        mm.add_coverage("cart.*")
        mm.add_coverage("checkout.*")
        assert "cart.*" in mm.capability_coverage
        assert "checkout.*" in mm.capability_coverage

    def test_set_preference_weight(self):
        mm = MetaMemory()
        mm.set_preference("speed", 0.8)
        assert mm.preference_weights["speed"] == 0.8

    def test_to_dict(self):
        mm = MetaMemory(token_budget_remaining=1000)
        mm.add_coverage("payments.*")
        mm.set_preference("cost", 0.3)
        d = mm.to_dict()
        assert d["token_budget_remaining"] == 1000
        assert "payments.*" in d["capability_coverage"]
        assert d["preference_weights"]["cost"] == 0.3

    def test_from_dict_roundtrip(self):
        mm = MetaMemory(token_budget_remaining=5000)
        mm.add_coverage("cart.*")
        restored = MetaMemory.from_dict(mm.to_dict())
        assert restored.token_budget_remaining == 5000
        assert "cart.*" in restored.capability_coverage


# ---------------------------------------------------------------------------
# MemoryStore (the 5-layer aggregator)
# ---------------------------------------------------------------------------


class TestMemoryStore:
    def test_memory_store_has_all_layers(self):
        store = MemoryStore()
        assert isinstance(store.working, WorkingMemory)
        assert isinstance(store.episodic, EpisodicMemory)
        assert isinstance(store.semantic, SemanticMemory)
        assert isinstance(store.procedural, ProceduralMemory)
        assert isinstance(store.meta, MetaMemory)

    def test_snapshot_returns_memory_snapshot(self):
        store = MemoryStore()
        store.working.set("step", "checkout")
        store.episodic.append("capability_executed")
        store.semantic.set("pref", "fast")

        snap = store.snapshot()
        assert isinstance(snap, MemorySnapshot)
        assert snap.working["step"] == "checkout"
        assert len(snap.episodic) == 1
        assert snap.semantic["pref"] == "fast"

    def test_snapshot_to_dict_conforms_to_schema(self):
        """MemorySnapshot dict must conform to session.schema.json memory sub-schema."""
        import json
        from pathlib import Path
        from jsonschema import Draft202012Validator

        schema_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "aicp-core"
            / "spec"
            / "schemas"
            / "session.schema.json"
        )
        with open(schema_path) as f:
            full_schema = json.load(f)

        sub_schema = full_schema["properties"]["memory"]
        validator = Draft202012Validator(sub_schema)

        store = MemoryStore()
        store.working.set("x", 1)
        store.episodic.append("test_event")
        store.procedural.add_pattern("a -> b", confidence=0.7)
        store.meta.token_budget_remaining = 10000

        errors = list(validator.iter_errors(store.snapshot().to_dict()))
        assert not errors, f"MemorySnapshot does not conform to schema: {errors}"

    def test_restore_from_snapshot(self):
        store = MemoryStore()
        store.working.set("phase", "payment")
        store.semantic.set("user_pref", "gluten-free")

        snap = store.snapshot()
        restored = MemoryStore.from_snapshot(snap)
        assert restored.working.get("phase") == "payment"
        assert restored.semantic.get("user_pref") == "gluten-free"

    def test_clear_working_clears_only_working_layer(self):
        store = MemoryStore()
        store.working.set("temp", "data")
        store.semantic.set("fact", "permanent")
        store.working.clear()
        assert store.working.get("temp") is None
        assert store.semantic.get("fact") == "permanent"


# ---------------------------------------------------------------------------
# MetaMemory — token budget enforcement (TDD additions)
# ---------------------------------------------------------------------------


class TestMetaMemoryTokenBudget:
    def test_has_budget_true_when_positive(self):
        mm = MetaMemory(token_budget_remaining=1000)
        assert mm.has_budget() is True

    def test_has_budget_false_when_zero(self):
        mm = MetaMemory(token_budget_remaining=0)
        assert mm.has_budget() is False

    def test_consume_tokens_deducts_amount(self):
        mm = MetaMemory(token_budget_remaining=1000)
        mm.consume_tokens(200)
        assert mm.token_budget_remaining == 800

    def test_consume_tokens_reaches_zero(self):
        mm = MetaMemory(token_budget_remaining=100)
        mm.consume_tokens(100)
        assert mm.token_budget_remaining == 0
        assert mm.has_budget() is False

    def test_consume_tokens_raises_when_exhausted(self):
        from aicp_runtime.memory.store import TokenBudgetExhaustedError

        mm = MetaMemory(token_budget_remaining=50)
        with pytest.raises(TokenBudgetExhaustedError):
            mm.consume_tokens(100)

    def test_token_budget_does_not_go_negative(self):
        from aicp_runtime.memory.store import TokenBudgetExhaustedError

        mm = MetaMemory(token_budget_remaining=10)
        with pytest.raises(TokenBudgetExhaustedError):
            mm.consume_tokens(20)
        # Budget should remain unchanged when the call fails
        assert mm.token_budget_remaining == 10

    def test_consume_zero_tokens_is_noop(self):
        mm = MetaMemory(token_budget_remaining=500)
        mm.consume_tokens(0)
        assert mm.token_budget_remaining == 500

    def test_consume_tokens_rejects_negative(self):
        mm = MetaMemory(token_budget_remaining=500)
        with pytest.raises(ValueError, match="tokens"):
            mm.consume_tokens(-1)

    def test_budget_rounds_with_multiple_consumes(self):
        mm = MetaMemory(token_budget_remaining=300)
        mm.consume_tokens(100)
        mm.consume_tokens(100)
        mm.consume_tokens(100)
        assert mm.token_budget_remaining == 0

    def test_set_token_budget_replaces_existing(self):
        mm = MetaMemory(token_budget_remaining=1000)
        mm.set_token_budget(5000)
        assert mm.token_budget_remaining == 5000

    def test_set_token_budget_rejects_negative(self):
        mm = MetaMemory()
        with pytest.raises(ValueError, match="budget"):
            mm.set_token_budget(-1)

    def test_to_dict_includes_token_budget(self):
        mm = MetaMemory(token_budget_remaining=999)
        d = mm.to_dict()
        assert d["token_budget_remaining"] == 999
