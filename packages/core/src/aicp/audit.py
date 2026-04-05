"""
Audit and Replay Module
Module 18 - Full audit trail, distributed tracing, live execution feed
"""

from enum import Enum
from typing import Optional, Any, Callable
from pydantic import BaseModel, Field
import json
import uuid
from datetime import datetime
from collections import deque
from dataclasses import dataclass, asdict


class AuditEventType(str, Enum):
    """Types of audit events"""
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STEP = "workflow_step"
    WORKFLOW_COMPLETED = "workflow_completed"
    POLICY_EVALUATED = "policy_evaluated"
    SESSION_CREATED = "session_created"
    SESSION_RESUMED = "session_resumed"
    CAPABILITY_INVOKED = "capability_invoked"
    ERROR_OCCURRED = "error_occurred"


class TraceLevel(str, Enum):
    """Tracing level"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class TraceSpan:
    """Distributed tracing span"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: dict[str, Any] = None
    logs: list[dict[str, Any]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.logs is None:
            self.logs = []
    
    def finish(self, end_time: float = None):
        self.end_time = end_time or datetime.now().timestamp()
    
    def add_tag(self, key: str, value: Any):
        self.tags[key] = value
    
    def add_log(self, message: str, payload: dict[str, Any] = None):
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "payload": payload or {}
        })
    
    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": int((self.end_time - self.start_time) * 1000) if self.end_time else None,
            "tags": self.tags,
            "logs": self.logs
        }


class TraceContext:
    """Distributed tracing context"""
    
    def __init__(self):
        self._traces: dict[str, list[TraceSpan]] = {}
        self._current_span: Optional[TraceSpan] = None
    
    def start_trace(self, operation_name: str, trace_id: str = None, parent_span_id: str = None) -> TraceSpan:
        """Start a new trace span"""
        trace_id = trace_id or str(uuid.uuid4())
        span_id = f"span_{uuid.uuid4().hex[:8]}"
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=datetime.now().timestamp()
        )
        
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        self._traces[trace_id].append(span)
        self._current_span = span
        
        return span
    
    def end_trace(self, span: TraceSpan):
        """End a trace span"""
        span.finish()
        self._current_span = None
    
    def get_trace(self, trace_id: str) -> list[TraceSpan]:
        """Get all spans for a trace"""
        return self._traces.get(trace_id, [])
    
    def get_current_span(self) -> Optional[TraceSpan]:
        """Get current active span"""
        return self._current_span


class AuditEntry(BaseModel):
    """Audit log entry"""
    id: str = Field(default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}")
    event_type: AuditEventType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    actor: str
    actor_type: str = "agent"  # agent, human, system
    session_id: Optional[str] = None
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    capability_name: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AuditLog:
    """
    Append-only audit log with replay capability
    Module 18 - Full audit trail and replay
    """

    def __init__(self, max_entries: int = 100000):
        self._max_entries = max_entries
        self._entries: deque[AuditEntry] = deque(maxlen=max_entries)
        self._trace_context = TraceContext()
        self._live_subscribers: list[Callable] = []
        
        # Index for fast queries
        self._by_session: dict[str, list[str]] = {}  # session_id -> [entry_ids]
        self._by_workflow: dict[str, list[str]] = {}  # workflow_id -> [entry_ids]
        self._by_trace: dict[str, list[str]] = {}  # trace_id -> [entry_ids]

    def log(self, entry: AuditEntry):
        """Add entry to audit log"""
        self._entries.append(entry)
        
        # Update indexes
        if entry.session_id:
            if entry.session_id not in self._by_session:
                self._by_session[entry.session_id] = []
            self._by_session[entry.session_id].append(entry.id)
        
        if entry.workflow_id:
            if entry.workflow_id not in self._by_workflow:
                self._by_workflow[entry.workflow_id] = []
            self._by_workflow[entry.workflow_id].append(entry.id)
        
        if entry.trace_id:
            if entry.trace_id not in self._by_trace:
                self._by_trace[entry.trace_id] = []
            self._by_trace[entry.trace_id].append(entry.id)
        
        # Notify live subscribers
        for subscriber in self._live_subscribers:
            try:
                subscriber(entry)
            except Exception:
                pass

    def get_entries(
        self,
        session_id: str = None,
        workflow_id: str = None,
        trace_id: str = None,
        event_type: AuditEventType = None,
        limit: int = 100,
        since: datetime = None
    ) -> list[AuditEntry]:
        """Query audit entries with filters"""
        entries = list(self._entries)
        
        if session_id:
            entry_ids = self._by_session.get(session_id, [])
            entries = [e for e in entries if e.id in entry_ids]
        
        if workflow_id:
            entry_ids = self._by_workflow.get(workflow_id, [])
            entries = [e for e in entries if e.id in entry_ids]
        
        if trace_id:
            entry_ids = self._by_trace.get(trace_id, [])
            entries = [e for e in entries if e.id in entry_ids]
        
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        
        if since:
            since_iso = since.isoformat()
            entries = [e for e in entries if e.timestamp >= since_iso]
        
        # Sort by timestamp descending (newest first)
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        
        return entries[:limit]

    def get_execution_timeline(self, execution_id: str) -> list[AuditEntry]:
        """Get timeline of an execution for replay"""
        return self.get_entries(execution_id=execution_id, limit=1000)

    def get_workflow_timeline(self, workflow_id: str) -> list[AuditEntry]:
        """Get full timeline of a workflow"""
        return self.get_entries(workflow_id=workflow_id, limit=10000)

    def subscribe(self, callback: Callable):
        """Subscribe to live audit events"""
        self._live_subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Unsubscribe from live audit events"""
        if callback in self._live_subscribers:
            self._live_subscribers.remove(callback)

    def export_jsonl(self, path: str) -> int:
        """Export audit log to JSONL file"""
        count = 0
        with open(path, 'w') as f:
            for entry in self._entries:
                f.write(json.dumps(entry.model_dump()) + '\n')
                count += 1
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get audit log statistics"""
        return {
            "total_entries": len(self._entries),
            "max_entries": self._max_entries,
            "sessions_tracked": len(self._by_session),
            "workflows_tracked": len(self._by_workflow),
            "traces_tracked": len(self._by_trace),
            "event_types": self._count_by_event_type()
        }

    def _count_by_event_type(self) -> dict[str, int]:
        counts = {}
        for entry in self._entries:
            event = entry.event_type
            counts[event] = counts.get(event, 0) + 1
        return counts


