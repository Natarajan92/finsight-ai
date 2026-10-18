"""Bound caller wait even when a transport keeps making slow I/O progress."""

from collections.abc import Callable
from contextvars import copy_context
from queue import Empty, Queue
from threading import BoundedSemaphore, Thread
from time import monotonic

from finsight.runtime.errors import FinsightError

_slots = BoundedSemaphore(16)


def bounded_call[T](send: Callable[[], T], timeout: float) -> T:
    """Late results have no consumer; accounting/cache mutation stays with the caller.

    Transport timeouts still apply. A timeout cannot prove remote cancellation, so
    the dispatcher retains unknown billing and never retries this result.
    """
    if timeout <= 0:
        raise TimeoutError()
    if not _slots.acquire(blocking=False):
        raise FinsightError("provider_capacity")
    deadline = monotonic() + timeout
    result = Queue(maxsize=1)
    inherited = copy_context()

    def worker():
        try:
            if monotonic() >= deadline:
                raise TimeoutError()
            value = inherited.run(send)
            result.put((True, value))
        except BaseException as error:
            result.put((False, error))
        finally:
            _slots.release()

    # A hung provider must not make CLI shutdown join a non-daemon executor.
    try:
        Thread(target=worker, name="finsight-provider", daemon=True).start()
    except BaseException:
        _slots.release()
        raise
    try:
        success, value = result.get(timeout=max(0, deadline - monotonic()))
    except Empty:
        raise TimeoutError() from None
    if monotonic() > deadline:
        raise TimeoutError()
    if not success:
        raise value
    return value
