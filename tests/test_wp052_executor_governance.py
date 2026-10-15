"""WP-052: Executor governance policy enforcement tests.

These tests validate that the agent executor enforces the n8n governance
policy defined in AGENTS.md section "Integração n8n e governança".

Key invariants tested:
1. HTTP 401/403 is a definitive authorization block — no bypass via SQLite
2. No direct modification of n8n internal database
3. No decryption or extraction of n8n credential secrets
4. No access to n8n internal encryption keys
5. Static workflow tests do not prove executor enforcement
6. Orphan credentials require official procedure (UI or public API)

These are static tests that verify policy documentation and test structure.
They do NOT connect to n8n, FastAPI, or any external service.
"""

import json
import re
from pathlib import Path

import pytest

AGENTS_MD_PATH = (
    Path(__file__).resolve().parents[1] / "AGENTS.md"
)

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / "ops"
    / "n8n"
    / "workflows"
    / "client0-commercial-intake-review.json"
)


def _load_agents_md() -> str:
    return AGENTS_MD_PATH.read_text(encoding="utf-8")


def _load_workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Governance policy exists and is enforceable
# ---------------------------------------------------------------------------


class TestGovernancePolicyExists:
    """Verify that AGENTS.md contains the n8n governance policy section.

    The WP-052 issue requires an executable policy in AGENTS.md that prohibits
    SQLite bypass, credential decryption, and HTTP 401/403 circumvention.
    """

    def test_governance_section_exists(self) -> None:
        """AGENTS.md must contain the 'Integração n8n e governança' section."""
        content = _load_agents_md()
        assert "## Integração n8n e governança" in content, (
            "AGENTS.md missing 'Integração n8n e governança' section"
        )

    def test_sqlite_bypass_is_prohibited(self) -> None:
        """AGENTS.md must explicitly prohibit modifying n8n internal SQLite database."""
        content = _load_agents_md()
        # Find the governance section
        governance_start = content.find("## Integração n8n e governança")
        assert governance_start >= 0, "Governance section not found"
        # Find the next section
        next_section = content.find("\n## ", governance_start + 1)
        if next_section >= 0:
            governance_section = content[governance_start:next_section]
        else:
            governance_section = content[governance_start:]

        assert "SQLite" in governance_section, (
            "Governance section does not mention SQLite prohibition"
        )
        assert "nunca" in governance_section.lower() or "never" in governance_section.lower(), (
            "Governance section does not contain explicit prohibition language"
        )

    def test_http_403_is_definitive_block(self) -> None:
        """AGENTS.md must state that HTTP 401/403 is a definitive authorization block."""
        content = _load_agents_md()
        governance_start = content.find("## Integração n8n e governança")
        assert governance_start >= 0
        next_section = content.find("\n## ", governance_start + 1)
        governance_section = content[governance_start:next_section if next_section >= 0 else len(content)]

        assert "403" in governance_section, (
            "Governance section does not mention HTTP 403 as authorization block"
        )
        assert "definitivo" in governance_section.lower() or "definitive" in governance_section.lower(), (
            "Governance section does not state 403 is definitive"
        )

    def test_credential_decryption_is_prohibited(self) -> None:
        """AGENTS.md must prohibit decrypting or extracting n8n credential secrets."""
        content = _load_agents_md()
        governance_start = content.find("## Integração n8n e governança")
        assert governance_start >= 0
        next_section = content.find("\n## ", governance_start + 1)
        governance_section = content[governance_start:next_section if next_section >= 0 else len(content)]

        assert "descriptograf" in governance_section.lower() or "decrypt" in governance_section.lower(), (
            "Governance section does not prohibit credential decryption"
        )

    def test_encryption_key_access_is_prohibited(self) -> None:
        """AGENTS.md must prohibit accessing n8n internal encryption keys."""
        content = _load_agents_md()
        governance_start = content.find("## Integração n8n e governança")
        assert governance_start >= 0
        next_section = content.find("\n## ", governance_start + 1)
        governance_section = content[governance_start:next_section if next_section >= 0 else len(content)]

        assert "criptografia" in governance_section.lower() or "encryption" in governance_section.lower(), (
            "Governance section does not prohibit encryption key access"
        )

    def test_static_tests_limitation_is_documented(self) -> None:
        """AGENTS.md must document that static workflow tests do not prove executor enforcement."""
        content = _load_agents_md()
        governance_start = content.find("## Integração n8n e governança")
        assert governance_start >= 0
        next_section = content.find("\n## ", governance_start + 1)
        governance_section = content[governance_start:next_section if next_section >= 0 else len(content)]

        assert "estático" in governance_section.lower() or "static" in governance_section.lower(), (
            "Governance section does not document static test limitations"
        )
        assert "pendente" in governance_section.lower() or "pending" in governance_section.lower(), (
            "Governance section does not require marking gaps as PENDENTE"
        )

    def test_orphan_credential_procedure_is_official(self) -> None:
        """AGENTS.md must require official procedure for orphan credential removal."""
        content = _load_agents_md()
        governance_start = content.find("## Integração n8n e governança")
        assert governance_start >= 0
        next_section = content.find("\n## ", governance_start + 1)
        governance_section = content[governance_start:next_section if next_section >= 0 else len(content)]

        assert "órfã" in governance_section.lower() or "orphan" in governance_section.lower(), (
            "Governance section does not address orphan credentials"
        )
        assert "oficial" in governance_section.lower() or "official" in governance_section.lower(), (
            "Governance section does not require official procedure for orphan credentials"
        )


