"""Cooperative cancellation for generation workers and their renderers."""

import subprocess
import threading
from contextlib import contextmanager


class TaskCancelled(BaseException):
    # Cancellation must bypass provider retries and renderer fallbacks.
    pass


_events: dict[str, threading.Event] = {}
_lock = threading.RLock()
_worker = threading.local()


def prepare(task_id):
    with _lock:
        return _events.setdefault(task_id, threading.Event())


def discard(task_id):
    with _lock:
        _events.pop(task_id, None)


def request(task_id):
    with _lock:
        event = _events.get(task_id)
        if event is None:
            return False
        event.set()
        return True


def requested(task_id):
    with _lock:
        event = _events.get(task_id)
        return event is not None and event.is_set()


def check():
    event = getattr(_worker, "event", None)
    if event is not None and event.is_set():
        raise TaskCancelled()


@contextmanager
def scope(task_id):
    previous = getattr(_worker, "event", None)
    _worker.event = prepare(task_id)
    try:
        check()
        yield
    finally:
        _worker.event = previous
        discard(task_id)


def run(command, **kwargs):
    """Like subprocess.run, but reap the render process on cancellation."""
    if getattr(_worker, "event", None) is None:
        return subprocess.run(command, **kwargs)
    check()
    kwargs.pop("check", None)
    if kwargs.pop("capture_output", False):
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with subprocess.Popen(command, **kwargs) as process:
        try:
            while True:
                check()
                try:
                    stdout, stderr = process.communicate(timeout=0.2)
                    check()
                    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
                except subprocess.TimeoutExpired:
                    continue
        except BaseException:
            process.terminate()
            try:
                process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
            raise


def moviepy_logger():
    from proglog import ProgressBarLogger

    class CancellationLogger(ProgressBarLogger):
        def callback(self, **changes):
            check()

        def bars_callback(self, bar, attr, value, old_value=None):
            check()

    return CancellationLogger()
