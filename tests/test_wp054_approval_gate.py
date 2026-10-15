"""WP-054: Approval gate and integrity journal tests.

These tests validate that the ApprovalGate provides REAL approval enforcement:
1. HMAC-SHA256 signatures cannot be forged without the secret
2. Expired approvals are rejected
3. Payload mismatch is detected
4. Operation mismatch is detected
5. IntegrityJournal chain detects tampering
6. Agent cannot create valid approvals without the secret

Unlike WP-053 tests which verified the executor blocks operations,
these tests verify the approval mechanism itself is unforgeable.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from app.services.approval_gate import (
    ApprovalGate,
    ApprovalExpiredError,
    ApprovalOperationMismatchError,
    ApprovalPayloadMismatchError,
    ApprovalSignatureError,
    IntegrityJournal,
    JournalEntry,
    SignedApproval,
)


# ---------------------------------------------------------------------------
# SignedApproval tests
# ---------------------------------------------------------------------------


class TestSignedApproval:
    """Test the SignedApproval dataclass."""

    def test_signed_approval_is_frozen(self):
        """SignedApproval should be immutable."""
        approval = SignedApproval(
            operation="workflow:activate",
            payload_hash="abc123",
            operator="human-admin",
            expires_at=time.time() + 300,
            signature="sig123",
        )
        with pytest.raises(Exception):
            approval.operation = "workflow:deactivate"  # type: ignore

    def test_to_signed_message_format(self):
        """The signed message should be deterministic JSON."""
        approval = SignedApproval(
            operation="workflow:activate",
            payload_hash="abc123",
            operator="human-admin",
            expires_at=1234567890.0,
            signature="sig123",
        )
        message = approval.to_signed_message()
        parsed = json.loads(message)
        assert parsed["operation"] == "workflow:activate"
        assert parsed["payload_hash"] == "abc123"
        assert parsed["operator"] == "human-admin"
        assert parsed["expires_at"] == 1234567890.0
        # Signature is NOT in the signed message — it's the output, not input

    def test_to_signed_message_is_sorted(self):
        """Keys should be sorted for deterministic signing."""
        approval = SignedApproval(
            operation="workflow:activate",
            payload_hash="abc123",
            operator="human-admin",
            expires_at=1234567890.0,
            signature="sig123",
        )
        message = approval.to_signed_message()
        # Keys should appear in alphabetical order
        keys = list(json.loads(message).keys())
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# ApprovalGate signature tests
# ---------------------------------------------------------------------------


class TestApprovalGateSignature:
    """Test HMAC signature creation and validation."""

    def test_valid_signature_passes(self):
        """A properly signed approval should validate."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "99999999-9999-4999-8999-999999999999"}
        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )
        result = gate.validate(approval, payload)
        assert result is True

    def test_forged_signature_fails(self):
        """An approval with a forged signature should be rejected."""
        gate = ApprovalGate(secret="real-secret")
        payload = {"workflow_id": "99999999-9999-4999-8999-999999999999"}

        # Agent tries to forge an approval with wrong secret
        fake_gate = ApprovalGate(secret="fake-secret")
        approval = fake_gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="imposter",
        )

        with pytest.raises(ApprovalSignatureError):
            gate.validate(approval, payload)

    def test_empty_signature_fails(self):
        """An approval with empty signature should be rejected."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}
        approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
            operator="human-admin",
            expires_at=time.time() + 300,
            signature="",
        )
        with pytest.raises(ApprovalSignatureError):
            gate.validate(approval, payload)

    def test_tampered_signature_fails(self):
        """A slightly modified signature should be rejected."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}
        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )
        # Tamper with the signature
        tampered_signature = "0" * len(approval.signature)
        tampered_approval = SignedApproval(
            operation=approval.operation,
            payload_hash=approval.payload_hash,
            operator=approval.operator,
            expires_at=approval.expires_at,
            signature=tampered_signature,
        )
        with pytest.raises(ApprovalSignatureError):
            gate.validate(tampered_approval, payload)

    def test_different_secret_rejects(self):
        """Approval signed with one secret should fail with different secret."""
        sign_gate = ApprovalGate(secret="secret-a")
        verify_gate = ApprovalGate(secret="secret-b")
        payload = {"workflow_id": "test"}
        approval = sign_gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )
        with pytest.raises(ApprovalSignatureError):
            verify_gate.validate(approval, payload)

    def test_agent_cannot_forge_without_secret(self):
        """Simulate agent trying to create approval without knowing the secret.

        This is the core test: the agent knows the payload and operation,
        but does NOT know the HMAC secret. It should not be able to create
        a valid approval.
        """
        real_secret = "secret-only-human-knows"
        gate = ApprovalGate(secret=real_secret)
        payload = {"workflow_id": "99999999-9999-4999-8999-999999999999"}

        # Agent computes the payload hash correctly
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        # Agent tries to create a SignedApproval with a fake signature
        # (it doesn't know the HMAC secret)
        forged_approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=payload_hash,
            operator="agent-pretending-to-be-human",
            expires_at=time.time() + 300,
            signature="agent-guessed-signature",
        )

        with pytest.raises(ApprovalSignatureError):
            gate.validate(forged_approval, payload)

    def test_agent_cannot_replay_old_approval(self):
        """An approval signed with the correct secret but for different payload
        should fail the payload hash check."""
        gate = ApprovalGate(secret="test-secret")
        original_payload = {"workflow_id": "original"}
        different_payload = {"workflow_id": "different"}

        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=original_payload,
            operator="human-admin",
        )

        # Agent tries to replay the approval with a different payload
        with pytest.raises(ApprovalPayloadMismatchError):
            gate.validate(approval, different_payload)


