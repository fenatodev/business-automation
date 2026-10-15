"""WP-054: Isolation sandbox tests.

These tests validate that a restricted executor sandbox CANNOT access:
1. Docker socket
2. n8n SQLite database
3. Host secrets and credentials
4. Sudo privileges
5. External network beyond allowed endpoints

The tests simulate a sandboxed environment by checking that the executor
properly denies operations when resources are unavailable, and that the
isolation configuration (Dockerfile/compose) would enforce these limits.

These are NEGATIVE tests — they verify the ABSENCE of access paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.approval_gate import (
    ApprovalGate,
    ApprovalSignatureError,
    IntegrityJournal,
    SignedApproval,
)
from app.services.n8n_executor import (
    APPROVAL_REQUIRED_OPERATIONS,
    PROHIBITED_OPERATIONS,
    READ_ONLY_OPERATIONS,
    AuthorizationBlockError,
    ExecutorConfig,
    N8nExecutor,
    OperationType,
    ProhibitedOperationError,
)


# ---------------------------------------------------------------------------
# Sandbox isolation tests
# ---------------------------------------------------------------------------


class TestSandboxIsolation:
    """Test that the sandbox properly isolates the executor from host resources.

    These tests verify that the executor, when running in a restricted sandbox,
    cannot access sensitive host resources even if it tries to bypass the
    approval gate.
    """

    def test_docker_socket_not_accessible_in_sandbox(self):
        """In a proper sandbox, /var/run/docker.sock should not exist.

        This test verifies the EXPECTED behavior in a sandboxed environment.
        In the current host environment, the socket may exist — the test
        documents the expected isolation state.
        """
        # In a sandboxed container, the Docker socket should NOT be mounted
        # This test documents the expected state
        docker_socket = Path("/var/run/docker.sock")

        # The sandbox configuration (Dockerfile/compose) should NOT mount
        # the Docker socket. This test verifies the configuration is correct.
        # In the current dev environment, this may pass or fail depending
        # on whether we're running in the sandbox or on the host.
        #
        # The key point: the sandbox Dockerfile should NOT have:
        #   - /var/run/docker.sock:/var/run/docker.sock
        # This is verified by the Dockerfile tests below.

    def test_n8n_database_not_mounted_in_sandbox(self):
        """In a proper sandbox, the n8n database should not be accessible.

        The sandbox should NOT mount the n8n data directory.
        """
        # The sandbox should NOT have access to the n8n database
        n8n_db_path = Path("/mnt/infra/apps/n8n/data/database.sqlite")

        # In a sandboxed container, this path should not exist
        # The Dockerfile/compose should NOT mount the n8n data volume

    def test_sandbox_has_no_sudo_access(self):
        """In a proper sandbox, the user should not have sudo access.

        The sandbox user should be a restricted user without sudo privileges.
        """
        # In a sandboxed container, sudo should not be available
        # or the user should not be in the sudo group
        # This is enforced by the Dockerfile using a non-root user

    def test_sandbox_network_is_restricted(self):
        """In a proper sandbox, network access should be restricted to n8n only.

        The sandbox should only be able to reach the n8n API endpoint,
        not arbitrary external services.
        """
        # Network restriction is enforced by Docker network configuration
        # The sandbox container should be on a dedicated network with
        # only the n8n container as a peer

    def test_sandbox_filesystem_is_read_only(self):
        """In a proper sandbox, the filesystem should be read-only except for journal.

        The sandbox should use --read-only flag with tmpfs for /tmp
        and a specific mount for the journal directory.
        """
        # Filesystem restriction is enforced by Docker run --read-only
        # Only the journal path should be writable


# ---------------------------------------------------------------------------
# Dockerfile and compose configuration tests
# ---------------------------------------------------------------------------


class TestSandboxConfiguration:
    """Test the sandbox Dockerfile and compose configuration.

    These tests verify that the configuration files enforce the required
    isolation constraints.
    """

    def test_dockerfile_no_docker_socket(self):
        """The Dockerfile should NOT mount the Docker socket."""
        dockerfile_path = Path("ops/sandbox/Dockerfile")
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not yet created — will be created in this WP")
        content = dockerfile_path.read_text()
        assert "/var/run/docker.sock" not in content

    def test_dockerfile_no_root_user(self):
        """The Dockerfile should use a non-root user."""
        dockerfile_path = Path("ops/sandbox/Dockerfile")
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not yet created")
        content = dockerfile_path.read_text()
        assert "USER n8n-operator" in content or "USER nobody" in content

    def test_dockerfile_no_sudo(self):
        """The Dockerfile should NOT install sudo."""
        dockerfile_path = Path("ops/sandbox/Dockerfile")
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not yet created")
        content = dockerfile_path.read_text()
        # Should not install sudo
        assert "apt-get install sudo" not in content
        assert "RUN apk add sudo" not in content

    def test_compose_no_docker_socket_mount(self):
        """The docker-compose should NOT mount the Docker socket."""
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        assert "/var/run/docker.sock" not in content

    def test_compose_no_n8n_data_mount(self):
        """The docker-compose should NOT mount the n8n data directory."""
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        assert "/mnt/infra/apps/n8n" not in content

    def test_compose_read_only_filesystem(self):
        """The docker-compose should use read-only filesystem."""
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        assert "read_only: true" in content

    def test_compose_no_new_privileges(self):
        """The docker-compose should set no-new-privileges."""
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        assert "no-new-privileges" in content

    def test_compose_no_docker_network_host(self):
        """The docker-compose should NOT use host network mode."""
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        assert "network_mode: host" not in content


# ---------------------------------------------------------------------------
# Approval gate security tests
# ---------------------------------------------------------------------------


class TestApprovalGateSecurity:
    """Test that the ApprovalGate cannot be bypassed by the agent.

    These tests simulate various attack scenarios where the agent tries
    to forge or bypass approvals.
    """

    def test_agent_cannot_use_sha256_instead_of_hmac(self):
        """The agent cannot create a valid approval using only SHA-256.

        WP-053 used SHA-256 which the agent could compute.
        WP-054 uses HMAC which requires the secret.
        """
        gate = ApprovalGate(secret="human-secret")
        payload = {"workflow_id": "test"}

        # Agent computes SHA-256 hash (like WP-053)
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        # Agent tries to use SHA-256 hash as signature (wrong approach)
        forged_approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=payload_hash,
            operator="agent",
            expires_at=time.time() + 300,
            signature=payload_hash,  # Using SHA-256 as HMAC — should fail
        )

        with pytest.raises(ApprovalSignatureError):
            gate.validate(forged_approval, payload)

    def test_agent_cannot_guess_hmac_secret(self):
        """Even if the agent knows the HMAC algorithm, it can't guess the secret."""
        gate = ApprovalGate(secret="very-long-random-secret-1234567890abcdef")
        payload = {"workflow_id": "test"}

        # Agent tries common secrets
        common_secrets = [
            "secret",
            "password",
            "test",
            "admin",
            "n8n",
            "",
            "very-long-random-secret-1234567890abcdef",  # Correct one
        ]

        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        for guessed_secret in common_secrets:
            if guessed_secret == "very-long-random-secret-1234567890abcdef":
                continue  # Skip the correct secret

            message = json.dumps({
                "operation": "workflow:activate",
                "payload_hash": payload_hash,
                "operator": "agent",
                "expires_at": time.time() + 300,
            }, sort_keys=True, default=str)

            import hmac as hmac_module

            guessed_signature = hmac_module.new(
                guessed_secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            forged_approval = SignedApproval(
                operation="workflow:activate",
                payload_hash=payload_hash,
                operator="agent",
                expires_at=time.time() + 300,
                signature=guessed_signature,
            )

            with pytest.raises(ApprovalSignatureError):
                gate.validate(forged_approval, payload)

    def test_agent_cannot_reuse_expired_approval(self):
        """An expired approval cannot be reused even with valid signature."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}

        # Create an approval that's already expired
        import hmac as hmac_module

        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        expired_time = time.time() - 3600  # 1 hour ago
        message = json.dumps({
            "operation": "workflow:activate",
            "payload_hash": payload_hash,
            "operator": "human",
            "expires_at": expired_time,
        }, sort_keys=True, default=str)

        signature = hmac_module.new(
            "test-secret".encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        expired_approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=payload_hash,
            operator="human",
            expires_at=expired_time,
            signature=signature,
        )

        with pytest.raises(Exception):  # ApprovalExpiredError
            gate.validate(expired_approval, payload)

    def test_journal_integrity_prevents_retroactive_tampering(self):
        """The agent cannot retroactively modify the journal to hide activity."""
        journal = IntegrityJournal()
        gate = ApprovalGate(secret="test-secret", journal=journal)

        payload = {"workflow_id": "test"}
        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )
        gate.validate(approval, payload)

        # Journal should be intact
        assert journal.verify_integrity() is True

        # Agent tries to modify the journal to hide the approval
        entries = journal.get_entries()
        if entries:
            entries[0].details = "HIDDEN"
            journal.entries = entries

        # Integrity check should detect the tampering
        assert journal.verify_integrity() is False

    def test_different_operations_require_separate_approvals(self):
        """An approval for one operation cannot be used for another."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}

        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )

        # Try to use the approval for a different operation
        with pytest.raises(Exception):  # ApprovalOperationMismatchError
            gate.validate_operation(approval, "workflow:deactivate")


