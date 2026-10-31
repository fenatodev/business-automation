"""WP-143 — Timeline de atividades da oportunidade.

Testa o endpoint GET /opportunities/{id}/timeline que retorna eventos
derivados dos dados existentes: criação, triagem e brief status changes.
"""
from datetime import datetime, timezone


class TestOpportunityTimeline:
    """Test opportunity activity timeline endpoint."""

    def _create_company(self, client, headers):
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def _create_opportunity(self, client, company_id, headers):
        resp = client.post("/opportunities", json={
            "company_id": company_id,
            "source": "manual",
            "external_url": "https://example.com/opp",
            "title": "Test Opportunity",
            "description": "Test description",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def test_timeline_returns_created_event(self, client, admin_headers, operator_a_headers):
        """Timeline always includes the creation event."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(
            f"/opportunities/{opp['id']}/timeline",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        created = [e for e in events if e["type"] == "created"]
        assert len(created) == 1
        assert "manual" in created[0]["detail"]

    def test_timeline_includes_triage_event(self, client, admin_headers, operator_a_headers):
        """Timeline includes triage event when triage_note exists."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        # Apply triage with note
        client.patch(
            f"/opportunities/{opp['id']}/triage",
            json={"next_action": "follow", "triage_note": "Acompanhar em 30 dias"},
            headers=operator_a_headers,
        )

        resp = client.get(
            f"/opportunities/{opp['id']}/timeline",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        triage = [e for e in events if e["type"] == "triage"]
        assert len(triage) == 1
        assert "follow" in triage[0]["detail"]
        assert "Acompanhar em 30 dias" in triage[0]["detail"]

    def test_timeline_no_triage_event_without_note(self, client, admin_headers, operator_a_headers):
        """Timeline does not include triage event when no triage_note."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(
            f"/opportunities/{opp['id']}/timeline",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        triage = [e for e in events if e["type"] == "triage"]
        assert len(triage) == 0

    def test_timeline_includes_brief_events(self, client, admin_headers, operator_a_headers):
        """Timeline includes brief creation and status events."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        # Must triage to prepare_proposal before creating brief
        client.patch(
            f"/opportunities/{opp['id']}/triage",
            json={"next_action": "prepare_proposal", "triage_note": "Preparar proposta"},
            headers=operator_a_headers,
        )

        # Create brief
        client.post(
            f"/opportunities/{opp['id']}/proposal-brief",
            json={
                "offer_reference": "test-offer",
                "diagnosis": "Test diagnosis",
                "scope": "Test scope",
                "deliverables": "Test deliverables",
                "acceptance_criteria": "Test criteria",
            },
            headers=operator_a_headers,
        )

        resp = client.get(
            f"/opportunities/{opp['id']}/timeline",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        brief_created = [e for e in events if e["type"] == "brief_created"]
        assert len(brief_created) == 1
        assert "test-offer" in brief_created[0]["detail"]

    def test_timeline_includes_brief_status_change(self, client, admin_headers, operator_a_headers):
        """Timeline includes brief status change when status is not draft."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        # Must triage to prepare_proposal before creating brief
        client.patch(
            f"/opportunities/{opp['id']}/triage",
            json={"next_action": "prepare_proposal", "triage_note": "Preparar proposta"},
            headers=operator_a_headers,
        )

        # Create brief
        client.post(
            f"/opportunities/{opp['id']}/proposal-brief",
            json={
                "offer_reference": "test-offer",
                "diagnosis": "Test diagnosis",
                "scope": "Test scope",
                "deliverables": "Test deliverables",
                "acceptance_criteria": "Test criteria",
            },
            headers=operator_a_headers,
        )

        # Update brief status
        client.patch(
            f"/opportunities/{opp['id']}/proposal-brief",
            json={
                "offer_reference": "test-offer",
                "diagnosis": "Test diagnosis",
                "scope": "Test scope",
                "deliverables": "Test deliverables",
                "acceptance_criteria": "Test criteria",
                "status": "ready_for_review",
            },
            headers=operator_a_headers,
        )

        resp = client.get(
            f"/opportunities/{opp['id']}/timeline",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        events = resp.json()
        brief_status = [e for e in events if e["type"] == "brief_status"]
        assert len(brief_status) == 1
        assert "ready_for_review" in brief_status[0]["detail"]

    def test_timeline_ordered_descending(self, client, admin_headers, operator_a_headers):
        """Timeline events are ordered by timestamp descending."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(
            f"/opportunities/{opp['id']}/timeline",
            headers=operator_a_headers,
        )
        events = resp.json()
        timestamps = [e["timestamp"] for e in events]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_timeline_requires_auth(self, client, admin_headers, operator_a_headers):
        """Timeline endpoint requires authentication."""
        company = self._create_company(client, admin_headers)
        opp = self._create_opportunity(client, company["id"], operator_a_headers)

        resp = client.get(f"/opportunities/{opp['id']}/timeline")
        assert resp.status_code in (401, 403)

    def test_timeline_404_for_unknown_opportunity(self, client, admin_headers, operator_a_headers):
        """Returns 404 when opportunity doesn't exist."""
        resp = client.get(
            "/opportunities/99999/timeline",
            headers=operator_a_headers,
        )
        assert resp.status_code == 404

    def test_timeline_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Cannot access timeline from another tenant's opportunity."""
        company_a = self._create_company(client, admin_headers)
        company_b = client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b-timeline",
        }, headers=admin_headers).json()
        opp_b = self._create_opportunity(client, company_b["id"], operator_b_headers)

        resp = client.get(
            f"/opportunities/{opp_b['id']}/timeline",
            headers=operator_a_headers,
        )
        assert resp.status_code == 404
