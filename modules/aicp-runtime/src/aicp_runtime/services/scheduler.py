import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

from aicp.errors import AicpError


class ScheduleState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduleType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    ONE_TIME = "one_time"


class MissedExecutionPolicy(str, Enum):
    SKIP = "skip"
    CATCH_UP = "catch_up"
    ALERT = "alert"


class ScheduleConfig(BaseModel):
    schedule_id: str = Field(..., pattern=r"^sched_[a-zA-Z0-9]+$")
    name: str = Field(..., min_length=1, max_length=100)
    schedule_type: ScheduleType
    capability_name: str = Field(..., pattern=r"^[a-zA-Z0-9_.]+$")
    capability_input: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    one_time_timestamp: Optional[datetime] = None
    timezone: str = "UTC"
    missed_execution_policy: MissedExecutionPolicy = MissedExecutionPolicy.SKIP
    state: ScheduleState = ScheduleState.PENDING
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_result: Optional[dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScheduleNotFoundError(AicpError):
    def __init__(self, schedule_id: str):
        self.schedule_id = schedule_id
        super().__init__(f"Schedule not found: {schedule_id}")


class InvalidCronExpressionError(AicpError):
    def __init__(self, expression: str):
        self.expression = expression
        super().__init__(f"Invalid cron expression: {expression}")


class SchedulerError(AicpError):
    pass


class CronParser:
    @classmethod
    def parse(cls, expression: str) -> dict[str, list[int]]:
        parts = expression.strip().split()
        if len(parts) != 5:
            raise InvalidCronExpressionError(expression)
        result = {}
        field_names = ["minute", "hour", "day", "month", "dow"]
        for i, name in enumerate(field_names):
            result[name] = cls._parse_field(parts[i], name)
        return result

    @classmethod
    def _parse_field(cls, value: str, field: str) -> list[int]:
        if value == "*":
            return cls._get_range(field)
        result = []
        for part in value.split(","):
            if "/" in part:
                base, step = part.split("/")
                step = int(step)
                rng = (
                    cls._get_range(field)
                    if base == "*"
                    else cls._parse_range(base, field)
                )
                result.extend(rng[::step])
            elif "-" in part:
                result.extend(cls._parse_range(part, field))
            else:
                result.append(int(part))
        return sorted(set(result))

    @classmethod
    def _get_range(cls, field: str) -> list[int]:
        ranges = {
            "minute": list(range(60)),
            "hour": list(range(24)),
            "day": list(range(1, 32)),
            "month": list(range(1, 13)),
            "dow": list(range(7)),
        }
        return ranges.get(field, [])

    @classmethod
    def _parse_range(cls, value: str, field: str) -> list[int]:
        start, end = value.split("-")
        start, end = int(start), int(end)
        rng = cls._get_range(field)
        return [x for x in rng if start <= x <= end]

    @classmethod
    def get_next_run(
        cls, expression: str, from_time: Optional[datetime] = None
    ) -> datetime:
        parsed = cls.parse(expression)
        now = from_time or datetime.now(timezone.utc)
        current = now.replace(second=0, microsecond=0)
        for _ in range(60 * 24 * 32):
            if (
                current.minute in parsed["minute"]
                and current.hour in parsed["hour"]
                and current.day in parsed["day"]
                and current.month in parsed["month"]
                and current.weekday() in parsed["dow"]
            ):
                return current
            current += timedelta(minutes=1)
        raise SchedulerError("Could not calculate next run time")


class SchedulerService:
    def __init__(self, db_path: str = ":memory:", executor: Optional[Callable] = None):
        self._db_path = db_path
        self._executor = executor
        self._schedules: dict[str, ScheduleConfig] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._init_db()

    def _init_db(self) -> None:
        if self._db_path == ":memory:":
            return
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schedules (
                schedule_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        conn.commit()
        conn.close()

    def _persist_schedule(self, schedule: ScheduleConfig) -> None:
        if self._db_path == ":memory:":
            return
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO schedules (schedule_id, data, updated_at) VALUES (?, ?, ?)",
            (
                schedule.schedule_id,
                schedule.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def _load_schedules(self) -> None:
        if self._db_path == ":memory:":
            return
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute("SELECT data FROM schedules")
        for row in cursor:
            schedule = ScheduleConfig.model_validate_json(row[0])
            self._schedules[schedule.schedule_id] = schedule
        conn.close()

    def create_schedule(self, config: ScheduleConfig) -> ScheduleConfig:
        if config.schedule_id in self._schedules:
            raise SchedulerError(f"Schedule already exists: {config.schedule_id}")
        if config.schedule_type == ScheduleType.CRON and not config.cron_expression:
            raise SchedulerError("Cron expression required for cron schedule")
        if (
            config.schedule_type == ScheduleType.INTERVAL
            and not config.interval_seconds
        ):
            raise SchedulerError("Interval seconds required for interval schedule")
        if (
            config.schedule_type == ScheduleType.ONE_TIME
            and not config.one_time_timestamp
        ):
            raise SchedulerError("One time timestamp required for one_time schedule")
        if config.schedule_type == ScheduleType.CRON and config.cron_expression:
            try:
                config.next_run = CronParser.get_next_run(config.cron_expression)
            except InvalidCronExpressionError as e:
                raise InvalidCronExpressionError(e.expression) from e
        elif config.schedule_type == ScheduleType.INTERVAL:
            if config.interval_seconds is None:
                raise SchedulerError("Interval seconds required")
            ival: int = config.interval_seconds
            config.next_run = datetime.now(timezone.utc) + timedelta(
                seconds=float(ival)
            )
        else:
            config.next_run = config.one_time_timestamp
        config.updated_at = datetime.now(timezone.utc)
        self._schedules[config.schedule_id] = config
        self._locks[config.schedule_id] = asyncio.Lock()
        self._persist_schedule(config)
        return config

    def get_schedule(self, schedule_id: str) -> ScheduleConfig:
        if schedule_id not in self._schedules:
            raise ScheduleNotFoundError(schedule_id)
        return self._schedules[schedule_id]

    def list_schedules(self) -> list[ScheduleConfig]:
        return list(self._schedules.values())

    def delete_schedule(self, schedule_id: str) -> None:
        if schedule_id not in self._schedules:
            raise ScheduleNotFoundError(schedule_id)
        del self._schedules[schedule_id]
        if schedule_id in self._locks:
            del self._locks[schedule_id]
        if self._db_path != ":memory:":
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM schedules WHERE schedule_id = ?", (schedule_id,))
            conn.commit()
            conn.close()

    def trigger_now(self, schedule_id: str) -> dict[str, Any]:
        schedule = self.get_schedule(schedule_id)
        schedule.state = ScheduleState.RUNNING
        schedule.last_run = datetime.now(timezone.utc)
        schedule.updated_at = datetime.now(timezone.utc)
        self._persist_schedule(schedule)
        if self._executor:
            result = self._executor(schedule.capability_name, schedule.capability_input)
            schedule.last_result = {
                "status": "success",
                "execution_id": result.get("execution_id"),
            }
        else:
            schedule.last_result = {"status": "skipped", "execution_id": None}
        schedule.state = ScheduleState.PENDING
        self._update_next_run(schedule)
        self._persist_schedule(schedule)
        return schedule.last_result

    def _update_next_run(self, schedule: ScheduleConfig) -> None:
        if schedule.schedule_type == ScheduleType.CRON and schedule.cron_expression:
            try:
                schedule.next_run = CronParser.get_next_run(
                    schedule.cron_expression, schedule.last_run
                )
            except SchedulerError:
                schedule.next_run = None
                schedule.state = ScheduleState.COMPLETED
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            if schedule.interval_seconds is None:
                schedule.next_run = None
            else:
                ival: int = schedule.interval_seconds
                schedule.next_run = datetime.now(timezone.utc) + timedelta(
                    seconds=float(ival)
                )
        else:
            schedule.next_run = None
            schedule.state = ScheduleState.COMPLETED
        schedule.updated_at = datetime.now(timezone.utc)

    def get_next_run(self, schedule_id: str) -> Optional[datetime]:
        return self.get_schedule(schedule_id).next_run

    def pause_schedule(self, schedule_id: str) -> ScheduleConfig:
        schedule = self.get_schedule(schedule_id)
        if schedule.state == ScheduleState.RUNNING:
            raise SchedulerError("Cannot pause a running schedule")
        schedule.state = ScheduleState.PAUSED
        schedule.enabled = False
        schedule.updated_at = datetime.now(timezone.utc)
        self._persist_schedule(schedule)
        return schedule

    def resume_schedule(self, schedule_id: str) -> ScheduleConfig:
        schedule = self.get_schedule(schedule_id)
        schedule.state = ScheduleState.PENDING
        schedule.enabled = True
        self._update_next_run(schedule)
        self._persist_schedule(schedule)
        return schedule

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_event_loop()
        self._task = self._loop.create_task(self._run_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        while self._running:
            now = datetime.now(timezone.utc)
            for schedule in self._schedules.values():
                if not schedule.enabled or schedule.state == ScheduleState.PAUSED:
                    continue
                if schedule.next_run and now >= schedule.next_run:
                    lock = self._locks.get(schedule.schedule_id)
                    if lock:
                        async with lock:
                            await self._execute_schedule(schedule)
            await asyncio.sleep(1)

    async def _execute_schedule(self, schedule: ScheduleConfig) -> None:
        if schedule.state == ScheduleState.RUNNING:
            return
        schedule.state = ScheduleState.RUNNING
        schedule.last_run = datetime.now(timezone.utc)
        schedule.updated_at = datetime.now(timezone.utc)
        self._persist_schedule(schedule)
        try:
            if self._executor:
                result = self._executor(
                    schedule.capability_name, schedule.capability_input
                )
                schedule.last_result = {
                    "status": "success",
                    "execution_id": result.get("execution_id"),
                }
            else:
                schedule.last_result = {"status": "skipped"}
        except Exception as e:
            schedule.last_result = {"status": "error", "error": str(e)}
            schedule.state = ScheduleState.FAILED
        else:
            schedule.state = ScheduleState.PENDING
        self._update_next_run(schedule)
        self._persist_schedule(schedule)
