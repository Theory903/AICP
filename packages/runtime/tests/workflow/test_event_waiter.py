"""TDD tests for EventWaiter — event-driven async flow primitive.

Tests are written RED-first against the public API contract. Implementation
lives at packages/runtime/src/aicp_runtime/workflow/events.py.

API contract
------------
EventWaiter(workflow_id: str)
    Per-workflow event bus. Events published here are scoped to one workflow.

async publish_event(name: str, payload: dict) -> None
    Broadcast an event to all waiters registered for *name*.

async wait_for_event(
    name: str,
    *,
    timeout_ms: int = 5000,
    event_filter: dict | None = None,
) -> dict
    Suspend until a matching event is published or timeout_ms elapses.
    Returns the event payload dict.
    Raises EventTimeoutError if the deadline passes.
    Raises EventFilterError if event_filter is not a dict (when provided).

EventTimeoutError(Exception)  — timeout elapsed before event arrived
EventFilterError(Exception)   — invalid filter argument
"""

from __future__ import annotations

import asyncio
import time

import pytest

from aicp_runtime.workflow.events import (
    EventFilterError,
    EventTimeoutError,
    EventWaiter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_waiter(workflow_id: str = "wf_test") -> EventWaiter:
    return EventWaiter(workflow_id=workflow_id)


# ===========================================================================
# 1. Construction
# ===========================================================================


class TestConstruction:
    def test_creates_with_workflow_id(self):
        w = EventWaiter(workflow_id="wf_abc")
        assert w.workflow_id == "wf_abc"

    def test_workflow_id_required(self):
        with pytest.raises(TypeError):
            EventWaiter()  # type: ignore[call-arg]

    def test_initial_pending_waiters_count_is_zero(self):
        w = make_waiter()
        assert w.pending_waiter_count == 0


# ===========================================================================
# 2. Basic publish / wait round-trip
# ===========================================================================


class TestBasicPublishWait:
    @pytest.mark.asyncio
    async def test_wait_receives_published_event(self):
        w = make_waiter()
        payload = {"order_id": "ord_1", "status": "placed"}

        async def publisher():
            await asyncio.sleep(0)  # yield so waiter registers first
            await w.publish_event("order.placed", payload)

        result, _ = await asyncio.gather(
            w.wait_for_event("order.placed"),
            publisher(),
        )
        assert result == payload

    @pytest.mark.asyncio
    async def test_wait_returns_exact_payload(self):
        w = make_waiter()
        data = {"x": 1, "y": [2, 3], "z": {"nested": True}}

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("data.ready", data)

        result, _ = await asyncio.gather(w.wait_for_event("data.ready"), pub())
        assert result == data

    @pytest.mark.asyncio
    async def test_publish_with_empty_payload(self):
        w = make_waiter()

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("ping", {})

        result, _ = await asyncio.gather(w.wait_for_event("ping"), pub())
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_waiters_on_same_event(self):
        """All waiters subscribed to the same event name receive the payload."""
        w = make_waiter()
        payload = {"v": 42}

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("shared.event", payload)

        r1, r2, _ = await asyncio.gather(
            w.wait_for_event("shared.event"),
            w.wait_for_event("shared.event"),
            pub(),
        )
        assert r1 == payload
        assert r2 == payload

    @pytest.mark.asyncio
    async def test_waiters_on_different_events_do_not_cross(self):
        """A waiter for event A should not be woken by event B."""
        w = make_waiter()
        b_payload = {"who": "B"}
        a_payload = {"who": "A"}

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("event.b", b_payload)
            await asyncio.sleep(0)
            await w.publish_event("event.a", a_payload)

        a_result, _ = await asyncio.gather(w.wait_for_event("event.a"), pub())
        assert a_result == a_payload


# ===========================================================================
# 3. Timeout
# ===========================================================================


class TestTimeout:
    @pytest.mark.asyncio
    async def test_raises_event_timeout_error_when_event_never_comes(self):
        w = make_waiter()
        with pytest.raises(EventTimeoutError):
            await w.wait_for_event("nonexistent.event", timeout_ms=50)

    @pytest.mark.asyncio
    async def test_timeout_error_message_contains_event_name(self):
        w = make_waiter()
        with pytest.raises(EventTimeoutError, match="order.placed"):
            await w.wait_for_event("order.placed", timeout_ms=50)

    @pytest.mark.asyncio
    async def test_timeout_error_message_contains_workflow_id(self):
        w = EventWaiter(workflow_id="wf_timeout_test")
        with pytest.raises(EventTimeoutError, match="wf_timeout_test"):
            await w.wait_for_event("some.event", timeout_ms=50)

    @pytest.mark.asyncio
    async def test_timeout_timing_is_approximate(self):
        """Timeout of 100 ms should elapse in under 500 ms wall-clock."""
        w = make_waiter()
        start = time.monotonic()
        with pytest.raises(EventTimeoutError):
            await w.wait_for_event("late.event", timeout_ms=100)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 500, f"timeout took too long: {elapsed_ms:.0f}ms"

    @pytest.mark.asyncio
    async def test_waiter_unregistered_after_timeout(self):
        """pending_waiter_count should return to 0 after timeout."""
        w = make_waiter()
        with pytest.raises(EventTimeoutError):
            await w.wait_for_event("ghost.event", timeout_ms=50)
        assert w.pending_waiter_count == 0

    @pytest.mark.asyncio
    async def test_event_arrives_just_before_timeout(self):
        """Event published within the timeout window should be received."""
        w = make_waiter()
        payload = {"just": "in_time"}

        async def late_pub():
            await asyncio.sleep(0.05)  # 50 ms
            await w.publish_event("close.call", payload)

        result, _ = await asyncio.gather(
            w.wait_for_event("close.call", timeout_ms=500),
            late_pub(),
        )
        assert result == payload


# ===========================================================================
# 4. Event filtering
# ===========================================================================


class TestEventFiltering:
    @pytest.mark.asyncio
    async def test_filter_passes_matching_payload(self):
        w = make_waiter()
        payload = {"order_id": "ord_42", "status": "confirmed"}

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("order.updated", payload)

        result, _ = await asyncio.gather(
            w.wait_for_event(
                "order.updated",
                event_filter={"order_id": "ord_42"},
            ),
            pub(),
        )
        assert result == payload

    @pytest.mark.asyncio
    async def test_filter_skips_non_matching_payload(self):
        """A publish with wrong order_id must NOT wake a filtered waiter."""
        w = make_waiter()
        correct_payload = {"order_id": "ord_99", "status": "confirmed"}

        async def pub():
            await asyncio.sleep(0)
            # Wrong id first
            await w.publish_event("order.updated", {"order_id": "ord_1", "status": "confirmed"})
            await asyncio.sleep(0)
            # Correct id second
            await w.publish_event("order.updated", correct_payload)

        result, _ = await asyncio.gather(
            w.wait_for_event(
                "order.updated",
                event_filter={"order_id": "ord_99"},
                timeout_ms=1000,
            ),
            pub(),
        )
        assert result == correct_payload

    @pytest.mark.asyncio
    async def test_filter_requires_all_keys_to_match(self):
        """Partial-match filter: event must contain ALL filter keys/values."""
        w = make_waiter()
        payload = {"order_id": "ord_1", "status": "placed", "amount": 100}

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("order.event", payload)

        result, _ = await asyncio.gather(
            w.wait_for_event(
                "order.event",
                event_filter={"order_id": "ord_1", "status": "placed"},
            ),
            pub(),
        )
        assert result == payload

    @pytest.mark.asyncio
    async def test_filter_raises_event_filter_error_on_non_dict(self):
        w = make_waiter()
        with pytest.raises(EventFilterError):
            await w.wait_for_event("x.event", event_filter="bad")  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_none_filter_accepts_all_events(self):
        """No filter (None) means accept any payload."""
        w = make_waiter()
        payload = {"random": "data"}

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("any.event", payload)

        result, _ = await asyncio.gather(
            w.wait_for_event("any.event", event_filter=None),
            pub(),
        )
        assert result == payload

    @pytest.mark.asyncio
    async def test_filtered_waiter_times_out_if_matching_event_never_arrives(self):
        """If no event ever matches the filter, EventTimeoutError is raised."""
        w = make_waiter()

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("order.updated", {"order_id": "ord_wrong"})

        with pytest.raises(EventTimeoutError):
            await asyncio.gather(
                w.wait_for_event(
                    "order.updated",
                    event_filter={"order_id": "ord_correct"},
                    timeout_ms=150,
                ),
                pub(),
            )


# ===========================================================================
# 5. pending_waiter_count
# ===========================================================================


class TestPendingWaiterCount:
    @pytest.mark.asyncio
    async def test_count_increments_while_waiting(self):
        w = make_waiter()
        counts: list[int] = []

        async def waiter():
            counts.append(w.pending_waiter_count)  # should be 1 once task starts
            await w.wait_for_event("x.event", timeout_ms=500)

        async def pub():
            await asyncio.sleep(0)
            counts.append(w.pending_waiter_count)  # should be 1
            await w.publish_event("x.event", {})

        await asyncio.gather(waiter(), pub())
        assert 1 in counts

    @pytest.mark.asyncio
    async def test_count_decrements_after_event_received(self):
        w = make_waiter()

        async def pub():
            await asyncio.sleep(0)
            await w.publish_event("done.event", {"ok": True})

        await asyncio.gather(w.wait_for_event("done.event"), pub())
        assert w.pending_waiter_count == 0

    @pytest.mark.asyncio
    async def test_count_with_multiple_concurrent_waiters(self):
        w = make_waiter()
        saw_two = asyncio.Event()

        async def pub():
            await asyncio.sleep(0)
            if w.pending_waiter_count == 2:
                saw_two.set()
            await w.publish_event("multi.event", {})
            await w.publish_event("multi.event", {})

        await asyncio.gather(
            w.wait_for_event("multi.event"),
            w.wait_for_event("multi.event"),
            pub(),
        )
        # After everything resolves, count must be 0
        assert w.pending_waiter_count == 0


# ===========================================================================
# 6. Workflow ID scoping
# ===========================================================================


class TestWorkflowScoping:
    @pytest.mark.asyncio
    async def test_events_in_different_waiters_do_not_leak(self):
        """Two EventWaiter instances with different workflow IDs are independent."""
        w1 = EventWaiter(workflow_id="wf_1")
        w2 = EventWaiter(workflow_id="wf_2")

        async def pub_w1():
            await asyncio.sleep(0)
            await w1.publish_event("shared.name", {"from": "w1"})

        # w2 waiter should time out because we only published on w1
        with pytest.raises(EventTimeoutError):
            await asyncio.gather(
                w2.wait_for_event("shared.name", timeout_ms=100),
                pub_w1(),
            )

    @pytest.mark.asyncio
    async def test_same_event_name_different_workflow_ids_isolated(self):
        w1 = EventWaiter(workflow_id="wf_A")
        w2 = EventWaiter(workflow_id="wf_B")
        p1 = {"workflow": "A"}
        p2 = {"workflow": "B"}

        async def pub_both():
            await asyncio.sleep(0)
            await w1.publish_event("tick", p1)
            await w2.publish_event("tick", p2)

        r1, r2, _ = await asyncio.gather(
            w1.wait_for_event("tick"),
            w2.wait_for_event("tick"),
            pub_both(),
        )
        assert r1 == p1
        assert r2 == p2


# ===========================================================================
# 7. Edge cases
# ===========================================================================


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_publish_with_no_waiters_does_not_raise(self):
        """Publishing when nobody is listening should be a no-op."""
        w = make_waiter()
        # Should not raise
        await w.publish_event("orphan.event", {"data": 1})

    @pytest.mark.asyncio
    async def test_publish_after_waiter_timed_out_does_not_raise(self):
        w = make_waiter()
        with pytest.raises(EventTimeoutError):
            await w.wait_for_event("late.event", timeout_ms=30)
        # Publishing after timeout should not raise
        await w.publish_event("late.event", {"too": "late"})

    @pytest.mark.asyncio
    async def test_zero_timeout_raises_immediately_if_no_event(self):
        """timeout_ms=0 should raise EventTimeoutError immediately."""
        w = make_waiter()
        with pytest.raises(EventTimeoutError):
            await w.wait_for_event("instant.event", timeout_ms=0)

    @pytest.mark.asyncio
    async def test_sequential_waits_on_same_name(self):
        """Two sequential (not concurrent) waits should both succeed."""
        w = make_waiter()
        p1 = {"seq": 1}
        p2 = {"seq": 2}

        async def pub1():
            await asyncio.sleep(0)
            await w.publish_event("seq.event", p1)

        async def pub2():
            await asyncio.sleep(0)
            await w.publish_event("seq.event", p2)

        r1, _ = await asyncio.gather(w.wait_for_event("seq.event"), pub1())
        r2, _ = await asyncio.gather(w.wait_for_event("seq.event"), pub2())

        assert r1 == p1
        assert r2 == p2
