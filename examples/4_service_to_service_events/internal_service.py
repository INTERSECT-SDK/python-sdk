"""Internal service.

This service periodically emits an 'internal_service_event' string, as an event.
The exposed service listens to the events of this service.
"""

import logging
import threading
import time
from typing import ClassVar

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectEventDefinition,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InternalServiceCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """Internal service capability."""

    intersect_sdk_capability_name = 'InternalServiceCapability'
    intersect_sdk_events: ClassVar[dict[str, IntersectEventDefinition]] = {
        'internal_service_event': IntersectEventDefinition(event_type=str),
    }

    def after_service_startup(self) -> None:
        """Called after service startup."""
        self.thread = threading.Thread(
            target=self.internal_service_event_generator, daemon=True, name='event_thread'
        )
        self.thread.start()

    def internal_service_event_generator(self) -> str:
        """Emits a periodic internal_service_event event."""
        while True:
            time.sleep(2.0)
            self.intersect_sdk_emit_event('internal_service_event', 'not_feeling_creative')


if __name__ == '__main__':
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 5672,
                'protocol': 'amqp0.9.1',
            },
        ],
    }
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='example-organization',
            facility='example-facility',
            system='example-system',
            subsystem='example-subsystem',
            service='internal-service',
        ),
        status_interval=30.0,
        **from_config_file,
    )
    capability = InternalServiceCapabilityImplementation()
    service = IntersectService([capability], config)
    logger.info('Starting Internal Service, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(
        service,
        post_startup_callback=capability.after_service_startup,
    )
