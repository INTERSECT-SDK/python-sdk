"""Second Service for example."""

import logging

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_message,
    intersect_status,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleServiceTwoCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """Service 2 Capability."""

    intersect_sdk_capability_name = 'ServiceTwo'

    @intersect_status()
    def status(self) -> str:
        """Basic status function which returns a hard-coded string."""
        return 'Up'

    @intersect_message
    def test_service(self, text: str) -> str:
        """Returns the text given along with acknowledgement."""
        return f'Acknowledging service one text -> {text}'


if __name__ == '__main__':
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt5.0',
            },
        ],
    }
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='example-organization',
            facility='example-facility',
            system='example-system',
            subsystem='example-subsystem',
            service='service-two',
        ),
        status_interval=30.0,
        **from_config_file,
    )
    capability = ExampleServiceTwoCapabilityImplementation()
    service = IntersectService([capability], config)
    logger.info('Starting Service 2, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(
        service,
    )