# ---------------------------------------------------------------------------
# Approval expiration tests
# ---------------------------------------------------------------------------


class TestApprovalExpiration:
    """Test approval expiration enforcement."""

    def test_expired_approval_fails(self):
        """An expired approval should be rejected."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}
        approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
            operator="human-admin",
            expires_at=time.time() - 60,  # Expired 1 minute ago
            signature="",  # Will fail signature first, but we test expiry
        )
        # Signature will fail first — create a valid signature for expired approval
        # We need to sign with the correct secret but set expired time
        import hmac as hmac_module

        message = json.dumps({
            "operation": "workflow:activate",
            "payload_hash": approval.payload_hash,
            "operator": "human-admin",
            "expires_at": approval.expires_at,
        }, sort_keys=True, default=str)
        signature = hmac_module.new(
            "test-secret".encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        expired_approval = SignedApproval(
            operation=approval.operation,
            payload_hash=approval.payload_hash,
            operator=approval.operator,
            expires_at=approval.expires_at,
            signature=signature,
        )

        with pytest.raises(ApprovalExpiredError):
            gate.validate(expired_approval, payload)

    def test_short_expiry_works_then_expires(self):
        """An approval with very short expiry should work immediately but expire quickly."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}
        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
            expires_in_seconds=0.1,  # 100ms expiry
        )
        # Should work immediately
        assert gate.validate(approval, payload) is True

        # Wait for expiry
        time.sleep(0.15)

        # Should fail after expiry
        with pytest.raises(ApprovalExpiredError):
            gate.validate(approval, payload)


# ---------------------------------------------------------------------------
# Payload and operation mismatch tests
# ---------------------------------------------------------------------------


