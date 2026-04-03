"""AICP EventWaiter — per-workflow in-memory async event bus.

Design
------
* One ``EventWaiter`` instance per workflow run (scoped by ``workflow_id``).
* ``publish_event`` wakes all coroutines currently waiting on that event name,
  optionally filtered by key-value matching against the payload.
* ``wait_for_event`` suspends until a matching event arrives or the deadline
  passes, then raises ``EventTimeoutError``.
* Thread-safety: designed for single-threaded ``asyncio`` event loops only.
  No locking is used; all operations are non-blocking except the ``asyncio.wait``
  inside ``wait_for_event``.
* Pending waiters are tracked in ``_waiters``:
  ``dict[event_name, list[_Waiter]]``
  Each ``_Waiter`` holds an ``asyncio.Event`` and the optional filter dict.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "EventFilterError",
    "EventTimeoutError",
    "EventWaiter",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class EventTimeoutError(Exception):
    """Raised when wait_for_event does not receive a matching event in time."""


class EventFilterError(Exception):
    """Raised when event_filter is not a dict."""


# ---------------------------------------------------------------------------
# Internal waiter slot
# ---------------------------------------------------------------------------


@dataclass
class _Waiter:
    """A single pending ``wait_for_event`` call."""

    event: asyncio.Event = field(default_factory=asyncio.Event)
    payload: dict[str, Any] | None = field(default=None)
    filter: dict[str, Any] | None = field(default=None)

    def matches(self, payload: dict[str, Any]) -> bool:
        """Return True if *payload* satisfies this waiter's filter."""
        if self.filter is None:
            return True
        return all(payload.get(k) == v for k, v in self.filter.items())

    def deliver(self, payload: dict[str, Any]) -> None:
        """Store payload and set the event so the waiter wakes up."""
        self.payload = payload
        self.event.set()


# ---------------------------------------------------------------------------
# EventWaiter
# ---------------------------------------------------------------------------


class EventWaiter:
    """Per-workflow in-memory async event bus.

    Parameters
    ----------
    workflow_id:
        Unique identifier for the workflow instance. Used only for
        error messages and scoping (two instances are independent).
    """

    def __init__(self, *, workflow_id: str) -> None:
        self._workflow_id = workflow_id
        # event_name → list of pending waiters
        self._waiters: dict[str, list[_Waiter]] = {}

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def pending_waiter_count(self) -> int:
        """Total number of coroutines currently waiting for an event."""
        return sum(len(ws) for ws in self._waiters.values())

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def publish_event(self, name: str, payload: dict[str, Any]) -> None:
        """Broadcast *payload* to all waiters registered for *name*.

        Waiters whose filter does not match are skipped and remain
        registered until their timeout fires.

        Parameters
        ----------
        name:
            Event name (e.g. ``"order.placed"``).
        payload:
            Arbitrary dict delivered to matching waiters.
        """
        waiters = self._waiters.get(name)
        if not waiters:
            return

        # Iterate over a snapshot so we can safely remove entries
        for waiter in list(waiters):
            if waiter.matches(payload):
                waiter.deliver(payload)
                # Remove it — once delivered, the waiter is done
                try:
                    waiters.remove(waiter)
                except ValueError:
                    pass  # already removed (race guard)

        # Clean up empty lists
        if name in self._waiters and not self._waiters[name]:
            del self._waiters[name]

        # Yield control so woken coroutines can run
        await asyncio.sleep(0)

    async def wait_for_event(
        self,
        name: str,
        *,
        timeout_ms: int = 5000,
        event_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Suspend until a matching event is published or the timeout elapses.

        Parameters
        ----------
        name:
            Event name to listen for.
        timeout_ms:
            Maximum time to wait in milliseconds. Defaults to 5 000 ms.
        event_filter:
            Optional key-value dict; the event payload must contain all
            supplied keys with the specified values. ``None`` accepts any
            payload.

        Returns
        -------
        dict
            The event payload.

        Raises
        ------
        EventFilterError
            If *event_filter* is provided but is not a ``dict``.
        EventTimeoutError
            If no matching event arrives within *timeout_ms*.
        """
        if event_filter is not None and not isinstance(event_filter, dict):
            raise EventFilterError(
                f"event_filter must be a dict or None, got {type(event_filter).__name__!r}"
            )

        waiter = _Waiter(filter=event_filter)

        # Register
        self._waiters.setdefault(name, []).append(waiter)

        timeout_s = timeout_ms / 1000.0
        try:
            await asyncio.wait_for(waiter.event.wait(), timeout=timeout_s)
        except asyncio.TimeoutError:
            # Clean up registration
            self._remove_waiter(name, waiter)
            raise EventTimeoutError(
                f"Timed out after {timeout_ms} ms waiting for event '{name}' "
                f"in workflow '{self._workflow_id}'"
            )

        # Waiter was delivered — already removed from list in publish_event
        # but guard against edge cases:
        self._remove_waiter(name, waiter)

        assert waiter.payload is not None, "waiter woke without payload"
        return waiter.payload

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_waiter(self, name: str, waiter: _Waiter) -> None:
        """Remove *waiter* from the registry if still present."""
        bucket = self._waiters.get(name)
        if not bucket:
            return
        try:
            bucket.remove(waiter)
        except ValueError:
            pass
        if not bucket:
            del self._waiters[name]
