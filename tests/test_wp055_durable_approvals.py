"""WP-055 — Durable approvals, legacy bypass fix, and negative security tests.

These tests validate the fixes for the 5 risks identified in issue #136:
1. ApprovalVerifier._used_approvals is now persisted to journal file
2. N8nExecutor.execute() legacy SHA-256 path is blocked when verifier is configured
3. Durable approval consumption prevents replay after restart
4. Tampered signatures are rejected
5. HTTP 401/403 are definitive blocks

All tests use synthetic data and mock HTTP — no real n8n calls.
"""

import hashlib
import hmac
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.approval_gate import (
    ApprovalExpiredError,
    ApprovalReplayError,
    ApprovalSignatureError,
    ApprovalVerifier,
    ApprovalSigner,
    IntegrityJournal,
    SignedApproval,
)
from app.services.n8n_executor import (
    APPROVAL_REQUIRED_OPERATIONS,
    N8nExecutor,
    OperationApproval,
    OperationType,
    ExecutorConfig,
    AuthorizationBlockError,
    ApprovalRequiredError,
    ProhibitedOperationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_journal(tmp_path):
    """Create a temporary journal file path."""
    return tmp_path / "journal.json"


@pytest.fixture
def signer(tmp_journal):
    """Create an ApprovalSigner with a test secret."""
    journal = IntegrityJournal(path=tmp_journal)
    return ApprovalSigner(secret="test-hmac-secret", journal=journal)


@pytest.fixture
def verifier(tmp_journal):
    """Create an ApprovalVerifier with the same test secret."""
    journal = IntegrityJournal(path=tmp_journal)
    return ApprovalVerifier(secret="test-hmac-secret", journal=journal)


@pytest.fixture
def executor_config():
    """Create an ExecutorConfig for testing."""
    return ExecutorConfig(
        base_url="http://localhost:5678",
        api_key="test-api-key",
        timeout=1.0,
    )


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client that returns 200 OK."""
    client = MagicMock(spec=httpx.Client)
    response = MagicMock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"status": "ok"}
    response.text = '{"status": "ok"}'
    request = MagicMock()
    request.url.path = "/api/v1/workflows"
    response.request = request
    client.request.return_value = response
    client.headers = {}
    return client


# ---------------------------------------------------------------------------
# Test 1: Durable approval consumption — replay after restart is blocked
# ---------------------------------------------------------------------------


class TestDurableApprovalConsumption:
    """Test that used approvals survive restart and prevent replay."""

    def test_approval_consumed_and_loaded_after_restart(self, tmp_journal, signer):
        """An approval used once should not be reusable after creating a new verifier."""
        payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        # First verifier validates the approval
        verifier1 = ApprovalVerifier(
            secret="test-hmac-secret",
            journal=IntegrityJournal(path=tmp_journal),
        )
        assert verifier1.validate(approval, payload) is True

        # Simulate restart: create a new verifier that loads from the same journal
        verifier2 = ApprovalVerifier(
            secret="test-hmac-secret",
            journal=IntegrityJournal(path=tmp_journal),
        )
        # The approval should be rejected as already used
        with pytest.raises(ApprovalReplayError):
            verifier2.validate(approval, payload)

    def test_different_approval_can_be_used_after_restart(self, tmp_journal, signer):
        """A different approval should still work after restart."""
        payload1 = {"workflow_id": "test-123"}
        approval1 = signer.sign_approval(
            operation="workflow:activate",
            payload=payload1,
            operator="test-operator",
        )

        # Use first approval
        verifier1 = ApprovalVerifier(
            secret="test-hmac-secret",
            journal=IntegrityJournal(path=tmp_journal),
        )
        assert verifier1.validate(approval1, payload1) is True

        # Simulate restart
        verifier2 = ApprovalVerifier(
            secret="test-hmac-secret",
            journal=IntegrityJournal(path=tmp_journal),
        )

        # A different approval should work
        payload2 = {"workflow_id": "test-456"}
        approval2 = signer.sign_approval(
            operation="workflow:activate",
            payload=payload2,
            operator="test-operator",
        )
        assert verifier2.validate(approval2, payload2) is True

    def test_no_journal_path_means_no_durability(self, signer):
        """Without a journal file path, approvals are not persisted."""
        payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        # Verifier without journal path
        verifier1 = ApprovalVerifier(secret="test-hmac-secret")
        assert verifier1.validate(approval, payload) is True

        # New verifier without journal path — no durability, replay is allowed
        verifier2 = ApprovalVerifier(secret="test-hmac-secret")
        # This should NOT raise because there's no journal to load from
        assert verifier2.validate(approval, payload) is True


# ---------------------------------------------------------------------------
# Test 2: Legacy SHA-256 bypass is blocked when verifier is configured
# ---------------------------------------------------------------------------


class TestLegacyBypassBlocked:
    """Test that legacy OperationApproval is blocked when HMAC verifier is configured."""

    def test_legacy_approval_rejected_with_verifier(self, executor_config, mock_http_client):
        """Legacy SHA-256 approval should be rejected when verifier is configured."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        # Configure HMAC verifier
        executor.set_approval_verifier(
            ApprovalVerifier(secret="test-hmac-secret")
        )

        # Create a legacy approval
        payload = {"workflow_id": "test-123"}
        content_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        legacy_approval = OperationApproval(
            operation=OperationType.WORKFLOW_ACTIVATE,
            content_hash=content_hash,
            expires_at=time.time() + 300,
            operator="test-operator",
        )

        # Legacy approval should be rejected
        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
                approval=legacy_approval,
            )

    def test_signed_approval_works_with_verifier(self, executor_config, mock_http_client, signer):
        """HMAC-signed approval should work when verifier is configured."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        # Configure HMAC verifier with the same secret
        executor.set_approval_verifier(
            ApprovalVerifier(secret="test-hmac-secret")
        )

        payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        # Signed approval should work
        result = executor.execute(
            operation=OperationType.WORKFLOW_ACTIVATE,
            payload=payload,
            signed_approval=approval,
        )
        assert result == {"status": "ok"}

    def test_legacy_approval_rejected_without_verifier(self, executor_config, mock_http_client):
        """Legacy approval is ALWAYS rejected — no bypass, even without verifier.

        WP-056: OperationApproval (SHA-256) is no longer accepted on any path.
        The agent could forge SHA-256 hashes, so this path is eliminated.
        """
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        # No verifier configured — legacy approval should still be rejected
        payload = {"workflow_id": "test-123"}
        content_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        legacy_approval = OperationApproval(
            operation=OperationType.WORKFLOW_ACTIVATE,
            content_hash=content_hash,
            expires_at=time.time() + 300,
            operator="test-operator",
        )

        # Legacy approval is now ALWAYS rejected
        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
                approval=legacy_approval,
            )

    def test_write_op_rejected_without_verifier(self, executor_config, mock_http_client):
        """Write operations require a configured verifier — fail-closed."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        # No verifier configured — even signed_approval is rejected
        payload = {"workflow_id": "test-123"}

        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
            )

    def test_no_approval_rejected_for_write_op(self, executor_config, mock_http_client):
        """Write operations without any approval should be rejected."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        payload = {"workflow_id": "test-123"}
        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
            )


# ---------------------------------------------------------------------------
# Test 3: Tampered signature is rejected
# ---------------------------------------------------------------------------


class TestTamperedSignature:
    """Test that tampered HMAC signatures are rejected."""

    def test_modified_payload_rejected(self, verifier, signer):
        """If the payload is modified after signing, validation should fail."""
        original_payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=original_payload,
            operator="test-operator",
        )

        tampered_payload = {"workflow_id": "malicious-999"}
        with pytest.raises(Exception):  # ApprovalPayloadMismatchError
            verifier.validate(approval, tampered_payload)

    def test_modified_signature_rejected(self, verifier, signer):
        """If the signature is tampered, validation should fail."""
        payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        # Tamper with the signature
        tampered_approval = SignedApproval(
            operation=approval.operation,
            payload_hash=approval.payload_hash,
            operator=approval.operator,
            expires_at=approval.expires_at,
            signature="0" * 64,  # Invalid signature
        )

        with pytest.raises(ApprovalSignatureError):
            verifier.validate(tampered_approval, payload)

    def test_wrong_secret_rejected(self, signer):
        """Approval signed with one secret should not verify with another."""
        payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        wrong_verifier = ApprovalVerifier(secret="different-secret")
        with pytest.raises(ApprovalSignatureError):
            wrong_verifier.validate(approval, payload)


# ---------------------------------------------------------------------------
# Test 4: HTTP 401/403 are definitive blocks
# ---------------------------------------------------------------------------


class TestAuthorizationBlocks:
    """Test that HTTP 401/403 are treated as definitive blocks."""

    def test_401_raises_authorization_block(self, executor_config):
        """HTTP 401 should raise AuthorizationBlockError."""
        executor = N8nExecutor(executor_config)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        request = MagicMock()
        request.url.path = "/api/v1/workflows/test"
        mock_response.request = request

        with patch.object(executor._client, 'request', return_value=mock_response):
            with pytest.raises(AuthorizationBlockError) as exc_info:
                executor.execute(operation=OperationType.WORKFLOW_GET)
            assert exc_info.value.status_code == 401

    def test_403_raises_authorization_block(self, executor_config):
        """HTTP 403 should raise AuthorizationBlockError."""
        executor = N8nExecutor(executor_config)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        request = MagicMock()
        request.url.path = "/api/v1/workflows/test"
        mock_response.request = request

        with patch.object(executor._client, 'request', return_value=mock_response):
            with pytest.raises(AuthorizationBlockError) as exc_info:
                executor.execute(operation=OperationType.WORKFLOW_GET)
            assert exc_info.value.status_code == 403

    def test_no_retry_on_403(self, executor_config):
        """403 should not trigger any retry."""
        executor = N8nExecutor(executor_config)
        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            response = MagicMock(spec=httpx.Response)
            response.status_code = 403
            response.text = "Forbidden"
            request = MagicMock()
            request.url.path = "/api/v1/workflows"
            response.request = request
            return response

        with patch.object(executor._client, 'request', side_effect=mock_request):
            with pytest.raises(AuthorizationBlockError):
                executor.execute(operation=OperationType.WORKFLOW_LIST)

        # Should only be called once — no retry
        assert call_count == 1


# ---------------------------------------------------------------------------
# Test 5: Unauthorized calls are blocked
# ---------------------------------------------------------------------------


class TestUnauthorizedCalls:
    """Test that unauthorized operations are blocked."""

    def test_prohibited_operation_blocked(self, executor_config, mock_http_client):
        """Prohibited operations should be blocked before any HTTP call."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        with pytest.raises(ProhibitedOperationError):
            executor.execute(operation=OperationType.CREDENTIAL_DELETE)

        # HTTP client should not have been called
        mock_http_client.request.assert_not_called()

    def test_database_direct_blocked(self, executor_config, mock_http_client):
        """Direct database access should be blocked."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        with pytest.raises(ProhibitedOperationError):
            executor.execute(operation=OperationType.DATABASE_DIRECT)

    def test_read_only_operation_no_approval_needed(self, executor_config, mock_http_client):
        """Read-only operations should not require approval."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        # Should not raise ApprovalRequiredError
        result = executor.execute(operation=OperationType.WORKFLOW_LIST)
        assert result == {"status": "ok"}


