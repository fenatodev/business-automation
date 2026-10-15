"""WP-054: Negative confinement tests for the n8n executor sandbox.

These tests verify that the executor properly denies operations when:
1. No ApprovalVerifier is configured
2. ApprovalVerifier cannot sign approvals
3. Replay attacks are detected
4. Expired approvals are rejected
5. Forged signatures are rejected
6. Prohibited operations are always denied

These are NEGATIVE tests — they verify the ABSENCE of bypass paths.
They do NOT require access to secrets or real databases.
"""

from __future__ import annotations

import hashlib
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.approval_gate import (
    ApprovalExpiredError,
    ApprovalGate,
    ApprovalOperationMismatchError,
    ApprovalPayloadMismatchError,
    ApprovalReplayError,
    ApprovalSignatureError,
    ApprovalSigner,
    ApprovalVerifier,
    IntegrityJournal,
    SignedApproval,
)
from app.services.n8n_executor import (
    APPROVAL_REQUIRED_OPERATIONS,
    PROHIBITED_OPERATIONS,
    READ_ONLY_OPERATIONS,
    ApprovalRequiredError,
    AuthorizationBlockError,
    ExecutorConfig,
    N8nExecutor,
    OperationType,
    ProhibitedOperationError,
)


# ---------------------------------------------------------------------------
# Verifier cannot sign — trust boundary enforcement
# ---------------------------------------------------------------------------


class TestVerifierCannotSign:
    """Verify that ApprovalVerifier has NO sign_approval method.

    This is the core trust boundary: the executor sandbox has a verifier
    that can validate approvals but cannot create them.
    """

    def test_verifier_has_no_sign_approval_method(self):
        """ApprovalVerifier must not have sign_approval."""
        verifier = ApprovalVerifier(secret="test-secret")
        assert not hasattr(verifier, "sign_approval"), (
            "ApprovalVerifier must not have sign_approval — "
            "this breaks the trust boundary"
        )

    def test_verifier_cannot_forge_approval(self):
        """The verifier cannot create a valid approval for itself."""
        verifier = ApprovalVerifier(secret="test-secret")

        # The verifier has no sign_approval, so it cannot create approvals
        # Even if it tries to construct one manually, it needs the secret
        # to compute a valid HMAC — but having the secret in the verifier
        # is required for verification, not signing.
        #
        # The key point: the verifier can validate but cannot CREATE.
        # An approval must come from outside (ApprovalSigner/human operator).

        # Try to construct a fake approval without proper signing
        payload = {"workflow_id": "test"}
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        fake_approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=payload_hash,
            operator="agent",
            expires_at=time.time() + 300,
            signature="fake-signature-that-wont-match",
        )

        with pytest.raises(ApprovalSignatureError):
            verifier.validate(fake_approval, payload)

    def test_signer_can_sign(self):
        """ApprovalSigner can create valid approvals."""
        signer = ApprovalSigner(secret="test-secret")
        payload = {"workflow_id": "test"}

        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )

        assert approval.operation == "workflow:activate"
        assert approval.operator == "human-admin"
        assert approval.signature != ""

    def test_signer_approval_verifies(self):
        """An approval signed by ApprovalSigner verifies with ApprovalVerifier."""
        secret = "test-secret"
        signer = ApprovalSigner(secret=secret)
        verifier = ApprovalVerifier(secret=secret)
        payload = {"workflow_id": "test"}

        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )

        # Should verify successfully
        result = verifier.validate(approval, payload)
        assert result is True


# ---------------------------------------------------------------------------
# Replay prevention
# ---------------------------------------------------------------------------


class TestReplayPrevention:
    """Verify that approvals can only be used once."""

    def test_reuse_same_approval_fails(self):
        """Using the same approval twice should fail on the second use."""
        secret = "test-secret"
        signer = ApprovalSigner(secret=secret)
        verifier = ApprovalVerifier(secret=secret)
        payload = {"workflow_id": "test"}

        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )

        # First use — should succeed
        verifier.validate(approval, payload)

        # Second use — should fail with replay error
        with pytest.raises(ApprovalReplayError):
            verifier.validate(approval, payload)

    def test_different_payloads_dont_cause_replay(self):
        """Approvals for different payloads should not interfere."""
        secret = "test-secret"
        signer = ApprovalSigner(secret=secret)
        verifier = ApprovalVerifier(secret=secret)

        approval1 = signer.sign_approval(
            operation="workflow:activate",
            payload={"workflow_id": "test-1"},
            operator="human-admin",
        )
        approval2 = signer.sign_approval(
            operation="workflow:activate",
            payload={"workflow_id": "test-2"},
            operator="human-admin",
        )

        # Both should verify independently
        verifier.validate(approval1, {"workflow_id": "test-1"})
        verifier.validate(approval2, {"workflow_id": "test-2"})