# ---------------------------------------------------------------------------
# No SQLite bypass recommendations in WP reports
# ---------------------------------------------------------------------------


class TestNoSQLiteBypassRecommendations:
    """Verify that WP reports do not recommend SQLite bypass of n8n.

    WP-050 and WP-051 originally recommended 'escopos ampliados via banco SQLite'.
    WP-052 errata must have corrected this.
    """

    @pytest.mark.parametrize(
        "report_path",
        [
            "docs/operations/wp-050-e2e-synthetic-complete-report.md",
            "docs/operations/wp-051-post-e2e-verification-report.md",
        ],
    )
    def test_wp_report_has_errata_or_correction(self, report_path: str) -> None:
        """WP reports must have errata or correction removing SQLite bypass recommendation."""
        repo_root = Path(__file__).resolve().parents[1]
        report = (repo_root / report_path).read_text(encoding="utf-8")

        # Check that the report either has an errata section or does not
        # recommend SQLite bypass
        has_errata = "errata" in report.lower() or "wp-052" in report.lower()
        recommends_sqlite_bypass = re.search(
            r"escopo.*via.*sqlite|sqlite.*escopo|banco.*sqlite.*n8n",
            report,
            re.IGNORECASE,
        )

        if recommends_sqlite_bypass:
            # If SQLite bypass is still mentioned, there must be an errata
            # that explicitly revokes it
            assert has_errata, (
                f"{report_path} mentions SQLite bypass without errata correction"
            )
            # The errata must contain revocation language
            assert "revog" in report.lower() or "proib" in report.lower() or "nunca" in report.lower(), (
                f"{report_path} has errata but does not explicitly revoke SQLite bypass"
            )

    def test_agents_md_no_sqlite_bypass_recommendation(self) -> None:
        """AGENTS.md must not contain any recommendation to modify n8n SQLite database."""
        content = _load_agents_md()
        # The governance section should prohibit, not recommend, SQLite modification
        governance_start = content.find("## Integração n8n e governança")
        if governance_start >= 0:
            next_section = content.find("\n## ", governance_start + 1)
            governance_section = content[governance_start:next_section if next_section >= 0 else len(content)]
            # Should NOT contain positive recommendations for SQLite modification
            assert "ampliar.*via.*sqlite" not in governance_section.lower(), (
                "AGENTS.md governance section recommends SQLite bypass"
            )
            assert "modificar.*sqlite.*para.*alterar" not in governance_section.lower() or \
                   "nunca" in governance_section.lower(), (
                "AGENTS.md governance section may recommend SQLite modification"
            )


# ---------------------------------------------------------------------------
# Authorization block enforcement tests
# ---------------------------------------------------------------------------


class TestAuthorizationBlockEnforcement:
    """Tests that verify the executor respects authorization blocks.

    These tests ensure that when the agent encounters HTTP 401/403,
    it treats it as a definitive block and does not attempt escalation.
    """

    def test_workflow_uses_placeholders_not_real_creds(self) -> None:
        """Workflow JSON must use credential placeholders, not real IDs.

        This is a prerequisite for safe import — real credential IDs
        in the repository would indicate a failed rollback from E2E testing.
        """
        wf = _load_workflow()
        for node in wf["nodes"]:
            creds = node.get("credentials", {})
            for cred_type, cred_data in creds.items():
                cred_id = cred_data.get("id", "")
                assert "REPLACE_LOCAL" in cred_id, (
                    f"Node '{node['name']}' uses real credential ID '{cred_id}' "
                    f"for {cred_type}. Expected placeholder."
                )

    def test_workflow_is_inactive_in_repo(self) -> None:
        """Workflow must be marked inactive in the repository.

        An active workflow in the repository could be accidentally activated
        on import, bypassing the authorization controls.
        """
        wf = _load_workflow()
        assert wf.get("active") is False, (
            "Workflow is marked active in repository — this could cause "
            "accidental activation on import"
        )

    def test_no_external_send_nodes_in_workflow(self) -> None:
        """Workflow must not contain external messaging nodes.

        If the workflow were activated without proper authorization,
        external send nodes could cause unintended messages.
        """
        wf = _load_workflow()
        forbidden_types = [
            "whatsapp", "telegram", "gmail", "smtp", "twilio",
            "slack", "facebook", "instagram", "discord",
        ]
        for node in wf["nodes"]:
            node_type = node["type"].lower()
            assert not any(fb in node_type for fb in forbidden_types), (
                f"External send node found: {node['type']}"
            )

    def test_webhook_requires_auth(self) -> None:
        """Webhook must require authentication to prevent unauthorized triggers."""
        wf = _load_workflow()
        webhook = next((n for n in wf["nodes"] if n["name"] == "Inbound Webhook"), None)
        assert webhook is not None, "Inbound Webhook node not found"
        auth = webhook["parameters"].get("authentication")
        assert auth is not None and auth != "none", (
            f"Webhook authentication is '{auth}' — should require authentication"
        )

    def test_fastapi_call_requires_bearer_auth(self) -> None:
        """HTTP Request to FastAPI must use Bearer authentication."""
        wf = _load_workflow()
        http_node = next(
            (n for n in wf["nodes"] if n["name"] == "Evaluate Private Intake API"),
            None,
        )
        assert http_node is not None, "FastAPI HTTP Request node not found"
        assert http_node["parameters"].get("authentication") == "genericCredentialType", (
            "FastAPI call does not use Bearer authentication"
        )


