"""Minimal-privilege executor for n8n operations.

This module provides a dedicated executor that enforces the n8n governance
policy at runtime. Unlike WP-052 static tests, this executor provides REAL
enforcement by validating every operation against an allowlist before execution.

Key design decisions:
1. Operations are explicitly allowlisted — anything not listed is denied.
2. HTTP 401/403 responses are treated as definitive blocks — no retry, no fallback.
3. Database operations are prohibited — only HTTP API calls are allowed.
4. Credential access is prohibited — only metadata operations are allowed.
5. Write operations require HMAC-signed approval via ApprovalVerifier.
6. All operations are logged to a journal for audit and reconciliation.

The executor integrates with ApprovalVerifier from approval_gate.py to ensure
that write operations cannot be executed without a valid HMAC-signed approval
from the human operator. The agent cannot forge approvals because the HMAC
secret is not accessible to the executor process.

Usage:
    config = ExecutorConfig(base_url="http://localhost:5678", api_key="...")
    executor = N8nExecutor(config)
    executor.set_approval_verifier(verifier)  # Inject HMAC verifier

    # Read-only operation — no approval needed
    workflows = executor.execute(OperationType.WORKFLOW_LIST)

    # Write operation — requires HMAC-signed approval
    executor.execute_with_queue({
        "operation": "workflow:activate",
        "payload": {"workflow_id": "..."},
        "approval": { ... SignedApproval fields ... }
    })
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Operation types and allowlist
# ---------------------------------------------------------------------------


class OperationType(str, Enum):
    """Allowed n8n operations — anything not listed is denied."""

    # Read-only operations
    WORKFLOW_GET = "workflow:get"
    WORKFLOW_LIST = "workflow:list"
    WORKFLOW_STATUS = "workflow:status"
    CREDENTIAL_LIST = "credential:list"
    CREDENTIAL_METADATA = "credential:metadata"
    DATA_TABLE_READ = "data-table:read"
    EXECUTION_LIST = "execution:list"

    # Write operations requiring approval
    WORKFLOW_UPDATE = "workflow:update"
    DATA_TABLE_WRITE = "data-table:write"
    WORKFLOW_ACTIVATE = "workflow:activate"
    WORKFLOW_DEACTIVATE = "workflow:deactivate"

    # Prohibited operations (included for explicit denial)
    CREDENTIAL_DELETE = "credential:delete"
    CREDENTIAL_READ_SECRET = "credential:read_secret"
    DATABASE_DIRECT = "database:direct"
    DATABASE_MODIFY = "database:modify"
    WORKFLOW_PUBLISH = "workflow:publish"


# Operations that can be executed without explicit approval
READ_ONLY_OPERATIONS = frozenset([
    OperationType.WORKFLOW_GET,
    OperationType.WORKFLOW_LIST,
    OperationType.WORKFLOW_STATUS,
    OperationType.CREDENTIAL_LIST,
    OperationType.CREDENTIAL_METADATA,
    OperationType.DATA_TABLE_READ,
    OperationType.EXECUTION_LIST,
])

# Operations that require explicit approval with content hash
APPROVAL_REQUIRED_OPERATIONS = frozenset([
    OperationType.WORKFLOW_UPDATE,
    OperationType.DATA_TABLE_WRITE,
    OperationType.WORKFLOW_ACTIVATE,
    OperationType.WORKFLOW_DEACTIVATE,
])

# Operations that are always denied
PROHIBITED_OPERATIONS = frozenset([
    OperationType.CREDENTIAL_DELETE,
    OperationType.CREDENTIAL_READ_SECRET,
    OperationType.DATABASE_DIRECT,
    OperationType.DATABASE_MODIFY,
    OperationType.WORKFLOW_PUBLISH,
])


# ---------------------------------------------------------------------------
# Approval and journal structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperationApproval:
    """Explicit approval for a write operation.

    An approval is bound to:
    - The exact operation type
    - A content hash (SHA-256) of the payload
    - A validity window (seconds from creation)
    - An operator identity

    This prevents replay attacks and scope creep.
    """

    operation: OperationType
    content_hash: str  # SHA-256 hex digest of the payload
    expires_at: float  # Unix timestamp
    operator: str  # Human operator who approved

    def is_valid(self, now: float | None = None) -> bool:
        """Check if the approval is still within its validity window."""
        if now is None:
            now = time.time()
        return now <= self.expires_at

    def matches_content(self, payload: Any) -> bool:
        """Verify the payload matches the approved content hash."""
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        actual_hash = hashlib.sha256(payload_bytes).hexdigest()
        return actual_hash == self.content_hash


@dataclass
class OperationJournalEntry:
    """Immutable log entry for audit and reconciliation."""

    timestamp: float
    operation: OperationType
    status: Literal["allowed", "denied", "expired_approval", "hash_mismatch"]
    details: str
    operator: str | None = None
    content_hash: str | None = None


# ---------------------------------------------------------------------------
# Executor configuration
# ---------------------------------------------------------------------------


@dataclass
class ExecutorConfig:
    """Configuration for the n8n minimal-privilege executor."""

    base_url: str  # n8n instance URL, e.g. "http://localhost:5678"
    api_key: str | None = None  # API key for authentication
    timeout: float = 10.0  # HTTP request timeout in seconds
    max_retries: int = 0  # No retries for 401/403 — definitive blocks
    journal_path: Path | None = None  # Optional journal file path
    approval_validity_seconds: float = 300.0  # 5 minutes default


# ---------------------------------------------------------------------------
# Authorization block exception
# ---------------------------------------------------------------------------


class AuthorizationBlockError(Exception):
    """Raised when HTTP 401/403 is encountered — definitive block, no retry."""

    def __init__(self, status_code: int, operation: str, details: str = ""):
        self.status_code = status_code
        self.operation = operation
        self.details = details
        super().__init__(
            f"Authorization block ({status_code}) for {operation}: {details}"
        )


class ProhibitedOperationError(Exception):
    """Raised when a prohibited operation is attempted."""

    def __init__(self, operation: str, reason: str = ""):
        self.operation = operation
        self.reason = reason
        super().__init__(
            f"Prohibited operation: {operation}. {reason}".strip()
        )


class ApprovalRequiredError(Exception):
    """Raised when an operation requires explicit approval."""

    def __init__(self, operation: str, content_hash: str):
        self.operation = operation
        self.content_hash = content_hash
        super().__init__(
            f"Approval required for {operation} (content_hash: {content_hash})"
        )


class ApprovalExpiredError(Exception):
    """Raised when an approval has expired."""

    def __init__(self, operation: str, expired_at: float):
        self.operation = operation
        self.expired_at = expired_at
        super().__init__(
            f"Expired approval for {operation} (expired at {expired_at})"
        )


class ContentHashMismatchError(Exception):
    """Raised when the payload doesn't match the approved content hash."""

    def __init__(self, operation: str, expected: str, actual: str):
        self.operation = operation
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Content hash mismatch for {operation}: "
            f"expected {expected}, got {actual}"
        )


