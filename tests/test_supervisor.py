"""Tests for the internal task queue supervisor (WP-068)."""

import pytest

from app.models import Company
from app.schemas import ReviewQueueTrigger
from app.services import internal_tasks as tasks
from app.services.supervisor import SupervisorStats, run_loop
from conftest import TestingSessionLocal


@pytest.fixture
def companies():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="task-a"),
                    Company(id=2, name="Synthetic B", slug="task-b")])
        db.commit()


def trigger(event="supervisor-task-1"):
    return ReviewQueueTrigger(
        channel="web", message="Gostaria de automatizar processos", event_id=event
    )


def test_run_loop_executes_max_cycles(companies):
    """run_loop stops after max_cycles iterations."""
    stats = run_loop(TestingSessionLocal, "synthetic", max_cycles=3, interval=0)
    assert stats.cycles == 3
    assert stats.running is False


def test_run_loop_processes_tasks(companies):
    """run_loop processes available tasks and counts them."""
    with TestingSessionLocal() as db:
        tasks.enqueue(db, trigger(event="s1"), 1)
        tasks.enqueue(db, trigger(event="s2"), 1)
    stats = run_loop(TestingSessionLocal, "synthetic", max_cycles=5, interval=0)
    assert stats.cycles == 5  # 2 tasks + 3 idle cycles
    assert stats.tasks_processed == 2
    assert stats.errors == 0
    assert stats.running is False


def test_run_loop_counts_errors_without_crashing(companies, monkeypatch):
    """Errors in run_once are caught and counted; loop continues."""
    call_count = 0

    def broken_run_once(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(tasks, "run_once", broken_run_once)
    stats = run_loop(TestingSessionLocal, "synthetic", max_cycles=3, interval=0)
    assert stats.cycles == 3
    assert stats.tasks_processed == 0
    assert stats.errors == 3
    assert stats.running is False


def test_run_loop_mixed_success_and_error(companies, monkeypatch):
    """Loop handles alternating success and error cycles."""
    call_count = 0

    def mixed_run_once(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 0:
            raise RuntimeError("even cycle fails")
        return True

    monkeypatch.setattr(tasks, "run_once", mixed_run_once)
    stats = run_loop(TestingSessionLocal, "synthetic", max_cycles=4, interval=0)
    assert stats.cycles == 4
    assert stats.tasks_processed == 2  # cycles 1 and 3
    assert stats.errors == 2  # cycles 2 and 4
    assert stats.running is False


def test_supervisor_stats_defaults():
    """SupervisorStats has correct default values."""
    stats = SupervisorStats()
    assert stats.cycles == 0
    assert stats.tasks_processed == 0
    assert stats.errors == 0
    assert stats.running is False


def test_supervisor_stats_running_true():
    """SupervisorStats can be created with running=True."""
    stats = SupervisorStats(running=True)
    assert stats.running is True


def test_run_loop_no_tasks_idle_cycles(companies):
    """When no tasks are available, cycles still count but tasks_processed stays 0."""
    stats = run_loop(TestingSessionLocal, "synthetic", max_cycles=2, interval=0)
    assert stats.cycles == 2
    assert stats.tasks_processed == 0
    assert stats.errors == 0


def test_run_loop_processes_all_queued_tasks(companies):
    """Multiple tasks are processed across cycles until queue is empty."""
    with TestingSessionLocal() as db:
        for i in range(5):
            tasks.enqueue(db, trigger(event=f"batch-{i}"), 1)
    stats = run_loop(TestingSessionLocal, "synthetic", max_cycles=10, interval=0)
    # 5 tasks processed, then 5 idle cycles = 10 total
    assert stats.cycles == 10
    assert stats.tasks_processed == 5
    assert stats.errors == 0