# ---------------------------------------------------------------------------
# Executor requires verifier for write operations
# ---------------------------------------------------------------------------


class TestExecutorRequiresVerifier:
    """Verify that the executor rejects write operations without a verifier."""

    def test_write_op_fails_without_verifier(self):
        """execute_with_queue should reject write ops without verifier."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        queue_data = {
            "operation": "workflow:activate",
            "payload": {"workflow_id": "test"},
            "approval": {
                "operation": "workflow:activate",
                "payload_hash": "fake",
                "operator": "test",
                "expires_at": time.time() + 300,
                "signature": "fake",
            },
        }

        with pytest.raises(ApprovalRequiredError):
            executor.execute_with_queue(queue_data)
        executor.close()

    def test_write_op_requires_valid_approval(self):
        """execute_with_queue should validate Ed25519 approval."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        private_key = Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        from app.services.approval_gate import (
            ApprovalLedger,
            Ed25519Signer,
            Ed25519Verifier,
        )
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            ledger_path = f.name

        try:
            ledger = ApprovalLedger(path=ledger_path)
            signer = Ed25519Signer(private_key_pem=private_pem)
            verifier = Ed25519Verifier(public_key_pem=public_pem, ledger=ledger)
            executor.set_approval_verifier(verifier)

            payload = {"workflow_id": "test"}
            approval = signer.sign(
                operation="workflow:activate",
                payload=payload,
                operator="human-admin",
            )

            queue_data = {
                "operation": "workflow:activate",
                "payload": payload,
                "approval": {
                    "operation": approval.operation,
                    "payload_hash": approval.payload_hash,
                    "operator": approval.operator,
                    "expires_at": approval.expires_at,
                    "nonce": approval.nonce,
                    "signature": approval.signature,
                },
            }

            with patch.object(executor, "_execute_http") as mock_http:
                mock_http.return_value = {"status": "ok"}
                result = executor.execute_with_queue(queue_data)
                assert result["status"] == "ok"
        finally:
            import os
            os.unlink(ledger_path)

        executor.close()

    def test_expired_approval_rejected_by_executor(self):
        """Executor should reject expired Ed25519 approvals."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        private_key = Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        from app.services.approval_gate import (
            ApprovalLedger,
            Ed25519Signer,
            Ed25519Verifier,
        )
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            ledger_path = f.name

        try:
            ledger = ApprovalLedger(path=ledger_path)
            signer = Ed25519Signer(private_key_pem=private_pem)
            verifier = Ed25519Verifier(public_key_pem=public_pem, ledger=ledger)
            executor.set_approval_verifier(verifier)

            payload = {"workflow_id": "test"}
            approval = signer.sign(
                operation="workflow:activate",
                payload=payload,
                operator="human-admin",
                expires_in_seconds=-1,  # Already expired
            )

            queue_data = {
                "operation": "workflow:activate",
                "payload": payload,
                "approval": {
                    "operation": approval.operation,
                    "payload_hash": approval.payload_hash,
                    "operator": approval.operator,
                    "expires_at": approval.expires_at,
                    "nonce": approval.nonce,
                    "signature": approval.signature,
                },
            }

            with patch.object(executor, "_execute_http"):
                with pytest.raises(ApprovalExpiredError):
                    executor.execute_with_queue(queue_data)
        finally:
            import os
            os.unlink(ledger_path)

        executor.close()

    def test_forged_approval_rejected_by_executor(self):
        """Executor should reject Ed25519 approvals with forged signatures."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        # Real key pair for verifier
        real_private = Ed25519PrivateKey.generate()
        real_public_pem = real_private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        # Fake key pair for attacker
        fake_private = Ed25519PrivateKey.generate()
        fake_pem = fake_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        from app.services.approval_gate import (
            ApprovalLedger,
            Ed25519Signer,
            Ed25519Verifier,
        )
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            ledger_path = f.name

        try:
            ledger = ApprovalLedger(path=ledger_path)
            fake_signer = Ed25519Signer(private_key_pem=fake_pem)
            verifier = Ed25519Verifier(public_key_pem=real_public_pem, ledger=ledger)
            executor.set_approval_verifier(verifier)

            payload = {"workflow_id": "test"}
            approval = fake_signer.sign(
                operation="workflow:activate",
                payload=payload,
                operator="attacker",
            )

            queue_data = {
                "operation": "workflow:activate",
                "payload": payload,
                "approval": {
                    "operation": approval.operation,
                    "payload_hash": approval.payload_hash,
                    "operator": approval.operator,
                    "expires_at": approval.expires_at,
                    "nonce": approval.nonce,
                    "signature": approval.signature,
                },
            }

            with patch.object(executor, "_execute_http"):
                with pytest.raises(ApprovalSignatureError):
                    executor.execute_with_queue(queue_data)
        finally:
            import os
            os.unlink(ledger_path)

        executor.close()