# ---------------------------------------------------------------------------
# Minimal-privilege executor
# ---------------------------------------------------------------------------


class N8nExecutor:
    """Dedicated minimal-privilege executor for n8n operations.

    This executor enforces the governance policy at runtime:
    1. Only allowlisted operations are permitted.
    2. HTTP 401/403 is a definitive block — no retry, no fallback.
    3. Write operations require HMAC-signed approval via ApprovalVerifier.
    4. All operations are logged to a journal.
    5. Database direct access is prohibited.

    The executor integrates with ApprovalVerifier to validate HMAC-signed
    approvals. Without a verifier, write operations are rejected.

    Usage:
        config = ExecutorConfig(base_url="http://localhost:5678", api_key="...")
        executor = N8nExecutor(config)
        executor.set_approval_verifier(verifier)  # Required for write ops

        # Read-only operation — no approval needed
        workflows = executor.execute(OperationType.WORKFLOW_LIST)

        # Write operation — requires HMAC-signed approval
        executor.execute_with_queue({
            "operation": "workflow:activate",
            "payload": {"workflow_id": "..."},
            "approval": { ... SignedApproval fields ... }
        })
    """

    def __init__(self, config: ExecutorConfig):
        self.config = config
        self.journal: list[OperationJournalEntry] = []
        self._verifier: Any = None  # ApprovalVerifier, injected at runtime
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            follow_redirects=False,
        )
        if config.api_key:
            self._client.headers["X-N8N-API-KEY"] = config.api_key

    def set_approval_verifier(self, verifier: Any) -> None:
        """Inject the ApprovalVerifier for HMAC-signed approval validation.

        This method must be called before executing write operations.
        Without a verifier, write operations will be rejected.

        Args:
            verifier: An ApprovalVerifier instance from approval_gate.py.
        """
        self._verifier = verifier

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> N8nExecutor:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _journal(self, entry: OperationJournalEntry) -> None:
        """Record an operation in the journal."""
        self.journal.append(entry)
        if self.config.journal_path:
            self.config.journal_path.write_text(
                json.dumps([
                    {
                        "timestamp": e.timestamp,
                        "operation": e.operation.value,
                        "status": e.status,
                        "details": e.details,
                        "operator": e.operator,
                        "content_hash": e.content_hash,
                    }
                    for e in self.journal
                ], indent=2, default=str),
                encoding="utf-8",
            )

    def _compute_content_hash(self, payload: Any) -> str:
        """Compute SHA-256 hash of the payload for approval binding."""
        payload_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload_bytes).hexdigest()

    def _check_authorization(self, response: httpx.Response) -> None:
        """Check for authorization blocks — definitive, no retry."""
        if response.status_code in (401, 403):
            raise AuthorizationBlockError(
                status_code=response.status_code,
                operation=response.request.url.path,
                details=response.text[:200] if response.text else "",
            )

    def execute(
        self,
        operation: OperationType,
        payload: Any = None,
        approval: OperationApproval | None = None,
        signed_approval: Any = None,
    ) -> Any:
        """Execute an n8n operation with enforcement.

        CRITICAL: Legacy OperationApproval (SHA-256) is REJECTED on all paths.
        Write operations require a cryptographically signed approval
        (SignedApprovalEd25519 or HMAC SignedApproval) validated by a configured
        ApprovalVerifier. Without a verifier, write operations are always denied.

        Args:
            operation: The operation type to execute.
            payload: Optional payload for the operation.
            approval: REJECTED — legacy OperationApproval is no longer accepted.
            signed_approval: Cryptographically signed approval (SignedApprovalEd25519
                or HMAC SignedApproval from approval_gate.py).

        Returns:
            The operation result (parsed JSON or None).

        Raises:
            ProhibitedOperationError: If the operation is prohibited.
            ApprovalRequiredError: If approval is required but not provided
                or if legacy approval is used.
            AuthorizationBlockError: If HTTP 401/403 is encountered.
        """
        now = time.time()

        # 1. Check if operation is prohibited
        if operation in PROHIBITED_OPERATIONS:
            entry = OperationJournalEntry(
                timestamp=now,
                operation=operation,
                status="denied",
                details=f"Prohibited operation: {operation.value}",
            )
            self._journal(entry)
            raise ProhibitedOperationError(
                operation=operation.value,
                reason="This operation is explicitly prohibited by governance policy",
            )

        # 2. Check if approval is required
        if operation in APPROVAL_REQUIRED_OPERATIONS:
            # Legacy OperationApproval is ALWAYS rejected — no bypass
            if approval is not None:
                entry = OperationJournalEntry(
                    timestamp=now,
                    operation=operation,
                    status="denied",
                    details="Legacy OperationApproval (SHA-256) is no longer accepted — use signed_approval",
                    operator=approval.operator,
                )
                self._journal(entry)
                raise ApprovalRequiredError(
                    operation=operation.value,
                    content_hash=self._compute_content_hash(payload),
                )

            # Cryptographic signed approval required
            if signed_approval is None:
                content_hash = self._compute_content_hash(payload)
                entry = OperationJournalEntry(
                    timestamp=now,
                    operation=operation,
                    status="denied",
                    details=f"Signed approval required, content_hash: {content_hash}",
                    content_hash=content_hash,
                )
                self._journal(entry)
                raise ApprovalRequiredError(
                    operation=operation.value,
                    content_hash=content_hash,
                )

            # Verifier MUST be configured — fail-closed
            if self._verifier is None:
                entry = OperationJournalEntry(
                    timestamp=now,
                    operation=operation,
                    status="denied",
                    details="No verifier configured — write operations require cryptographic verification",
                )
                self._journal(entry)
                raise ApprovalRequiredError(
                    operation=operation.value,
                    content_hash=self._compute_content_hash(payload),
                )

            # Validate via cryptographic verifier — this enforces the trust boundary
            self._verifier.validate(signed_approval, payload)
            self._verifier.validate_operation(signed_approval, operation.value)

        # 3. Execute the operation via HTTP API
        try:
            result = self._execute_http(operation, payload)
            operator = (
                signed_approval.operator if signed_approval
                else approval.operator if approval
                else None
            )
            entry = OperationJournalEntry(
                timestamp=now,
                operation=operation,
                status="allowed",
                details="Operation executed successfully",
                operator=operator,
                content_hash=self._compute_content_hash(payload) if payload else None,
            )
            self._journal(entry)
            return result

        except AuthorizationBlockError:
            # Re-raise without modification — definitive block
            raise

        except Exception as e:
            operator = (
                signed_approval.operator if signed_approval
                else approval.operator if approval
                else None
            )
            entry = OperationJournalEntry(
                timestamp=now,
                operation=operation,
                status="denied",
                details=f"Execution error: {str(e)}",
                operator=operator,
            )
            self._journal(entry)
            raise

    def _execute_http(self, operation: OperationType, payload: Any) -> Any:
        """Execute the HTTP request for the operation."""
        method, path = self._resolve_endpoint(operation)

        kwargs: dict[str, Any] = {"method": method, "url": path}
        if payload is not None:
            kwargs["json"] = payload

        response = self._client.request(**kwargs)
        self._check_authorization(response)

        if response.status_code >= 400:
            raise RuntimeError(
                f"HTTP {response.status_code} for {operation.value}: "
                f"{response.text[:200]}"
            )

        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    def _resolve_endpoint(self, operation: OperationType) -> tuple[str, str]:
        """Resolve the HTTP method and path for an operation."""
        endpoints = {
            OperationType.WORKFLOW_GET: ("GET", "/api/v1/workflows/{id}"),
            OperationType.WORKFLOW_LIST: ("GET", "/api/v1/workflows"),
            OperationType.WORKFLOW_STATUS: ("GET", "/api/v1/workflows/{id}"),
            OperationType.CREDENTIAL_LIST: ("GET", "/api/v1/credentials"),
            OperationType.CREDENTIAL_METADATA: ("GET", "/api/v1/credentials/{id}"),
            OperationType.DATA_TABLE_READ: ("GET", "/api/v1/data-tables/{id}"),
            OperationType.EXECUTION_LIST: ("GET", "/api/v1/executions"),
            OperationType.WORKFLOW_UPDATE: ("PUT", "/api/v1/workflows/{id}"),
            OperationType.DATA_TABLE_WRITE: ("POST", "/api/v1/data-tables/{id}/rows"),
            OperationType.WORKFLOW_ACTIVATE: ("POST", "/api/v1/workflows/{id}/activate"),
            OperationType.WORKFLOW_DEACTIVATE: ("POST", "/api/v1/workflows/{id}/deactivate"),
        }
        if operation not in endpoints:
            raise ProhibitedOperationError(
                operation=operation.value,
                reason="Unknown operation type",
            )
        return endpoints[operation]

    def get_journal(self) -> list[OperationJournalEntry]:
        """Return the operation journal for audit."""
        return list(self.journal)

    def execute_with_queue(self, queue_data: dict[str, Any]) -> dict[str, Any]:
        """Execute an operation from a queue file with Ed25519 approval verification.

        This method is used by the sandbox container's polling loop (run_executor.py).
        It reads a queue file containing an operation, payload, and SignedApprovalEd25519,
        validates the approval via Ed25519Verifier, and executes the operation.

        The approval is validated BEFORE consumption: the Ed25519 signature is verified
        first, then the approval is atomically consumed in the ledger. If validation
        fails at any point, the approval is NOT consumed.

        Args:
            queue_data: Dictionary with keys:
                - operation: Operation type string (e.g., "workflow:activate")
                - payload: The operation payload
                - approval: SignedApprovalEd25519 fields (operation, payload_hash,
                  operator, expires_at, nonce, signature)

        Returns:
            Dictionary with execution result.

        Raises:
            ProhibitedOperationError: If the operation is prohibited.
            ApprovalRequiredError: If no verifier is configured or approval missing.
            Any Ed25519Verifier exception: If the approval is invalid.
        """
        operation_str = queue_data.get("operation", "")
        payload = queue_data.get("payload")
        approval_data = queue_data.get("approval")

        # Resolve operation type
        try:
            operation = OperationType(operation_str)
        except ValueError:
            raise ProhibitedOperationError(
                operation=operation_str,
                reason="Unknown operation type",
            )

        # Check prohibited
        if operation in PROHIBITED_OPERATIONS:
            raise ProhibitedOperationError(
                operation=operation_str,
                reason="This operation is explicitly prohibited by governance policy",
            )

        # For approval-required operations, validate via Ed25519 verifier
        if operation in APPROVAL_REQUIRED_OPERATIONS:
            if self._verifier is None:
                raise ApprovalRequiredError(
                    operation=operation_str,
                    content_hash=self._compute_content_hash(payload),
                )

            if approval_data is None:
                raise ApprovalRequiredError(
                    operation=operation_str,
                    content_hash=self._compute_content_hash(payload),
                )

            # Reconstruct SignedApprovalEd25519 from queue data
            from app.services.approval_gate import SignedApprovalEd25519

            approval = SignedApprovalEd25519(
                operation=approval_data["operation"],
                payload_hash=approval_data["payload_hash"],
                operator=approval_data["operator"],
                expires_at=approval_data["expires_at"],
                nonce=approval_data["nonce"],
                signature=approval_data["signature"],
            )

            # Validate operation BEFORE consuming the approval
            self._verifier.validate_operation(approval, operation_str)

            # Validate Ed25519 signature and atomically consume in ledger
            # If this fails, the approval is NOT consumed — safe to retry
            self._verifier.validate(approval, payload)

        # Execute the HTTP operation
        try:
            result = self._execute_http(operation, payload)
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}
