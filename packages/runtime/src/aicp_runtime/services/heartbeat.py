import asyncio
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class HeartbeatError(AicpError):
    pass


class HeartbeatTaskType(str, Enum):
    HEALTH_CHECK = "health_check"
    CACHE_WARMING = "cache_warming"
    SESSION_CLEANUP = "session_cleanup"
    SCHEDULE_TRIGGER = "schedule_trigger"
    METRICS_COLLECTION = "metrics_collection"


@dataclass
class HeartbeatTask:
    name: str
    interval_seconds: int
    task_type: HeartbeatTaskType
    enabled: bool = True
    failure_threshold: int = 3
    _callback: Optional[Callable] = field(default=None, repr=False)
    _last_run: Optional[datetime] = field(default=None, repr=False)


@dataclass
class TaskResult:
    task_name: str
    executed_at: datetime
    duration_ms: int
    success: bool
    error: Optional[str] = None


@dataclass
class LeaderInfo:
    instance_id: str
    last_heartbeat: datetime
    is_active: bool


class HeartbeatConfig(BaseModel):
    task_name: str = Field(..., min_length=1)
    interval_seconds: int = Field(..., ge=30, le=3600)
    enabled: bool = True
    failure_threshold: int = Field(default=3, ge=1, le=10)
    instance_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])


class HeartbeatService:
    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._tasks: dict[str, HeartbeatTask] = {}
        self._running = False
        self._task_handle: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._instance_id = uuid.uuid4().hex[:8]
        self._is_leader = False
        self._lock = threading.Lock()
        self._last_heartbeat: Optional[datetime] = None
        self._failure_count = 0
        self._init_db()

    def _init_db(self) -> None:
        if self._db_path == ":memory:":
            return
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS heartbeat (
                instance_id TEXT PRIMARY KEY,
                last_heartbeat TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )"""
        )
        conn.commit()
        conn.close()

    def _acquire_leadership(self) -> bool:
        if self._db_path == ":memory:":
            self._is_leader = True
            return True
        conn = None
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT last_heartbeat, is_active FROM heartbeat WHERE instance_id = ?",
                (self._instance_id,),
            )
            row = cursor.fetchone()
            now = datetime.now(timezone.utc).isoformat()
            if row is None:
                conn.execute(
                    "INSERT INTO heartbeat (instance_id, last_heartbeat, is_active) VALUES (?, ?, 1)",
                    (self._instance_id, now),
                )
                conn.commit()
                self._is_leader = True
                return True
            last_heartbeat_str, is_active = row
            last_heartbeat = datetime.fromisoformat(last_heartbeat_str.replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - last_heartbeat).total_seconds()
            if elapsed > 15 and is_active:
                conn.execute(
                    "UPDATE heartbeat SET last_heartbeat = ?, is_active = 1 WHERE instance_id = ?",
                    (now, self._instance_id),
                )
                conn.commit()
                self._is_leader = True
                return True
            elif not is_active:
                conn.execute(
                    "UPDATE heartbeat SET last_heartbeat = ?, is_active = 1 WHERE instance_id = ?",
                    (now, self._instance_id),
                )
                conn.commit()
                self._is_leader = True
                return True
            self._is_leader = False
            return False
        except Exception:
            self._is_leader = False
            return False
        finally:
            if conn:
                conn.close()

    def _release_leadership(self) -> None:
        if self._db_path == ":memory:" or not self._is_leader:
            return
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "UPDATE heartbeat SET is_active = 0 WHERE instance_id = ?",
                (self._instance_id,),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def register_task(
        self,
        name: str,
        interval_seconds: int,
        task_type: HeartbeatTaskType,
        callback: Optional[Callable] = None,
    ) -> HeartbeatTask:
        task = HeartbeatTask(
            name=name,
            interval_seconds=interval_seconds,
            task_type=task_type,
            _callback=callback,
        )
        self._tasks[name] = task
        return task

    def unregister_task(self, name: str) -> None:
        if name in self._tasks:
            del self._tasks[name]

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_event_loop()
        self._task_handle = self._loop.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        self._release_leadership()
        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        while self._running:
            self._acquire_leadership()
            self._last_heartbeat = datetime.now(timezone.utc)
            if self._is_leader:
                await self._execute_tasks()
            await asyncio.sleep(5)

    async def _execute_tasks(self) -> None:
        now = datetime.now(timezone.utc)
        for task in self._tasks.values():
            if not task.enabled:
                continue
            last_run = getattr(task, "_last_run", None)
            if last_run is None:
                task._last_run = now
                await self._run_task(task)
            else:
                elapsed = (now - last_run).total_seconds()
                if elapsed >= task.interval_seconds:
                    task._last_run = now
                    await self._run_task(task)

    async def _run_task(self, task: HeartbeatTask) -> TaskResult:
        start = time.perf_counter()
        try:
            if task._callback:
                await task._callback()
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._failure_count = 0
            return TaskResult(
                task_name=task.name,
                executed_at=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                success=True,
            )
        except Exception as e:
            self._failure_count += 1
            duration_ms = int((time.perf_counter() - start) * 1000)
            if self._failure_count >= task.failure_threshold:
                self._release_leadership()
                self._is_leader = False
            return TaskResult(
                task_name=task.name,
                executed_at=datetime.now(timezone.utc),
                duration_ms=duration_ms,
                success=False,
                error=str(e),
            )

    def is_leader(self) -> bool:
        return self._is_leader

    def get_leader_id(self) -> Optional[str]:
        if self._db_path == ":memory:":
            return self._instance_id if self._is_leader else None
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT instance_id FROM heartbeat WHERE is_active = 1 ORDER BY last_heartbeat DESC LIMIT 1"
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def get_instance_id(self) -> str:
        return self._instance_id

    def get_tasks(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "interval_seconds": t.interval_seconds,
                "task_type": t.task_type.value,
                "enabled": t.enabled,
            }
            for t in self._tasks.values()
        ]

    def get_last_heartbeat(self) -> Optional[datetime]:
        return self._last_heartbeat
