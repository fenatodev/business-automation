"""WP-133 — Opportunity status transition validation."""

import pytest


class TestOpportunityStatusTransitions:
    """Validate that opportunity triage follows the F2 commercial cycle."""

    def _create_opportunity(self, client, admin_headers, operator_a_headers):
        """Create an opportunity without triage."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-tri"}, headers=admin_headers)
        resp = client.post(
            "/opportunities",
            json={
                "source": "manual",
                "external_url": "https://example.com/test-001",
                "title": "Test opportunity",
                "description": "Test",
                "captured_at": "2026-10-31T12:00:00-03:00",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_initial_triage_from_pending(self, client, admin_headers, operator_a_headers):
        """New opportunity (default pending) can transition to valid statuses."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-none"}, headers=admin_headers)
        # New opportunities default to "pending"
        for status in ["ignore", "follow", "prepare_proposal", "in_progress"]:
            resp = client.post(
                "/opportunities",
                json={
                    "source": "manual",
                    "external_url": f"https://example.com/pend-{status}",
                    "title": f"Test {status}",
                    "description": "Test",
                    "captured_at": "2026-10-31T12:00:00-03:00",
                },
                headers=operator_a_headers,
            )
            assert resp.status_code == 200
            opp_id = resp.json()["id"]
            triage_resp = client.patch(
                f"/opportunities/{opp_id}/triage",
                json={"next_action": status},
                headers=operator_a_headers,
            )
            assert triage_resp.status_code == 200, f"Should allow transition to {status}"

    def test_pending_to_follow(self, client, admin_headers, operator_a_headers):
        """Pending can transition to follow."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "pending"},
            headers=operator_a_headers,
        )
        resp = client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "follow"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["next_action"] == "follow"

    def test_pending_to_prepare_proposal(self, client, admin_headers, operator_a_headers):
        """Pending can transition to prepare_proposal."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "pending"},
            headers=operator_a_headers,
        )
        resp = client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "prepare_proposal"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200

    def test_in_progress_to_done(self, client, admin_headers, operator_a_headers):
        """In progress can transition to done."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "in_progress"},
            headers=operator_a_headers,
        )
        resp = client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "done"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["next_action"] == "done"

    def test_in_progress_to_lost(self, client, admin_headers, operator_a_headers):
        """In progress can transition to lost."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "in_progress"},
            headers=operator_a_headers,
        )
        resp = client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "lost"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["next_action"] == "lost"

    def test_done_is_terminal(self, client, admin_headers, operator_a_headers):
        """Done cannot transition to any other status."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "in_progress"},
            headers=operator_a_headers,
        )
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "done"},
            headers=operator_a_headers,
        )
        for status in ["pending", "follow", "prepare_proposal", "in_progress", "lost"]:
            resp = client.patch(
                f"/opportunities/{opp_id}/triage",
                json={"next_action": status},
                headers=operator_a_headers,
            )
            assert resp.status_code == 400, f"Done should not allow transition to {status}"

    def test_lost_is_terminal(self, client, admin_headers, operator_a_headers):
        """Lost cannot transition to any other status."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "in_progress"},
            headers=operator_a_headers,
        )
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "lost"},
            headers=operator_a_headers,
        )
        for status in ["pending", "follow", "prepare_proposal", "in_progress", "done"]:
            resp = client.patch(
                f"/opportunities/{opp_id}/triage",
                json={"next_action": status},
                headers=operator_a_headers,
            )
            assert resp.status_code == 400, f"Lost should not allow transition to {status}"

    def test_ignore_is_terminal(self, client, admin_headers, operator_a_headers):
        """Ignore cannot transition to any other status."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "ignore"},
            headers=operator_a_headers,
        )
        for status in ["pending", "follow", "prepare_proposal", "in_progress", "done", "lost"]:
            resp = client.patch(
                f"/opportunities/{opp_id}/triage",
                json={"next_action": status},
                headers=operator_a_headers,
            )
            assert resp.status_code == 400, f"Ignore should not allow transition to {status}"

    def test_invalid_transition_error_message(self, client, admin_headers, operator_a_headers):
        """Invalid transition should return descriptive error."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "done"},
            headers=operator_a_headers,
        )
        resp = client.patch(
            f"/opportunities/{opp_id}/triage",
            json={"next_action": "pending"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 400
        assert "Cannot transition" in resp.json()["detail"]

    def test_full_f2_cycle(self, client, admin_headers, operator_a_headers):
        """Complete F2 cycle: pending (default) → follow → prepare_proposal → in_progress → done."""
        opp_id = self._create_opportunity(client, admin_headers, operator_a_headers)
        # Opportunity defaults to "pending", so we start from there
        transitions = [
            ("follow", 200),
            ("prepare_proposal", 200),
            ("in_progress", 200),
            ("done", 200),
        ]
        for status, expected_code in transitions:
            resp = client.patch(
                f"/opportunities/{opp_id}/triage",
                json={"next_action": status},
                headers=operator_a_headers,
            )
            assert resp.status_code == expected_code, f"Transition to {status} failed"


class TestBulkTriageTransitions:
    """Bulk triage should respect transition validation."""

    def _create_opportunities(self, client, admin_headers, operator_a_headers, count=3):
        """Create multiple opportunities."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-bulk"}, headers=admin_headers)
        ids = []
        for i in range(count):
            resp = client.post(
                "/opportunities",
                json={
                    "source": "manual",
                    "external_url": f"https://example.com/bulk-{i}",
                    "title": f"Bulk test {i}",
                    "description": "Test",
                    "captured_at": "2026-10-31T12:00:00-03:00",
                },
                headers=operator_a_headers,
            )
            assert resp.status_code == 200
            ids.append(resp.json()["id"])
        return ids

    def test_bulk_triage_respects_transitions(self, client, admin_headers, operator_a_headers):
        """Bulk triage skips opportunities with invalid transitions."""
        ids = self._create_opportunities(client, admin_headers, operator_a_headers, 2)
        # Set one to done (terminal)
        client.patch(
            f"/opportunities/{ids[0]}/triage",
            json={"next_action": "in_progress"},
            headers=operator_a_headers,
        )
        client.patch(
            f"/opportunities/{ids[0]}/triage",
            json={"next_action": "done"},
            headers=operator_a_headers,
        )
        # Bulk triage to follow — should skip the done one
        resp = client.post(
            "/opportunities/bulk-triage",
            json={"opportunity_ids": ids, "next_action": "follow"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"] == 1  # Only the non-terminal one
        assert data["skipped"] == 1  # The done one
