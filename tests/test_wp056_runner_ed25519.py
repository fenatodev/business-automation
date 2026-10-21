"""WP-056: Tests for the sandbox runner migrated to Ed25519.

These tests validate that the runner (run_executor.py) and executor
(N8nExecutor.execute_with_queue) use Ed25519 asymmetric signatures
instead of HMAC-SHA256, and that the ApprovalLedger provides
fail-closed durability.

Key scenarios:
1. Runner requires ED25519_PUBLIC_KEY, not APPROVAL_SECRET
2. execute_with_queue uses SignedApprovalEd25519, not SignedApproval HMAC
3. Operation is validated BEFORE approval consumption
4. Ledger persistence prevents replay after restart
5. Forged signatures are rejected
6. Divergent operations are rejected
7. Legacy HMAC approvals are rejected
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.approval_gate import (
    ApprovalLedger,
    ApprovalOperationMismatchError,
    ApprovalReplayError,
    Ed25519Signer,
    Ed25519Verifier,
    LedgerError,
    SignedApprovalEd25519,
)
from app.services.n8n_executor import (
    ApprovalRequiredError as ExecutorApprovalRequiredError,
    ExecutorConfig,
    N8nExecutor,
    OperationType,
    ProhibitedOperationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
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


@pytest.fixture()
def signer(ed25519_keys):
    """Create an Ed25519 signer with synthetic private key."""
    private_pem, _ = ed25519_keys
    return Ed25519Signer(private_key_pem=private_pem)


@pytest.fixture()
def ledger_path(tmp_path):
    """Return a temporary ledger path."""
    return tmp_path / "ledger.db"


@pytest.fixture()
def ledger(ledger_path):
    """Create an ApprovalLedger for testing."""
    return ApprovalLedger(path=ledger_path)


@pytest.fixture()
def verifier(ed25519_keys, ledger):
    """Create an Ed25519Verifier with synthetic public key."""
    _, public_pem = ed25519_keys
    return Ed25519Verifier(public_key_pem=public_pem, ledger=ledger)


@pytest.fixture()
def executor(tmp_path):
    """Create an N8nExecutor for testing."""
    config = ExecutorConfig(
        base_url="http://localhost:5678",
        api_key="test-key",
        journal_path=tmp_path / "executor_journal.json",
    )
    return N8nExecutor(config)


# ---------------------------------------------------------------------------
# TestRunnerEd25519: Runner uses Ed25519, not HMAC
# ---------------------------------------------------------------------------


class TestRunnerEd25519:
    """Validate that run_executor.py uses Ed25519, not HMAC."""

    def test_runner_imports_ed25519_verifier(self):
        """The runner imports Ed25519Verifier, not ApprovalVerifier."""
        runner_source = Path("ops/sandbox/run_executor.py").read_text(encoding="utf-8")
        assert "Ed25519Verifier" in runner_source
        assert "ApprovalVerifier" not in runner_source

    def test_runner_imports_approval_ledger(self):
        """The runner imports ApprovalLedger for durable consumption."""
        runner_source = Path("ops/sandbox/run_executor.py").read_text(encoding="utf-8")
        assert "ApprovalLedger" in runner_source

    def test_runner_requires_public_key(self):
        """The runner requires ED25519_PUBLIC_KEY, not APPROVAL_SECRET."""
        runner_source = Path("ops/sandbox/run_executor.py").read_text(encoding="utf-8")
        assert "ED25519_PUBLIC_KEY" in runner_source
        assert "APPROVAL_SECRET" not in runner_source

    def test_runner_no_hmac_secret(self):
        """The runner does not reference HMAC secret anywhere."""
        runner_source = Path("ops/sandbox/run_executor.py").read_text(encoding="utf-8")
        assert "APPROVAL_SECRET" not in runner_source
        assert "hmac" not in runner_source.lower() or "hmac" not in runner_source.split("Ed25519")[0].lower()

    def test_runner_ledger_fail_closed(self):
        """The runner exits if ledger initialization fails."""
        runner_source = Path("ops/sandbox/run_executor.py").read_text(encoding="utf-8")
        assert "sys.exit(1)" in runner_source
        assert "Ledger initialization failed" in runner_source


# ---------------------------------------------------------------------------
# TestDockerfileCryptography: Dockerfile includes cryptography
# ---------------------------------------------------------------------------


class TestDockerfileCryptography:
    """Validate that the Dockerfile installs cryptography."""

    def test_dockerfile_installs_cryptography(self):
        """The Dockerfile installs cryptography for Ed25519."""
        dockerfile = Path("ops/sandbox/Dockerfile").read_text(encoding="utf-8")
        assert "cryptography" in dockerfile

    def test_dockerfile_no_approval_secret(self):
        """The Dockerfile does not reference APPROVAL_SECRET."""
        dockerfile = Path("ops/sandbox/Dockerfile").read_text(encoding="utf-8")
        assert "APPROVAL_SECRET" not in dockerfile

    def test_dockerfile_references_ed25519(self):
        """The Dockerfile references Ed25519 in comments."""
        dockerfile = Path("ops/sandbox/Dockerfile").read_text(encoding="utf-8")
        assert "Ed25519" in dockerfile


# ---------------------------------------------------------------------------
# TestDockerComposeEd25519: Compose uses Ed25519 public key
# ---------------------------------------------------------------------------


class TestDockerComposeEd25519:
    """Validate that docker-compose.yml uses Ed25519, not HMAC."""

    def test_compose_has_public_key(self):
        """The compose file sets ED25519_PUBLIC_KEY."""
        compose = Path("ops/sandbox/docker-compose.yml").read_text(encoding="utf-8")
        assert "ED25519_PUBLIC_KEY" in compose

    def test_compose_no_approval_secret(self):
        """The compose file does not set APPROVAL_SECRET."""
        compose = Path("ops/sandbox/docker-compose.yml").read_text(encoding="utf-8")
        assert "APPROVAL_SECRET" not in compose

    def test_compose_has_ledger_path(self):
        """The compose file sets LEDGER_PATH for persistent ledger."""
        compose = Path("ops/sandbox/docker-compose.yml").read_text(encoding="utf-8")
        assert "LEDGER_PATH" in compose

    def test_compose_has_persistent_volume(self):
        """The compose file has a persistent volume for ledger data."""
        compose = Path("ops/sandbox/docker-compose.yml").read_text(encoding="utf-8")
        assert "n8n-executor-data" in compose


# ---------------------------------------------------------------------------
# TestExecuteWithQueueEd25519: execute_with_queue uses Ed25519
# ---------------------------------------------------------------------------


class TestExecuteWithQueueEd25519:
    """Validate that execute_with_queue uses SignedApprovalEd25519."""

    def test_queue_uses_ed25519_approval(self, executor, verifier, signer):
        """execute_with_queue accepts SignedApprovalEd25519 approval data."""
        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        approval = signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
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

        # Mock HTTP execution to avoid real network calls
        with patch.object(executor, "_execute_http", return_value={"status": "active"}):
            result = executor.execute_with_queue(queue_data)

        assert result["status"] == "ok"

    def test_queue_rejects_missing_nonce(self, executor, verifier, signer):
        """execute_with_queue rejects approval data without nonce field."""
        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        approval = signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        # Omit nonce — should fail to reconstruct SignedApprovalEd25519
        queue_data = {
            "operation": "workflow:activate",
            "payload": payload,
            "approval": {
                "operation": approval.operation,
                "payload_hash": approval.payload_hash,
                "operator": approval.operator,
                "expires_at": approval.expires_at,
                # "nonce" intentionally missing
                "signature": approval.signature,
            },
        }

        with pytest.raises(KeyError):
            executor.execute_with_queue(queue_data)

    def test_queue_validates_operation_before_consume(self, executor, verifier, signer, ledger):
        """Operation is validated BEFORE approval is consumed in ledger."""
        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        # Sign for workflow:activate but try to execute workflow:deactivate
        approval = signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        queue_data = {
            "operation": "workflow:deactivate",
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

        # Should raise operation mismatch BEFORE consuming
        with pytest.raises(ApprovalOperationMismatchError):
            executor.execute_with_queue(queue_data)

        # Approval should NOT be consumed — ledger is empty
        assert ledger.get_consumed_count() == 0

    def test_queue_rejects_forged_signature(self, executor, verifier, signer, ed25519_keys):
        """execute_with_queue rejects approval with forged signature."""
        _, public_pem = ed25519_keys

        # Create a DIFFERENT signer to forge the signature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        fake_private = Ed25519PrivateKey.generate()
        fake_signer = Ed25519Signer(
            private_key_pem=fake_private.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        fake_approval = fake_signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="attacker",
        )

        queue_data = {
            "operation": "workflow:activate",
            "payload": payload,
            "approval": {
                "operation": fake_approval.operation,
                "payload_hash": fake_approval.payload_hash,
                "operator": fake_approval.operator,
                "expires_at": fake_approval.expires_at,
                "nonce": fake_approval.nonce,
                "signature": fake_approval.signature,
            },
        }

        # The forged signature raises ApprovalSignatureError which is caught
        # by execute_with_queue and returned as an error status.
        # However, the exception propagates because it's not a generic Exception
        # in the HTTP execution path — it's raised during validation.
        from app.services.approval_gate import ApprovalSignatureError

        with pytest.raises(ApprovalSignatureError):
            executor.execute_with_queue(queue_data)

    def test_queue_rejects_legacy_hmac_approval(self, executor, verifier):
        """execute_with_queue rejects legacy HMAC approval data (no nonce)."""
        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        # Legacy HMAC approval — no nonce field
        queue_data = {
            "operation": "workflow:activate",
            "payload": payload,
            "approval": {
                "operation": "workflow:activate",
                "payload_hash": payload_hash,
                "operator": "legacy-operator",
                "expires_at": time.time() + 300,
                "signature": "fake-hmac-signature",
                # No "nonce" field — SignedApprovalEd25519 requires it
            },
        }

        with pytest.raises(KeyError):
            executor.execute_with_queue(queue_data)

    def test_queue_rejects_without_verifier(self, executor):
        """execute_with_queue rejects write ops without verifier configured."""
        queue_data = {
            "operation": "workflow:activate",
            "payload": {"workflow_id": "test-123"},
            "approval": {
                "operation": "workflow:activate",
                "payload_hash": "abc",
                "operator": "test",
                "expires_at": time.time() + 300,
                "nonce": "test-nonce",
                "signature": "test-sig",
            },
        }

        with pytest.raises(ExecutorApprovalRequiredError):
            executor.execute_with_queue(queue_data)

    def test_queue_prohibited_operation(self, executor, verifier):
        """execute_with_queue rejects prohibited operations."""
        executor.set_approval_verifier(verifier)

        queue_data = {
            "operation": "credential:delete",
            "payload": {"credential_id": "123"},
        }

        with pytest.raises(ProhibitedOperationError):
            executor.execute_with_queue(queue_data)


# ---------------------------------------------------------------------------
# TestLedgerReplayAfterRestart: Ledger prevents replay
# ---------------------------------------------------------------------------


class TestLedgerReplayAfterRestart:
    """Validate that ledger prevents replay after process restart."""

    def test_replay_blocked_after_restart(self, ed25519_keys, signer, tmp_path):
        """Approval consumed in one ledger instance is blocked in another."""
        ledger_path = tmp_path / "ledger.db"

        # First "process" — consume approval
        ledger1 = ApprovalLedger(path=ledger_path)
        verifier1 = Ed25519Verifier(
            public_key_pem=ed25519_keys[1],
            ledger=ledger1,
        )

        payload = {"workflow_id": "test-123"}
        approval = signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        verifier1.validate(approval, payload)
        assert ledger1.get_consumed_count() == 1

        # Simulate restart — new ledger instance from same file
        ledger2 = ApprovalLedger(path=ledger_path)
        verifier2 = Ed25519Verifier(
            public_key_pem=ed25519_keys[1],
            ledger=ledger2,
        )

        # Replay should be blocked
        with pytest.raises(ApprovalReplayError):
            verifier2.validate(approval, payload)

    def test_ledger_persists_across_connections(self, ed25519_keys, signer, tmp_path):
        """Ledger data persists across separate database connections."""
        ledger_path = tmp_path / "ledger.db"
        ledger = ApprovalLedger(path=ledger_path)

        payload = {"workflow_id": "test-123"}
        approval = signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        verifier = Ed25519Verifier(
            public_key_pem=ed25519_keys[1],
            ledger=ledger,
        )
        verifier.validate(approval, payload)

        # Verify data is in the file
        conn = sqlite3.connect(str(ledger_path))
        row = conn.execute(
            "SELECT approval_id, operation FROM consumed_approvals"
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == approval.nonce
        assert row[1] == "workflow:activate"


# ---------------------------------------------------------------------------
# TestFailClosed: Ledger errors cause fail-closed behavior
# ---------------------------------------------------------------------------


class TestFailClosed:
    """Validate fail-closed behavior when ledger is unavailable."""

    def test_verifier_fails_closed_on_bad_ledger(self, ed25519_keys, signer):
        """Verifier raises LedgerError when ledger is corrupted."""
        _, public_pem = ed25519_keys

        # Create a corrupted ledger file
        with tempfile.NamedTemporaryFile(
            suffix=".db", delete=False, mode="wb"
        ) as f:
            f.write(b"this is not a valid sqlite database")
            corrupted_path = f.name

        try:
            with pytest.raises(LedgerError):
                ApprovalLedger(path=corrupted_path)
        finally:
            os.unlink(corrupted_path)

    def test_verifier_fails_closed_on_unwritable_ledger(self, ed25519_keys, signer, tmp_path):
        """Verifier fails closed when ledger directory is not writable."""
        _, public_pem = ed25519_keys

        unwritable_dir = tmp_path / "unwritable"
        unwritable_dir.mkdir()
        unwritable_dir.chmod(0o000)

        ledger_path = unwritable_dir / "ledger.db"
        try:
            with pytest.raises(LedgerError):
                ApprovalLedger(path=ledger_path)
        finally:
            unwritable_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# TestN8nExecutorEd25519Integration: Executor uses Ed25519
# ---------------------------------------------------------------------------


class TestN8nExecutorEd25519Integration:
    """Validate N8nExecutor.execute() uses Ed25519, not HMAC."""

    def test_execute_accepts_ed25519_approval(self, executor, verifier, signer):
        """executor.execute() accepts SignedApprovalEd25519."""
        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        approval = signer.sign(
            operation="workflow:activate",
            payload=payload,
            operator="test-operator",
        )

        with patch.object(executor, "_execute_http", return_value={"status": "active"}):
            result = executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
                signed_approval=approval,
            )

        assert result == {"status": "active"}

    def test_execute_rejects_legacy_approval(self, executor, verifier):
        """executor.execute() rejects legacy OperationApproval."""
        executor.set_approval_verifier(verifier)

        payload = {"workflow_id": "test-123"}
        from app.services.n8n_executor import OperationApproval

        legacy_approval = OperationApproval(
            operation=OperationType.WORKFLOW_ACTIVATE,
            content_hash=hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
            expires_at=time.time() + 300,
            operator="legacy-operator",
        )

        with pytest.raises(ExecutorApprovalRequiredError):
            executor.execute(
                operation=OperationType.WORKFLOW_ACTIVATE,
                payload=payload,
                approval=legacy_approval,
            )

    def test_read_only_no_approval_needed(self, executor, verifier):
        """Read-only operations don't need approval."""
        executor.set_approval_verifier(verifier)

        with patch.object(executor, "_execute_http", return_value=[]):
            result = executor.execute(operation=OperationType.WORKFLOW_LIST)

        assert result == []
