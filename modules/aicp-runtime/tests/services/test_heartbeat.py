import tempfile

import pytest
from aicp_runtime.services.heartbeat import (
    HeartbeatConfig,
    HeartbeatService,
    HeartbeatTaskType,
    TaskResult,
)


class TestHeartbeatConfig:
    def test_default_config(self):
        config = HeartbeatConfig(task_name="test-task", interval_seconds=60)
        assert config.task_name == "test-task"
        assert config.interval_seconds == 60
        assert config.enabled is True
        assert config.failure_threshold == 3

    def test_custom_config(self):
        config = HeartbeatConfig(
            task_name="custom-task",
            interval_seconds=120,
            enabled=False,
            failure_threshold=5,
        )
        assert config.task_name == "custom-task"
        assert config.interval_seconds == 120
        assert config.enabled is False
        assert config.failure_threshold == 5

    def test_interval_bounds(self):
        with pytest.raises(ValueError):
            HeartbeatConfig(task_name="test", interval_seconds=10)
        with pytest.raises(ValueError):
            HeartbeatConfig(task_name="test", interval_seconds=4000)


class TestHeartbeatTaskTypes:
    def test_task_type_values(self):
        assert HeartbeatTaskType.HEALTH_CHECK == "health_check"
        assert HeartbeatTaskType.CACHE_WARMING == "cache_warming"
        assert HeartbeatTaskType.SESSION_CLEANUP == "session_cleanup"
        assert HeartbeatTaskType.SCHEDULE_TRIGGER == "schedule_trigger"
        assert HeartbeatTaskType.METRICS_COLLECTION == "metrics_collection"


class TestTaskResult:
    def test_task_result_creation(self):
        from datetime import datetime, timezone

        result = TaskResult(
            task_name="test",
            executed_at=datetime.now(timezone.utc),
            duration_ms=100,
            success=True,
        )
        assert result.task_name == "test"
        assert result.success is True
        assert result.error is None

    def test_task_result_with_error(self):
        from datetime import datetime, timezone

        result = TaskResult(
            task_name="test",
            executed_at=datetime.now(timezone.utc),
            duration_ms=100,
            success=False,
            error="Connection timeout",
        )
        assert result.success is False
        assert result.error == "Connection timeout"


class TestHeartbeatServiceInitialization:
    def test_in_memory_db(self):
        service = HeartbeatService(":memory:")
        assert service._db_path == ":memory:"
        assert service.is_leader() is False

    def test_file_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        service = HeartbeatService(path)
        assert service._db_path == path
        assert service.is_leader() is False

    def test_instance_id_generated(self):
        service1 = HeartbeatService(":memory:")
        service2 = HeartbeatService(":memory:")
        assert len(service1.get_instance_id()) == 8
        assert service1.get_instance_id() != service2.get_instance_id()


class TestHeartbeatTaskRegistration:
    def test_register_task(self):
        service = HeartbeatService(":memory:")
        task = service.register_task(
            "cleanup",
            interval_seconds=60,
            task_type=HeartbeatTaskType.SESSION_CLEANUP,
        )
        assert task.name == "cleanup"
        assert task.interval_seconds == 60
        assert task.task_type == HeartbeatTaskType.SESSION_CLEANUP

    def test_register_multiple_tasks(self):
        service = HeartbeatService(":memory:")
        service.register_task("task1", 60, HeartbeatTaskType.HEALTH_CHECK)
        service.register_task("task2", 120, HeartbeatTaskType.CACHE_WARMING)
        tasks = service.get_tasks()
        assert len(tasks) == 2
        assert any(t["name"] == "task1" for t in tasks)
        assert any(t["name"] == "task2" for t in tasks)

    def test_unregister_task(self):
        service = HeartbeatService(":memory:")
        service.register_task("to-remove", 60, HeartbeatTaskType.HEALTH_CHECK)
        service.unregister_task("to-remove")
        tasks = service.get_tasks()
        assert len(tasks) == 0