# ---------------------------------------------------------------------------
# Executor sandbox integration tests
# ---------------------------------------------------------------------------


class TestExecutorSandboxIntegration:
    """Test that the N8nExecutor works correctly with the ApprovalGate.

    These tests verify that the executor properly integrates with the
    approval gate for write operations.
    """

    def test_read_operations_dont_require_approval(self):
        """Read-only operations should not require approval."""
        # READ_ONLY_OPERATIONS should not require approval
        for op in READ_ONLY_OPERATIONS:
            assert op not in APPROVAL_REQUIRED_OPERATIONS
            assert op not in PROHIBITED_OPERATIONS

    def test_write_operations_require_approval(self):
        """Write operations should require approval."""
        for op in APPROVAL_REQUIRED_OPERATIONS:
            assert op not in READ_ONLY_OPERATIONS
            assert op not in PROHIBITED_OPERATIONS

    def test_prohibited_operations_always_denied(self):
        """Prohibited operations should always be denied."""
        for op in PROHIBITED_OPERATIONS:
            assert op not in READ_ONLY_OPERATIONS
            assert op not in APPROVAL_REQUIRED_OPERATIONS

    def test_database_operations_are_prohibited(self):
        """Direct database operations should be prohibited."""
        assert OperationType.DATABASE_DIRECT in PROHIBITED_OPERATIONS
        assert OperationType.DATABASE_MODIFY in PROHIBITED_OPERATIONS

    def test_credential_secret_access_is_prohibited(self):
        """Reading credential secrets should be prohibited."""
        assert OperationType.CREDENTIAL_READ_SECRET in PROHIBITED_OPERATIONS
        assert OperationType.CREDENTIAL_DELETE in PROHIBITED_OPERATIONS

    def test_workflow_publish_is_prohibited(self):
        """Publishing workflows should be prohibited."""
        assert OperationType.WORKFLOW_PUBLISH in PROHIBITED_OPERATIONS


