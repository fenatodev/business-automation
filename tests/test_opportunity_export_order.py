"""CSV preserves the selected opportunity order across filtered pages."""
import csv
import io
import subprocess
from datetime import datetime

import pytest

from app.models import Company, Opportunity
from conftest import TestingSessionLocal


@pytest.fixture
def ordered_opportunities():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="order-a"),
                    Company(id=2, name="Synthetic B", slug="order-b")])
        db.flush()
        for ident, tenant, day, status in [(1, 1, 1, "pending"), (2, 1, 3, "follow"),
                                         (3, 1, 3, "pending"), (4, 1, 4, "done"),
                                         (5, 2, 3, "pending")]:
            db.add(Opportunity(id=ident, company_id=tenant, title="Synthetic match",
                               description="Synthetic", source="manual", next_action=status,
                               external_url=f"https://example.com/order/{ident}",
                               captured_at=datetime(2026, 11, 2, 12), created_at=datetime(2026, 11, day)))
        db.commit()


def ids(response):
    assert response.status_code == 200
    return [int(row["ID"]) for row in csv.DictReader(io.StringIO(response.text))]


@pytest.mark.parametrize("sort,expected", [("id", [1, 2, 3]), ("created_at", [3, 2, 1]),
                                          ("next_action", [2, 1, 3]), ("priority", [1, 3, 2])])
def test_export_order(client, operator_a_headers, ordered_opportunities, sort, expected):
    params = dict(sort=sort, exclude_archived=True, q="match", source="manual",
                  from_date="2026-11-01", to_date="2026-11-03")
    assert ids(client.get("/opportunities/export.csv", params=params, headers=operator_a_headers)) == expected
    if sort != "priority":
        page = client.get("/opportunities", params={**params, "limit": 1, "offset": 1}, headers=operator_a_headers)
        assert [row["id"] for row in page.json()] == expected[1:2]


def test_export_defaults_validation_and_tenant(client, operator_a_headers, operator_b_headers, ordered_opportunities):
    path = "/opportunities/export.csv"
    assert ids(client.get(path, headers=operator_a_headers)) == [1, 2, 3, 4]
    assert ids(client.get(path + "?sort=priority", headers=operator_b_headers)) == [5]
    assert ids(client.get(path + "?sort=created_at&q=absent", headers=operator_a_headers)) == []
    assert client.get(path + "?sort=unknown", headers=operator_a_headers).status_code == 422


def test_export_listener():
    subprocess.run(["node", "tests/js/opportunity_export_order.cjs"], check=True)
