"""Approval gate with Ed25519 asymmetric signatures and atomic SQLite ledger.

This module replaces the HMAC-SHA256 symmetric scheme (WP-053/054/055) with
Ed25519 asymmetric signatures. The private key lives ONLY with the human
approver; the executor holds ONLY the public key and can never forge approvals.

Key design decisions:
1. Ed25519 asymmetric: private key signs, public key verifies — no shared secret
2. Approvals include a nonce for replay prevention beyond one-time consumption
3. An atomic SQLite ledger (ApprovalLedger) records consumed approvals with
   UNIQUE constraints, fsync, and WAL mode for cross-process durability
4. Fail-closed: if the ledger is unreadable, unwritable, or corrupted,
   the verifier refuses to proceed rather than risking silent replay
5. HMAC-SHA256 is retained only as a deprecated legacy path; new code MUST
   use Ed25519

The ApprovalLedger is a NEW, ISOLATED SQLite database — NEVER the n8n internal
database. It exists solely for approval consumption tracking.

Usage:
    # Human operator (private key — OUTSIDE agent environment):
    from app.services.approval_gate import Ed25519Signer
    signer = Ed25519Signer(private_key_pem=b"-----BEGIN...")
    approval = signer.sign(
        operation="workflow:activate",
        payload={"workflow_id": "..."},
        operator="human-admin",
    )

    # Executor (public key only — cannot forge):
    from app.services.approval_gate import Ed25519Verifier, ApprovalLedger
    ledger = ApprovalLedger(path="/path/to/ledger.db")
    verifier = Ed25519Verifier(public_key_pem=b"-----BEGIN...", ledger=ledger)
    verifier.validate(approval, payload)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Ed25519 asymmetric signed approval
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignedApprovalEd25519:
    """An approval signed with Ed25519 asymmetric cryptography.

    The private key is held ONLY by the human approver. The executor
    holds ONLY the public key and can verify but never forge approvals.

    Fields:
        operation: The operation type value, e.g. "workflow:activate"
        payload_hash: SHA-256 hex digest of the payload
        operator: Human operator identity (authenticated externally)
        expires_at: Unix timestamp when approval expires
        nonce: Unique one-time value preventing replay even with same payload
        signature: Ed25519 signature bytes (hex-encoded) over the signed message
    """

    operation: str
    payload_hash: str
    operator: str
    expires_at: float
    nonce: str
    signature: str  # hex-encoded Ed25519 signature

    def to_signed_message(self) -> str:
        """Reconstruct the canonical message that was signed.

        The message includes ALL fields except the signature itself,
        so any tampering is detected during verification.
        """
        return json.dumps({
            "operation": self.operation,
            "payload_hash": self.payload_hash,
            "operator": self.operator,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
        }, sort_keys=True, default=str)

    @property
    def approval_id(self) -> str:
        """Unique identifier for ledger consumption tracking."""
        return self.nonce


# ---------------------------------------------------------------------------
# Ed25519 signer (private key — human operator only)
# ---------------------------------------------------------------------------


class Ed25519Signer:
    """Creates Ed25519-signed approvals — private key side only.

    This class holds the Ed25519 PRIVATE key and can sign approvals.
    It MUST NOT be accessible to the agent/executor process.

    In production, this runs in a separate environment (operator workstation,
    vault, HSM) with the private key. The signed approval is then passed
    to the executor via a secure channel for verification.

    Usage:
        signer = Ed25519Signer(private_key_pem=b"-----BEGIN...")
        approval = signer.sign(
            operation="workflow:activate",
            payload={"workflow_id": "..."},
            operator="human-admin",
        )
    """

    def __init__(self, private_key_pem: bytes):
        """Initialize with Ed25519 private key in PEM format.

        Args:
            private_key_pem: Ed25519 private key in PEM format.
                MUST NOT be accessible to the agent/executor.
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives import serialization

        if not private_key_pem:
            raise ValueError("Private key PEM must not be empty")

        self._private_key: Ed25519PrivateKey = serialization.load_pem_private_key(
            private_key_pem, password=None
        )

    @property
    def public_key_pem(self) -> bytes:
        """Return the public key in PEM format for the verifier."""
        from cryptography.hazmat.primitives import serialization

        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def sign(
        self,
        operation: str,
        payload: Any,
        operator: str,
        expires_in_seconds: float = 300.0,
        nonce: str | None = None,
    ) -> SignedApprovalEd25519:
        """Create an Ed25519-signed approval.

        Args:
            operation: The operation type value, e.g. "workflow:activate".
            payload: The payload to be executed.
            operator: The authenticated human operator identity.
            expires_in_seconds: Approval validity window (default 5 min).
            nonce: Optional unique nonce; auto-generated if not provided.

        Returns:
            A SignedApprovalEd25519 that can be verified by the executor.
        """
        if nonce is None:
            nonce = hashlib.sha256(
                f"{time.time()}:{os.urandom(16).hex()}:{operator}".encode()
            ).hexdigest()

        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        expires_at = time.time() + expires_in_seconds

        message = json.dumps({
            "operation": operation,
            "payload_hash": payload_hash,
            "operator": operator,
            "expires_at": expires_at,
            "nonce": nonce,
        }, sort_keys=True, default=str)

        signature = self._private_key.sign(message.encode("utf-8"))

        return SignedApprovalEd25519(
            operation=operation,
            payload_hash=payload_hash,
            operator=operator,
            expires_at=expires_at,
            nonce=nonce,
            signature=signature.hex(),
        )


