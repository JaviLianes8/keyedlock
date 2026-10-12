"""Thread helpers shared by the test modules."""

from __future__ import annotations

import threading
from collections.abc import Callable


def run_threads(workers: list[Callable[[], None]], timeout: float = 30) -> None:
    """Run every worker on its own thread and fail if any is still running at the end."""
    errors: list[BaseException] = []

    def wrap(worker: Callable[[], None]) -> Callable[[], None]:
        def run() -> None:
            try:
                worker()
            except BaseException as error:
                errors.append(error)

        return run

    threads = [threading.Thread(target=wrap(worker), daemon=True) for worker in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=timeout)
    assert all(not thread.is_alive() for thread in threads), "a worker is stuck (deadlock?)"
    if errors:
        raise errors[0]