class TestApprovalMismatch:
    """Test payload and operation mismatch detection."""

    def test_payload_mismatch_detected(self):
        """Different payload should be detected."""
        gate = ApprovalGate(secret="test-secret")
        original_payload = {"workflow_id": "original"}
        different_payload = {"workflow_id": "different"}

        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=original_payload,
            operator="human-admin",
        )

        with pytest.raises(ApprovalPayloadMismatchError) as exc_info:
            gate.validate(approval, different_payload)

        assert exc_info.value.expected == approval.payload_hash
        assert exc_info.value.actual != approval.payload_hash

    def test_operation_mismatch_detected(self):
        """Different operation should be detected."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"workflow_id": "test"}
        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )

        with pytest.raises(ApprovalOperationMismatchError) as exc_info:
            gate.validate_operation(approval, "workflow:deactivate")

        assert exc_info.value.approved == "workflow:activate"
        assert exc_info.value.requested == "workflow:deactivate"

    def test_same_payload_different_order_matches(self):
        """Payload with same content but different dict order should match
        because we use sort_keys=True."""
        gate = ApprovalGate(secret="test-secret")
        payload_a = {"b": 2, "a": 1}
        payload_b = {"a": 1, "b": 2}

        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload_a,
            operator="human-admin",
        )

        # Should match because sort_keys=True normalizes the order
        assert gate.validate(approval, payload_b) is True


# ---------------------------------------------------------------------------
# IntegrityJournal tests
# ---------------------------------------------------------------------------


class TestIntegrityJournal:
    """Test the tamper-evident journal with hash chain."""

    def test_empty_journal_is_valid(self):
        """An empty journal should have valid integrity."""
        journal = IntegrityJournal()
        assert journal.verify_integrity() is True

    def test_single_entry_is_valid(self):
        """A journal with one entry should have valid integrity."""
        journal = IntegrityJournal()
        journal.append(
            operation="workflow:activate",
            status="allowed",
            details="Test operation",
        )
        assert journal.verify_integrity() is True

    def test_chain_of_entries_is_valid(self):
        """A journal with multiple entries should have valid chain."""
        journal = IntegrityJournal()
        for i in range(5):
            journal.append(
                operation=f"operation-{i}",
                status="allowed",
                details=f"Test {i}",
            )
        assert journal.verify_integrity() is True

    def test_tampered_entry_detected(self):
        """Modifying an entry should break the chain."""
        journal = IntegrityJournal()
        journal.append(
            operation="workflow:activate",
            status="allowed",
            details="Original",
        )
        journal.append(
            operation="workflow:deactivate",
            status="allowed",
            details="Second",
        )
        assert journal.verify_integrity() is True

        # Tamper with the first entry
        entries = journal.get_entries()
        entries[0].details = "TAMPERED"

        # The chain should be broken because the hash of entry 0 changed,
        # but entry 1 still references the old hash
        journal.entries = entries
        assert journal.verify_integrity() is False

    def test_modified_previous_hash_detected(self):
        """Directly modifying previous_hash should be detected."""
        journal = IntegrityJournal()
        journal.append(
            operation="op-1",
            status="allowed",
            details="First",
        )
        journal.append(
            operation="op-2",
            status="allowed",
            details="Second",
        )
        assert journal.verify_integrity() is True

        # Modify the previous_hash of the second entry
        entries = journal.get_entries()
        entries[1].previous_hash = "0" * 64
        journal.entries = entries
        assert journal.verify_integrity() is False

    def test_modified_entry_hash_detected(self):
        """Directly modifying entry_hash should be detected."""
        journal = IntegrityJournal()
        journal.append(
            operation="op-1",
            status="allowed",
            details="First",
        )
        assert journal.verify_integrity() is True

        entries = journal.get_entries()
        entries[0].entry_hash = "0" * 64
        journal.entries = entries
        assert journal.verify_integrity() is False

    def test_persist_and_load_preserves_integrity(self, tmp_path: Path):
        """Persisting and loading journal should preserve integrity chain."""
        journal_path = tmp_path / "journal.json"
        journal = IntegrityJournal(path=journal_path)

        for i in range(3):
            journal.append(
                operation=f"op-{i}",
                status="allowed",
                details=f"Test {i}",
            )

        assert journal.verify_integrity() is True

        # Load from file
        loaded_journal = IntegrityJournal(path=journal_path)
        assert loaded_journal.verify_integrity() is True
        assert len(loaded_journal.get_entries()) == 3

    def test_tampered_file_detected(self, tmp_path: Path):
        """Tampering with the persisted journal file should be detected."""
        journal_path = tmp_path / "journal.json"
        journal = IntegrityJournal(path=journal_path)

        journal.append(
            operation="op-1",
            status="allowed",
            details="Original",
        )
        journal.append(
            operation="op-2",
            status="allowed",
            details="Second",
        )

        # Tamper with the file
        data = json.loads(journal_path.read_text())
        data[0]["details"] = "TAMPERED"
        journal_path.write_text(json.dumps(data, indent=2))

        # Load and verify — should detect tampering
        loaded_journal = IntegrityJournal(path=journal_path)
        assert loaded_journal.verify_integrity() is False

    def test_corrupted_file_starts_fresh(self, tmp_path: Path):
        """A corrupted journal file should start fresh."""
        journal_path = tmp_path / "journal.json"
        journal_path.write_text("not valid json")

        journal = IntegrityJournal(path=journal_path)
        assert len(journal.get_entries()) == 0

    def test_first_entry_has_empty_previous_hash(self):
        """The first entry should have an empty previous_hash."""
        journal = IntegrityJournal()
        journal.append(
            operation="op-1",
            status="allowed",
            details="First",
        )
        assert journal.entries[0].previous_hash == ""

    def test_subsequent_entries_chain_to_previous(self):
        """Each entry should chain to the previous entry's hash."""
        journal = IntegrityJournal()
        journal.append(
            operation="op-1",
            status="allowed",
            details="First",
        )
        journal.append(
            operation="op-2",
            status="allowed",
            details="Second",
        )
        assert journal.entries[1].previous_hash == journal.entries[0].entry_hash


# ---------------------------------------------------------------------------
# ApprovalGate journal integration tests
# ---------------------------------------------------------------------------


