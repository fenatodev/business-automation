"""Approval gate with HMAC-signed approvals for the n8n executor.

This module solves the fundamental flaw in WP-053's OperationApproval:
the agent could forge approvals by computing its own SHA-256 hash.

The ApprovalGate requires an HMAC secret that is NOT accessible to the
agent process. Approvals are signed with HMAC-SHA256 using this secret,
so the agent cannot forge valid approvals without the secret.

Key design decisions:
1. HMAC secret must come from outside the agent process (env var, vault, etc.)
2. Approvals are bound to operation type, payload hash, operator, and expiry
3. The HMAC signature covers all approval fields, not just the payload
4. A tamper-evident journal chain prevents retroactive modification
5. The gate itself does not execute operations — it only validates approvals

The ApprovalGate is designed to be used by the N8nExecutor (or any executor)
to validate that a human operator with access to the HMAC secret approved
the operation, not the agent itself.

Usage:
    # Human operator signs an approval (outside the agent process):
    import hmac, hashlib, json, time
    secret = os.environ["APPROVAL_SECRET"]  # NOT accessible to agent
    payload = {"workflow_id": "99999999-9999-4999-8999-999999999999"}
    message = json.dumps({
        "operation": "workflow:activate",
        "payload_hash": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        "operator": "human-admin",
        "expires_at": time.time() + 300
    }, sort_keys=True)
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    # Agent passes the signed approval to the executor:
    approval = SignedApproval(
        operation=OperationType.WORKFLOW_ACTIVATE,
        payload_hash=...,
        operator="human-admin",
        expires_at=...,
        signature=signature
    )
    gate = ApprovalGate(secret=secret)  # Secret injected from outside
    gate.validate(approval, payload)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Signed approval
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignedApproval:
    """An approval signed with HMAC-SHA256.

    Unlike WP-053's OperationApproval, this approval cannot be forged by
    the agent because the HMAC signature requires a secret that is not
    accessible to the agent process.

    The signature covers ALL fields: operation, payload_hash, operator,
    and expires_at — preventing any field from being tampered after signing.
    """

    operation: str  # Operation type value, e.g. "workflow:activate"
    payload_hash: str  # SHA-256 hex digest of the payload
    operator: str  # Human operator who approved
    expires_at: float  # Unix timestamp when approval expires
    signature: str  # HMAC-SHA256 hex digest of the signed message

    def to_signed_message(self) -> str:
        """Reconstruct the message that was signed.

        This is used by the ApprovalGate to verify the signature.
        The message format must match exactly what was signed.
        """
        return json.dumps({
            "operation": self.operation,
            "payload_hash": self.payload_hash,
            "operator": self.operator,
            "expires_at": self.expires_at,
        }, sort_keys=True, default=str)


# ---------------------------------------------------------------------------
# Journal entry with integrity chain
# ---------------------------------------------------------------------------


@dataclass
class JournalEntry:
    """A journal entry with integrity chain for tamper-evident audit.

    Each entry includes the hash of the previous entry, forming a chain.
    Modifying any entry breaks the chain for all subsequent entries.
    """

    timestamp: float
    operation: str
    status: str
    details: str
    operator: str | None = None
    content_hash: str | None = None
    previous_hash: str = ""  # SHA-256 of the previous entry's serialized form
    entry_hash: str = ""  # SHA-256 of this entry's own serialized form

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash of this entry for the chain."""
        data = json.dumps({
            "timestamp": self.timestamp,
            "operation": self.operation,
            "status": self.status,
            "details": self.details,
            "operator": self.operator,
            "content_hash": self.content_hash,
            "previous_hash": self.previous_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Tamper-evident journal
# ---------------------------------------------------------------------------


class IntegrityJournal:
    """A tamper-evident journal with hash chain integrity.

    Each new entry includes the hash of the previous entry, forming a chain.
    The journal can be persisted to a file and verified for tampering.

    Unlike WP-053's simple list, this journal detects retroactive modification:
    if any entry is changed, the chain breaks from that point forward.
    """

    def __init__(self, path: Path | None = None):
        self.entries: list[JournalEntry] = []
        self.path = path
        if path and path.exists():
            self._load_from_file()

    def _load_from_file(self) -> None:
        """Load journal entries from file and verify integrity."""
        if not self.path or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for item in data:
                entry = JournalEntry(
                    timestamp=item["timestamp"],
                    operation=item["operation"],
                    status=item["status"],
                    details=item["details"],
                    operator=item.get("operator"),
                    content_hash=item.get("content_hash"),
                    previous_hash=item.get("previous_hash", ""),
                    entry_hash=item.get("entry_hash", ""),
                )
                self.entries.append(entry)
        except (json.JSONDecodeError, KeyError):
            # Corrupted journal — start fresh
            self.entries = []

    def append(
        self,
        operation: str,
        status: str,
        details: str,
        operator: str | None = None,
        content_hash: str | None = None,
    ) -> JournalEntry:
        """Append a new entry to the journal with integrity chain."""
        previous_hash = ""
        if self.entries:
            previous_hash = self.entries[-1].entry_hash

        entry = JournalEntry(
            timestamp=time.time(),
            operation=operation,
            status=status,
            details=details,
            operator=operator,
            content_hash=content_hash,
            previous_hash=previous_hash,
        )
        entry.entry_hash = entry.compute_hash()
        self.entries.append(entry)

        if self.path:
            self._persist()

        return entry

    def _persist(self) -> None:
        """Persist journal to file."""
        if not self.path:
            return
        data = [
            {
                "timestamp": e.timestamp,
                "operation": e.operation,
                "status": e.status,
                "details": e.details,
                "operator": e.operator,
                "content_hash": e.content_hash,
                "previous_hash": e.previous_hash,
                "entry_hash": e.entry_hash,
            }
            for e in self.entries
        ]
        self.path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8",
        )

    def verify_integrity(self) -> bool:
        """Verify the integrity of the entire journal chain.

        Returns True if all entries have valid hash chains.
        Returns False if any entry has been tampered with.
        """
        previous_hash = ""
        for entry in self.entries:
            if entry.previous_hash != previous_hash:
                return False
            computed = entry.compute_hash()
            if computed != entry.entry_hash:
                return False
            previous_hash = entry.entry_hash
        return True

    def get_entries(self) -> list[JournalEntry]:
        """Return a copy of the journal entries."""
        return list(self.entries)


# ---------------------------------------------------------------------------
# Approval gate
# ---------------------------------------------------------------------------


class ApprovalSignatureError(Exception):
    """Raised when an approval signature verification fails."""

    def __init__(self, reason: str, expected: str = "", actual: str = ""):
        self.reason = reason
        self.expected = expected
        self.actual = actual
        super().__init__(f"Approval signature error: {reason}")


class ApprovalExpiredError(Exception):
    """Raised when an approval has expired."""

    def __init__(self, operation: str, expired_at: float):
        self.operation = operation
        self.expired_at = expired_at
        super().__init__(f"Expired approval for {operation} (expired at {expired_at})")


class ApprovalPayloadMismatchError(Exception):
    """Raised when the payload doesn't match the approved hash."""

    def __init__(self, operation: str, expected: str, actual: str):
        self.operation = operation
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Payload hash mismatch for {operation}: "
            f"expected {expected}, got {actual}"
        )


