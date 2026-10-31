"""WP-096 — Intake persistence tests: POST /internal/commercial-intake/create."""
from datetime import datetime, timezone

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


class TestIntakeCreate:
    """Verify POST /internal/commercial-intake/create endpoint."""

    def test_create_intake_opportunity(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={
                "channel": "whatsapp",
                "message": "Preciso de automação para meu e-commerce",
                "event_id": "intake-test-001",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "opportunity_id" in data
        assert data["event_id"] == "intake-test-001"
        assert isinstance(data["intent"], str)
        assert isinstance(data["needs_human_review"], bool)
        assert isinstance(data["flags"], list)

    def test_create_intake_opportunity_exists_in_list(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Quero integrar meu ERP com o WhatsApp",
                "event_id": "intake-test-002",
            },
        )
        assert res.status_code == 200
        opp_id = res.json()["opportunity_id"]
        # Verify the opportunity appears in the list
        list_res = client.get("/opportunities", headers=operator_a_headers)
        assert list_res.status_code == 200
        opps = list_res.json()
        assert any(o["id"] == opp_id for o in opps)

    def test_create_intake_deduplication(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        payload = {
            "channel": "email",
            "message": "Automação de processos",
            "event_id": "intake-dedup-001",
        }
        res1 = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json=payload,
        )
        assert res1.status_code == 200
        opp_id_1 = res1.json()["opportunity_id"]
        # Second request with same event_id should return the same opportunity
        res2 = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json=payload,
        )
        assert res2.status_code == 200
        opp_id_2 = res2.json()["opportunity_id"]
        assert opp_id_1 == opp_id_2

    def test_create_intake_requires_auth(self, client):
        res = client.post(
            "/internal/commercial-intake/create",
            json={
                "channel": "web",
                "message": "Test",
                "event_id": "no-auth",
            },
        )
        assert res.status_code in (401, 403)

    def test_create_intake_validation_missing_fields(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={"channel": "web"},
        )
        assert res.status_code == 422

    def test_create_intake_validation_control_characters(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Test\x00message",
                "event_id": "test-ctrl",
            },
        )
        assert res.status_code == 422

    def test_create_intake_tenant_isolation(
        self, client, admin_headers, operator_a_headers, operator_b_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Alpha intake",
                "event_id": "tenant-test-001",
            },
        )
        assert res.status_code == 200
        # Operator B should not see Alpha's intake opportunity
        list_res = client.get("/opportunities", headers=operator_b_headers)
        assert list_res.status_code == 200
        opps = list_res.json()
        assert not any(o["source"] == "intake" for o in opps)

    def test_create_intake_source_is_intake(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={
                "channel": "whatsapp",
                "message": "Preciso de ajuda com automação",
                "event_id": "source-test-001",
            },
        )
        assert res.status_code == 200
        opp_id = res.json()["opportunity_id"]
        # Verify the opportunity has source="intake"
        list_res = client.get("/opportunities", headers=operator_a_headers)
        opp = next((o for o in list_res.json() if o["id"] == opp_id), None)
        assert opp is not None
        assert opp["source"] == "intake"

    def test_create_intake_external_url_format(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Test message",
                "event_id": "url-format-001",
            },
        )
        assert res.status_code == 200
        opp_id = res.json()["opportunity_id"]
        list_res = client.get("/opportunities", headers=operator_a_headers)
        opp = next((o for o in list_res.json() if o["id"] == opp_id), None)
        assert opp["external_url"] == "intake://url-format-001"

    def test_create_intake_title_from_intent(
        self, client, admin_headers, operator_a_headers
    ):
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/internal/commercial-intake/create",
            headers=operator_a_headers,
            json={
                "channel": "web",
                "message": "Preciso de automação de processos",
                "event_id": "title-test-001",
            },
        )
        assert res.status_code == 200
        opp_id = res.json()["opportunity_id"]
        list_res = client.get("/opportunities", headers=operator_a_headers)
        opp = next((o for o in list_res.json() if o["id"] == opp_id), None)
        assert "Intake" in opp["title"]