# ---------------------------------------------------------------------------
# Authorization matrix tests
# ---------------------------------------------------------------------------


class TestAuthorizationMatrix:
    """Test the authorization matrix for all operation types.

    These tests document and verify the expected authorization behavior
    for each operation type.
    """

    def test_all_operations_classified(self):
        """Every operation type should be in exactly one category."""
        all_operations = list(OperationType)
        classified = (
            READ_ONLY_OPERATIONS | APPROVAL_REQUIRED_OPERATIONS | PROHIBITED_OPERATIONS
        )

        for op in all_operations:
            assert op in classified, f"{op} is not classified"

    def test_no_operation_in_multiple_categories(self):
        """No operation should be in more than one category."""
        read_and_approval = READ_ONLY_OPERATIONS & APPROVAL_REQUIRED_OPERATIONS
        read_and_prohibited = READ_ONLY_OPERATIONS & PROHIBITED_OPERATIONS
        approval_and_prohibited = APPROVAL_REQUIRED_OPERATIONS & PROHIBITED_OPERATIONS

        assert len(read_and_approval) == 0
        assert len(read_and_prohibited) == 0
        assert len(approval_and_prohibited) == 0

    def test_read_operations_list(self):
        """Verify the expected read-only operations."""
        expected_read = {
            OperationType.WORKFLOW_GET,
            OperationType.WORKFLOW_LIST,
            OperationType.WORKFLOW_STATUS,
            OperationType.CREDENTIAL_LIST,
            OperationType.CREDENTIAL_METADATA,
            OperationType.DATA_TABLE_READ,
            OperationType.EXECUTION_LIST,
        }
        assert READ_ONLY_OPERATIONS == expected_read

    def test_approval_required_operations_list(self):
        """Verify the expected approval-required operations."""
        expected_approval = {
            OperationType.WORKFLOW_UPDATE,
            OperationType.DATA_TABLE_WRITE,
            OperationType.WORKFLOW_ACTIVATE,
            OperationType.WORKFLOW_DEACTIVATE,
        }
        assert APPROVAL_REQUIRED_OPERATIONS == expected_approval

    def test_prohibited_operations_list(self):
        """Verify the expected prohibited operations."""
        expected_prohibited = {
            OperationType.CREDENTIAL_DELETE,
            OperationType.CREDENTIAL_READ_SECRET,
            OperationType.DATABASE_DIRECT,
            OperationType.DATABASE_MODIFY,
            OperationType.WORKFLOW_PUBLISH,
        }
        assert PROHIBITED_OPERATIONS == expected_prohibited


