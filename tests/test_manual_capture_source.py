"""WP-130 — Configurable source in manual opportunity capture."""

import pytest


class TestManualCaptureSource:
    """Test that 'manual' is a valid source for OpportunityCreate."""

    def test_create_opportunity_with_manual_source(self, client, admin_headers, operator_a_headers):
        """Creating an opportunity with source='manual' should succeed."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-manual"}, headers=admin_headers)
        resp = client.post(
            "/opportunities",
            json={
                "source": "manual",
                "external_url": "https://example.com/manual-001",
                "title": "Manual capture test",
                "description": "Test manual capture with configurable source",
                "captured_at": "2026-10-31T12:00:00-03:00",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "manual"
        assert data["title"] == "Manual capture test"

    def test_create_opportunity_with_99freelas_source(self, client, admin_headers, operator_a_headers):
        """Creating an opportunity with source='99freelas' should still work."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-99"}, headers=admin_headers)
        resp = client.post(
            "/opportunities",
            json={
                "source": "99freelas",
                "external_url": "https://99freelas.com/opp-001",
                "title": "99Freelas test",
                "description": "Test 99freelas source",
                "captured_at": "2026-10-31T12:00:00-03:00",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["source"] == "99freelas"

    def test_create_opportunity_with_intake_source(self, client, admin_headers, operator_a_headers):
        """Creating an opportunity with source='intake' should work."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-intake"}, headers=admin_headers)
        resp = client.post(
            "/opportunities",
            json={
                "source": "intake",
                "external_url": "https://example.com/intake-001",
                "title": "Intake test",
                "description": "Test intake source",
                "captured_at": "2026-10-31T12:00:00-03:00",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["source"] == "intake"

    def test_create_opportunity_with_review_queue_source(self, client, admin_headers, operator_a_headers):
        """Creating an opportunity with source='review_queue' should work."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-review"}, headers=admin_headers)
        resp = client.post(
            "/opportunities",
            json={
                "source": "review_queue",
                "external_url": "https://example.com/review-001",
                "title": "Review queue test",
                "description": "Test review_queue source",
                "captured_at": "2026-10-31T12:00:00-03:00",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["source"] == "review_queue"

    def test_create_opportunity_with_invalid_source(self, client, admin_headers, operator_a_headers):
        """Creating an opportunity with invalid source should fail."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-invalid"}, headers=admin_headers)
        resp = client.post(
            "/opportunities",
            json={
                "source": "invalid_source",
                "external_url": "https://example.com/invalid-001",
                "title": "Invalid source test",
                "description": "Test invalid source",
                "captured_at": "2026-10-31T12:00:00-03:00",
            },
            headers=operator_a_headers,
        )
        assert resp.status_code == 422

    def test_list_opportunities_shows_source(self, client, admin_headers, operator_a_headers):
        """Listing opportunities should include the source field."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-list"}, headers=admin_headers)
        # Create opportunity with manual source
        client.post(
            "/opportunities",
            json={
                "source": "manual",
                "external_url": "https://example.com/list-001",
                "title": "List test manual",
                "description": "Test",
                "captured_at": "2026-10-31T12:00:00-03:00",
            },
            headers=operator_a_headers,
        )
        resp = client.get("/opportunities", headers=operator_a_headers)
        assert resp.status_code == 200
        opportunities = resp.json()
        assert len(opportunities) >= 1
        # Find our manual source opportunity
        manual_opp = [o for o in opportunities if o["source"] == "manual"]
        assert len(manual_opp) >= 1


class TestManualCaptureUIContract:
    """Test the UI contract for manual capture with configurable source."""

    def test_capture_form_has_source_select(self):
        """The capture form should have a source select element."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="capture-source"' in content
        assert 'name="source"' in content
        assert '<option value="manual">' in content
        assert '<option value="99freelas">' in content

    def test_capture_form_source_is_required(self):
        """The source select should be required."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        # Find the source select and check it has required attribute
        assert '<select id="capture-source" name="source" required>' in content

    def test_app_js_uses_selected_source(self):
        """The app.js should use the selected source from the form."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        # Should use fields.source instead of hardcoded "99freelas"
        assert 'source: fields.source' in content
        # Should NOT have hardcoded "99freelas" in the capture form handler
        assert 'source: "99freelas"' not in content

    def test_source_literal_includes_manual(self):
        """The OpportunityCreate schema should include 'manual' as a valid source."""
        with open("app/schemas.py") as f:
            content = f.read()
        assert '"manual"' in content
        # Check it's in the OpportunityCreate source Literal
        assert 'Literal["99freelas", "intake", "review_queue", "manual"]' in content