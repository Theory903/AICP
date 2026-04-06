"""Tests for scheduler service."""

import pytest
from datetime import datetime, timedelta, timezone

from aicp_runtime.services.scheduler import (
    CronParser,
    InvalidCronExpressionError,
    MissedExecutionPolicy,
    ScheduleConfig,
    ScheduleNotFoundError,
    ScheduleState,
    ScheduleType,
    SchedulerService,
    SchedulerError,
)


class TestCronParser:
    def test_parse_every_minute(self):
        result = CronParser.parse("* * * * *")
        assert result["minute"] == list(range(60))
        assert result["hour"] == list(range(24))

    def test_parse_specific_minute(self):
        result = CronParser.parse("30 * * * *")
        assert result["minute"] == [30]

    def test_parse_range(self):
        result = CronParser.parse("0 9-17 * * *")
        assert result["hour"] == list(range(9, 18))

    def test_parse_step(self):
        result = CronParser.parse("*/15 * * * *")
        assert result["minute"] == [0, 15, 30, 45]

    def test_parse_list(self):
        result = CronParser.parse("0,30 * * * *")
        assert result["minute"] == [0, 30]

    def test_invalid_cron(self):
        with pytest.raises(InvalidCronExpressionError):
            CronParser.parse("not-a-cron")

    def test_get_next_run(self):
        next_run = CronParser.get_next_run("0 0 * * *")
        assert next_run is not None
        assert next_run.hour == 0
        assert next_run.minute == 0


class TestSchedulerService:
    def test_create_cron_schedule(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test1",
            name="Test Cron",
            schedule_type=ScheduleType.CRON,
            capability_name="test.capability",
            cron_expression="0 0 * * *",
        )
        result = svc.create_schedule(config)
        assert result.schedule_id == "sched_test1"
        assert result.state == ScheduleState.PENDING
        assert result.next_run is not None

    def test_create_interval_schedule(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test2",
            name="Test Interval",
            schedule_type=ScheduleType.INTERVAL,
            capability_name="test.capability",
            interval_seconds=3600,
        )
        result = svc.create_schedule(config)
        assert result.schedule_id == "sched_test2"
        assert result.next_run is not None

    def test_create_one_time_schedule(self):
        svc = SchedulerService()
        future = datetime.now(timezone.utc) + timedelta(days=1)
        config = ScheduleConfig(
            schedule_id="sched_test3",
            name="Test One-Time",
            schedule_type=ScheduleType.ONE_TIME,
            capability_name="test.capability",
            one_time_timestamp=future,
        )
        result = svc.create_schedule(config)
        assert result.schedule_id == "sched_test3"
        assert result.next_run == future

    def test_get_schedule(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test4",
            name="Test",
            schedule_type=ScheduleType.CRON,
            capability_name="test.cap",
            cron_expression="0 0 * * *",
        )
        svc.create_schedule(config)
        result = svc.get_schedule("sched_test4")
        assert result.schedule_id == "sched_test4"

    def test_get_schedule_not_found(self):
        svc = SchedulerService()
        with pytest.raises(ScheduleNotFoundError):
            svc.get_schedule("sched_nonexistent")

    def test_list_schedules(self):
        svc = SchedulerService()
        for i in range(3):
            config = ScheduleConfig(
                schedule_id=f"sched_test{i}",
                name=f"Test {i}",
                schedule_type=ScheduleType.CRON,
                capability_name="test.cap",
                cron_expression="0 0 * * *",
            )
            svc.create_schedule(config)
        schedules = svc.list_schedules()
        assert len(schedules) == 3

    def test_delete_schedule(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test5",
            name="Test Delete",
            schedule_type=ScheduleType.CRON,
            capability_name="test.cap",
            cron_expression="0 0 * * *",
        )
        svc.create_schedule(config)
        svc.delete_schedule("sched_test5")
        with pytest.raises(ScheduleNotFoundError):
            svc.get_schedule("sched_test5")

    def test_pause_schedule(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test6",
            name="Test Pause",
            schedule_type=ScheduleType.CRON,
            capability_name="test.cap",
            cron_expression="0 0 * * *",
        )
        svc.create_schedule(config)
        result = svc.pause_schedule("sched_test6")
        assert result.state == ScheduleState.PAUSED
        assert result.enabled is False

    def test_resume_schedule(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test7",
            name="Test Resume",
            schedule_type=ScheduleType.CRON,
            capability_name="test.cap",
            cron_expression="0 0 * * *",
        )
        svc.create_schedule(config)
        svc.pause_schedule("sched_test7")
        result = svc.resume_schedule("sched_test7")
        assert result.state == ScheduleState.PENDING
        assert result.enabled is True

    def test_trigger_now(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test8",
            name="Test Trigger",
            schedule_type=ScheduleType.CRON,
            capability_name="test.cap",
            cron_expression="0 0 * * *",
        )
        svc.create_schedule(config)
        result = svc.trigger_now("sched_test8")
        assert result["status"] in ("success", "skipped")

    def test_duplicate_schedule_error(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test9",
            name="Test Duplicate",
            schedule_type=ScheduleType.CRON,
            capability_name="test.cap",
            cron_expression="0 0 * * *",
        )
        svc.create_schedule(config)
        with pytest.raises(SchedulerError):
            svc.create_schedule(config)

    def test_missing_cron_expression(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test10",
            name="Test Missing Cron",
            schedule_type=ScheduleType.CRON,
            capability_name="test.cap",
        )
        with pytest.raises(SchedulerError):
            svc.create_schedule(config)

    def test_missing_interval_seconds(self):
        svc = SchedulerService()
        config = ScheduleConfig(
            schedule_id="sched_test11",
            name="Test Missing Interval",
            schedule_type=ScheduleType.INTERVAL,
            capability_name="test.cap",
        )
        with pytest.raises(SchedulerError):
            svc.create_schedule(config)