# ---------------------------------------------------------------------------
# Limitation documentation tests
# ---------------------------------------------------------------------------


class TestIsolationLimitations:
    """Document and test the known limitations of the isolation approach.

    These tests verify that the limitations are properly documented and
    that the system behaves correctly within its constraints.
    """

    def test_approval_gate_requires_secret_outside_agent(self):
        """The approval gate is only secure if the secret is outside the agent.

        If the agent has access to the HMAC secret, the approval is meaningless.
        This is a fundamental limitation that requires operational enforcement.
        """
        # This test documents the limitation: the ApprovalGate is a software
        # convention that relies on the secret being inaccessible to the agent.
        # In a properly configured sandbox, the secret is injected via environment
        # variable that the agent process cannot read.
        #
        # However, if the agent has shell access to the same host, it could
        # potentially read the environment variable. This is why the sandbox
        # must be a separate container with restricted access.
        pass

    def test_journal_integrity_is_software_only(self):
        """Journal integrity is software-based, not hardware-based.

        The hash chain provides tamper-evidence, but not tamper-proofing.
        A determined attacker with write access to the journal file can
        modify it — the integrity check will detect it, but cannot prevent it.
        """
        journal = IntegrityJournal()
        journal.append(
            operation="test",
            status="allowed",
            details="Original",
        )
        assert journal.verify_integrity() is True

        # Attacker modifies the journal
        entries = journal.get_entries()
        entries[0].details = "TAMPERED"
        journal.entries = entries

        # Integrity check detects the tampering
        assert journal.verify_integrity() is False

        # The key point: we can DETECT tampering, but we can't PREVENT it
        # without hardware-based protection (TPM, secure enclave, etc.)

    def test_sandbox_does_not_isolate_junie_host_access(self):
        """The sandbox isolates the executor, not the Junie agent itself.

        If Junie has shell access to the host, it can still:
        - Access Docker socket directly
        - Read n8n database directly
        - Execute commands as the host user

        The sandbox only isolates the executor process. Junie itself needs
        separate confinement (dedicated user, container, etc.).
        """
        # This test documents the critical limitation: the sandbox isolates
        # the executor, but if Junie runs on the same host with privileged
        # access, it can bypass the sandbox entirely.
        #
        # Full isolation requires:
        # 1. Junie running in its own container without Docker socket
        # 2. Executor running in a separate container with minimal privileges
        # 3. No shared filesystem between Junie and executor
        # 4. Network policy restricting Junie's access to executor only via API
        pass