# ---------------------------------------------------------------------------
# Test 6: Expired approval is rejected
# ---------------------------------------------------------------------------


class TestExpiredApproval:
    """Test that expired approvals are rejected."""

    def test_expired_approval_rejected(self, verifier, tmp_journal):
        """An expired approval should be rejected."""
        payload = {"workflow_id": "test-123"}

        # Create an approval that expired in the past
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        expires_at = time.time() - 600  # Expired 10 minutes ago

        message = json.dumps({
            "operation": "workflow:activate",
            "payload_hash": payload_hash,
            "operator": "test-operator",
            "expires_at": expires_at,
        }, sort_keys=True, default=str)

        signature = hmac.new(
            b"test-hmac-secret",
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=payload_hash,
            operator="test-operator",
            expires_at=expires_at,
            signature=signature,
        )

        with pytest.raises(ApprovalExpiredError):
            verifier.validate(approval, payload)


# ---------------------------------------------------------------------------
# Test 7: N8nExecutor.execute() with signed_approval parameter
# ---------------------------------------------------------------------------


class TestExecutorWithSignedApproval:
    """Test N8nExecutor.execute() with the new signed_approval parameter."""

    def test_signed_approval_via_execute(self, executor_config, mock_http_client, signer):
        """execute() should accept signed_approval and validate via verifier."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client
        executor.set_approval_verifier(
            ApprovalVerifier(secret="test-hmac-secret")
        )

        payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        result = executor.execute(
            operation=OperationType.WORKFLOW_ACTIVATE,
            payload=payload,
            signed_approval=approval,
        )
        assert result == {"status": "ok"}

    def test_signed_approval_requires_verifier(self, executor_config, mock_http_client, signer):
        """signed_approval should fail if no verifier is configured."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client
        # No verifier configured

        payload = {"workflow_id": "test-123"}
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
                signed_approval=approval,
            )
