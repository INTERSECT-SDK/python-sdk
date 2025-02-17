"""Exposed service.

This service listens for events from the internal service, and then emits its own
'exposed_service_event' event. The client listens for the 'exposed_service_event'.
"""

import logging

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectEventDefinition,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_event,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExposedServiceCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """Exposed service capability."""

    intersect_sdk_capability_name = 'ExposedService'

    def on_service_startup(self) -> None:
        """This function will get called when starting up the Service.

        Note that while we could call this function earlier, we should not call this function in the constructor. The order of things which need to happen:

        1) Capability constructor is called
        2) Service constructor is called (which will include this capability)
        3) We can now start listening for events.

        Note that you do not have to explicitly start the Service, you only need to follow steps one and two.
        """
        self.intersect_sdk_listen_for_service_event(
            HierarchyConfig(
                organization='example-organization',
                facility='example-facility',
                system='example-system',
                subsystem='example-subsystem',
                service='internal-service',
            ),
            'internal_service_event',
            self.on_internal_service_event,
        )

    @intersect_event(events={'exposed_service_event': IntersectEventDefinition(event_type=str)})
    def on_internal_service_event(
        self, source: str, _operation: str, event_name: str, payload: str
    ) -> None:
        """When we get an event back from the internal_service, we will emit our own event."""
        self.intersect_sdk_emit_event(
            'exposed_service_event',
            f'From event "{event_name}", received message "{payload}" from "{source}"',
        )


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
            service='exposed-service',
        ),
        status_interval=30.0,
        **from_config_file,
    )
    capability = ExposedServiceCapabilityImplementation()
    service = IntersectService([capability], config)
    logger.info('Starting Service 1, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(service, post_startup_callback=capability.on_service_startup)
