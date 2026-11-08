"""WP-541 — Job persistence with SQLite tests."""
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.services.job_queue import Job, JobStatus
from app.services.job_store import JobStore


def _new_store():
    """Create a JobStore with a temporary database."""
    tmp = tempfile.mkdtemp()
    return JobStore(db_path=Path(tmp) / "test_jobs.db")


# --- Basic save/get ---


def test_save_and_get_job():
    """Save a job and retrieve it."""
    store = _new_store()
    job = Job(task_type="test", company_id=1)
    store.save(job)

    retrieved = store.get(job.job_id)
    assert retrieved is not None
    assert retrieved.job_id == job.job_id
    assert retrieved.task_type == "test"
    assert retrieved.company_id == 1
    assert retrieved.status == JobStatus.PENDING


def test_get_nonexistent_job():
    """Get returns None for unknown job."""
    store = _new_store()
    assert store.get("nonexistent") is None


def test_save_updates_existing_job():
    """Save updates an existing job."""
    store = _new_store()
    job = Job(task_type="test", company_id=1)
    store.save(job)

    job.status = JobStatus.COMPLETED
    job.result = "done"
    store.save(job)

    retrieved = store.get(job.job_id)
    assert retrieved.status == JobStatus.COMPLETED
    assert retrieved.result == "done"


# --- Job fields preservation ---


def test_save_preserves_retry_fields():
    """Save preserves retry-related fields."""
    store = _new_store()
    job = Job(task_type="test", max_retries=5, backoff_multiplier=3.0)
    job.retry_count = 2
    job.next_retry_at = datetime.now(timezone.utc)
    store.save(job)

    retrieved = store.get(job.job_id)
    assert retrieved.max_retries == 5
    assert retrieved.retry_count == 2
    assert retrieved.backoff_multiplier == 3.0
    assert retrieved.next_retry_at is not None


def test_save_preserves_timestamps():
    """Save preserves timestamps."""
    store = _new_store()
    job = Job(task_type="test")
    job.started_at = datetime.now(timezone.utc)
    job.completed_at = datetime.now(timezone.utc)
    store.save(job)

    retrieved = store.get(job.job_id)
    assert retrieved.started_at is not None
    assert retrieved.completed_at is not None


def test_save_preserves_payload():
    """Save preserves job payload."""
    store = _new_store()
    job = Job(task_type="test", payload={"key": "value", "num": 42})
    store.save(job)

    retrieved = store.get(job.job_id)
    assert retrieved.payload == {"key": "value", "num": 42}


def test_save_preserves_error():
    """Save preserves job error."""
    store = _new_store()
    job = Job(task_type="test")
    job.status = JobStatus.FAILED
    job.error = "something went wrong"
    store.save(job)

    retrieved = store.get(job.job_id)
    assert retrieved.status == JobStatus.FAILED
    assert retrieved.error == "something went wrong"


# --- List jobs ---


def test_list_jobs():
    """List returns all jobs."""
    store = _new_store()
    for i in range(3):
        store.save(Job(task_type=f"test-{i}", company_id=1))

    jobs = store.list()
    assert len(jobs) == 3


def test_list_jobs_filter_by_company():
    """List filters by company_id."""
    store = _new_store()
    store.save(Job(task_type="a", company_id=1))
    store.save(Job(task_type="b", company_id=2))
    store.save(Job(task_type="c", company_id=1))

    jobs = store.list(company_id=1)
    assert len(jobs) == 2
    assert all(j.company_id == 1 for j in jobs)


def test_list_jobs_filter_by_status():
    """List filters by status."""
    store = _new_store()
    job1 = Job(task_type="a")
    job1.status = JobStatus.COMPLETED
    store.save(job1)

    job2 = Job(task_type="b")
    job2.status = JobStatus.PENDING
    store.save(job2)

    jobs = store.list(status=JobStatus.COMPLETED)
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.COMPLETED


def test_list_jobs_limit():
    """List respects limit."""
    store = _new_store()
    for i in range(10):
        store.save(Job(task_type=f"test-{i}"))

    jobs = store.list(limit=5)
    assert len(jobs) == 5


# --- Delete ---


def test_delete_job():
    """Delete removes a job."""
    store = _new_store()
    job = Job(task_type="test")
    store.save(job)

    assert store.delete(job.job_id) is True
    assert store.get(job.job_id) is None


def test_delete_nonexistent_job():
    """Delete returns False for unknown job."""
    store = _new_store()
    assert store.delete("nonexistent") is False


# --- Cleanup ---


def test_cleanup_completed():
    """Cleanup removes old completed jobs."""
    store = _new_store()
    job = Job(task_type="test")
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc).replace(
        year=2020, month=1, day=1
    )
    store.save(job)

    removed = store.cleanup_completed(older_than_seconds=3600)
    assert removed == 1
    assert store.get(job.job_id) is None


def test_cleanup_keeps_recent():
    """Cleanup keeps recent jobs."""
    store = _new_store()
    job = Job(task_type="test")
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    store.save(job)

    removed = store.cleanup_completed(older_than_seconds=3600)
    assert removed == 0
    assert store.get(job.job_id) is not None


# --- Load all ---


def test_load_all():
    """Load all returns all jobs."""
    store = _new_store()
    for i in range(5):
        store.save(Job(task_type=f"test-{i}"))

    jobs = store.load_all()
    assert len(jobs) == 5


# --- Persistence survives recreation ---


def test_persistence_survives_recreation():
    """Jobs persist across store recreations (simulates restart)."""
    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "persist_test.db"

    # First store instance
    store1 = JobStore(db_path=db_path)
    job = Job(task_type="persistent", company_id=42)
    job.status = JobStatus.COMPLETED
    job.result = "survived"
    store1.save(job)

    # Second store instance (simulates restart)
    store2 = JobStore(db_path=db_path)
    retrieved = store2.get(job.job_id)
    assert retrieved is not None
    assert retrieved.task_type == "persistent"
    assert retrieved.company_id == 42
    assert retrieved.status == JobStatus.COMPLETED
    assert retrieved.result == "survived"


# --- Integration with JobQueue ---


def test_job_queue_persists_on_create():
    """JobQueue creates jobs that are persisted."""
    from app.services.job_queue import JobQueue

    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "queue_test.db"

    # Override the store for this test
    import app.services.job_store as store_module
    original = store_module.job_store
    store_module.job_store = JobStore(db_path=db_path)

    try:
        q = JobQueue()
        job = q.create_job("test", company_id=1)

        # Verify persistence
        retrieved = store_module.job_store.get(job.job_id)
        assert retrieved is not None
        assert retrieved.task_type == "test"
        assert retrieved.company_id == 1
    finally:
        store_module.job_store = original


def test_job_queue_persists_on_completion():
    """JobQueue persists job status after completion."""
    from app.services.job_queue import JobQueue

    tmp = tempfile.mkdtemp()
    db_path = Path(tmp) / "queue_test2.db"

    import app.services.job_store as store_module
    original = store_module.job_store
    store_module.job_store = JobStore(db_path=db_path)

    try:
        q = JobQueue()
        job = q.create_job("test", company_id=1, max_retries=0)
        q.execute_job(job.job_id, lambda: "done", _async=False)

        retrieved = store_module.job_store.get(job.job_id)
        assert retrieved is not None
        assert retrieved.status == JobStatus.COMPLETED
        assert retrieved.result == "done"
    finally:
        store_module.job_store = original
