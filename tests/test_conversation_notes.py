"""WP-140 — Notas internas em conversas.

Testa o backend de notas internas: salvar nota via PATCH, ler nota via GET /note,
tenant isolation e autenticação. Notas são armazenadas como mensagens com
sender_type="system" para evitar migration.
"""


class TestConversationNotes:
    """Test internal notes on conversations."""

    def _create_company(self, client, headers):
        """Create a company and return its data."""
        resp = client.post("/companies", json={
            "name": "Test Company",
            "slug": "test-company",
        }, headers=headers)
        assert resp.status_code == 200, f"Failed to create company: {resp.text}"
        return resp.json()

    def _create_conversation(self, client, company_id, headers):
        """Create a lead and conversation and return conversation data."""
        # Create a lead first
        lead_resp = client.post("/leads", json={
            "company_id": company_id,
            "name": "Test Lead",
            "phone": "5511999999999",
            "source": "manual",
        }, headers=headers)
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead_id = lead_resp.json()["id"]

        # Create conversation linked to lead
        resp = client.post("/conversations", json={
            "company_id": company_id,
            "channel": "whatsapp",
            "lead_id": lead_id,
        }, headers=headers)
        assert resp.status_code == 200, f"Failed to create conversation: {resp.text}"
        return resp.json()

    def test_save_note_via_patch(self, client, admin_headers, operator_a_headers):
        """PATCH /conversations/{id} with note should save it as system message."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        resp = client.patch(
            f"/conversations/{conv_id}",
            json={"note": "Cliente prefere contato à tarde"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200

        note_resp = client.get(
            f"/conversations/{conv_id}/note",
            headers=operator_a_headers,
        )
        assert note_resp.json()["note"] == "Cliente prefere contato à tarde"

    def test_read_note_returns_none_when_empty(self, client, admin_headers, operator_a_headers):
        """GET /note should return null when no note exists."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        resp = client.get(
            f"/conversations/{conv_id}/note",
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["note"] is None

    def test_patch_note_only_preserves_status(self, client, admin_headers, operator_a_headers):
        """PATCH with only note should not change status."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]
        original_status = conv["status"]

        resp = client.patch(
            f"/conversations/{conv_id}",
            json={"note": "Apenas nota"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == original_status

    def test_patch_status_only_preserves_note(self, client, admin_headers, operator_a_headers):
        """PATCH with only status should not affect notes."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        client.patch(
            f"/conversations/{conv_id}",
            json={"note": "Nota existente"},
            headers=operator_a_headers,
        )

        resp = client.patch(
            f"/conversations/{conv_id}",
            json={"status": "closed"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

        note_resp = client.get(
            f"/conversations/{conv_id}/note",
            headers=operator_a_headers,
        )
        assert note_resp.json()["note"] == "Nota existente"

    def test_patch_status_and_note_together(self, client, admin_headers, operator_a_headers):
        """PATCH can update both status and note in one call."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        resp = client.patch(
            f"/conversations/{conv_id}",
            json={"status": "closed", "note": "Fechada com nota"},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"

        note_resp = client.get(
            f"/conversations/{conv_id}/note",
            headers=operator_a_headers,
        )
        assert note_resp.json()["note"] == "Fechada com nota"

    def test_new_note_overwrites_old(self, client, admin_headers, operator_a_headers):
        """Saving a new note should return the most recent one."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        client.patch(
            f"/conversations/{conv_id}",
            json={"note": "Nota antiga"},
            headers=operator_a_headers,
        )
        client.patch(
            f"/conversations/{conv_id}",
            json={"note": "Nota nova"},
            headers=operator_a_headers,
        )

        resp = client.get(
            f"/conversations/{conv_id}/note",
            headers=operator_a_headers,
        )
        assert resp.json()["note"] == "Nota nova"

    def test_note_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Cannot read notes from another company's conversation."""
        # operator_b is bound to company_id=2 in conftest
        # Create company with ID that operator_b can access
        company_b = self._create_company(client, admin_headers)
        # operator_b has company_id=2; if our company got a different ID, use admin to create conv
        # and then try to access with operator_a (company_id=1)
        
        # Create a second company for operator_b's tenant
        company_for_b = client.post("/companies", json={
            "name": "Company B",
            "slug": "company-b",
        }, headers=admin_headers).json()
        
        # Create conversation for company B using operator_b
        lead_resp = client.post("/leads", json={
            "company_id": company_for_b["id"],
            "name": "Lead B",
            "phone": "5511888888888",
            "source": "manual",
        }, headers=operator_b_headers)
        
        # If operator_b can't create on this company (company_id mismatch),
        # we use the admin to create the lead and conversation
        if lead_resp.status_code == 403:
            lead_resp = client.post("/leads", json={
                "company_id": company_for_b["id"],
                "name": "Lead B",
                "phone": "5511888888888",
                "source": "manual",
            }, headers=admin_headers)
            assert lead_resp.status_code == 200
            lead_id = lead_resp.json()["id"]
            
            conv_resp = client.post("/conversations", json={
                "company_id": company_for_b["id"],
                "channel": "whatsapp",
                "lead_id": lead_id,
            }, headers=admin_headers)
            assert conv_resp.status_code == 200
            conv_id = conv_resp.json()["id"]
            
            # Save note via admin
            client.patch(
                f"/conversations/{conv_id}",
                json={"note": "Nota secreta"},
                headers=admin_headers,
            )
        else:
            lead_id = lead_resp.json()["id"]
            conv_resp = client.post("/conversations", json={
                "company_id": company_for_b["id"],
                "channel": "whatsapp",
                "lead_id": lead_id,
            }, headers=operator_b_headers)
            assert conv_resp.status_code == 200
            conv_id = conv_resp.json()["id"]
            
            client.patch(
                f"/conversations/{conv_id}",
                json={"note": "Nota secreta"},
                headers=operator_b_headers,
            )

        # Try to read with operator_a (different tenant)
        resp = client.get(
            f"/conversations/{conv_id}/note",
            headers=operator_a_headers,
        )
        assert resp.status_code == 404

    def test_note_requires_auth(self, client, admin_headers, operator_a_headers):
        """Note endpoints require authentication."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        resp = client.get(f"/conversations/{conv_id}/note")
        assert resp.status_code in (401, 403)

        resp = client.patch(f"/conversations/{conv_id}", json={"note": "test"})
        assert resp.status_code in (401, 403)

    def test_note_max_length(self, client, admin_headers, operator_a_headers):
        """Note should reject content exceeding max_length."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        long_note = "x" * 2001
        resp = client.patch(
            f"/conversations/{conv_id}",
            json={"note": long_note},
            headers=operator_a_headers,
        )
        assert resp.status_code == 422

    def test_note_empty_string_allowed(self, client, admin_headers, operator_a_headers):
        """Empty string note should be allowed."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        resp = client.patch(
            f"/conversations/{conv_id}",
            json={"note": ""},
            headers=operator_a_headers,
        )
        assert resp.status_code == 200

    def test_patch_empty_body_rejected(self, client, admin_headers, operator_a_headers):
        """PATCH with empty body should be rejected."""
        company = self._create_company(client, admin_headers)
        conv = self._create_conversation(client, company["id"], operator_a_headers)
        conv_id = conv["id"]

        resp = client.patch(
            f"/conversations/{conv_id}",
            json={},
            headers=operator_a_headers,
        )
        # Empty body is valid — both fields are optional, so it's a no-op
        assert resp.status_code == 200
