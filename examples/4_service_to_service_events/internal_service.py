"""Internal service.

This service periodically emits an 'internal_service_event' string, as an event.
The exposed service listens to the events of this service.
"""

import logging
import threading
import time

from intersect_sdk import (
    ControlPlaneConfig,
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectEventDefinition,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_event,
)
from intersect_sdk.config.shared import BrokerConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InternalServiceCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """Internal service capability."""

    intersect_sdk_capability_name = 'InternalService'

    def after_service_startup(self) -> None:
        """Called after service startup."""
        self.thread = threading.Thread(
            target=self.internal_service_event_generator, daemon=True, name='event_thread'
        )
        self.thread.start()

    @intersect_event(events={'internal_service_event': IntersectEventDefinition(event_type=str)})
    def internal_service_event_generator(self) -> str:
        """Emits a periodic internal_service_event event."""
        while True:
            time.sleep(2.0)
            self.intersect_sdk_emit_event('internal_service_event', 'not_feeling_creative')


if __name__ == '__main__':
    broker_configs = [
        {'host': 'localhost', 'port': 1883},
    ]

    brokers = [
        ControlPlaneConfig(
            protocol='mqtt3.1.1',
            username='intersect_username',
            password='intersect_password',
            brokers=[BrokerConfig(**broker) for broker in broker_configs],
        )
    ]
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='example-organization',
            facility='example-facility',
            system='example-system',
            subsystem='example-subsystem',
            service='internal-service',
        ),
        status_interval=30.0,
        brokers=brokers,
    )
    capability = InternalServiceCapabilityImplementation()
    service = IntersectService([capability], config)
    logger.info('Starting Service 2, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(
        service,
        post_startup_callback=capability.after_service_startup,
    )
