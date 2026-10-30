"""Continuous supervisor for the internal task queue.

Wraps `internal_tasks.run_once()` in a polling loop with graceful shutdown
on SIGTERM/SIGINT and basic health statistics.
"""

import signal
import threading
from dataclasses import dataclass


@dataclass
class SupervisorStats:
    """Accumulated supervisor health metrics."""
    cycles: int = 0
    tasks_processed: int = 0
    errors: int = 0
    running: bool = False


_stop_event = threading.Event()


def _shutdown_handler(signum, frame):
    """Set the stop event on SIGTERM or SIGINT."""
    _stop_event.set()


def run_loop(
    session_factory,
    service_context: str,
    *,
    interval: float = 5.0,
    max_cycles: int | None = None,
) -> SupervisorStats:
    """Run the task queue loop until stopped or max_cycles reached.

    Args:
        session_factory: Callable that returns a DB session context manager
            (e.g., ``TestingSessionLocal`` from tests).
        service_context: Service description string passed to ``run_once()``.
        interval: Seconds to sleep between cycles when no task was processed.
        max_cycles: If set, stop after this many cycles (useful for tests).

    Returns:
        ``SupervisorStats`` with accumulated metrics.
    """
    from app.services import internal_tasks as tasks

    stats = SupervisorStats(running=True)
    old_sigterm = signal.getsignal(signal.SIGTERM)
    old_sigint = signal.getsignal(signal.SIGINT)

    try:
        signal.signal(signal.SIGTERM, _shutdown_handler)
        signal.signal(signal.SIGINT, _shutdown_handler)

        while not _stop_event.is_set():
            if max_cycles is not None and stats.cycles >= max_cycles:
                break

            processed = False
            try:
                processed = tasks.run_once(session_factory, service_context)
                stats.tasks_processed += int(processed)
            except Exception:
                stats.errors += 1

            stats.cycles += 1

            if not processed and not _stop_event.is_set():
                # Only sleep when idle; stop immediately when signaled
                _stop_event.wait(timeout=interval)

    finally:
        stats.running = False
        # Restore previous handlers
        signal.signal(signal.SIGTERM, old_sigterm)
        signal.signal(signal.SIGINT, old_sigint)

    return stats


def run(
    session_factory,
    service_context: str,
    *,
    interval: float = 5.0,
) -> SupervisorStats:
    """Block indefinitely, running the task queue loop.

    Stops only on SIGTERM or SIGINT.
    """
    return run_loop(session_factory, service_context, interval=interval)
