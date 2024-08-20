"""First Service for example. Sends a message to service two and emits an event for the client."""

import logging

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectDirectMessageParams,
    IntersectEventDefinition,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_event,
    intersect_message,
    intersect_status,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleServiceOneCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """Service One Capability."""

    @intersect_status()
    def status(self) -> str:
        """Basic status function which returns a hard-coded string."""
        return 'Up'

    @intersect_message()
    def pass_text_to_service_2(self, text: str) -> None:
        """Takes in a string parameter and sends it to service 2."""
        logger.info('maing it to service one')
        msg_to_send = IntersectDirectMessageParams(
            destination='example-organization.example-facility.example-system.example-subsystem.service-two',
            operation='ServiceTwo.test_service',
            payload=text,
        )

        # Send intersect message to another service
        self.intersect_sdk_call_service(msg_to_send, self.service_2_handler)

    @intersect_event(events={'response_event': IntersectEventDefinition(event_type=str)})
    def service_2_handler(self, msg: str) -> None:
        """Handles response from service two and emites the response as an event for the client."""
        logger.info('maing it to right before emitting event')
        self.intersect_sdk_emit_event('response_event', f'Received Response from Service 2: {msg}')


if __name__ == '__main__':
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='example-organization',
            facility='example-facility',
            system='example-system',
            subsystem='example-subsystem',
            service='service-one',
        ),
        status_interval=30.0,
        **from_config_file,
    )
    capability = ExampleServiceOneCapabilityImplementation()
    capability.capability_name = 'ServiceOne'
    service = IntersectService([capability], config)
    logger.info('Starting service one, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(
        service,
    )