@pytest.mark.asyncio
class TestHeartbeatServiceLifecycle:
    async def test_start_and_stop(self):
        service = HeartbeatService(":memory:")
        await service.start()
        assert service._running is True
        assert service._task_handle is not None
        await service.stop()
        assert service._running is False

    async def test_start_is_idempotent(self):
        service = HeartbeatService(":memory:")
        await service.start()
        handle1 = service._task_handle
        await service.start()
        handle2 = service._task_handle
        assert handle1 is handle2
        await service.stop()

    async def test_stop_is_idempotent(self):
        service = HeartbeatService(":memory:")
        await service.start()
        await service.stop()
        await service.stop()
        assert service._running is False


@pytest.mark.asyncio
class TestHeartbeatTaskExecution:
    async def test_task_execution(self):
        service = HeartbeatService(":memory:")
        executed = []

        async def callback():
            executed.append(1)

        service.register_task("test", 30, HeartbeatTaskType.HEALTH_CHECK, callback)
        await service._run_task(service._tasks["test"])
        assert len(executed) == 1

    async def test_task_failure_tracking(self):
        service = HeartbeatService(":memory:")

        async def failing_callback():
            raise RuntimeError("Test error")

        service.register_task("fail", 30, HeartbeatTaskType.HEALTH_CHECK, failing_callback)
        result = await service._run_task(service._tasks["fail"])
        assert result.success is False
        assert result.error is not None
        assert "Test error" in result.error


class TestHeartbeatLeadership:
    def test_in_memory_is_always_leader(self):
        service = HeartbeatService(":memory:")
        service._acquire_leadership()
        assert service.is_leader() is True

    def test_get_leader_id_in_memory(self):
        service = HeartbeatService(":memory:")
        service._acquire_leadership()
        assert service.get_leader_id() == service.get_instance_id()

    def test_no_leader_when_not_acquired(self):
        service = HeartbeatService(":memory:")
        service._is_leader = False
        assert service.get_leader_id() is None


class TestHeartbeatState:
    def test_get_tasks_empty(self):
        service = HeartbeatService(":memory:")
        tasks = service.get_tasks()
        assert tasks == []

    def test_get_tasks_returns_task_info(self):
        service = HeartbeatService(":memory:")
        service.register_task("t1", 60, HeartbeatTaskType.HEALTH_CHECK)
        tasks = service.get_tasks()
        assert len(tasks) == 1
        assert tasks[0]["name"] == "t1"
        assert tasks[0]["interval_seconds"] == 60
        assert tasks[0]["task_type"] == "health_check"
        assert tasks[0]["enabled"] is True

    def test_get_last_heartbeat_initially_none(self):
        service = HeartbeatService(":memory:")
        assert service.get_last_heartbeat() is None

    def test_is_leader_initially_false(self):
        service = HeartbeatService(":memory:")
        assert service.is_leader() is False


@pytest.mark.asyncio
class TestHeartbeatFailureHandling:
    async def test_failure_count_increments(self):
        service = HeartbeatService(":memory:")
        service._acquire_leadership()

        async def fail():
            raise Exception("Fail")

        service.register_task("f", 30, HeartbeatTaskType.HEALTH_CHECK, fail)
        await service._run_task(service._tasks["f"])
        assert service._failure_count == 1
        await service._run_task(service._tasks["f"])
        assert service._failure_count == 2

    async def test_releases_leadership_after_threshold(self):
        service = HeartbeatService(":memory:")
        service._acquire_leadership()
        assert service.is_leader() is True

        async def fail():
            raise Exception("Fail")

        service.register_task("f", 30, HeartbeatTaskType.HEALTH_CHECK, fail)
        service._tasks["f"].failure_threshold = 2
        service._failure_count = 1
        await service._run_task(service._tasks["f"])
        assert service._failure_count == 2
        assert service.is_leader() is False
