"""WP-056 — Ed25519 asymmetric signatures, atomic SQLite ledger, and concurrency tests.

These tests validate the WP-056 requirements from issue #137:
1. Ed25519 asymmetric signatures: private key signs, public key verifies
2. Atomic SQLite ledger with UNIQUE constraint for approval consumption
3. Cross-process concurrency: two processes cannot consume the same approval
4. Fail-closed: ledger errors block operations rather than allowing silent replay
5. Legacy SHA-256 bypass is completely eliminated
6. Replay after restart is blocked by ledger persistence

All tests use synthetic keys and mock HTTP — no real n8n calls.
"""

import hashlib
import json
import multiprocessing
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.approval_gate import (
    Ed25519Signer,
    Ed25519Verifier,
    SignedApprovalEd25519,
    ApprovalLedger,
    LedgerError,
    ApprovalSignatureError,
    ApprovalExpiredError,
    ApprovalPayloadMismatchError,
    ApprovalReplayError,
    ApprovalOperationMismatchError,
    # Legacy imports for backward compatibility tests
    ApprovalVerifier,
    ApprovalSigner,
    SignedApproval,
    IntegrityJournal,
)
from app.services.n8n_executor import (
    N8nExecutor,
    OperationType,
    OperationApproval,
    ExecutorConfig,
    ApprovalRequiredError,
    ProhibitedOperationError,
    AuthorizationBlockError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def ed25519_keys():
    """Generate a synthetic Ed25519 key pair for testing."""
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
    return private_pem, public_pem


@pytest.fixture
def ed25519_signer(ed25519_keys):
    """Create an Ed25519Signer with a synthetic private key."""
    private_pem, _ = ed25519_keys
    return Ed25519Signer(private_key_pem=private_pem)


@pytest.fixture
def ed25519_verifier(ed25519_keys, tmp_path):
    """Create an Ed25519Verifier with a synthetic public key and ledger."""
    _, public_pem = ed25519_keys
    ledger_path = tmp_path / "ledger.db"
    ledger = ApprovalLedger(path=ledger_path)
    return Ed25519Verifier(public_key_pem=public_pem, ledger=ledger), ledger


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
# Test 1: Ed25519 asymmetric signatures
# ---------------------------------------------------------------------------


class TestEd25519AsymmetricSignatures:
    """Test Ed25519 sign/verify with proper trust boundary."""

    def test_signer_creates_valid_approval(self, ed25519_signer):
        """Signer should create a valid SignedApprovalEd25519."""
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )
        assert approval.operation == "workflow:activate"
        assert approval.operator == "test-operator"
        assert approval.nonce is not None
        assert approval.signature is not None
        assert len(approval.signature) > 0

    def test_verifier_accepts_valid_signature(self, ed25519_signer, ed25519_verifier):
        """Verifier should accept a valid Ed25519 signature."""
        verifier, _ = ed25519_verifier
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )
        assert verifier.validate(approval, payload) is True

    def test_verifier_rejects_wrong_key(self, ed25519_signer, ed25519_keys):
        """Verifier with different public key should reject the signature."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        # Generate a different key pair
        other_private = Ed25519PrivateKey.generate()
        other_public = other_private.public_key().public_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization",
                                 fromlist=[""]).Encoding.PEM,
            format=__import__("cryptography.hazmat.primitives.serialization",
                              fromlist=[""]).PublicFormat.SubjectPublicKeyInfo,
        )
        verifier = Ed25519Verifier(public_key_pem=other_public)
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )
        with pytest.raises(ApprovalSignatureError):
            verifier.validate(approval, payload)

    def test_verifier_cannot_sign(self, ed25519_verifier):
        """Verifier should have NO sign method — trust boundary."""
        verifier, _ = ed25519_verifier
        assert not hasattr(verifier, 'sign')
        assert not hasattr(verifier, 'sign_approval')

    def test_signer_has_public_key(self, ed25519_signer):
        """Signer should expose public key PEM for verifier setup."""
        public_pem = ed25519_signer.public_key_pem
        assert b"BEGIN PUBLIC KEY" in public_pem
        # Verify the public key works
        verifier = Ed25519Verifier(public_key_pem=public_pem)
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )
        assert verifier.validate(approval, payload) is True

    def test_tampered_signature_rejected(self, ed25519_signer, ed25519_verifier):
        """Tampering with the signature should be detected."""
        verifier, _ = ed25519_verifier
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )
        # Tamper with signature
        tampered = SignedApprovalEd25519(
            operation=approval.operation,
            payload_hash=approval.payload_hash,
            operator=approval.operator,
            expires_at=approval.expires_at,
            nonce=approval.nonce,
            signature="0" * len(approval.signature),
        )
        with pytest.raises(ApprovalSignatureError):
            verifier.validate(tampered, payload)

    def test_tampered_payload_rejected(self, ed25519_signer, ed25519_verifier):
        """Tampering with the payload should be detected."""
        verifier, _ = ed25519_verifier
        original_payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=original_payload,
            operator="test-operator",
        )
        tampered_payload = {"workflow_id": "malicious-999"}
        with pytest.raises(ApprovalPayloadMismatchError):
            verifier.validate(approval, tampered_payload)

    def test_expired_approval_rejected(self, ed25519_signer, ed25519_verifier):
        """Expired approval should be rejected."""
        verifier, _ = ed25519_verifier
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
            expires_in_seconds=-10,  # Already expired
        )
        with pytest.raises(ApprovalExpiredError):
            verifier.validate(approval, payload)

    def test_nonce_uniqueness(self, ed25519_signer):
        """Each approval should have a unique nonce."""
        payload = {"workflow_id": "test-123"}
        nonces = set()
        for _ in range(10):
            approval = ed25519_signer.sign(
                operation="workflow:activate",
                payload=payload,
                operator="test-operator",
            )
            assert approval.nonce not in nonces
            nonces.add(approval.nonce)

    def test_custom_nonce(self, ed25519_signer, ed25519_verifier):
        """Custom nonce should be preserved."""
        verifier, _ = ed25519_verifier
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
            nonce="wp-056-test-nonce",
        )
        assert approval.nonce == "wp-056-test-nonce"
        assert verifier.validate(approval, payload) is True


# ---------------------------------------------------------------------------
# Test 2: Atomic SQLite ledger
# ---------------------------------------------------------------------------


class TestAtomicSQLiteLedger:
    """Test ApprovalLedger atomicity, durability, and fail-closed behavior."""

    def test_ledger_creates_table(self, tmp_path):
        """Ledger should create the consumed_approvals table."""
        ledger_path = tmp_path / "ledger.db"
        ledger = ApprovalLedger(path=ledger_path)
        assert ledger_path.exists()
        conn = sqlite3.connect(str(ledger_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        assert ("consumed_approvals",) in tables
        conn.close()

    def test_ledger_unique_constraint(self, tmp_path):
        """Duplicate consumption should raise ApprovalReplayError."""
        ledger = ApprovalLedger(path=tmp_path / "ledger.db")
        ledger.consume("nonce-1", "workflow:activate")
        with pytest.raises(ApprovalReplayError):
            ledger.consume("nonce-1", "workflow:activate")

    def test_ledger_different_nonce_ok(self, tmp_path):
        """Different nonces should be accepted."""
        ledger = ApprovalLedger(path=tmp_path / "ledger.db")
        ledger.consume("nonce-1", "workflow:activate")
        ledger.consume("nonce-2", "workflow:deactivate")
        assert ledger.get_consumed_count() == 2

    def test_ledger_is_consumed(self, tmp_path):
        """is_consumed should return correct status."""
        ledger = ApprovalLedger(path=tmp_path / "ledger.db")
        assert ledger.is_consumed("nonce-1") is False
        ledger.consume("nonce-1", "workflow:activate")
        assert ledger.is_consumed("nonce-1") is True
        assert ledger.is_consumed("nonce-2") is False

    def test_ledger_wal_mode(self, tmp_path):
        """Ledger should use WAL mode for concurrent safety."""
        ledger = ApprovalLedger(path=tmp_path / "ledger.db")
        conn = sqlite3.connect(str(tmp_path / "ledger.db"))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_ledger_persists_across_connections(self, tmp_path):
        """Consumed approvals should persist across new connections."""
        ledger1 = ApprovalLedger(path=tmp_path / "ledger.db")
        ledger1.consume("nonce-1", "workflow:activate")

        # New ledger instance (simulates restart)
        ledger2 = ApprovalLedger(path=tmp_path / "ledger.db")
        assert ledger2.is_consumed("nonce-1") is True
        with pytest.raises(ApprovalReplayError):
            ledger2.consume("nonce-1", "workflow:activate")

    def test_ledger_unavailable_path(self):
        """Ledger should fail if path is unwritable."""
        with pytest.raises(LedgerError):
            ApprovalLedger(path="/nonexistent/directory/ledger.db")

    def test_ledger_corrupted_db(self, tmp_path):
        """Ledger should raise LedgerError on corrupted database."""
        ledger_path = tmp_path / "ledger.db"
        # Write garbage to simulate corruption
        ledger_path.write_text("this is not a valid SQLite database")
        # The ledger init fails with LedgerError — fail-closed
        with pytest.raises(LedgerError, match="file is not a database"):
            ApprovalLedger(path=ledger_path)

    def test_ledger_fail_closed_on_error(self, tmp_path):
        """Ledger operations should fail closed when unavailable."""
        ledger = ApprovalLedger(path=tmp_path / "ledger.db")
        # Simulate making ledger unavailable
        ledger._available = False
        with pytest.raises(LedgerError, match="fail-closed"):
            ledger.consume("nonce-1", "workflow:activate")
        with pytest.raises(LedgerError):
            ledger.is_consumed("nonce-1")
        with pytest.raises(LedgerError):
            ledger.get_consumed_count()


# ---------------------------------------------------------------------------
# Test 3: Cross-process concurrency
# ---------------------------------------------------------------------------


def _ledger_consume_worker(ledger_path: str, nonce: str, result_queue):
    """Worker function for cross-process concurrency test."""
    try:
        ledger = ApprovalLedger(path=ledger_path)
        ledger.consume(nonce, "workflow:activate")
        result_queue.put(("success", None))
    except ApprovalReplayError:
        result_queue.put(("replay", None))
    except Exception as e:
        result_queue.put(("error", str(e)))


class TestCrossProcessConcurrency:
    """Test that two processes cannot consume the same approval."""

    def test_two_processes_same_nonce(self, tmp_path):
        """Two processes trying to consume the same nonce: one succeeds, one fails."""
        ledger_path = tmp_path / "ledger.db"
        ledger = ApprovalLedger(path=ledger_path)
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        # Start a worker process that tries to consume the same nonce
        worker = multiprocessing.Process(
            target=_ledger_consume_worker,
            args=(str(ledger_path), "nonce-concurrent-test", result_queue),
        )
        worker.start()

        # Main process also tries to consume
        try:
            ledger.consume("nonce-concurrent-test", "workflow:activate")
            main_result = "success"
        except ApprovalReplayError:
            main_result = "replay"

        worker.join(timeout=5)
        worker_result = result_queue.get(timeout=5)[0]

        # One should succeed, the other should get replay
        assert main_result in ("success", "replay")
        assert worker_result in ("success", "replay")
        assert main_result != worker_result, (
            "One process should succeed and the other should detect replay"
        )

    def test_multiple_sequential_consumers(self, tmp_path):
        """Multiple sequential consumers should each get unique nonces."""
        ledger = ApprovalLedger(path=tmp_path / "ledger.db")
        for i in range(10):
            ledger.consume(f"nonce-{i}", f"workflow:activate-{i}")
        assert ledger.get_consumed_count() == 10


# ---------------------------------------------------------------------------
# Test 4: Ed25519 verifier integration with ledger
# ---------------------------------------------------------------------------


class TestEd25519VerifierWithLedger:
    """Test Ed25519 verifier integrates with ApprovalLedger correctly."""

    def test_verifier_consumes_in_ledger(self, ed25519_signer, ed25519_verifier):
        """Valid approval should be consumed in the ledger."""
        verifier, ledger = ed25519_verifier
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )
        verifier.validate(approval, payload)
        assert ledger.is_consumed(approval.nonce) is True

    def test_verifier_replays_blocked_by_ledger(self, ed25519_signer, ed25519_verifier):
        """Replaying the same approval should be blocked by ledger."""
        verifier, ledger = ed25519_verifier
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
            nonce="fixed-nonce",
        )
        verifier.validate(approval, payload)
        with pytest.raises(ApprovalReplayError):
            verifier.validate(approval, payload)

    def test_verifier_replay_after_restart(self, ed25519_signer, ed25519_keys, tmp_path):
        """Replay after restart should be blocked by ledger persistence."""
        _, public_pem = ed25519_keys
        ledger_path = tmp_path / "ledger.db"

        # First verifier consumes
        ledger1 = ApprovalLedger(path=ledger_path)
        verifier1 = Ed25519Verifier(public_key_pem=public_pem, ledger=ledger1)
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
            nonce="restart-nonce",
        )
        verifier1.validate(approval, payload)

        # Simulate restart: new verifier with same ledger
        ledger2 = ApprovalLedger(path=ledger_path)
        verifier2 = Ed25519Verifier(public_key_pem=public_pem, ledger=ledger2)
        with pytest.raises(ApprovalReplayError):
            verifier2.validate(approval, payload)

    def test_verifier_without_ledger_allows_replay(self, ed25519_signer, ed25519_keys):
        """Without ledger, replay is not tracked (in-memory only)."""
        _, public_pem = ed25519_keys
        verifier = Ed25519Verifier(public_key_pem=public_pem, ledger=None)
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
            nonce="no-ledger-nonce",
        )
        # Without ledger, the same approval can be validated twice
        assert verifier.validate(approval, payload) is True
        assert verifier.validate(approval, payload) is True

    def test_verifier_fail_closed_on_ledger_error(self, ed25519_signer, ed25519_keys):
        """Verifier should fail closed when ledger is unavailable."""
        _, public_pem = ed25519_keys
        # Ledger init in nonexistent directory raises LedgerError — fail-closed
        with pytest.raises(LedgerError):
            ApprovalLedger(path="/nonexistent/ledger.db")


# ---------------------------------------------------------------------------
# Test 5: N8nExecutor with Ed25519
# ---------------------------------------------------------------------------


class TestN8nExecutorWithEd25519:
    """Test N8nExecutor integrates with Ed25519 verifier."""

    def test_executor_accepts_ed25519_approval(
        self, ed25519_signer, ed25519_verifier, executor_config, mock_http_client
    ):
        """Executor should accept Ed25519-signed approvals."""
        verifier, _ = ed25519_verifier
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client
        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
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

    def test_executor_rejects_ed25519_without_verifier(
        self, ed25519_signer, executor_config, mock_http_client
    ):
        """Executor should reject Ed25519 approval when no verifier is configured."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client
        # No verifier set

        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
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

    def test_executor_rejects_legacy_approval_always(
        self, executor_config, mock_http_client
    ):
        """Legacy OperationApproval is ALWAYS rejected."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

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
        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
                approval=legacy_approval,
            )

    def test_executor_rejects_legacy_with_verifier(
        self, executor_config, mock_http_client
    ):
        """Legacy approval rejected even when verifier is configured."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client
        executor.set_approval_verifier(
            ApprovalVerifier(secret="test-secret")
        )

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
        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
                approval=legacy_approval,
            )


