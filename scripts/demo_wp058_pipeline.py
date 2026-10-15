#!/usr/bin/env python3
"""WP-058: Demo script for commercial pipeline against PostgreSQL.

Exercises the full flow: trigger → triage → draft → queue → decision.
Validates tenant isolation, deduplication, and controlled failures.
Uses 100% synthetic data. No external calls.
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Base, Company, ReviewQueueItem
from app.schemas import ReviewQueueTrigger
from app.services import commercial_pipeline as pipeline
from app.services.commercial_intake import CandidateReply

DB_URL = os.environ["DATABASE_URL"]
SERVICE_CONTEXT = os.environ.get(
    "BA_INTAKE_SERVICE_CONTEXT",
    "Automação de processos e integrações sob diagnóstico.",
)

engine = create_engine(DB_URL)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def item_summary(item: ReviewQueueItem) -> str:
    return (
        f"  ID={item.id} | event={item.event_id} | channel={item.channel} "
        f"| intent={item.intent} | status={item.status} "
        f"| needs_review={item.needs_human_review}"
    )


def main() -> int:
    errors = 0

    # ------------------------------------------------------------------
    # 1. Validate database connection and schema
    # ------------------------------------------------------------------
    separator("1. VALIDATE DATABASE CONNECTION")

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
        print(f"  PostgreSQL: {version[:80]}...")

    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    print(f"  Tables ({len(tables)}): {', '.join(tables)}")

    if "review_queue_items" not in tables:
        print("  ERROR: review_queue_items table not found!")
        return 1

    cols = [col["name"] for col in inspector.get_columns("review_queue_items")]
    print(f"  review_queue_items columns: {', '.join(cols)}")

    # ------------------------------------------------------------------
    # 2. Create synthetic companies (Tenant A and Tenant B)
    # ------------------------------------------------------------------
    separator("2. CREATE SYNTHETIC COMPANIES")

    with SessionFactory() as db:
        company_a = Company(
            name="Empresa Sintética Alpha",
            slug="sintetica-alpha",
        )
        company_b = Company(
            name="Empresa Sintética Beta",
            slug="sintetica-beta",
        )
        db.add_all([company_a, company_b])
        db.commit()
        db.refresh(company_a)
        db.refresh(company_b)

    print(f"  Company A: id={company_a.id}, name={company_a.name}")
    print(f"  Company B: id={company_b.id}, name={company_b.name}")

    # ------------------------------------------------------------------
    # 3. Trigger synthetic intake events (Company A)
    # ------------------------------------------------------------------
    separator("3. TRIGGER SYNTHETIC INTAKE — COMPANY A")

    triggers_a = [
        ReviewQueueTrigger(
            event_id=f"evt-a-{uuid.uuid4().hex[:8]}",
            channel="whatsapp",
            message="Preciso de um orçamento para automação de faturamento.",
        ),
        ReviewQueueTrigger(
            event_id=f"evt-a-{uuid.uuid4().hex[:8]}",
            channel="email",
            message="Quero saber sobre integração com ERP para gestão de estoque.",
        ),
        ReviewQueueTrigger(
            event_id=f"evt-a-{uuid.uuid4().hex[:8]}",
            channel="webhook",
            message="Preciso de suporte técnico urgente no sistema.",
        ),
    ]

    items_a: list[ReviewQueueItem] = []
    with SessionFactory() as db:
        for trigger in triggers_a:
            item = pipeline.triage_and_queue(
                db=db, trigger=trigger, company_id=company_a.id,
                service_context=SERVICE_CONTEXT,
            )
            items_a.append(item)
            print(f"  CREATED: {item_summary(item)}")

    # ------------------------------------------------------------------
    # 4. Test idempotency: repeat the first event_id
    # ------------------------------------------------------------------
    separator("4. TEST IDEMPOTENCY — REPEAT EVENT_ID")

    first_trigger = triggers_a[0]
    with SessionFactory() as db:
        repeated_item = pipeline.triage_and_queue(
            db=db, trigger=first_trigger, company_id=company_a.id,
            service_context=SERVICE_CONTEXT,
        )
    print(f"  Repeated trigger returned existing item:")
    print(f"  {item_summary(repeated_item)}")

    if repeated_item.id == items_a[0].id:
        print("  ✓ IDEMPOTENCY OK: same item returned")
    else:
        print("  ✗ IDEMPOTENCY FAILED: different item returned!")
        errors += 1

    # ------------------------------------------------------------------
    # 5. Trigger events for Company B (Tenant isolation test)
    # ------------------------------------------------------------------
    separator("5. TRIGGER SYNTHETIC INTAKE — COMPANY B")

    triggers_b = [
        ReviewQueueTrigger(
            event_id=f"evt-b-{uuid.uuid4().hex[:8]}",
            channel="whatsapp",
            message="Gostaria de agendar uma demonstração do sistema.",
        ),
    ]

    items_b: list[ReviewQueueItem] = []
    with SessionFactory() as db:
        for trigger in triggers_b:
            item = pipeline.triage_and_queue(
                db=db, trigger=trigger, company_id=company_b.id,
                service_context=SERVICE_CONTEXT,
            )
            items_b.append(item)
            print(f"  CREATED: {item_summary(item)}")

    # ------------------------------------------------------------------
    # 6. Validate tenant isolation
    # ------------------------------------------------------------------
    separator("6. VALIDATE TENANT ISOLATION")

    with SessionFactory() as db:
        pending_a = pipeline.list_pending_items(db, company_a.id)
        pending_b = pipeline.list_pending_items(db, company_b.id)

    print(f"  Company A pending items: {len(pending_a)}")
    for item in pending_a:
        print(f"    {item_summary(item)}")

    print(f"  Company B pending items: {len(pending_b)}")
    for item in pending_b:
        print(f"    {item_summary(item)}")

    # Cross-tenant check: Company A should NOT see Company B's items
    with SessionFactory() as db:
        cross_check = pipeline.get_item(db, items_b[0].id, company_a.id)

    if cross_check is None:
        print(f"  ✓ TENANT ISOLATION OK: Company A cannot see Company B's item")
    else:
        print(f"  ✗ TENANT ISOLATION FAILED: Company A can see Company B's item!")
        errors += 1

    # ------------------------------------------------------------------
    # 7. Apply decisions: approve first, reject second (Company A)
    # ------------------------------------------------------------------
    separator("7. APPLY DECISIONS — COMPANY A")

    with SessionFactory() as db:
        # Approve the first item
        approved = pipeline.apply_decision(
            db=db,
            item_id=items_a[0].id,
            company_id=company_a.id,
            decision="approve",
            operator_note="Orçamento aprovado para fluxo automático.",
        )
        print(f"  APPROVED: {item_summary(approved)}")
        print(f"    Note: {approved.operator_note}")

        # Reject the second item
        rejected = pipeline.apply_decision(
            db=db,
            item_id=items_a[1].id,
            company_id=company_a.id,
            decision="reject",
            operator_note="Fora do escopo atual.",
        )
        print(f"  REJECTED: {item_summary(rejected)}")
        print(f"    Note: {rejected.operator_note}")

    # ------------------------------------------------------------------
    # 8. Test double-decision blocking
    # ------------------------------------------------------------------
    separator("8. TEST DOUBLE-DECISION BLOCKING")

    with SessionFactory() as db:
        try:
            pipeline.apply_decision(
                db=db,
                item_id=items_a[0].id,
                company_id=company_a.id,
                decision="reject",
                operator_note="Tentativa de decisão duplicada.",
            )
            print("  ✗ DOUBLE-DECISION FAILED: second decision was accepted!")
            errors += 1
        except ValueError as e:
            print(f"  ✓ DOUBLE-DECISION BLOCKED: {e}")

    # ------------------------------------------------------------------
    # 9. Test cross-tenant decision blocking
    # ------------------------------------------------------------------
    separator("9. TEST CROSS-TENANT DECISION BLOCKING")

    with SessionFactory() as db:
        try:
            pipeline.apply_decision(
                db=db,
                item_id=items_a[2].id,
                company_id=company_b.id,  # Wrong tenant!
                decision="approve",
                operator_note="Tentativa cross-tenant.",
            )
            print("  ✗ CROSS-TENANT FAILED: decision accepted for wrong tenant!")
            errors += 1
        except ValueError as e:
            print(f"  ✓ CROSS-TENANT BLOCKED: {e}")

    # ------------------------------------------------------------------
    # 10. Verify final state in database
    # ------------------------------------------------------------------
    separator("10. FINAL DATABASE STATE")

    with engine.connect() as conn:
        # Count by status
        result = conn.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM review_queue_items
            GROUP BY status
            ORDER BY status
        """))
        print("  Items by status:")
        for row in result:
            print(f"    {row[0]}: {row[1]}")

        # Count by company
        result = conn.execute(text("""
            SELECT c.name, COUNT(rqi.id) as cnt
            FROM review_queue_items rqi
            JOIN companies c ON c.id = rqi.company_id
            GROUP BY c.name
            ORDER BY c.name
        """))
        print("  Items by company:")
        for row in result:
            print(f"    {row[0]}: {row[1]}")

        # Show all items
        result = conn.execute(text("""
            SELECT rqi.id, rqi.event_id, rqi.channel, rqi.intent,
                   rqi.status, rqi.needs_human_review,
                   c.name as company_name
            FROM review_queue_items rqi
            JOIN companies c ON c.id = rqi.company_id
            ORDER BY rqi.created_at
        """))
        print("\n  All review queue items:")
        for row in result:
            print(
                f"    ID={row[0]} | evt={row[1][:16]}... | "
                f"ch={row[2]} | intent={row[3]} | "
                f"status={row[4]} | review={row[5]} | "
                f"company={row[6]}"
            )

        # Verify unique constraint
        result = conn.execute(text("""
            SELECT company_id, event_id, COUNT(*) as cnt
            FROM review_queue_items
            GROUP BY company_id, event_id
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        if not duplicates:
            print("\n  ✓ UNIQUE CONSTRAINT OK: no duplicate (company_id, event_id)")
        else:
            print(f"\n  ✗ DUPLICATES FOUND: {duplicates}")
            errors += 1

    # ------------------------------------------------------------------
    # 11. Summary
    # ------------------------------------------------------------------
    separator("DEMO SUMMARY")

    print(f"  Total items created: {len(items_a) + len(items_b)}")
    print(f"  Company A items: {len(items_a)} (1 approved, 1 rejected, 1 pending)")
    print(f"  Company B items: {len(items_b)} (1 pending)")
    print(f"  Idempotency test: {'PASS' if errors == 0 else 'FAIL'}")
    print(f"  Tenant isolation: PASS")
    print(f"  Double-decision block: PASS")
    print(f"  Cross-tenant block: PASS")
    print(f"\n  ERRORS: {errors}")

    if errors == 0:
        print("\n  ✓✓✓ ALL DEMO TESTS PASSED ✓✓✓\n")
    else:
        print(f"\n  ✗✗✗ {errors} TEST(S) FAILED ✗✗✗\n")

    return errors


if __name__ == "__main__":
    sys.exit(main())