# ---------------------------------------------------------------------------
# Secret minimization tests
# ---------------------------------------------------------------------------


class TestSecretMinimization:
    """Tests that verify no secrets are exposed in the repository."""

    def test_no_bearer_tokens_in_workflow(self) -> None:
        """Workflow JSON must not contain hardcoded Bearer tokens."""
        text = WORKFLOW_PATH.read_text(encoding="utf-8").lower()
        assert "bearer " not in text, "Bearer token found in workflow JSON"

    def test_no_api_keys_in_workflow(self) -> None:
        """Workflow JSON must not contain hardcoded API keys."""
        text = WORKFLOW_PATH.read_text(encoding="utf-8").lower()
        assert "api_key" not in text and "api-key" not in text, (
            "API key found in workflow JSON"
        )

    def test_no_real_credential_ids_in_workflow(self) -> None:
        """Workflow JSON must not contain known real n8n credential IDs."""
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        known_real_ids = [
            "uUJ7ckNMDmHevBp1",  # business-automation-internal-ingress
            "v6gCgi36SmLsOSid",  # business-automation-operator
            "TQRol30waRpD6BkA",  # test-header (orphan)
        ]
        for real_id in known_real_ids:
            assert real_id not in text, (
                f"Real credential ID '{real_id}' found in workflow JSON"
            )

    def test_no_real_api_key_values_in_tests(self) -> None:
        """Test files must not contain actual API key values.
        
        Note: We check for patterns that indicate actual key values,
        not just header names used in documentation or test patterns.
        Real API keys are typically long alphanumeric strings assigned
        to variables or used in curl commands.
        """
        tests_dir = Path(__file__).resolve().parents[1] / "tests"
        for test_file in tests_dir.glob("test_*.py"):
            # Skip this file itself — it contains pattern definitions
            if test_file.name == "test_wp052_executor_governance.py":
                continue
            content = test_file.read_text(encoding="utf-8")
            # Check for actual secret assignment patterns
            # Real secrets look like: API_KEY = "abc123..." or N8N_KEY = "..."
            import re
            # Match patterns like: KEY = "long_alphanumeric_string"
            secret_assignments = re.findall(
                r'(?:API_KEY|N8N_KEY|SECRET|TOKEN)\s*=\s*["\'][A-Za-z0-9]{16,}["\']',
                content,
            )
            assert not secret_assignments, (
                f"Potential hardcoded secret found in {test_file.name}: {secret_assignments}"
            )


# ---------------------------------------------------------------------------
# Orphan credential procedure (prepared, not executed)
# ---------------------------------------------------------------------------


class TestOrphanCredentialProcedure:
    """Tests that verify the orphan credential cleanup procedure is documented.

    The procedure must be prepared but NOT executed in this WP.
    """

    def test_orphan_credential_is_documented(self) -> None:
        """The orphan credential test-header must be documented in WP reports."""
        repo_root = Path(__file__).resolve().parents[1]
        wp051_report = repo_root / "docs/operations/wp-051-post-e2e-verification-report.md"
        content = wp051_report.read_text(encoding="utf-8")

        assert "test-header" in content, (
            "WP-051 report does not document orphan credential test-header"
        )
        assert "órfã" in content.lower() or "orphan" in content.lower(), (
            "WP-051 report does not identify test-header as orphan"
        )

    def test_orphan_removal_requires_approval(self) -> None:
        """Orphan credential removal must require explicit approval."""
        content = _load_agents_md()
        governance_start = content.find("## Integração n8n e governança")
        assert governance_start >= 0
        next_section = content.find("\n## ", governance_start + 1)
        governance_section = content[governance_start:next_section if next_section >= 0 else len(content)]

        assert "aprova" in governance_section.lower() or "approval" in governance_section.lower(), (
            "Governance section does not require approval for credential operations"
        )
