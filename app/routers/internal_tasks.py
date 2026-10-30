"""Operator-only creation/status for internal synthetic intake tasks."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import AccessIdentity
from app.dependencies import get_db, require_operator
from app.schemas import InternalTaskOut, ReviewQueueTrigger
from app.services import internal_tasks as tasks

router = APIRouter(prefix="/internal-tasks", tags=["internal-tasks"])


@router.get("/", response_model=list[InternalTaskOut])
def list_internal_tasks(
    status: Literal["queued", "running", "succeeded", "failed"] | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    identity: AccessIdentity = Depends(require_operator),
):
    return tasks.list_tasks(db, identity.company_id, status=status, limit=limit, offset=offset)


@router.get("/summary", response_model=dict[str, int])
def summarize_internal_tasks(db: Session = Depends(get_db),
                             identity: AccessIdentity = Depends(require_operator)):
    return tasks.task_summary(db, identity.company_id)


@router.post("/", response_model=InternalTaskOut, status_code=202)
def create_task(trigger: ReviewQueueTrigger, db: Session = Depends(get_db),
                identity: AccessIdentity = Depends(require_operator)):
    try:
        return tasks.enqueue(db, trigger, identity.company_id)
    except ValueError:
        raise HTTPException(409, "Event already registered with different input")


@router.get("/{task_id}", response_model=InternalTaskOut)
def task_status(task_id: int, db: Session = Depends(get_db),
                identity: AccessIdentity = Depends(require_operator)):
    task = tasks.get_task(db, task_id, identity.company_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    return task