# ---------------------------------------------------------------------------
# Prohibited operations are always denied
# ---------------------------------------------------------------------------


class TestProhibitedOperationsAlwaysDenied:
    """Verify that prohibited operations cannot be executed even with approval."""

    def test_database_direct_always_denied(self):
        """Direct database access should always be denied."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        queue_data = {
            "operation": "database:direct",
            "payload": {},
            "approval": None,
        }

        with pytest.raises(ProhibitedOperationError):
            executor.execute_with_queue(queue_data)
        executor.close()

    def test_credential_delete_always_denied(self):
        """Credential deletion should always be denied."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        queue_data = {
            "operation": "credential:delete",
            "payload": {},
            "approval": None,
        }

        with pytest.raises(ProhibitedOperationError):
            executor.execute_with_queue(queue_data)
        executor.close()

    def test_unknown_operation_denied(self):
        """Unknown operations should be denied."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        queue_data = {
            "operation": "unknown:operation",
            "payload": {},
            "approval": None,
        }

        with pytest.raises(ProhibitedOperationError):
            executor.execute_with_queue(queue_data)
        executor.close()


# ---------------------------------------------------------------------------
# Authorization block enforcement
# ---------------------------------------------------------------------------


class TestAuthorizationBlockEnforcement:
    """Verify that HTTP 401/403 is treated as definitive block."""

    def test_401_raises_authorization_block(self):
        """HTTP 401 should raise AuthorizationBlockError."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        with patch.object(executor._client, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.request.url.path = "/api/v1/workflows"
            mock_request.return_value = mock_response

            with pytest.raises(AuthorizationBlockError) as exc_info:
                executor.execute(OperationType.WORKFLOW_LIST)

            assert exc_info.value.status_code == 401

        executor.close()

    def test_403_raises_authorization_block(self):
        """HTTP 403 should raise AuthorizationBlockError."""
        config = ExecutorConfig(base_url="http://localhost:5678")
        executor = N8nExecutor(config)

        with patch.object(executor._client, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_response.request.url.path = "/api/v1/workflows"
            mock_request.return_value = mock_response

            with pytest.raises(AuthorizationBlockError) as exc_info:
                executor.execute(OperationType.WORKFLOW_LIST)

            assert exc_info.value.status_code == 403

        executor.close()


# ---------------------------------------------------------------------------
# Journal integrity
# ---------------------------------------------------------------------------


class TestJournalIntegrity:
    """Verify that the journal detects tampering."""

    def test_journal_detects_tampering(self):
        """Modifying a journal entry should break integrity."""
        journal = IntegrityJournal()

        journal.append("test", "ok", "Test entry")
        journal.append("test2", "ok", "Second entry")

        assert journal.verify_integrity() is True

        # Tamper with first entry
        entries = journal.get_entries()
        if entries:
            entries[0].details = "TAMPERED"
            journal.entries = entries

        assert journal.verify_integrity() is False

    def test_journal_persists_and_loads(self, tmp_path):
        """Journal should persist to file and load correctly."""
        journal_path = tmp_path / "journal.json"
        journal = IntegrityJournal(path=journal_path)

        journal.append("test", "ok", "Persistent entry")
        assert journal.verify_integrity() is True

        # Load from file
        journal2 = IntegrityJournal(path=journal_path)
        assert len(journal2.entries) == 1
        assert journal2.verify_integrity() is True


# ---------------------------------------------------------------------------
# ApprovalGate backward compatibility
# ---------------------------------------------------------------------------


class TestApprovalGateBackwardCompatibility:
    """Verify that ApprovalGate still works for existing tests."""

    def test_approval_gate_can_sign_and_verify(self):
        """ApprovalGate should still support sign + verify for backward compat."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}

        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )

        # ApprovalGate extends ApprovalVerifier, so validate works
        # But the approval was already used by sign_approval's journal
        # We need a fresh verifier for the test
        verifier = ApprovalVerifier(secret="test-secret")
        result = verifier.validate(approval, payload)
        assert result is True

    def test_approval_gate_is_verifier_subclass(self):
        """ApprovalGate should be a subclass of ApprovalVerifier."""
        assert issubclass(ApprovalGate, ApprovalVerifier)

    def test_approval_gate_has_sign_approval(self):
        """ApprovalGate should have sign_approval for backward compat."""
        gate = ApprovalGate(secret="test-secret")
        assert hasattr(gate, "sign_approval")