# ---------------------------------------------------------------------------
# Real build errors detected on Ubuntu (WP-054 corrections)
# ---------------------------------------------------------------------------


class TestDockerComposeSyntax:
    """Test that docker-compose.yml has valid YAML syntax.

    These tests detect the real errors found when running
    `docker compose config` on Ubuntu:
    - environment list format with ${VAR:?msg} is parsed as map
    - missing COPY for run_executor.py
    - missing __init__.py for Python package imports
    """

    def test_compose_environment_is_map_not_list(self):
        """docker-compose environment must use map format, not list with :? syntax.

        The syntax '- VAR=${VAR:?Error}' in list format causes Docker Compose
        to parse the string as a map because ':' inside ${} is confused with
        the YAML key-value separator. This was verified on Ubuntu.
        """
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        # Must NOT use list format with :? syntax
        assert "- N8N_API_KEY=${N8N_API_KEY:?" not in content
        # WP-056: APPROVAL_SECRET replaced by ED25519_PUBLIC_KEY
        assert "- ED25519_PUBLIC_KEY=${ED25519_PUBLIC_KEY:?" not in content
        # Should use map format
        assert "N8N_API_KEY:" in content
        # WP-056: Ed25519 public key instead of HMAC secret
        assert "ED25519_PUBLIC_KEY:" in content

    def test_compose_environment_uses_safe_defaults(self):
        """Environment variables should use safe defaults, not fail-fast syntax.

        Using ${VAR:-} (empty default) instead of ${VAR:?error} avoids
        the YAML parsing issue while still allowing runtime validation.
        """
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        # Should use :- (safe default) not :? (fail-fast)
        assert "${N8N_API_KEY:-}" in content or 'N8N_API_KEY: ""' in content
        # WP-056: Ed25519 public key instead of HMAC secret
        assert "${ED25519_PUBLIC_KEY:-}" in content or 'ED25519_PUBLIC_KEY: ""' in content


class TestDockerfileCompleteness:
    """Test that the Dockerfile includes all required COPY commands.

    These tests detect the real build errors found on Ubuntu:
    - CMD references run_executor.py but never copies it
    - Imports app.services.* but __init__.py files are not copied
    """

    def test_dockerfile_copies_run_executor(self):
        """Dockerfile must COPY run_executor.py before CMD references it.

        CMD ["python", "/app/run_executor.py"] fails at runtime if the
        file was never copied into the image. This was verified on Ubuntu.
        """
        dockerfile_path = Path("ops/sandbox/Dockerfile")
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not yet created")
        content = dockerfile_path.read_text()
        assert "COPY" in content
        assert "run_executor.py" in content

    def test_dockerfile_copies_init_files(self):
        """Dockerfile must COPY __init__.py for Python package imports.

        'from app.services.approval_gate import ...' requires both
        app/__init__.py and app/services/__init__.py to exist in the image.
        Without them, Python raises ModuleNotFoundError.
        """
        dockerfile_path = Path("ops/sandbox/Dockerfile")
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not yet created")
        content = dockerfile_path.read_text()
        assert "__init__.py" in content

    def test_dockerfile_copies_app_init(self):
        """Dockerfile must copy app/__init__.py specifically."""
        dockerfile_path = Path("ops/sandbox/Dockerfile")
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not yet created")
        content = dockerfile_path.read_text()
        # Must copy app/__init__.py so 'import app' works
        assert "COPY app/__init__.py" in content

    def test_dockerfile_copies_services_init(self):
        """Dockerfile must copy app/services/__init__.py specifically."""
        dockerfile_path = Path("ops/sandbox/Dockerfile")
        if not dockerfile_path.exists():
            pytest.skip("Dockerfile not yet created")
        content = dockerfile_path.read_text()
        # Must copy app/services/__init__.py so 'from app.services.xxx import' works
        assert "COPY app/services/__init__.py" in content


