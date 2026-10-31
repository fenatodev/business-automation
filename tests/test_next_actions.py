"""WP-161 — Resumo de próximas ações no dashboard.

Testa o campo next_actions retornado por GET /internal-tasks/dashboard.
"""
from datetime import datetime, timezone


class TestNextActions:
    """Test next actions summary in dashboard."""

    def _create_company(self, client, admin_headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=admin_headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_opportunity(self, client, company_id, headers, url_suffix="1"):
        resp = client.post(
            "/opportunities",
            json={
                "company_id": company_id,
                "source": "manual",
                "external_url": f"https://example.com/opp-{url_suffix}",
                "title": "Test Opportunity",
                "description": "Test",
                "captured_at": datetime.now(timezone.utc).isoformat(),
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"Failed to create opportunity: {resp.text}"
        return resp.json()

    def test_empty_dashboard_has_no_next_actions(self, client, admin_headers, operator_a_headers):
        """Empty company returns empty next_actions list."""
        self._create_company(client, admin_headers)
        resp = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "next_actions" in data
        assert data["next_actions"] == []

    def test_pending_opportunity_shows_in_next_actions(self, client, admin_headers, operator_a_headers):
        """Pending opportunities appear in next_actions."""
        company = self._create_company(client, admin_headers)
        self._create_opportunity(client, company["id"], operator_a_headers)
        resp = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        opp_actions = [a for a in data["next_actions"] if a["type"] == "opportunity"]
        assert len(opp_actions) == 1
        assert opp_actions[0]["count"] == 1
        assert opp_actions[0]["section"] == "opportunities"

    def _create_lead(self, client, company_id, headers, phone_suffix="0001"):
        resp = client.post(
            "/leads",
            json={
                "company_id": company_id,
                "name": f"Lead {phone_suffix}",
                "phone": f"1199999{phone_suffix}",
                "source": "manual",
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"Failed to create lead: {resp.text}"
        return resp.json()

    def _create_conversation(self, client, company_id, lead_id, headers):
        resp = client.post(
            "/conversations",
            json={
                "company_id": company_id,
                "channel": "whatsapp",
                "lead_id": lead_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"Failed to create conversation: {resp.text}"
        return resp.json()

    def test_open_conversation_shows_in_next_actions(self, client, admin_headers, operator_a_headers):
        """Open conversations appear in next_actions."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers, "conv1")
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        resp = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        conv_actions = [a for a in data["next_actions"] if a["type"] == "conversation"]
        assert len(conv_actions) == 1
        assert conv_actions[0]["count"] == 1

    def test_new_lead_shows_in_next_actions(self, client, admin_headers, operator_a_headers):
        """New leads appear in next_actions."""
        company = self._create_company(client, admin_headers)
        resp = client.post(
            "/leads",
            json={
                "company_id": company["id"],
                "name": "Test Lead",
                "phone": "11999990001",
                "source": "manual",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        resp = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        lead_actions = [a for a in data["next_actions"] if a["type"] == "lead"]
        assert len(lead_actions) == 1
        assert lead_actions[0]["count"] == 1

    def test_closed_conversation_not_in_next_actions(self, client, admin_headers, operator_a_headers):
        """Closed conversations do not appear in next_actions."""
        company = self._create_company(client, admin_headers)
        lead = self._create_lead(client, company["id"], operator_a_headers, "closed1")
        conv = self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        # Close the conversation
        resp = client.patch(
            f"/conversations/{conv['id']}",
            json={"status": "closed"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        resp = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        conv_actions = [a for a in data["next_actions"] if a["type"] == "conversation"]
        assert len(conv_actions) == 0

    def test_multiple_next_actions(self, client, admin_headers, operator_a_headers):
        """Multiple categories with pending items all appear."""
        company = self._create_company(client, admin_headers)
        self._create_opportunity(client, company["id"], operator_a_headers, "multi-1")
        lead = self._create_lead(client, company["id"], operator_a_headers, "multi-lead")
        self._create_conversation(client, company["id"], lead["id"], operator_a_headers)
        # Create a separate new lead (different phone)
        self._create_lead(client, company["id"], operator_a_headers, "multi-new")
        resp = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["next_actions"]) == 3
        types = {a["type"] for a in data["next_actions"]}
        assert "opportunity" in types
        assert "conversation" in types
        assert "lead" in types

    def test_next_actions_requires_auth(self, client, admin_headers):
        """Next actions endpoint requires authentication."""
        self._create_company(client, admin_headers)
        resp = client.get("/internal-tasks/dashboard")
        assert resp.status_code in (401, 403)

    def test_next_actions_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Next actions only show items from authenticated tenant."""
        company_a = self._create_company(client, admin_headers)
        client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b",
        }, headers=admin_headers)
        self._create_opportunity(client, company_a["id"], operator_a_headers, "iso-1")
        resp = client.get("/internal-tasks/dashboard", headers=operator_b_headers)
        assert resp.status_code == 200
        assert resp.json()["next_actions"] == []

    def test_next_action_has_label(self, client, admin_headers, operator_a_headers):
        """Each next action has a human-readable label."""
        company = self._create_company(client, admin_headers)
        self._create_opportunity(client, company["id"], operator_a_headers, "label-1")
        resp = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        for action in data["next_actions"]:
            assert "label" in action
            assert isinstance(action["label"], str)
            assert len(action["label"]) > 0
