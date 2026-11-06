"""Conversation CSV follows the operator's order across all filtered pages."""
import csv
import io
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.models import Company, Conversation, Message
from conftest import TestingSessionLocal


@pytest.fixture
def export_conversations():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="conv-order-a"),
                    Company(id=2, name="Synthetic B", slug="conv-order-b")])
        db.flush()
        for conv_id, tenant, day, channel in [
            (1, 1, 2, "web"), (2, 1, 3, "web"), (3, 1, 3, "web"),
            (4, 1, 4, "email"), (5, 2, 3, "web"), (6, 1, 1, "web"),
        ]:
            db.add(Conversation(id=conv_id, company_id=tenant, channel=channel,
                                status="open", created_at=datetime(2026, 11, day)))
        db.flush()
        for conv_id, day in [(1, 5), (2, 4), (3, 4), (4, 6), (5, 7)]:
            db.add(Message(conversation_id=conv_id, sender_type="customer",
                           content="Synthetic match", created_at=datetime(2026, 11, day)))
        db.commit()


def csv_ids(response):
    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=conversations.csv"
    return [int(row["ID"]) for row in csv.DictReader(io.StringIO(response.text))]


@pytest.mark.parametrize("sort,expected", [
    ("id", [1, 2, 3]), ("created_at", [2, 3, 1]), ("last_message", [1, 2, 3]),
])
def test_export_sorted_filtered_all_pages(client, operator_a_headers, export_conversations, sort, expected):
    params = {"sort": sort, "q": "match", "channel": "web", "status": "open",
              "from_date": "2026-11-02", "to_date": "2026-11-03"}
    listing = client.get("/companies/1/conversations", params={**params, "limit": 1, "offset": 1},
                         headers=operator_a_headers)
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == expected[1:2]
    response = client.get("/companies/1/conversations/export.csv", params=params, headers=operator_a_headers)
    assert csv_ids(response) == expected
    assert "[customer] Synthetic match" in response.text


def test_export_default_empty_and_tenant(client, operator_a_headers, operator_b_headers, export_conversations):
    path = "/companies/1/conversations/export.csv"
    assert csv_ids(client.get(path, headers=operator_a_headers)) == [1, 2, 3, 4, 6]
    assert csv_ids(client.get(path + "?sort=created_at&q=absent", headers=operator_a_headers)) == []
    assert csv_ids(client.get("/companies/2/conversations/export.csv?sort=last_message",
                              headers=operator_b_headers)) == [5]
    assert client.get(path + "?sort=last_message", headers=operator_b_headers).status_code in (403, 404)


def test_export_last_message_includes_empty_conversations(client, operator_a_headers, export_conversations):
    params = {"sort": "last_message"}
    listing = client.get("/companies/1/conversations", params=params, headers=operator_a_headers)
    response = client.get("/companies/1/conversations/export.csv", params=params, headers=operator_a_headers)
    assert csv_ids(response) == [row["id"] for row in listing.json()] == [4, 1, 2, 3, 6]


def test_export_unknown_sort(client, operator_a_headers):
    assert client.get("/companies/1/conversations/export.csv?sort=channel",
                      headers=operator_a_headers).status_code == 422


def test_export_button():
    subprocess.run(["node", "tests/js/conversation_export_order.cjs"],
                   cwd=Path(__file__).resolve().parents[1], check=True)