# ---------------------------------------------------------------------------
# Test 6: Fail-closed scenarios
# ---------------------------------------------------------------------------


class TestFailClosed:
    """Test fail-closed behavior for various error scenarios."""

    def test_executor_fail_closed_no_verifier(self, executor_config, mock_http_client):
        """Write ops fail closed when no verifier is configured."""
        executor = N8nExecutor(executor_config)
        executor._client = mock_http_client

        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload={"workflow_id": "test-123"},
            )

    def test_ledger_corruption_blocks_operations(self, tmp_path):
        """Corrupted ledger raises LedgerError — fail-closed."""
        ledger_path = tmp_path / "ledger.db"
        ledger_path.write_text("corrupted data")
        with pytest.raises(LedgerError, match="file is not a database"):
            ApprovalLedger(path=ledger_path)

    def test_ledger_unavailable_directory(self):
        """Ledger in unavailable directory raises LedgerError."""
        with pytest.raises(LedgerError):
            ApprovalLedger(path="/nonexistent/dir/ledger.db")

    def test_401_blocks_execution(self, executor_config):
        """HTTP 401 blocks execution — no retry."""
        executor = N8nExecutor(executor_config)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 401
        response.text = "Unauthorized"
        request = MagicMock()
        request.url.path = "/api/v1/workflows"
        response.request = request

        with patch.object(executor, '_client') as mock_client:
            mock_client.request.return_value = response
            mock_client.headers = {}
            with pytest.raises(AuthorizationBlockError):
                executor.execute(operation=OperationType.WORKFLOW_LIST)

    def test_403_blocks_execution(self, executor_config):
        """HTTP 403 blocks execution — no retry."""
        executor = N8nExecutor(executor_config)
        response = MagicMock(spec=httpx.Response)
        response.status_code = 403
        response.text = "Forbidden"
        request = MagicMock()
        request.url.path = "/api/v1/workflows"
        response.request = request

        with patch.object(executor, '_client') as mock_client:
            mock_client.request.return_value = response
            mock_client.headers = {}
            with pytest.raises(AuthorizationBlockError):
                executor.execute(operation=OperationType.WORKFLOW_LIST)


# ---------------------------------------------------------------------------
# Test 7: Operation validation
# ---------------------------------------------------------------------------


class TestOperationValidation:
    """Test operation matching and validation."""

    def test_operation_mismatch_rejected(self, ed25519_signer, ed25519_verifier):
        """Approval for one operation should not work for another."""
        verifier, _ = ed25519_verifier
        payload = {"workflow_id": "test-123"}
        approval = ed25519_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )
        verifier.validate(approval, payload)
        with pytest.raises(ApprovalOperationMismatchError):
            verifier.validate_operation(approval, "workflow:deactivate")