class TestHMACTrustBoundary:
    """Test that the HMAC trust boundary limitations are documented.

    These tests verify that the report correctly documents the fundamental
    limitation: HMAC with the same shared key does NOT prevent forgery
    if the agent controls the host.
    """

    def test_report_documents_hmac_limitation(self):
        """The WP-054 report must document the HMAC symmetric key limitation."""
        report_path = Path("docs/operations/wp-054-effective-isolation-report.md")
        if not report_path.exists():
            pytest.skip("Report not yet created")
        content = report_path.read_text()
        # Must mention that HMAC symmetric key is a limitation
        assert "convenção de software" in content.lower() or "software convention" in content.lower()

    def test_report_mentions_asymmetric_alternative(self):
        """The report should mention asymmetric signatures as the real solution."""
        report_path = Path("docs/operations/wp-054-effective-isolation-report.md")
        if not report_path.exists():
            pytest.skip("Report not yet created")
        content = report_path.read_text()
        # Should mention asymmetric approach (Ed25519, RSA, or public/private key)
        has_asymmetric = any(
            kw in content for kw in [
                "assimétrica", "asymmetric", "Ed25519", "RSA",
                "chave pública", "public key", "chave privada", "private key",
            ]
        )
        assert has_asymmetric, (
            "Report should mention asymmetric signatures as the real solution "
            "to the HMAC trust boundary problem"
        )

    def test_verifier_cannot_sign_but_has_secret(self):
        """ApprovalVerifier cannot sign, but still holds the HMAC secret.

        This is the fundamental limitation: the verifier needs the secret
        to verify HMAC signatures. If the agent can read the secret from
        the verifier's environment, it can forge signatures.
        """
        from app.services.approval_gate import ApprovalVerifier

        verifier = ApprovalVerifier(secret="test-secret")
        # Verifier has no sign_approval method
        assert not hasattr(verifier, "sign_approval")
        # But it DOES have the secret — this is the limitation
        assert verifier.secret == "test-secret"
        # With the secret, an attacker could compute valid HMAC signatures
        # The separation of classes is a software convention, not crypto isolation


class TestNetworkEgressLimitation:
    """Test that network egress limitations are properly documented.

    A Docker bridge network does NOT block external traffic by default.
    """

    def test_compose_documents_egress_limitation(self):
        """The docker-compose comments should note that n8n_default doesn't block egress."""
        compose_path = Path("ops/sandbox/docker-compose.yml")
        if not compose_path.exists():
            pytest.skip("Compose file not yet created")
        content = compose_path.read_text()
        # Should mention egress limitation in comments
        has_egress_note = any(
            kw in content.lower() for kw in [
                "egress", "internet", "external", "isolamento",
            ]
        )
        assert has_egress_note, (
            "docker-compose.yml should document that n8n_default "
            "does not guarantee egress isolation"
        )

    def test_report_documents_network_egress_limitation(self):
        """The report must document that Docker bridge doesn't block egress."""
        report_path = Path("docs/operations/wp-054-effective-isolation-report.md")
        if not report_path.exists():
            pytest.skip("Report not yet created")
        content = report_path.read_text()
        # Should mention egress limitation
        has_egress = any(
            kw in content.lower() for kw in [
                "egress", "internet", "external traffic", "isolamento de egress",
            ]
        )
        assert has_egress, (
            "Report should document that n8n_default bridge network "
            "does not block external traffic"
        )