class LiveExecutionFeed:
    """
    Live execution feed for real-time monitoring
    Module 18 - Live execution feed
    """

    def __init__(self, max_items: int = 1000):
        self._max_items = max_items
        self._feed: deque[dict[str, Any]] = deque(maxlen=max_items)
        self._subscribers: list[Callable] = []

    def publish(self, execution_data: dict[str, Any]):
        """Publish execution to live feed"""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            **execution_data
        }
        self._feed.append(data)
        
        # Notify subscribers
        for sub in self._subscribers:
            try:
                sub(data)
            except Exception:
                pass

    def subscribe(self, callback: Callable):
        """Subscribe to live feed"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Unsubscribe from live feed"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def get_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent executions"""
        items = list(self._feed)
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items[:limit]


class ReplayDebugger:
    """
    Replay debugger for execution analysis
    Module 18 - Replay and debugging
    """

    def __init__(self, audit_log: AuditLog):
        self._audit_log = audit_log
        self._breakpoints: dict[str, dict] = {}

    def set_breakpoint(self, event_type: AuditEventType, condition: dict[str, Any] = None):
        """Set a breakpoint for debugging"""
        bp_id = f"bp_{uuid.uuid4().hex[:8]}"
        self._breakpoints[bp_id] = {
            "event_type": event_type,
            "condition": condition,
            "enabled": True
        }
        return bp_id

    def remove_breakpoint(self, bp_id: str):
        """Remove a breakpoint"""
        if bp_id in self._breakpoints:
            del self._breakpoints[bp_id]

    def get_session_events(self, session_id: str, limit: int = 100) -> list[AuditEntry]:
        """Get all events for a session"""
        return self._audit_log.get_entries(session_id=session_id, limit=limit)

    def replay_session(self, session_id: str, event_filter: AuditEventType = None) -> list[AuditEntry]:
        """Replay a session's execution"""
        events = self._audit_log.get_entries(
            session_id=session_id,
            event_type=event_filter,
            limit=10000
        )
        # Return in chronological order for replay
        events.sort(key=lambda e: e.timestamp)
        return events

    def analyze_failure(self, execution_id: str) -> dict[str, Any]:
        """Analyze execution failure"""
        entries = self._audit_log.get_entries(execution_id=execution_id, limit=100)
        
        errors = [e for e in entries if e.event_type == AuditEventType.ERROR_OCCURRED]
        failed = [e for e in entries if e.event_type == AuditEventType.EXECUTION_FAILED]
        
        return {
            "execution_id": execution_id,
            "total_events": len(entries),
            "errors": [e.model_dump() for e in errors],
            "failed_events": [e.model_dump() for e in failed],
            "timeline": [e.model_dump() for e in entries]
        }


# Helper functions

def create_audit_entry(
    event_type: AuditEventType,
    actor: str,
    capability_name: str = None,
    session_id: str = None,
    workflow_id: str = None,
    execution_id: str = None,
    trace_id: str = None,
    payload: dict[str, Any] = None,
    result: dict[str, Any] = None,
    error: str = None
) -> AuditEntry:
    """Helper to create audit entry"""
    return AuditEntry(
        event_type=event_type,
        actor=actor,
        capability_name=capability_name,
        session_id=session_id,
        workflow_id=workflow_id,
        execution_id=execution_id,
        trace_id=trace_id,
        payload=payload or {},
        result=result,
        error=error
    )


# Global instances
_audit_log = None
_live_feed = None

def get_audit_log() -> AuditLog:
    """Get global audit log instance"""
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log

def get_live_feed() -> LiveExecutionFeed:
    """Get global live execution feed"""
    global _live_feed
    if _live_feed is None:
        _live_feed = LiveExecutionFeed()
    return _live_feed