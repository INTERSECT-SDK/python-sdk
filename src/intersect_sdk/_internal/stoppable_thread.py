import threading
from typing import Any


class StoppableThread(threading.Thread):
    """Thread class which can stop and wait for execution."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def wait(self, amount: float) -> None:
        self._stop_event.wait(amount)
