"""Synthetic concurrency checks, called only by the disposable Alembic harness."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from threading import Barrier, Event, current_thread
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

url = make_url(os.environ["DATABASE_URL"])
if url.host != "127.0.0.1" or not (url.database or "").startswith("wp004_fresh_"):
    raise SystemExit("Only harness-owned disposable PostgreSQL is allowed")

from app.models import Company, InternalTask, ReviewQueueItem
from app.schemas import ReviewQueueTrigger
from app.services import internal_tasks as tasks

engine = create_engine(url)
factory = sessionmaker(engine, autoflush=False)
with factory() as db:
    company = Company(name="Synthetic task concurrency", slug="wp063-synthetic")
    db.add(company)
    db.commit()
    company_id = company.id

for index in range(10):
    with factory() as db:
        task_id = tasks.enqueue(db, ReviewQueueTrigger(
            event_id=f"race-{index}", channel="web", message="Synthetic request",
        ), company_id).id
    barrier = Barrier(2)
    def compete():
        with factory() as db:
            barrier.wait(timeout=10)
            return tasks.claim(db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: compete(), range(2)))
    winners = [r for r in results if r is not None]
    assert len(winners) == 1, results
    with factory() as db:
        assert tasks.execute_claim(db, *winners[0], "Synthetic context")
        assert not tasks.execute_claim(db, *winners[0], "Synthetic context")
        assert db.get(InternalTask, task_id).attempts == 1

with factory() as db:
    task_id = tasks.enqueue(db, ReviewQueueTrigger(
        event_id="stale", channel="web", message="Synthetic restart",
    ), company_id).id
    now = tasks.utcnow()
    stale = tasks.claim(db, now=now)
# New connection simulates worker restart, old token must not persist any effect.
with factory() as db:
    later = now + timedelta(seconds=61)
    assert tasks.recover_expired(db, now=later) == 1
    current = tasks.claim(db, now=later + timedelta(seconds=3))
with factory() as db:
    assert not tasks.execute_claim(db, *stale, "Synthetic", now=later)
    assert db.scalar(select(func.count()).select_from(ReviewQueueItem).where(
        ReviewQueueItem.event_id == "stale")) == 0
with factory() as db:
    assert tasks.execute_claim(db, *current, "Synthetic", now=later + timedelta(seconds=4))
with factory() as db:
    task = db.get(InternalTask, task_id)
    assert task.status == "succeeded"
    item = db.get(ReviewQueueItem, task.result["review_item_id"])
    assert item.company_id == company_id
    assert item.status == "pending"
# Hold execution's row lock while another connection tries lease recovery.
with factory() as db:
    tasks.enqueue(db, ReviewQueueTrigger(
        event_id="locked", channel="web", message="Synthetic lock race",
    ), company_id)
    lock_now = tasks.utcnow()
    locked_claim = tasks.claim(db, now=lock_now)
entered = Event()
recover_update = Event()
original_build = tasks.build_review_item

def held_build(*args):
    entered.set()
    assert recover_update.wait(timeout=10)
    return original_build(*args)

def observe_recovery(conn, cursor, statement, parameters, context, executemany):
    if current_thread().name.startswith("recovery") and statement.startswith("UPDATE internal_tasks"):
        recover_update.set()

def finish_locked():
    with factory() as db:
        return tasks.execute_claim(db, *locked_claim, "Synthetic", now=lock_now)

def recover_locked():
    assert entered.wait(timeout=10)
    with factory() as db:
        return tasks.recover_expired(db, now=lock_now + timedelta(seconds=61))

event.listen(engine, "before_cursor_execute", observe_recovery)
try:
    with patch.object(tasks, "build_review_item", held_build):
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="executor") as executor:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="recovery") as recovery:
                finished = executor.submit(finish_locked)
                recovered = recovery.submit(recover_locked)
                assert finished.result(timeout=15)
                assert recovered.result(timeout=15) == 0
finally:
    event.remove(engine, "before_cursor_execute", observe_recovery)
print("INTERNAL_TASKS_LOCK_RACE_OK completion_wins=true recovery_no_overwrite=true")
engine.dispose()
print("INTERNAL_TASKS_POSTGRES_OK claim_races=10 restart=true stale_fenced=true external_actions=false")
