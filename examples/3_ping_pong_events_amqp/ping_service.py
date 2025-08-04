"""Simple service which regularly emits an event."""

import logging
import threading
import time
from typing import ClassVar

from intersect_sdk import IntersectEventDefinition

from .service_runner import P_ngBaseCapabilityImplementation, run_service

logging.basicConfig(level=logging.INFO)
logging.getLogger('pika').setLevel(logging.WARNING)


class PingCapabilityImplementation(P_ngBaseCapabilityImplementation):
    """Basic capability definition, very similar to the other capability except for the type of event it emits."""

    intersect_sdk_capability_name = 'ping'
    intersect_sdk_events: ClassVar[dict[str, IntersectEventDefinition]] = {
        'ping': IntersectEventDefinition(event_type=str),
    }

    def after_service_startup(self) -> None:
        """Called after service startup."""
        self.counter_thread = threading.Thread(
            target=self.ping_event,
            daemon=True,
            name='counter_thread',
        )
        self.counter_thread.start()

    def ping_event(self) -> None:
        """Send out a ping event every 2 seconds."""
        while True:
            time.sleep(2.0)
            self.intersect_sdk_emit_event('ping', 'ping')


if __name__ == '__main__':
    run_service(PingCapabilityImplementation())