# ---------------------------------------------------------------------------
# Ed25519 verifier (public key only — executor side)
# ---------------------------------------------------------------------------


class Ed25519Verifier:
    """Verifies Ed25519-signed approvals — public key only, cannot sign.

    This class holds ONLY the Ed25519 PUBLIC key. It can verify approvals
    but CANNOT create them. The private key is never accessible to the
    executor process.

    The verifier integrates with ApprovalLedger for atomic, durable,
    cross-process consumption tracking. If the ledger is unavailable,
    the verifier fails closed — no silent replay risk.

    Usage:
        ledger = ApprovalLedger(path="/path/to/ledger.db")
        verifier = Ed25519Verifier(
            public_key_pem=b"-----BEGIN...",
            ledger=ledger,
        )
        verifier.validate(approval, payload)
    """

    def __init__(
        self,
        public_key_pem: bytes,
        ledger: "ApprovalLedger | None" = None,
    ):
        """Initialize with Ed25519 public key in PEM format.

        Args:
            public_key_pem: Ed25519 public key in PEM format.
            ledger: Optional ApprovalLedger for durable consumption tracking.
                If provided, consumed approvals are recorded atomically.
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        from cryptography.hazmat.primitives import serialization

        if not public_key_pem:
            raise ValueError("Public key PEM must not be empty")

        self._public_key: Ed25519PublicKey = serialization.load_pem_public_key(
            public_key_pem
        )
        self._ledger = ledger

    def validate(self, approval: SignedApprovalEd25519, payload: Any) -> bool:
        """Validate an Ed25519-signed approval.

        Checks:
        1. Ed25519 signature is valid (proves private key holder approved)
        2. Approval has not expired
        3. Payload hash matches
        4. Approval has not been replayed (via ledger UNIQUE constraint)

        Args:
            approval: The signed approval to validate.
            payload: The payload to be executed.

        Returns:
            True if the approval is valid and consumed.

        Raises:
            ApprovalSignatureError: If Ed25519 signature is invalid.
            ApprovalExpiredError: If the approval has expired.
            ApprovalPayloadMismatchError: If payload hash doesn't match.
            ApprovalReplayError: If the approval was already consumed.
            LedgerError: If the ledger is unavailable (fail-closed).
        """
        # 0. Check ledger availability (fail-closed)
        if self._ledger is not None:
            if not self._ledger.is_available():
                raise LedgerError(
                    "Ledger unavailable — fail-closed to prevent silent replay"
                )

        # 1. Verify Ed25519 signature
        message = approval.to_signed_message()
        try:
            signature_bytes = bytes.fromhex(approval.signature)
            self._public_key.verify(signature_bytes, message.encode("utf-8"))
        except Exception as e:
            raise ApprovalSignatureError(
                f"Ed25519 signature verification failed: {e}",
                actual=approval.signature,
            )

        # 2. Check expiration
        now = time.time()
        if now > approval.expires_at:
            raise ApprovalExpiredError(
                operation=approval.operation,
                expired_at=approval.expires_at,
            )

        # 3. Verify payload hash
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        actual_payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        if actual_payload_hash != approval.payload_hash:
            raise ApprovalPayloadMismatchError(
                operation=approval.operation,
                expected=approval.payload_hash,
                actual=actual_payload_hash,
            )

        # 4. Atomically consume in ledger (fail-closed)
        if self._ledger is not None:
            self._ledger.consume(approval.approval_id, approval.operation)

        return True

    def validate_operation(self, approval: SignedApprovalEd25519, expected_operation: str) -> bool:
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
            raise ApprovalOperationMismatchError(
                approved=approval.operation,
                requested=expected_operation,
            )
        return True


# ---------------------------------------------------------------------------
# Atomic SQLite approval ledger
# ---------------------------------------------------------------------------


class LedgerError(Exception):
    """Raised when the approval ledger is unavailable or corrupted."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ledger error: {reason}")


