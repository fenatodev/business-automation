"""In-memory rate limiter per company (WP-534).

Tracks API call counts per company within a time window to control
AI service usage costs.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimitEntry:
    count: int = 0
    window_start: float = field(default_factory=time.time)


class RateLimiter:
    """In-memory rate limiter keyed by company_id."""

    def __init__(self, default_limit: int = 100, window_seconds: int = 3600):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._limits: dict[int, int] = {}
        self._entries: dict[int, RateLimitEntry] = {}

    def set_limit(self, company_id: int, limit: int) -> None:
        """Set a custom rate limit for a company."""
        self._limits[company_id] = limit

    def get_limit(self, company_id: int) -> int:
        """Get the rate limit for a company."""
        return self._limits.get(company_id, self.default_limit)

    def check(self, company_id: int) -> bool:
        """Check if a company has remaining quota. Returns True if allowed."""
        now = time.time()
        limit = self.get_limit(company_id)

        entry = self._entries.get(company_id)
        if entry is None or (now - entry.window_start) >= self.window_seconds:
            self._entries[company_id] = RateLimitEntry(count=1, window_start=now)
            return True

        entry.count += 1
        return entry.count <= limit

    def remaining(self, company_id: int) -> int:
        """Get remaining quota for a company."""
        now = time.time()
        limit = self.get_limit(company_id)

        entry = self._entries.get(company_id)
        if entry is None or (now - entry.window_start) >= self.window_seconds:
            return limit

        return max(0, limit - entry.count)

    def reset_time(self, company_id: int) -> float:
        """Get seconds until the rate limit window resets."""
        entry = self._entries.get(company_id)
        if entry is None:
            return 0.0
        elapsed = time.time() - entry.window_start
        return max(0.0, self.window_seconds - elapsed)

    def status(self, company_id: int) -> dict:
        """Get full rate limit status for a company."""
        limit = self.get_limit(company_id)
        rem = self.remaining(company_id)
        return {
            "limit": limit,
            "remaining": rem,
            "used": limit - rem,
            "reset_in_seconds": self.reset_time(company_id),
            "window_seconds": self.window_seconds,
        }

    def reset(self, company_id: int) -> None:
        """Reset the rate limit for a company (admin only)."""
        self._entries.pop(company_id, None)


# Global rate limiter instance
rate_limiter = RateLimiter()