class TestApprovalGateJournal:
    """Test that ApprovalGate logs to the integrity journal."""

    def test_valid_approval_logs_to_journal(self):
        """A valid approval should create journal entries."""
        journal = IntegrityJournal()
        gate = ApprovalGate(secret="test-secret", journal=journal)
        payload = {"workflow_id": "test"}
        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )
        gate.validate(approval, payload)

        entries = journal.get_entries()
        # Should have at least 2 entries: creation + validation
        assert len(entries) >= 2
        assert journal.verify_integrity() is True

    def test_forged_approval_logs_to_journal(self):
        """A forged approval attempt should be logged."""
        journal = IntegrityJournal()
        gate = ApprovalGate(secret="real-secret", journal=journal)
        payload = {"workflow_id": "test"}

        forged_approval = SignedApproval(
            operation="workflow:activate",
            payload_hash=hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
            operator="imposter",
            expires_at=time.time() + 300,
            signature="fake-signature",
        )

        with pytest.raises(ApprovalSignatureError):
            gate.validate(forged_approval, payload)

        entries = journal.get_entries()
        assert any(e.status == "signature_invalid" for e in entries)
        assert journal.verify_integrity() is True

    def test_expired_approval_logs_to_journal(self):
        """An expired approval should be logged."""
        journal = IntegrityJournal()
        gate = ApprovalGate(secret="test-secret", journal=journal)
        payload = {"workflow_id": "test"}

        import hmac as hmac_module

        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        # Use a single expired timestamp for both message and approval
        expired_time = time.time() - 60
        message = json.dumps({
            "operation": "workflow:activate",
            "payload_hash": payload_hash,
            "operator": "human-admin",
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
            operator="human-admin",
            expires_at=expired_time,
            signature=signature,
        )

        with pytest.raises(ApprovalExpiredError):
            gate.validate(expired_approval, payload)

        entries = journal.get_entries()
        assert any(e.status == "approval_expired" for e in entries)


# ---------------------------------------------------------------------------
# ApprovalGate constructor tests
# ---------------------------------------------------------------------------


class TestApprovalGateConstructor:
    """Test ApprovalGate initialization."""

    def test_empty_secret_raises(self):
        """Empty secret should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            ApprovalGate(secret="")

    def test_none_secret_raises(self):
        """None-like secret should raise ValueError."""
        with pytest.raises(ValueError):
            ApprovalGate(secret="")

    def test_default_journal_created(self):
        """If no journal is provided, a default one should be created."""
        gate = ApprovalGate(secret="test-secret")
        assert gate.journal is not None
        assert isinstance(gate.journal, IntegrityJournal)


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestApprovalEdgeCases:
    """Test edge cases for approval validation."""

    def test_none_payload(self):
        """None payload should be handled correctly."""
        gate = ApprovalGate(secret="test-secret")
        approval = gate.sign_approval(
            operation="workflow:deactivate",
            payload=None,
            operator="human-admin",
        )
        assert gate.validate(approval, None) is True

    def test_complex_payload(self):
        """Complex nested payload should be handled correctly."""
        gate = ApprovalGate(secret="test-secret")
        payload = {
            "workflow_id": "99999999-9999-4999-8999-999999999999",
            "nodes": [
                {"name": "Webhook", "type": "webhook"},
                {"name": "Data Table", "type": "data-table"},
            ],
            "metadata": {
                "client": "client0",
                "environment": "test",
            },
        }
        approval = gate.sign_approval(
            operation="workflow:update",
            payload=payload,
            operator="human-admin",
        )
        assert gate.validate(approval, payload) is True

    def test_unicode_payload(self):
        """Unicode payload should be handled correctly."""
        gate = ApprovalGate(secret="test-secret")
        payload = {"message": "Olá, mundo! 🌍", "emoji": "✅"}
        approval = gate.sign_approval(
            operation="data-table:write",
            payload=payload,
            operator="human-admin",
        )
        assert gate.validate(approval, payload) is True

    def test_approval_persistence_journal(self, tmp_path: Path):
        """Journal should persist approval attempts."""
        journal_path = tmp_path / "approval_journal.json"
        journal = IntegrityJournal(path=journal_path)
        gate = ApprovalGate(secret="test-secret", journal=journal)

        payload = {"workflow_id": "test"}
        approval = gate.sign_approval(
            operation="workflow:activate",
            payload=payload,
            operator="human-admin",
        )
        gate.validate(approval, payload)

        # Verify file exists and is valid
        assert journal_path.exists()
        data = json.loads(journal_path.read_text())
        assert len(data) >= 2
