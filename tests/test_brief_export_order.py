"""Brief CSV ordering follows the operator selection across filtered pages."""
import csv
import io
import subprocess
from datetime import datetime

import pytest

from app.models import Company, Opportunity, ProposalBrief
from conftest import TestingSessionLocal


@pytest.fixture
def ordered_briefs():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="brief-order-a"),
                    Company(id=2, name="Synthetic B", slug="brief-order-b")])
        db.flush()
        for ident, tenant, day, title, status in [
            (1, 1, 1, "Zulu", "draft"), (2, 1, 3, "Alpha", "ready_for_review"),
            (3, 1, 3, "Alpha", "draft"), (4, 1, 4, "Other", "draft"),
            (5, 2, 3, "Alpha", "draft"),
        ]:
            db.add(Opportunity(id=ident, company_id=tenant, title=title,
                               description="Synthetic", source="manual",
                               external_url=f"https://example.com/brief-order/{ident}",
                               captured_at=datetime(2026, 11, 1)))
            db.flush()
            db.add(ProposalBrief(id=ident, opportunity_id=ident, offer_reference="Synthetic match",
                                 diagnosis="Synthetic diagnosis", scope="Synthetic scope",
                                 deliverables="Synthetic deliverables",
                                 acceptance_criteria="Synthetic acceptance", status=status,
                                 created_at=datetime(2026, 11, day)))
        db.commit()


def ids(response):
    assert response.status_code == 200
    return [int(row["ID"]) for row in csv.DictReader(io.StringIO(response.text))]


@pytest.mark.parametrize("sort,expected", [
    ("id", [1, 2, 3]), ("created_at", [3, 2, 1]),
    ("status", [1, 3, 2]), ("title", [2, 3, 1]),
])
def test_export_order(client, operator_a_headers, ordered_briefs, sort, expected):
    params = dict(sort=sort, q="match", from_date="2026-11-01", to_date="2026-11-03")
    response = client.get("/proposal-briefs/export.csv", params=params, headers=operator_a_headers)
    assert ids(response) == expected
    page = client.get("/proposal-briefs", params={**params, "limit": 1, "offset": 1},
                      headers=operator_a_headers)
    assert page.status_code == 200
    assert [row["id"] for row in page.json()] == expected[1:2]
    assert "Synthetic diagnosis" in response.text


def test_export_filters_defaults_and_tenant(client, operator_a_headers, operator_b_headers, ordered_briefs):
    path = "/proposal-briefs/export.csv"
    assert ids(client.get(path, headers=operator_a_headers)) == [1, 2, 3, 4]
    assert ids(client.get(path + "?sort=title", headers=operator_b_headers)) == [5]
    assert ids(client.get(path + "?sort=title&status=draft&q=match&opportunity_id=3"
                          "&from_date=2026-11-01&to_date=2026-11-03",
                          headers=operator_a_headers)) == [3]
    assert ids(client.get(path + "?sort=created_at&q=absent", headers=operator_a_headers)) == []
    assert ids(client.get(path + "?sort=title&opportunity_id=5", headers=operator_a_headers)) == []
    assert client.get(path + "?sort=unknown", headers=operator_a_headers).status_code == 422


def test_export_listener():
    subprocess.run(["node", "tests/js/brief_export_order.cjs"], check=True)