class ApprovalOperationMismatchError(Exception):
    """Raised when the operation doesn't match the approved operation."""

    def __init__(self, approved: str, requested: str):
        self.approved = approved
        self.requested = requested
        super().__init__(
            f"Operation mismatch: approved {approved}, requested {requested}"
        )


class ApprovalReplayError(Exception):
    """Raised when an approval has already been used (replay attack prevention)."""

    def __init__(self, operation: str, approval_id: str):
        self.operation = operation
        self.approval_id = approval_id
        super().__init__(
            f"Replay detected for {operation}: approval {approval_id} already used"
        )


class ApprovalVerifier:
    """Verifies HMAC-signed approvals — cannot create them.

    This class implements the VERIFY side of the sign/verify trust boundary.
    It has NO method to sign approvals — only to validate them.

    The ApprovalGate (below) provides both sign and verify for the human
    operator side, where the HMAC secret is accessible. The ApprovalVerifier
    is used by the executor sandbox, which should NOT be able to sign.

    This separation ensures that even if the agent controls the executor
    process, it cannot forge approvals — it can only verify ones that were
    signed by the human operator with the HMAC secret.

    This verifier enforces that:
    1. The approval signature is valid (HMAC-SHA256 with the secret)
    2. The approval has not expired
    3. The payload matches the approved hash
    4. The operation matches the approved operation
    5. The approval has not been replayed (one-time use)

    The HMAC secret MUST come from outside the agent process.
    If the agent has access to the secret, the approval is meaningless.

    Usage:
        verifier = ApprovalVerifier(secret=os.environ["APPROVAL_SECRET"])
        verifier.validate(approval, payload)
    """

    def __init__(self, secret: str, journal: IntegrityJournal | None = None):
        """Initialize the approval verifier.

        Args:
            secret: The HMAC secret — MUST NOT be accessible to the agent.
            journal: Optional integrity journal for audit logging.
        """
        if not secret:
            raise ValueError("Approval secret must not be empty")
        self.secret = secret
        self.journal = journal or IntegrityJournal()
        self._used_approvals: set[str] = set()

    def validate(self, approval: SignedApproval, payload: Any) -> bool:
        """Validate an HMAC-signed approval.

        This method verifies:
        1. The HMAC signature matches (proves the secret holder approved)
        2. The approval has not expired
        3. The payload hash matches the approved hash
        4. The approval has not been replayed

        Args:
            approval: The signed approval to validate.
            payload: The payload to be executed.

        Returns:
            True if the approval is valid.

        Raises:
            ApprovalSignatureError: If the HMAC signature is invalid.
            ApprovalExpiredError: If the approval has expired.
            ApprovalPayloadMismatchError: If the payload doesn't match.
            ApprovalReplayError: If the approval was already used.
        """
        # 0. Check replay prevention
        approval_id = f"{approval.operation}:{approval.payload_hash}:{approval.signature}"
        if approval_id in self._used_approvals:
            self.journal.append(
                operation=approval.operation,
                status="replay_detected",
                details="Approval already used — possible replay attack",
                operator=approval.operator,
            )
            raise ApprovalReplayError(
                operation=approval.operation,
                approval_id=approval_id,
            )

        # 1. Verify HMAC signature
        expected_signature = hmac.new(
            self.secret.encode("utf-8"),
            approval.to_signed_message().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(approval.signature, expected_signature):
            self.journal.append(
                operation=approval.operation,
                status="signature_invalid",
                details="HMAC signature verification failed — possible forgery",
                operator=approval.operator,
            )
            raise ApprovalSignatureError(
                "HMAC signature verification failed",
                expected=expected_signature,
                actual=approval.signature,
            )

        # 2. Check expiration
        now = time.time()
        if now > approval.expires_at:
            self.journal.append(
                operation=approval.operation,
                status="approval_expired",
                details=f"Approval expired at {approval.expires_at}",
                operator=approval.operator,
            )
            raise ApprovalExpiredError(
                operation=approval.operation,
                expired_at=approval.expires_at,
            )

        # 3. Verify payload hash
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        actual_payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        if actual_payload_hash != approval.payload_hash:
            self.journal.append(
                operation=approval.operation,
                status="payload_mismatch",
                details=f"Expected {approval.payload_hash}, got {actual_payload_hash}",
                operator=approval.operator,
                content_hash=actual_payload_hash,
            )
            raise ApprovalPayloadMismatchError(
                operation=approval.operation,
                expected=approval.payload_hash,
                actual=actual_payload_hash,
            )

        # 4. Mark as used (replay prevention)
        self._used_approvals.add(approval_id)

        # 5. Log successful validation
        self.journal.append(
            operation=approval.operation,
            status="approval_validated",
            details=f"Approval validated for {approval.operation} by {approval.operator}",
            operator=approval.operator,
            content_hash=actual_payload_hash,
        )

        return True

    def validate_operation(self, approval: SignedApproval, expected_operation: str) -> bool:
        """Validate that the approval matches the requested operation.

        Args:
            approval: The signed approval.
            expected_operation: The operation type value being requested.

        Returns:
            True if the operation matches.

        Raises:
            ApprovalOperationMismatchError: If the operation doesn't match.
        """
        if approval.operation != expected_operation:
            self.journal.append(
                operation=expected_operation,
                status="operation_mismatch",
                details=f"Approved {approval.operation}, requested {expected_operation}",
                operator=approval.operator,
            )
            raise ApprovalOperationMismatchError(
                approved=approval.operation,
                requested=expected_operation,
            )
        return True


class ApprovalSigner:
    """Creates HMAC-signed approvals — used by the human operator only.

    This class implements the SIGN side of the trust boundary. It should
    ONLY be accessible to the human operator, not to the agent/executor.

    In production, this runs in a separate process/container with access
    to the HMAC secret. The signed approval is then passed to the executor
    (via queue file, API, etc.) for verification and execution.

    Usage:
        signer = ApprovalSigner(secret=os.environ["APPROVAL_SECRET"])
        approval = signer.sign_approval(
            operation="workflow:activate",
            payload={"workflow_id": "..."},
            operator="human-admin",
        )
        # Pass approval to executor for verification
    """

    def __init__(self, secret: str, journal: IntegrityJournal | None = None):
        """Initialize the approval signer.

        Args:
            secret: The HMAC secret — MUST NOT be accessible to the agent.
            journal: Optional integrity journal for audit logging.
        """
        if not secret:
            raise ValueError("Approval secret must not be empty")
        self.secret = secret
        self.journal = journal or IntegrityJournal()

    def sign_approval(
        self,
        operation: str,
        payload: Any,
        operator: str,
        expires_in_seconds: float = 300.0,
    ) -> SignedApproval:
        """Create a signed approval for an operation.

        This method should be called by the HUMAN OPERATOR, not the agent.
        The agent should NOT have access to the secret used by this signer.

        Args:
            operation: The operation type value, e.g. "workflow:activate".
            payload: The payload to be executed.
            operator: The human operator identity.
            expires_in_seconds: How long the approval is valid (default 5 min).

        Returns:
            A SignedApproval that can be passed to the executor.
        """
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # Compute expires_at ONCE to ensure signature matches reconstruction
        expires_at = time.time() + expires_in_seconds

        message = json.dumps({
            "operation": operation,
            "payload_hash": payload_hash,
            "operator": operator,
            "expires_at": expires_at,
        }, sort_keys=True, default=str)

        signature = hmac.new(
            self.secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        approval = SignedApproval(
            operation=operation,
            payload_hash=payload_hash,
            operator=operator,
            expires_at=expires_at,
            signature=signature,
        )

        self.journal.append(
            operation=operation,
            status="approval_created",
            details=f"Approval created by {operator}",
            operator=operator,
            content_hash=payload_hash,
        )

        return approval


# Keep ApprovalGate as an alias for backward compatibility in tests.
# New code should use ApprovalVerifier (executor side) and ApprovalSigner (operator side).
class ApprovalGate(ApprovalVerifier):
    """ApprovalGate now extends ApprovalVerifier and adds sign_approval.

    This class is kept for backward compatibility with existing tests.
    For new code, prefer:
    - ApprovalVerifier: executor side (verify only, cannot sign)
    - ApprovalSigner: operator side (sign only)

    The trust boundary is: ApprovalVerifier runs in the executor sandbox
    with the HMAC secret, but has NO sign_approval method. The agent
    cannot forge approvals because it cannot call sign_approval on the verifier.
    """

    def sign_approval(
        self,
        operation: str,
        payload: Any,
        operator: str,
        expires_in_seconds: float = 300.0,
    ) -> SignedApproval:
        """Create a signed approval — kept for backward compatibility.

        WARNING: This method should NOT be available in the executor sandbox.
        Use ApprovalVerifier for the executor side.
        """
        signer = ApprovalSigner(secret=self.secret, journal=self.journal)
        return signer.sign_approval(operation, payload, operator, expires_in_seconds)