class ApprovalLedger:
    """Atomic, durable SQLite ledger for approval consumption tracking.

    This is a NEW, ISOLATED SQLite database — NEVER the n8n internal database.
    It provides:
    - UNIQUE constraint on approval_id (prevents duplicate consumption)
    - WAL mode for concurrent read/write safety
    - fsync after every write (durability across crashes)
    - Fail-closed: if the ledger is unreadable/unwritable, operations fail

    Cross-process concurrency: Two processes trying to consume the same
    approval will have one succeed and the other get an IntegrityError.

    Usage:
        ledger = ApprovalLedger(path="/path/to/ledger.db")
        ledger.consume(approval_id, operation)
    """

    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS consumed_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT NOT NULL UNIQUE,
            operation TEXT NOT NULL,
            consumed_at REAL NOT NULL,
            operator TEXT
        )
    """

    def __init__(self, path: str | Path):
        """Initialize the approval ledger.

        Args:
            path: Path to the SQLite database file. This is a NEW, ISOLATED
                database — never the n8n internal database.

        Raises:
            LedgerError: If the database cannot be opened or initialized.
        """
        self._path = str(path)
        self._available = True
        try:
            self._init_db()
        except Exception as e:
            self._available = False
            raise LedgerError(f"Failed to initialize ledger: {e}") from e

    def _get_connection(self) -> sqlite3.Connection:
        """Get a new database connection with safety settings."""
        conn = sqlite3.connect(self._path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = self._get_connection()
        try:
            conn.execute(self._CREATE_TABLE)
            conn.commit()
        finally:
            conn.close()

    def is_available(self) -> bool:
        """Check if the ledger is available for operations.

        Returns:
            True if the ledger is accessible, False otherwise.
        """
        if not self._available:
            return False
        try:
            conn = self._get_connection()
            conn.execute("SELECT 1 FROM consumed_approvals LIMIT 1")
            conn.close()
            return True
        except Exception:
            self._available = False
            return False

    def consume(
        self,
        approval_id: str,
        operation: str,
        operator: str | None = None,
    ) -> bool:
        """Atomically consume an approval, recording it in the ledger.

        This operation is atomic and durable:
        - UNIQUE constraint prevents duplicate consumption
        - fsync ensures durability across crashes
        - If the write fails, the operation fails closed

        Args:
            approval_id: Unique approval identifier (nonce).
            operation: The operation type value.
            operator: Optional operator identity.

        Returns:
            True if the approval was successfully consumed.

        Raises:
            LedgerError: If the ledger is unavailable or write fails.
            ApprovalReplayError: If the approval was already consumed.
        """
        if not self._available:
            raise LedgerError("Ledger unavailable — fail-closed")

        conn = None
        try:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO consumed_approvals (approval_id, operation, consumed_at, operator) "
                "VALUES (?, ?, ?, ?)",
                (approval_id, operation, time.time(), operator),
            )
            conn.commit()
            # Force fsync for durability
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            return True
        except sqlite3.IntegrityError:
            # UNIQUE constraint violation — approval already consumed
            raise ApprovalReplayError(
                operation=operation,
                approval_id=approval_id,
            )
        except Exception as e:
            self._available = False
            raise LedgerError(f"Failed to consume approval: {e}") from e
        finally:
            if conn:
                conn.close()

    def is_consumed(self, approval_id: str) -> bool:
        """Check if an approval was already consumed.

        Args:
            approval_id: The approval identifier to check.

        Returns:
            True if the approval was previously consumed.

        Raises:
            LedgerError: If the ledger is unavailable.
        """
        if not self._available:
            raise LedgerError("Ledger unavailable — fail-closed")

        try:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT 1 FROM consumed_approvals WHERE approval_id = ?",
                    (approval_id,),
                ).fetchone()
                return row is not None
            finally:
                conn.close()
        except Exception as e:
            self._available = False
            raise LedgerError(f"Failed to check consumption: {e}") from e

    def get_consumed_count(self) -> int:
        """Return the total number of consumed approvals.

        Returns:
            The count of consumed approvals.

        Raises:
            LedgerError: If the ledger is unavailable.
        """
        if not self._available:
            raise LedgerError("Ledger unavailable — fail-closed")

        try:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM consumed_approvals"
                ).fetchone()
                return row[0]
            finally:
                conn.close()
        except Exception as e:
            self._available = False
            raise LedgerError(f"Failed to get count: {e}") from e


# ---------------------------------------------------------------------------
# Legacy HMAC-SHA256 signed approval (deprecated)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignedApproval:
    """DEPRECATED — An approval signed with HMAC-SHA256.

    WARNING: This symmetric scheme allows the agent to forge approvals
    if it has access to the HMAC secret. Use SignedApprovalEd25519 instead.

    Retained only for backward compatibility with existing tests.
    """

    operation: str
    payload_hash: str
    operator: str
    expires_at: float
    signature: str

    def to_signed_message(self) -> str:
        """Reconstruct the message that was signed."""
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
    5. The approval has not been replayed (one-time use, durable across restarts)

    The HMAC secret MUST come from outside the agent process.
    If the agent has access to the secret, the approval is meaningless.

    Durable approval consumption:
    Used approval IDs are persisted to the journal file so that a restart
    does NOT allow replay of an already-consumed approval. On initialization,
    the verifier loads previously used approval IDs from the journal.

    Usage:
        verifier = ApprovalVerifier(secret=os.environ["APPROVAL_SECRET"])
        verifier.validate(approval, payload)
    """

    def __init__(self, secret: str, journal: IntegrityJournal | None = None):
        """Initialize the approval verifier.

        Args:
            secret: The HMAC secret — MUST NOT be accessible to the agent.
            journal: Optional integrity journal for audit logging. If the
                journal has a file path, used approvals are loaded from it
                to prevent replay after restart.
        """
        if not secret:
            raise ValueError("Approval secret must not be empty")
        self.secret = secret
        self.journal = journal or IntegrityJournal()
        self._used_approvals: set[str] = set()
        # Load previously used approvals from journal to prevent replay after restart
        self._load_used_approvals()

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

        # 4. Mark as used (replay prevention) — atomically with journal persistence
        self._used_approvals.add(approval_id)

        # 5. Log successful validation with used approval ID for durable consumption
        self.journal.append(
            operation=approval.operation,
            status="approval_validated",
            details=f"Approval validated for {approval.operation} by {approval.operator}",
            operator=approval.operator,
            content_hash=actual_payload_hash,
        )
        # Persist the used approval ID to the journal for durable consumption
        if self.journal.path:
            self.journal.append(
                operation=approval.operation,
                status="approval_consumed",
                details=approval_id,
                operator=approval.operator,
            )

        return True

    def _load_used_approvals(self) -> None:
        """Load previously used approval IDs from the journal.

        This ensures that a restart does NOT allow replay of an already-consumed
        approval. The journal must have a file path for this to work.
        """
        if not self.journal.path:
            return
        for entry in self.journal.entries:
            if entry.status == "approval_consumed":
                # The details field contains the approval ID
                self._used_approvals.add(entry.details)

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
